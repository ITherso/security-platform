"""Regressions for issues found by the adversarial review: hostile inputs must
still yield a rejection report, and the inspector must not reject honest
outputs because capsule-supplied text resembles local identities."""
from __future__ import annotations

from argparse import Namespace
import json
import struct

import pytest

from exchange_contracts import InputError, json_bytes
from portable_capsule import ZIP_NAMES
from synthetic_fixtures import (
    canonical_capsule, canonical_members, local, phase42_record, raw_zip, rehash_manifest, request,
    synthetic_envelope, synthetic_task, zip_members,
)
import inspect_task_reconciliation
from reconciliation_contracts import MAX_FINDINGS
from reconciliation_engine import reconcile_capsule
from reconciliation_inputs import LoadedInputs
from reconciliation_manifest import input_identities, output_documents


def rules(report: dict) -> set:
    return {item["rule"] for item in report["findings"]}


def test_finding_flood_from_duplicated_names_still_yields_rejection_report():
    members = canonical_members()
    entries = [(n, members[n]) for n in ZIP_NAMES]
    for index in range(450):
        entries += [("d%04d" % index, b"x"), ("d%04d" % index, b"x")]
    capsule = raw_zip(entries)
    assert len(capsule) <= 128 * 1024
    report, inbox = reconcile_capsule(capsule, request(), local())
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    assert len(report["findings"]) <= MAX_FINDINGS
    assert "P44-MEMBER_DUPLICATE:unlisted_members" in {f["finding_id"] for f in report["findings"]}
    assert inbox["admitted_tasks"] == []


def _set_zip64_size(raw: bytes, name: bytes, size: int) -> bytes:
    """Patch one central-directory entry to 0xFFFFFFFF sizes plus a ZIP64 extra."""
    data = bytearray(raw)
    index = data.find(b"PK\x01\x02")
    while index != -1:
        name_length, extra_length = struct.unpack_from("<HH", data, index + 28)
        if bytes(data[index + 46:index + 46 + name_length]) == name and extra_length == 0:
            struct.pack_into("<II", data, index + 20, 0xFFFFFFFF, 0xFFFFFFFF)
            extra = struct.pack("<HHQQ", 0x0001, 16, size, size)
            struct.pack_into("<H", data, index + 30, len(extra))
            data[index + 46 + name_length:index + 46 + name_length] = extra
            end = data.rfind(b"PK\x05\x06")
            cd_size, = struct.unpack_from("<I", data, end + 12)
            struct.pack_into("<I", data, end + 12, cd_size + len(extra))
            return bytes(data)
        index = data.find(b"PK\x01\x02", index + 4)
    raise AssertionError("entry not found")


@pytest.mark.parametrize("size", [2**31 + 5, 2**53 - 1, 2**53, 2**64 - 1])
def test_zip64_extra_with_huge_declared_size_still_yields_rejection_report(size):
    capsule = _set_zip64_size(canonical_capsule(), b"task-request.json", size)
    report, inbox = reconcile_capsule(capsule, request(), local())
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    if report["archive"]["archive_state"] == "READABLE":
        assert "MEMBER_ZIP64_OR_EXTRA_FIELD" in rules(report)
        record = report["members"][0]
        assert record["declared_size"] in (None, size)
    json_bytes(report, maximum=512 * 1024)


@pytest.mark.parametrize("value", [2**31 + 1, 2**53 - 1])
def test_large_declared_integers_still_yield_rejection_report(value):
    envelope = synthetic_envelope()
    envelope["counts"] = dict(envelope["counts"], selected_task_count=value)
    members = rehash_manifest(dict(canonical_members(), **{"task-request.json": json_bytes(envelope)}))
    report, _ = reconcile_capsule(zip_members(members), request(), local())
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    assert report["task_declaration"]["declared_task_count"] == value
    members = canonical_members()
    manifest = json.loads(members["capsule-manifest.json"])
    manifest["files"][2]["bytes"] = value
    tampered = dict(members, **{"capsule-manifest.json": json_bytes(manifest)})
    report, _ = reconcile_capsule(zip_members(tampered), request(), local())
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    assert "MANIFEST_HASH_MISMATCH" in rules(report)


def test_crc_failure_is_reported_as_read_error_content_state():
    raw = bytearray(canonical_capsule())
    raw[raw.find(b"OFFLINE TASK REQUEST ONLY")] ^= 0x20
    report, _ = reconcile_capsule(bytes(raw), request(), local())
    states = {item["name"]: item["content_state"] for item in report["member_contents"]}
    assert states["README.txt"] == "READ_ERROR"
    assert report["archive"]["container_verdict"] == "REJECTED"


class _StableBudget:
    def check_stability(self) -> None:
        return None


def _inspect_in_memory(tmp_path, monkeypatch, capsule: bytes, req: dict, snapshot) -> dict:
    monkeypatch.chdir(tmp_path)
    request_raw = json_bytes(req)
    report, inbox = reconcile_capsule(capsule, req, snapshot)
    documents = output_documents(report, inbox, input_identities(capsule, request_raw, snapshot))
    (tmp_path / "out").mkdir()
    for name, raw in documents.items():
        (tmp_path / "out" / name).write_bytes(raw)
    monkeypatch.setattr(inspect_task_reconciliation, "load_inputs",
                        lambda _args: LoadedInputs(capsule, request_raw, req, snapshot, _StableBudget()))
    names = list(documents)
    args = Namespace(inbox="out/" + names[0], report="out/" + names[1], summary="out/" + names[2],
                     manifest="out/" + names[3])
    return inspect_task_reconciliation.inspect_task_reconciliation(args)


