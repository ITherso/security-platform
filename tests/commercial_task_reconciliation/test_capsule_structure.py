"""Container-level fail-closed behaviour on synthetic capsules."""
from __future__ import annotations

import os
import zipfile

from synthetic_fixtures import (
    canonical_capsule, canonical_members, local, raw_zip, rehash_manifest, request, zip_members,
)
from portable_capsule import ZIP_NAMES
from reconciliation_engine import reconcile_capsule


def run(capsule: bytes):
    return reconcile_capsule(capsule, request(), local())


def rules(report: dict) -> set:
    return {item["rule"] for item in report["findings"]}


def assert_rejected(report: dict, inbox: dict) -> None:
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    assert report["eligibility"]["manual_review"] == "NOT_ELIGIBLE"
    assert report["local_reconciliation"]["state"] == "NOT_PERFORMED_STRUCTURAL_REJECTION"
    assert {row["result"] for row in report["local_reconciliation"]["comparisons"]} == {"NOT_COMPARABLE"}
    assert all(row["local_value"] is None for row in report["local_reconciliation"]["comparisons"])
    assert inbox["lifecycle_stage"] == "REJECTED_NOT_ADMITTED"
    assert inbox["admitted_tasks"] == [] and inbox["admitted_task_count"] == 0
    assert report["capsule_identity"]["represented_state"] == "NOT_ESTABLISHED"


def test_valid_canonical_capsule_is_compatible_and_held_without_local_records():
    report, inbox = run(canonical_capsule())
    assert report["phase43_reader"] == {"compatibility": "COMPATIBLE", "owner_rejection_code": None}
    assert report["archive"]["container_verdict"] == "ACCEPTABLE"
    assert report["archive"]["member_count"] == 4
    assert [m["name"] for m in report["members"]] == list(ZIP_NAMES)
    assert all(item["presence"] == "PRESENT" for item in report["required_members"])
    assert {e["result"] for e in report["manifest_correspondence"]["entries"]} == {"MATCH"}
    assert report["manifest_correspondence"]["fixed_fields"] == "MATCH"
    assert report["capsule_identity"]["claimed_vs_represented"] == "MATCH"
    assert report["eligibility"]["status"] == "LOCAL_RECONCILIATION_UNAVAILABLE"
    assert inbox["lifecycle_stage"] == "QUARANTINED_HELD_LOCAL_RECONCILIATION_UNAVAILABLE"
    assert inbox["admitted_task_count"] == 1
    assert inbox["trust_state"] == "UNTRUSTED_IMPORT_NOT_AUTHENTICATED"
    assert set(inbox["non_claims"].values()) == {False}


def test_missing_member_rejected_without_reading_contents():
    members = canonical_members()
    report, inbox = run(raw_zip([(name, members[name]) for name in ZIP_NAMES if name != "README.txt"]))
    assert_rejected(report, inbox)
    assert "REQUIRED_MEMBER_ABSENT" in rules(report)
    presence = {item["name"]: item["presence"] for item in report["required_members"]}
    assert presence["README.txt"] == "ABSENT" and presence["task-request.json"] == "PRESENT"
    assert {item["content_state"] for item in report["member_contents"]} == {"NOT_EVALUATED"}
    assert report["phase43_reader"]["compatibility"] == "INCOMPATIBLE"


def test_duplicate_zip_entries_rejected():
    members = canonical_members()
    entries = [(name, members[name]) for name in ZIP_NAMES] + [("task-request.json", members["task-request.json"])]
    report, inbox = run(raw_zip(entries))
    assert_rejected(report, inbox)
    assert "MEMBER_DUPLICATE" in rules(report)
    presence = {item["name"]: item["presence"] for item in report["required_members"]}
    assert presence["task-request.json"] == "DUPLICATED"


def test_path_traversal_absolute_and_backslash_names_rejected_and_not_echoed():
    members = canonical_members()
    for hostile, hazard in (("../task-request.json", "PATH_TRAVERSAL"), ("/etc/task-request.json", "ABSOLUTE_PATH"),
                            ("C:/task-request.json", "ABSOLUTE_PATH"), ("dir\\README.txt", "BACKSLASH_SEPARATOR"),
                            ("nested/README.txt", "NESTED_PATH"), ("folder/", "DIRECTORY_ENTRY")):
        # zipfile rewrites os.sep on write, so a backslash name is patched into the raw bytes.
        placeholder = hostile.replace("\\", "#")
        entries = [(name, members[name]) for name in ZIP_NAMES] + [(placeholder, b"x" if not hostile.endswith("/") else b"")]
        report, inbox = run(raw_zip(entries).replace(placeholder.encode(), hostile.encode()))
        assert_rejected(report, inbox)
        assert "MEMBER_NAME_" + hazard in rules(report), hostile
        hostile_record = report["members"][-1]
        assert hostile_record["name"] is None and hazard in hostile_record["name_hazards"]
        assert hostile_record["name_state"] == "UNEXPECTED"


