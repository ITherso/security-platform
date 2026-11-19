"""Explicit local reference snapshot: Phase42 task records and Phase43 disclosure records.

Both groups are loaded only from explicitly supplied paths and validated by
their existing owners: Phase42 through ``phase42_adapter.load_source`` and
Phase43 through the Phase43 ``inspect_task_exchange`` function plus the
Phase43 recipient reader. The snapshot is recorded metadata, not source
truth, producer proof or a second copy of either owner contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib

from exchange_contracts import (
    MAX_CAPSULE_BYTES, MAX_INDEX_BYTES, MAX_MANIFEST_BYTES, MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, SOURCE_NAMES,
    TASK_FIELDS, InputError, digest_id, exchange_counts, identifier, json_bytes, parse_json,
    sha256, task_id,
)
from portable_capsule import ZIP_NAMES
from reconciliation_contracts import (
    INPUT_ROLES, LocalReferenceMode, closed, digest, expect, fail, member, uses_phase42, uses_phase43,
)

PHASE42_ROLES = INPUT_ROLES[2:7]
PHASE43_ROLES = INPUT_ROLES[7:]
PHASE43_OUTPUT_NAMES = ("task-exchange-capsule.zip", "task-exchange-index.json",
                        "task-exchange-source-receipt.json", "task-exchange-summary.md", "manifest.json")
_PHASE43_LIMITS = (MAX_CAPSULE_BYTES, MAX_INDEX_BYTES, MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES)
_MAX_RECORD_BYTES = 128 * 1024
_RECORD_FIELDS = ("mode", "phase42", "phase43")
_P42_FIELDS = ("register_sha256", "manifest_sha256", "tasks", "inputs")
_P43_FIELDS = ("index_sha256", "capsule_sha256", "manifest_sha256", "capsule_members",
               "source_phase42_register_sha256", "source_phase42_manifest_sha256", "request_reference",
               "task_ids", "tasks", "inputs")


def _inputs(value: object, roles: tuple, code: str) -> list:
    if type(value) is not list or len(value) != len(roles):
        fail(code)
    for item, role in zip(value, roles):
        row = closed(item, ("role", "bytes", "sha256"), code + "_fields")
        expect(row["role"], role, code + "_role")
        if type(row["bytes"]) is not int or not 0 < row["bytes"] <= 1024 * 1024:
            fail(code + "_bytes")
        digest(row["sha256"], code + "_sha256")
    return value


def _phase42_task(value: object) -> None:
    row = closed(value, TASK_FIELDS, "local_phase42_task_fields")
    try:
        task_id(row["task_id"])
        digest_id(row["reference_id"], "rust-ref-", "local_reference_id")
        identifier(row["candidate_id"], "local_candidate_id")
        digest_id(row["file_id"], "candidate-file-", "local_file_id")
        sha256(row["binding_digest"], "local_binding_digest")
        identifier(row["slot_status"], "local_slot_status")
        identifier(row["response_status"], "local_response_status")
    except InputError:
        fail("local_phase42_task_value")
    for key in ("candidate_present", "observation_verified", "task_completed"):
        if type(row[key]) is not bool:
            fail("local_phase42_task_state")


def validate_local_record(value: object) -> dict:
    """Closed check of the in-memory snapshot (owner-validated when loaded from files)."""
    json_bytes(value, maximum=_MAX_RECORD_BYTES)
    row = closed(value, _RECORD_FIELDS, "local_record_fields")
    mode = member(row["mode"], LocalReferenceMode, "local_record_mode")
    if uses_phase42(mode):
        p42 = closed(row["phase42"], _P42_FIELDS, "local_phase42_fields")
        digest(p42["register_sha256"], "local_phase42_register")
        digest(p42["manifest_sha256"], "local_phase42_manifest")
        if type(p42["tasks"]) is not list or not 1 <= len(p42["tasks"]) <= 64:
            fail("local_phase42_tasks")
        for task in p42["tasks"]:
            _phase42_task(task)
        ids = [task["task_id"] for task in p42["tasks"]]
        digests = [task["binding_digest"] for task in p42["tasks"]]
        triples = [(t["reference_id"], t["candidate_id"], t["file_id"]) for t in p42["tasks"]]
        if len(set(ids)) != len(ids) or len(set(digests)) != len(digests) or len(set(triples)) != len(triples):
            fail("local_phase42_ambiguous_task_or_binding")
        _inputs(p42["inputs"], PHASE42_ROLES, "local_phase42_inputs")
        expect(p42["inputs"][0]["sha256"], p42["register_sha256"], "local_phase42_register_input")
        expect(p42["inputs"][4]["sha256"], p42["manifest_sha256"], "local_phase42_manifest_input")
    elif row["phase42"] is not None:
        fail("local_phase42_must_be_null")
    if uses_phase43(mode):
        p43 = closed(row["phase43"], _P43_FIELDS, "local_phase43_fields")
        for key in ("index_sha256", "capsule_sha256", "manifest_sha256",
                    "source_phase42_register_sha256", "source_phase42_manifest_sha256"):
            digest(p43[key], "local_phase43_digest")
        members = p43["capsule_members"]
        if type(members) is not list or len(members) != len(ZIP_NAMES):
            fail("local_phase43_capsule_members")
        for item, name in zip(members, ZIP_NAMES):
            entry = closed(item, ("name", "bytes", "sha256"), "local_phase43_member_fields")
            expect(entry["name"], name, "local_phase43_member_name")
            if type(entry["bytes"]) is not int or entry["bytes"] <= 0:
                fail("local_phase43_member_bytes")
            digest(entry["sha256"], "local_phase43_member_sha256")
        try:
            identifier(p43["request_reference"], "local_phase43_request_reference")
            exchange_counts(p43["tasks"])
        except InputError:
            fail("local_phase43_disclosed_tasks")
        expect(p43["task_ids"], [task["task_id"] for task in p43["tasks"]], "local_phase43_task_ids")
        _inputs(p43["inputs"], PHASE43_ROLES, "local_phase43_inputs")
        expect(p43["inputs"][0]["sha256"], p43["capsule_sha256"], "local_phase43_capsule_input")
        expect(p43["inputs"][1]["sha256"], p43["index_sha256"], "local_phase43_index_input")
        expect(p43["inputs"][4]["sha256"], p43["manifest_sha256"], "local_phase43_manifest_input")
    elif row["phase43"] is not None:
        fail("local_phase43_must_be_null")
    if mode == LocalReferenceMode.BOTH:
        # The two local groups must describe the same Phase42 source group.
        expect(row["phase43"]["source_phase42_register_sha256"], row["phase42"]["register_sha256"],
               "local_records_inconsistent_register")
        expect(row["phase43"]["source_phase42_manifest_sha256"], row["phase42"]["manifest_sha256"],
               "local_records_inconsistent_manifest")
    return row


@dataclass(frozen=True, slots=True, repr=False)
class LocalReference:
    """Immutable canonical bytes of one validated local reference snapshot."""

    canonical: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.canonical) is not bytes:
            fail("local_reference_bytes")
        record = validate_local_record(parse_json(self.canonical, maximum=_MAX_RECORD_BYTES))
        if json_bytes(record, maximum=_MAX_RECORD_BYTES) != self.canonical:
            fail("local_reference_not_canonical")

    def record(self) -> dict:
        return validate_local_record(parse_json(self.canonical, maximum=_MAX_RECORD_BYTES))

    @property
    def mode(self) -> str:
        return self.record()["mode"]


def make_local_reference(record: dict) -> LocalReference:
    return LocalReference(json_bytes(validate_local_record(record), maximum=_MAX_RECORD_BYTES))


def _load_phase42(paths: tuple, budget) -> dict:
    from phase42_adapter import load_source, read_source

    snapshot = load_source(*paths, budget)
    intake, classification, _receipt, artifacts = read_source(snapshot)
    classified = {item["task_id"]: item for item in classification["task_classifications"]}
    tasks = []
    for entry in intake["intake_entries"]:
        if entry["task_id"] not in classified:
            fail("local_phase42_classification_missing")
        state = classified[entry["task_id"]]
        tasks.append({
            "task_id": entry["task_id"], "reference_id": entry["reference_id"],
            "candidate_id": entry["candidate_id"], "file_id": entry["file_id"],
            "binding_digest": entry["binding_digest"], "slot_status": entry["slot_status"],
            "response_status": entry["response_status"], "candidate_present": entry["candidate_present"],
            "observation_verified": state["observation_verified"], "task_completed": state["task_completed"],
        })
    expect([item["name"] for item in artifacts], list(SOURCE_NAMES), "local_phase42_artifact_order")
    return {"register_sha256": artifacts[0]["sha256"], "manifest_sha256": artifacts[-1]["sha256"], "tasks": tasks,
            "inputs": [{"role": role, "bytes": item["bytes"], "sha256": item["sha256"]}
                       for role, item in zip(PHASE42_ROLES, artifacts)]}


def _load_phase43(paths: tuple, budget) -> dict:
    from inspect_task_exchange import inspect_task_exchange
    from recipient_reader import inspect_task_exchange_capsule, read_portable_task_request

    report = inspect_task_exchange(*paths)          # the unchanged Phase43 owner inspection
    raws = []
    for path, limit, name in zip(paths, _PHASE43_LIMITS, PHASE43_OUTPUT_NAMES):
        raw = budget.read_binary(path, limit) if name.endswith(".zip") else budget.read_text(path, limit)
        raws.append(raw)
    actual = [{"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
              for name, raw in zip(PHASE43_OUTPUT_NAMES, raws)]
    # The owner inspection read these paths itself; the bytes read here must be
    # the same bytes, otherwise a file changed between the two reads.
    expect(actual, report["task_exchange_artifacts"], "local_phase43_reread_identity")
    envelope, _contract, members = read_portable_task_request(inspect_task_exchange_capsule(raws[0]))
    expect(report["capsule_sha256"], actual[0]["sha256"], "local_phase43_capsule_identity")
    expect(report["task_ids"], [task["task_id"] for task in envelope["tasks"]], "local_phase43_task_ids")
    return {
        "index_sha256": actual[1]["sha256"], "capsule_sha256": actual[0]["sha256"],
        "manifest_sha256": actual[4]["sha256"],
        "capsule_members": [{"name": item["name"], "bytes": item["bytes"], "sha256": item["sha256"]} for item in members],
        "source_phase42_register_sha256": report["source_phase42_register_sha256"],
        "source_phase42_manifest_sha256": report["source_phase42_manifest_sha256"],
        "request_reference": report["request_reference"], "task_ids": list(report["task_ids"]),
        "tasks": envelope["tasks"],
        "inputs": [{"role": role, "bytes": item["bytes"], "sha256": item["sha256"]}
                   for role, item in zip(PHASE43_ROLES, actual)],
    }


def load_local_reference(request: dict, budget, phase42_paths: tuple | None,
                         phase43_paths: tuple | None) -> LocalReference:
    """Load exactly the groups the request names, from explicit paths only."""
    mode = request["local_reference_mode"]
    if (phase42_paths is not None) != uses_phase42(mode) or (phase43_paths is not None) != uses_phase43(mode):
        fail("local_path_groups_do_not_match_request_mode")
    record = {"mode": mode, "phase42": None, "phase43": None}
    if phase42_paths is not None:
        if len(phase42_paths) != len(SOURCE_NAMES):
            fail("local_phase42_paths")
        record["phase42"] = _load_phase42(phase42_paths, budget)
        expect(record["phase42"]["register_sha256"], request["expected_local_phase42_register_sha256"],
               "local_phase42_register_pin")
    if phase43_paths is not None:
        if len(phase43_paths) != len(PHASE43_OUTPUT_NAMES):
            fail("local_phase43_paths")
        record["phase43"] = _load_phase43(phase43_paths, budget)
        expect(record["phase43"]["index_sha256"], request["expected_local_phase43_index_sha256"],
               "local_phase43_index_pin")
    return make_local_reference(record)


__all__ = ("LocalReference", "PHASE42_ROLES", "PHASE43_ROLES", "PHASE43_OUTPUT_NAMES",
           "load_local_reference", "make_local_reference", "validate_local_record")