def test_inspector_accepts_capsule_text_resembling_unclaimed_local_ids(tmp_path, monkeypatch):
    unclaimed = synthetic_task("F0009", "SYNTH0002", "b")
    p42 = phase42_record([synthetic_task("F0007"), unclaimed])
    snapshot = local("PHASE42_TASK_RECORDS_ONLY", p42, None)
    req = request("PHASE42_TASK_RECORDS_ONLY", p42["register_sha256"])
    members = canonical_members()
    capsule = raw_zip([(n, members[n]) for n in ZIP_NAMES] + [("SYNTH0002", b"x"), ("F0009", b"y")])
    inspection = _inspect_in_memory(tmp_path, monkeypatch, capsule, req, snapshot)
    assert inspection["reported_eligibility_status"] == "STRUCTURAL_REJECTION"
    assert inspection["eligibility_agreement"] == "AGREES"


def test_inspector_accepts_valid_capsule_whose_request_reference_names_a_local_task(tmp_path, monkeypatch):
    p42 = phase42_record([synthetic_task("F0007"), synthetic_task("F0009", "SYNTH0002", "b")])
    snapshot = local("PHASE42_TASK_RECORDS_ONLY", p42, None)
    req = request("PHASE42_TASK_RECORDS_ONLY", p42["register_sha256"])
    capsule = canonical_capsule(synthetic_envelope(reference="mentions-F0009"))
    inspection = _inspect_in_memory(tmp_path, monkeypatch, capsule, req, snapshot)
    assert inspection["eligibility_agreement"] == "AGREES"


@pytest.mark.parametrize("variant", ["escaped_reference", "escaped_superstring", "member_name", "hash_preimage"])
def test_inspector_accepts_capsule_derived_strings_resembling_local_ids(tmp_path, monkeypatch, variant):
    """Second-round regressions: JSON escapes, superstrings and Phase44-computed
    hashes of capsule text must not be read as local disclosure."""
    from synthetic_fixtures import sha

    unclaimed = synthetic_task("F0009", "SYNTH0002", "b")
    p42 = phase42_record([synthetic_task("F0007"), unclaimed])
    snapshot = local("PHASE42_TASK_RECORDS_ONLY", p42, None)
    req = request("PHASE42_TASK_RECORDS_ONLY", p42["register_sha256"])
    members = canonical_members()
    if variant == "escaped_reference":
        raw = members["task-request.json"].replace(b'"synthetic-fixture-request"', b'"ref-F000\\u0039"')
        capsule = zip_members(rehash_manifest(dict(members, **{"task-request.json": raw})))
    elif variant == "escaped_superstring":
        raw = members["task-request.json"].replace(b'"SYNTH0001"', b'"SYNTH000\\u00329"')
        capsule = zip_members(rehash_manifest(dict(members, **{"task-request.json": raw})))
    elif variant == "member_name":
        capsule = raw_zip([(n, members[n]) for n in ZIP_NAMES] + [("F0009", b"x"), ("SYNTH0002", b"y")])
    else:
        assert unclaimed["binding_digest"] == sha("binding-b")
        capsule = raw_zip([(n, members[n]) for n in ZIP_NAMES] + [("synthetic-binding-b", b"x")])
    inspection = _inspect_in_memory(tmp_path, monkeypatch, capsule, req, snapshot)
    assert inspection["reported_eligibility_status"] == "STRUCTURAL_REJECTION"
    assert inspection["eligibility_agreement"] == "AGREES"


def test_disclosure_check_rejects_echoed_undisclosed_local_value():
    from inspect_task_reconciliation import _check_disclosure
    from recipient_reader import inspect_task_exchange_capsule, read_portable_task_request

    local_task = synthetic_task()
    capsule = canonical_capsule(synthetic_envelope([dict(local_task, candidate_id="SYNTH0099")]))
    owner_tasks = read_portable_task_request(inspect_task_exchange_capsule(capsule))[0]["tasks"]
    p42 = phase42_record([local_task])
    snapshot = local("PHASE42_TASK_RECORDS_ONLY", p42, None)
    req = request("PHASE42_TASK_RECORDS_ONLY", p42["register_sha256"])
    report, inbox = reconcile_capsule(capsule, req, snapshot)
    documents = output_documents(report, inbox, input_identities(capsule, json_bytes(req), snapshot))
    manifest = json.loads(documents["manifest.json"])
    for row in report["local_reconciliation"]["comparisons"]:
        if row["field"] == "candidate_id" and row["result"] == "MISMATCH":
            row.update(local_value="SYNTH0001", local_value_disclosure="ECHOED")
    with pytest.raises(InputError, match="undisclosed_local_value_echoed"):
        _check_disclosure(report, inbox, manifest, snapshot.record(), owner_tasks)
    report["local_reconciliation"]["task_lookups"][0]["task_id"] = "F0063"
    for row in report["local_reconciliation"]["comparisons"]:
        row.update(local_value=None, local_value_disclosure="NOT_AVAILABLE") if row["result"] != "MATCH" else None
    with pytest.raises(InputError, match="lookup_names_unclaimed_task"):
        _check_disclosure(report, inbox, manifest, snapshot.record(), owner_tasks)