def test_unexpected_member_and_casefold_collision():
    members = canonical_members()
    report, inbox = run(raw_zip([(n, members[n]) for n in ZIP_NAMES] + [("readme.TXT", b"other")]))
    assert_rejected(report, inbox)
    assert {"MEMBER_UNEXPECTED", "MEMBER_NAME_CASEFOLD_COLLISION"} <= rules(report)


def test_noncanonical_order_and_comment_rejected():
    members = canonical_members()
    order = ("response-contract.json", "task-request.json", "README.txt", "capsule-manifest.json")
    report, inbox = run(zip_members(members, order))
    assert_rejected(report, inbox)
    assert "MEMBER_ORDER_NONCANONICAL" in rules(report)
    report, inbox = run(raw_zip([(n, members[n]) for n in ZIP_NAMES], comment=b"hello"))
    assert_rejected(report, inbox)
    assert "ARCHIVE_COMMENT_PRESENT" in rules(report)


def test_not_stored_symlink_and_encrypted_flag_rejected():
    members = canonical_members()
    report, _ = run(raw_zip([(n, members[n]) for n in ZIP_NAMES], compression=zipfile.ZIP_DEFLATED))
    assert "MEMBER_NOT_STORED" in rules(report)
    report, _ = run(raw_zip([(n, members[n]) for n in ZIP_NAMES], external_attr=(0o120777 << 16)))
    assert "MEMBER_NOT_REGULAR_FILE" in rules(report)
    assert {m["entry_type"] for m in report["members"]} == {"SYMLINK"}
    raw = bytearray(zip_members(members))
    # Set the encryption bit in every central directory header (signature PK\x01\x02, flags at +8).
    index = raw.find(b"PK\x01\x02")
    while index != -1:
        raw[index + 8] |= 0x01
        index = raw.find(b"PK\x01\x02", index + 4)
    report, inbox = run(bytes(raw))
    assert_rejected(report, inbox)
    assert "MEMBER_ENCRYPTED" in rules(report)


def test_size_limits_fail_closed():
    report, inbox = run(b"")
    assert_rejected(report, inbox)
    assert report["archive"]["archive_state"] == "EMPTY_INPUT" and "ARCHIVE_EMPTY" in rules(report)
    report, inbox = run(os.urandom(128 * 1024 + 1))
    assert_rejected(report, inbox)
    assert report["archive"]["archive_state"] == "SIZE_LIMIT_EXCEEDED"
    assert report["archive"]["member_count"] is None and report["members"] == []
    members = canonical_members()
    oversized = dict(members, **{"README.txt": b"x" * (4 * 1024 + 1)})
    report, inbox = run(zip_members(oversized))
    assert_rejected(report, inbox)
    assert "MEMBER_OVERSIZED" in rules(report)
    assert {item["content_state"] for item in report["member_contents"]} == {"NOT_EVALUATED"}
    bomb = raw_zip([("task-request.json", b"\0" * 64 * 1024), ("response-contract.json", b"\0" * 32 * 1024),
                    ("README.txt", b"\0" * 4 * 1024), ("capsule-manifest.json", b"\0" * 32 * 1024)],
                   compression=zipfile.ZIP_DEFLATED)
    assert len(bomb) < 128 * 1024
    report, inbox = run(bomb)
    assert_rejected(report, inbox)
    assert {"ARCHIVE_EXPANDED_LIMIT", "MEMBER_NOT_STORED"} <= rules(report)
    many = raw_zip([("m%02d.txt" % i, b"x") for i in range(20)])
    report, inbox = run(many)
    assert_rejected(report, inbox)
    assert report["archive"]["member_count"] == 20
    assert report["archive"]["listed_member_count"] == 16 and report["archive"]["omitted_member_count"] == 4
    assert "ARCHIVE_MEMBER_COUNT_LIMIT" in rules(report)


