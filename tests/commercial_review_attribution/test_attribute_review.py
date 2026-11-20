"""Phase17 -> 18 -> 19 -> attribution -> reconcile -> handoff, in a copied workspace.

The workspace follows the documented fixed layout: W/security-platform is a
real copy of the tracked repository files (plus the new attribution tool) and
W/outputs holds every output. Commands run from W with ``python -I -B`` exactly
as the tool READMEs document. The exported desk draft is synthetic and marks a
single committed sample observation for inclusion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from commercial_handoff.renderer import _html, _md  # noqa: E402
from commercial_handoff.review_rules import build_models  # noqa: E402
from commercial_handoff.schema import validate as validate_handoff  # noqa: E402
from commercial_review.decision_overlay import DECISION_CONTEXT_FIELDS, decision_context_digest  # noqa: E402

TOOL_DIR = "tools/commercial_review_attribution"
TOOL_FILES = ("__init__.py", "attribute_review.py", "README.md")
SP = "security-platform/tools"
REVIEWER = "analyst-07"
REVIEWED_AT = "2026-11-20T10:00:00Z"
SUMMARY = "Referrer-Policy header was not observed on the reviewed HTML response."
EMPTY_SELECTION = "kararlaştırılmış bir bulgu"
TRUST_FLAGS = ("human_review_verified", "producer_verified", "release_authorized")


class Workspace:
    def __init__(self, root: Path):
        self.root = root

    def run(self, script: str, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", "-B", f"{SP}/{script}", *args], cwd=self.root,
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)

    def ok(self, script: str, *args: str) -> subprocess.CompletedProcess:
        result = self.run(script, *args)
        assert result.returncode == 0, (script, result.returncode, result.stderr)
        return result

    def path(self, relative: str) -> Path:
        return self.root / relative

    def json(self, relative: str):
        return json.loads(self.path(relative).read_text(encoding="utf-8"))

    def text(self, relative: str) -> str:
        return self.path(relative).read_text(encoding="utf-8")

    def write_json(self, relative: str, value) -> None:
        target = self.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    def attribute(self, output: str, *, reviewer: str = REVIEWER, reviewed_at: str = REVIEWED_AT,
                  overlay: str = "outputs/phase19-finalized-overlay/decision-overlay.json",
                  overlay_manifest: str = "outputs/phase19-finalized-overlay/overlay-manifest.json"):
        return self.run("commercial_review_attribution/attribute_review.py", *PACKET_ARGS,
                        "--handoff-input", "outputs/phase17-intake/handoff-input.json",
                        "--overlay", overlay, "--overlay-manifest", overlay_manifest,
                        "--reviewer-ref", reviewer, "--reviewed-at", reviewed_at, "--output-dir", output)


PACKET_ARGS = ("--review-packet", "outputs/phase18-review-packet/review-packet.json",
               "--packet-manifest", "outputs/phase18-review-packet/review-packet-manifest.json")


def _copy_repository(target: Path) -> None:
    listed = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, timeout=60)
    if listed.returncode != 0:
        raise OSError("git ls-files failed")
    names = [name for name in listed.stdout.decode("utf-8").split("\0") if name]
    names += [f"{TOOL_DIR}/{name}" for name in TOOL_FILES]  # new, not yet tracked
    for name in dict.fromkeys(names):
        source = REPO / name
        if not source.is_file():
            continue  # tracked file absent from this working tree; not needed by the chain
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def _draft(ws: Workspace, decisions: list) -> dict:
    packet = ws.json("outputs/phase18-review-packet/review-packet.json")
    raw = ws.path("outputs/phase18-review-packet/review-packet.json").read_bytes()
    return {
        "schema_version": "termivar-analyst-decision-draft/v1",
        "review_packet_digest": hashlib.sha256(raw).hexdigest(),
        "source_assessment_digest": packet["source_assessment"]["sha256"],
        "decisions": decisions,
    }


def _finalize(ws: Workspace, draft: str, output: str) -> None:
    ws.ok("commercial_review_desk/finalize_desk.py", *PACKET_ARGS,
          "--handoff-input", "outputs/phase17-intake/handoff-input.json",
          "--decision-draft", draft, "--output-dir", output)


def _reconcile_and_build(ws: Workspace, overlay: str, reconciled: str, handoff: str) -> None:
    ws.ok("commercial_review/reconcile_review.py", *PACKET_ARGS,
          "--handoff-input", "outputs/phase17-intake/handoff-input.json",
          "--overlay", overlay, "--output-dir", reconciled)
    ws.ok("commercial_handoff/assemble.py", "--input", f"{reconciled}/handoff-input.json", "--output-dir", handoff)


@pytest.fixture(scope="module")
def ws(tmp_path_factory) -> Workspace:
    root = tmp_path_factory.mktemp("ws")
    try:
        _copy_repository(root / "security-platform")
    except (OSError, UnicodeError, subprocess.SubprocessError) as error:
        pytest.skip("repository copy failed: " + type(error).__name__)
    (root / "outputs").mkdir()
    space = Workspace(root)
    # Phase17 (tools/commercial_intake/README.md).
    space.ok("commercial_intake/assemble_intake.py",
             "--assessment", "security-platform/docs/commercial/examples/assessment.json",
             "--manifest", "security-platform/docs/commercial/examples/manifest.json",
             "--output-dir", "outputs/phase17-intake")
    # Phase18 (tools/commercial_review/README.md).
    space.ok("commercial_review/prepare_review.py",
             "--handoff-input", "outputs/phase17-intake/handoff-input.json",
             "--source-mapping", "outputs/phase17-intake/source-mapping.json",
             "--intake-manifest", "outputs/phase17-intake/intake-manifest.json",
             "--output-dir", "outputs/phase18-review-packet")
    # Phase19 (tools/commercial_review_desk/README.md).
    space.ok("commercial_review_desk/prepare_desk.py", *PACKET_ARGS,
             "--overlay-template", "outputs/phase18-review-packet/decision-overlay.template.json",
             "--output-dir", "outputs/phase19-review-desk")
    packet = space.json("outputs/phase18-review-packet/review-packet.json")
    first = packet["observations"][0]
    space.observation_id = first["observation_id"]
    space.write_json("outputs/phase19-exported/termivar-decision-draft.json", _draft(space, [{
        "observation_key": first["observation_key"], "review_status": "reviewed_for_delivery",
        "scope_status": "in_scope", "client_inclusion": "include_with_limits", "safe_summary": SUMMARY,
        "reason": "Analyst recorded header absence in the captured response.",
        "missing_evidence": None, "follow_up": None,
    }]))
    _finalize(space, "outputs/phase19-exported/termivar-decision-draft.json", "outputs/phase19-finalized-overlay")
    # Baseline without attribution: the desk overlay stays blocked.
    _reconcile_and_build(space, "outputs/phase19-finalized-overlay/decision-overlay.json",
                         "outputs/phase19-reconciled", "outputs/phase19-handoff")
    # New step, then the unchanged Phase18 reconcile and Phase16 builder.
    space.attribution = space.attribute("outputs/phase19-attributed-overlay")
    assert space.attribution.returncode == 0, space.attribution.stderr
    _reconcile_and_build(space, "outputs/phase19-attributed-overlay/decision-overlay.json",
                         "outputs/phase19-attributed-reconciled", "outputs/phase19-attributed-handoff")
    return space


def _blockers(ws: Workspace, reconciled: str) -> dict:
    internal, client = build_models(validate_handoff(ws.json(f"{reconciled}/handoff-input.json")))
    return {row.observation.observation_id: row.blockers for row in internal.observation_reviews}, client


MISSING = ("reviewer_reference_missing", "review_timestamp_missing")


def test_unattributed_desk_overlay_is_blocked(ws):
    blockers, client_model = _blockers(ws, "outputs/phase19-reconciled")
    assert blockers[ws.observation_id] == MISSING and client_model.selected_items == ()
    internal = ws.text("outputs/phase19-handoff/internal-review-summary.md")
    client = ws.text("outputs/phase19-handoff/client-handoff-draft.md")
    assert all(_md(code) in internal for code in MISSING)
    assert "Seçilmiş kayıt 1" not in client and _md(SUMMARY) not in client and EMPTY_SELECTION in client


def test_attributed_overlay_reaches_client_draft(ws):
    blockers, client_model = _blockers(ws, "outputs/phase19-attributed-reconciled")
    assert blockers[ws.observation_id] == ()
    assert [(item.observation_id, item.safe_summary) for item in client_model.selected_items] == [
        (ws.observation_id, SUMMARY)]
    assert client_model.incomplete_review is True
    internal = ws.text("outputs/phase19-attributed-handoff/internal-review-summary.md")
    client_md = ws.text("outputs/phase19-attributed-handoff/client-handoff-draft.md")
    client_html = ws.text("outputs/phase19-attributed-handoff/client-handoff-draft.html")
    assert not any(_md(code) in internal for code in MISSING)
    for client, escape in ((client_md, _md), (client_html, _html)):
        assert "Seçilmiş kayıt 1" in client and escape(SUMMARY) in client and escape(ws.observation_id) in client
        assert "Seçilmiş kayıt 2" not in client and escape(REVIEWER) not in client
    assert EMPTY_SELECTION not in client_md
    # The Phase16 trust and delivery guards are untouched by attribution.
    manifest = ws.json("outputs/phase19-attributed-handoff/manifest.json")
    assert (manifest["human_review_verified"], manifest["release_authorized"]) == (False, False)
    assert {"human_review_not_verified", "release_not_authorized"} <= set(manifest["delivery_blockers"])
    reconciled = ws.json("outputs/phase19-attributed-reconciled/reconciliation-manifest.json")
    for key in TRUST_FLAGS:
        assert reconciled[key] is False
    decision = ws.json("outputs/phase19-attributed-reconciled/handoff-input.json")["review_decisions"][0]
    assert (decision["reviewer_ref"], decision["reviewed_at"]) == (REVIEWER, REVIEWED_AT)


def test_attributed_overlay_changes_only_attribution_fields(ws):
    before = ws.json("outputs/phase19-finalized-overlay/decision-overlay.json")
    after = ws.json("outputs/phase19-attributed-overlay/decision-overlay.json")
    assert after["review_context"] == before["review_context"]
    for key in TRUST_FLAGS:
        assert after["review_context"][key] is False
    assert {k: v for k, v in after.items() if k != "decisions"} == {k: v for k, v in before.items() if k != "decisions"}
    assert len(after["decisions"]) == len(before["decisions"]) == 1
    old, new = before["decisions"][0], after["decisions"][0]
    assert (old["reviewer_ref"], old["reviewed_at"]) == (None, None)
    assert (new["reviewer_ref"], new["reviewed_at"]) == (REVIEWER, REVIEWED_AT)
    unchanged = DECISION_CONTEXT_FIELDS - {"reviewer_ref", "reviewed_at"}
    assert {k: new[k] for k in unchanged} == {k: old[k] for k in unchanged}
    assert new["decision_context_digest"] != old["decision_context_digest"]
    assert new["decision_context_digest"] == decision_context_digest({k: new[k] for k in DECISION_CONTEXT_FIELDS})


def test_attribution_manifest_is_closed_and_binds_bytes(ws):
    raw = ws.path("outputs/phase19-attributed-overlay/attribution-manifest.json").read_bytes()
    manifest = json.loads(raw)
    overlay = ws.path("outputs/phase19-attributed-overlay/decision-overlay.json").read_bytes()
    assert sorted(p.name for p in ws.path("outputs/phase19-attributed-overlay").iterdir()) == [
        "attribution-manifest.json", "decision-overlay.json"]
    assert manifest["schema_version"] == "termivar-review-attribution-manifest/v1"
    assert manifest["files"] == [{"name": "decision-overlay.json", "bytes": len(overlay),
                                  "sha256": hashlib.sha256(overlay).hexdigest()}]
    assert manifest["output_files"] == ["decision-overlay.json", "attribution-manifest.json"]
    for role, relative in (("review_packet", "outputs/phase18-review-packet/review-packet.json"),
                           ("packet_manifest", "outputs/phase18-review-packet/review-packet-manifest.json"),
                           ("handoff_input", "outputs/phase17-intake/handoff-input.json"),
                           ("overlay", "outputs/phase19-finalized-overlay/decision-overlay.json"),
                           ("overlay_manifest", "outputs/phase19-finalized-overlay/overlay-manifest.json")):
        data = ws.path(relative).read_bytes()
        assert manifest["inputs"][role] == {"sha256": hashlib.sha256(data).hexdigest(), "byte_length": len(data)}
    for key in TRUST_FLAGS + ("reviewer_identity_verified", "native_assessment_verified", "full_bundle_verified"):
        assert manifest[key] is False
    assert manifest["decision_count"] == 1 and manifest["attributed_fields"] == ["reviewer_ref", "reviewed_at"]
    # Reviewer text, review time and paths stay out of the manifest and stdout.
    for forbidden in (REVIEWER.encode(), REVIEWED_AT.encode(), b"outputs/", str(ws.root).encode()):
        assert forbidden not in raw
    assert REVIEWER not in ws.attribution.stdout and "human_review_verified=false" in ws.attribution.stdout


def test_attribution_is_deterministic(ws):
    result = ws.attribute("outputs/attr-repeat")
    assert result.returncode == 0, result.stderr
    for name in ("decision-overlay.json", "attribution-manifest.json"):
        assert (ws.path(f"outputs/attr-repeat/{name}").read_bytes()
                == ws.path(f"outputs/phase19-attributed-overlay/{name}").read_bytes())


def _rejected(ws: Workspace, result, code: str, output: str) -> None:
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert result.stderr == f"review_attribution: {code}\n"
    assert result.stdout == ""
    assert not ws.path(output).exists()


@pytest.mark.parametrize("reviewer", [
    "", " ", "x" * 129, "line\nbreak", "carriage\rreturn", "tab\there", " padded", "padded ",
    "bell\x07", "del\x7f", "c1\x85", "separator ", "zero​width",
])
def test_rejects_bad_reviewer_ref(ws, reviewer):
    _rejected(ws, ws.attribute("outputs/attr-bad-ref", reviewer=reviewer), "attribution_invalid_reviewer_ref",
              "outputs/attr-bad-ref")


@pytest.mark.parametrize("reviewer", ["not_provided", "NOT_VERIFIED", "pending_decision", "Not_Assigned"])
def test_rejects_placeholder_reviewer_ref(ws, reviewer):
    _rejected(ws, ws.attribute("outputs/attr-placeholder", reviewer=reviewer),
              "attribution_reviewer_ref_placeholder", "outputs/attr-placeholder")


def test_accepts_longest_reviewer_ref(ws):
    result = ws.attribute("outputs/attr-long-ref", reviewer="r" * 127 + "ş")
    assert result.returncode == 0, result.stderr
    decision = ws.json("outputs/attr-long-ref/decision-overlay.json")["decisions"][0]
    assert decision["reviewer_ref"] == "r" * 127 + "ş"


def test_markup_in_reviewer_ref_stays_internal_and_escaped(ws):
    hostile = "<script>alert(1)</script> [x](http://example.invalid) | `y`"
    result = ws.attribute("outputs/attr-markup", reviewer=hostile)
    assert result.returncode == 0, result.stderr
    _reconcile_and_build(ws, "outputs/attr-markup/decision-overlay.json",
                         "outputs/attr-markup-reconciled", "outputs/attr-markup-handoff")
    internal = ws.text("outputs/attr-markup-handoff/internal-review-summary.md")
    assert _md(hostile) in internal and "<script>" not in internal
    for name in ("client-handoff-draft.md", "client-handoff-draft.html"):
        client = ws.text(f"outputs/attr-markup-handoff/{name}")
        assert "Seçilmiş kayıt 1" in client and "script" not in client and "example.invalid" not in client


@pytest.mark.parametrize("reviewed_at", [
    "", "2026-11-20T10:00:00", "2026-11-20 10:00:00Z", "2026-11-20T10:00:00+00:00", "2026-11-20T10:00:00.5Z",
    "2026-02-30T10:00:00Z", "2026-11-20T25:00:00Z", "2026-11-20T10:60:00Z", "2026-13-01T10:00:00Z",
    "20261120T100000Z", "2026-11-20t10:00:00z", "２026-11-20T10:00:00Z", "2026-11-20T10:00:00Z\n",
])
def test_rejects_bad_review_time(ws, reviewed_at):
    _rejected(ws, ws.attribute("outputs/attr-bad-time", reviewed_at=reviewed_at), "attribution_invalid_review_time",
              "outputs/attr-bad-time")


def test_rejects_existing_output(ws):
    ws.path("outputs/attr-existing-empty").mkdir()
    result = ws.attribute("outputs/attr-existing-empty")
    assert (result.returncode, result.stderr) == (2, "review_attribution: output_directory_must_be_new\n")
    assert list(ws.path("outputs/attr-existing-empty").iterdir()) == []
    before = ws.path("outputs/phase19-attributed-overlay/decision-overlay.json").read_bytes()
    result = ws.attribute("outputs/phase19-attributed-overlay")
    assert (result.returncode, result.stderr) == (2, "review_attribution: output_directory_must_be_new\n")
    assert ws.path("outputs/phase19-attributed-overlay/decision-overlay.json").read_bytes() == before
    ws.path("outputs/attr-existing-file").write_bytes(b"x")
    result = ws.attribute("outputs/attr-existing-file")
    assert (result.returncode, result.stderr) == (2, "review_attribution: output_directory_must_be_new\n")


def test_rejects_absolute_or_parent_paths(ws):
    absolute = str(ws.path("outputs/attr-absolute"))
    result = ws.attribute(absolute)
    assert result.returncode == 2 and result.stderr.startswith("review_attribution: ")
    assert absolute not in result.stderr and not ws.path("outputs/attr-absolute").exists()
    result = ws.attribute("outputs/attr-parent", overlay="outputs/../outputs/phase19-finalized-overlay/decision-overlay.json")
    assert result.returncode == 2 and "outputs" not in result.stderr.removeprefix("review_attribution: ")
    assert not ws.path("outputs/attr-parent").exists()


def test_refuses_to_overwrite_prior_attribution(ws):
    result = ws.attribute("outputs/attr-twice", overlay="outputs/phase19-attributed-overlay/decision-overlay.json")
    _rejected(ws, result, "attribution_already_present", "outputs/attr-twice")
    result = ws.attribute("outputs/attr-twice", overlay="outputs/phase19-attributed-overlay/decision-overlay.json",
                          overlay_manifest="outputs/phase19-attributed-overlay/attribution-manifest.json")
    _rejected(ws, result, "attribution_already_present", "outputs/attr-twice")


def test_rejects_tampered_or_mismatched_overlay(ws):
    overlay = ws.json("outputs/phase19-finalized-overlay/decision-overlay.json")
    overlay["decisions"][0]["safe_summary"] = "Changed after finalization."
    ws.write_json("outputs/neg/tampered-overlay.json", overlay)
    _rejected(ws, ws.attribute("outputs/attr-tampered", overlay="outputs/neg/tampered-overlay.json"),
              "decision_context_digest_mismatch", "outputs/attr-tampered")
    # Same content, different bytes: no longer the finalize_desk rendering.
    compact = ws.json("outputs/phase19-finalized-overlay/decision-overlay.json")
    ws.path("outputs/neg/compact-overlay.json").write_bytes(json.dumps(compact, ensure_ascii=False).encode("utf-8"))
    _rejected(ws, ws.attribute("outputs/attr-compact", overlay="outputs/neg/compact-overlay.json"),
              "attribution_overlay_not_canonical", "outputs/attr-compact")
    manifest = ws.json("outputs/phase19-finalized-overlay/overlay-manifest.json")
    manifest["human_review_verified"] = True
    ws.write_json("outputs/neg/trusted-manifest.json", manifest)
    _rejected(ws, ws.attribute("outputs/attr-trusted", overlay_manifest="outputs/neg/trusted-manifest.json"),
              "attribution_overlay_manifest_mismatch", "outputs/attr-trusted")
    manifest = ws.json("outputs/phase19-finalized-overlay/overlay-manifest.json")
    manifest["inputs"]["handoff_input"]["sha256"] = "0" * 64
    ws.write_json("outputs/neg/input-manifest.json", manifest)
    _rejected(ws, ws.attribute("outputs/attr-input", overlay_manifest="outputs/neg/input-manifest.json"),
              "attribution_overlay_manifest_input_mismatch", "outputs/attr-input")
    manifest = ws.json("outputs/phase19-finalized-overlay/overlay-manifest.json")
    manifest["extra"] = True
    ws.write_json("outputs/neg/extra-manifest.json", manifest)
    _rejected(ws, ws.attribute("outputs/attr-extra", overlay_manifest="outputs/neg/extra-manifest.json"),
              "attribution_overlay_manifest_fields", "outputs/attr-extra")


def test_rejects_overlay_without_decisions(ws):
    ws.write_json("outputs/neg/empty-draft.json", _draft(ws, []))
    _finalize(ws, "outputs/neg/empty-draft.json", "outputs/neg/empty-finalized")
    result = ws.attribute("outputs/attr-empty", overlay="outputs/neg/empty-finalized/decision-overlay.json",
                          overlay_manifest="outputs/neg/empty-finalized/overlay-manifest.json")
    _rejected(ws, result, "attribution_requires_decisions", "outputs/attr-empty")


def test_rejects_missing_arguments(ws):
    result = ws.run("commercial_review_attribution/attribute_review.py", *PACKET_ARGS,
                    "--output-dir", "outputs/attr-missing")
    assert (result.returncode, result.stderr) == (2, "review_attribution: invalid_arguments\n")
    assert not ws.path("outputs/attr-missing").exists()