def test_unreadable_archive_and_crc_corruption():
    report, inbox = run(b"PK\x03\x04 definitely not a zip")
    assert_rejected(report, inbox)
    assert report["archive"]["archive_state"] == "UNREADABLE"
    raw = bytearray(canonical_capsule())
    marker = raw.find(b"OFFLINE TASK REQUEST ONLY")
    raw[marker] ^= 0x20          # same size, wrong CRC
    report, inbox = run(bytes(raw))
    assert_rejected(report, inbox)
    assert "MEMBER_READ_ERROR" in rules(report)


def test_malformed_json_and_duplicate_keys():
    members = canonical_members()
    broken = rehash_manifest(dict(members, **{"task-request.json": b'{"schema_version": '}))
    report, inbox = run(zip_members(broken))
    assert_rejected(report, inbox)
    content = report["member_contents"][0]
    assert content["content_state"] == "MALFORMED_JSON" and content["owner_rejection_code"].endswith("strict_json")
    assert "MEMBER_MALFORMED_JSON" in rules(report)
    duplicate = rehash_manifest(dict(members, **{"response-contract.json": b'{"a": 1, "a": 2}\n'}))
    report, inbox = run(zip_members(duplicate))
    assert_rejected(report, inbox)
    assert report["member_contents"][1]["content_state"] == "DUPLICATE_JSON_KEY"
    assert "MEMBER_DUPLICATE_JSON_KEY" in rules(report)


def test_schema_mismatch_is_unsupported_not_reinterpreted():
    import json

    from exchange_contracts import json_bytes
    from synthetic_fixtures import synthetic_envelope

    envelope = synthetic_envelope()
    envelope["schema_version"] = "termivar-offline-portable-task-request/v2"
    members = rehash_manifest(dict(canonical_members(), **{"task-request.json": json_bytes(envelope)}))
    report, inbox = run(zip_members(members))
    assert_rejected(report, inbox)
    content = report["member_contents"][0]
    assert content["schema_state"] == "UNSUPPORTED"
    assert content["declared_schema"] is None                       # unsupported strings are withheld
    schema = [f for f in report["envelope_fields"] if f["path"] == "task-request.json:schema_version"][0]
    assert schema["value_disclosure"] == "WITHHELD_INVALID_STRING" and schema["string_length"] == 41
    assert "SCHEMA_UNSUPPORTED" in rules(report)
    del envelope["schema_version"]
    members = rehash_manifest(dict(canonical_members(), **{"task-request.json": json_bytes(envelope)}))
    report, _ = run(zip_members(members))
    assert "SCHEMA_ABSENT" in rules(report)
    assert json.loads(json.dumps(report))["member_contents"][0]["schema_state"] == "ABSENT"


def test_member_hash_mismatch_against_inner_manifest():
    from exchange_contracts import json_bytes
    from synthetic_fixtures import synthetic_envelope

    members = canonical_members()
    altered = json_bytes(synthetic_envelope(reference="synthetic-altered-request"))
    stale = dict(members, **{"task-request.json": altered})      # inner manifest not updated
    report, inbox = run(zip_members(stale))
    assert_rejected(report, inbox)
    entry = report["manifest_correspondence"]["entries"][0]
    assert entry["member"] == "task-request.json" and entry["result"] == "MISMATCH"
    assert "MANIFEST_HASH_MISMATCH" in rules(report)
    # The altered envelope itself is owner-valid; only the binding to the manifest fails.
    assert report["member_contents"][0]["owner_contract"] == "OWNER_VALID"


def test_noncanonical_json_encoding_rejected():
    members = canonical_members()
    compact = members["task-request.json"].replace(b"\n  ", b"\n   ")
    report, inbox = run(zip_members(rehash_manifest(dict(members, **{"task-request.json": compact}))))
    assert_rejected(report, inbox)
    assert report["member_contents"][0]["canonical_encoding"] == "NONCANONICAL"
    assert "MEMBER_NONCANONICAL_ENCODING" in rules(report)


def test_diagnostic_owner_disagreement_fails_closed(monkeypatch):
    import reconciliation_engine
    from recipient_reader import inspect_task_exchange_capsule, read_portable_task_request

    good = canonical_capsule()
    envelope, _contract, artifacts = read_portable_task_request(inspect_task_exchange_capsule(good))
    monkeypatch.setattr(reconciliation_engine, "owner_reader_verdict",
                        lambda _raw: ("COMPATIBLE", None, envelope, artifacts))
    members = canonical_members()
    report, inbox = reconciliation_engine.reconcile_capsule(
        raw_zip([(n, members[n]) for n in ZIP_NAMES], comment=b"x"), request(), local())
    assert "DIAGNOSTIC_OWNER_DISAGREEMENT" in rules(report)
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    assert inbox["admitted_tasks"] == []
