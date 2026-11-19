"""Finding rules not exercised elsewhere, and the summary wording boundary.

Each case builds one synthetic hostile capsule and requires its named rule,
a STRUCTURAL_REJECTION and no admitted task. FINDINGS_TRUNCATED is not
here: with the current limits no capsule reaches 400 findings.
"""
from __future__ import annotations

import html
import json
import re
import struct

import pytest

from exchange_contracts import build_response_contract, json_bytes
from portable_capsule import ZIP_NAMES
from reconciliation_engine import reconcile_capsule
from reconciliation_renderer import render_reconciliation_summary
from synthetic_fixtures import (
    canonical_capsule, canonical_members, full_local, local, phase42_record, raw_zip, rehash_manifest, request,
    synthetic_envelope, synthetic_task, zip_members,
)


def with_extra_member(name: str) -> bytes:
    members = canonical_members()
    return raw_zip([(item, members[item]) for item in ZIP_NAMES] + [(name, b"x")])


def with_member(name: str, raw: bytes, rehash: bool = True) -> bytes:
    members = dict(canonical_members(), **{name: raw})
    return zip_members(rehash_manifest(members) if rehash else members)


def with_manifest(change) -> bytes:
    members = canonical_members()
    manifest = json.loads(members["capsule-manifest.json"])
    change(manifest)
    return zip_members(dict(members, **{"capsule-manifest.json": json_bytes(manifest)}))


def with_task(change) -> bytes:
    task = synthetic_task()
    change(task)
    return with_member("task-request.json", json_bytes(synthetic_envelope([task])))


def with_declared_size_mismatch() -> bytes:
    """README declared size in the central directory differs from its stored size."""
    raw = bytearray(canonical_capsule())
    position = raw.find(b"PK\x01\x02")
    for _ in range(ZIP_NAMES.index("README.txt")):
        name_length, extra_length, comment_length = struct.unpack("<HHH", raw[position + 28:position + 34])
        position += 46 + name_length + extra_length + comment_length
    size = struct.unpack("<I", raw[position + 24:position + 28])[0]
    struct.pack_into("<I", raw, position + 24, size + 1)
    return bytes(raw)


def _response_contract_with_extra_limitation() -> bytes:
    contract = build_response_contract()
    contract["limitations"] = list(contract["limitations"]) + ["synthetic_extra_limitation"]
    return json_bytes(contract)


CASES = {
    "MEMBER_NAME_CONTROL_CHARACTER": lambda: with_extra_member("bad\x01name.txt"),
    "MEMBER_NAME_NON_ASCII": lambda: with_extra_member("réadme.txt"),
    "MEMBER_NAME_EMPTY_NAME": lambda: with_extra_member(""),
    "MEMBER_NAME_OVERLONG_NAME": lambda: with_extra_member("a" * 129),
    "MEMBER_EMPTY": lambda: with_member("README.txt", b"", rehash=False),
    "MEMBER_SIZE_FIELDS_INCONSISTENT": with_declared_size_mismatch,
    "README_FIXED_TEXT_MISMATCH": lambda: with_member("README.txt", b"synthetic replacement readme\n"),
    "MEMBER_NOT_JSON_OBJECT": lambda: with_member("task-request.json", b"[]\n"),
    "MEMBER_JSON_CONTRACT_VIOLATION": lambda: with_member("task-request.json", b'{"a": 1.5}\n'),
    "MEMBER_OWNER_CONTRACT_REJECTED": lambda: with_member("response-contract.json",
                                                          _response_contract_with_extra_limitation()),
    "MANIFEST_FILES_NOT_LIST": lambda: with_manifest(lambda m: m.update(files={})),
    "MANIFEST_MALFORMED_ENTRY": lambda: with_manifest(lambda m: m["files"][0].pop("sha256")),
    "MANIFEST_UNKNOWN_ENTRY": lambda: with_manifest(lambda m: m["files"].append(dict(m["files"][2], name="x.txt"))),
    "MANIFEST_DUPLICATE_ENTRY": lambda: with_manifest(lambda m: m["files"].append(dict(m["files"][0]))),
    "MANIFEST_ENTRY_NOT_DECLARED": lambda: with_manifest(lambda m: m["files"].pop(2)),
    "MANIFEST_OWNER_MISMATCH": lambda: with_manifest(lambda m: m.update(integrity_scope="synthetic_other_scope")),
    "IDENTITY_EMPTY_ARRAY": lambda: with_task(lambda t: t.update(candidate_id=[])),
    "IDENTITY_EMPTY_OBJECT": lambda: with_task(lambda t: t.update(candidate_id={})),
    "FIELD_ABSENT": lambda: with_task(lambda t: t.pop("slot_status")),
    "FIELD_NULL": lambda: with_task(lambda t: t.update(slot_status=None)),
    "FIELD_EMPTY_STRING": lambda: with_task(lambda t: t.update(slot_status="")),
    "ARCHIVE_SIZE_LIMIT": lambda: b"\0" * (128 * 1024 + 1),
    "ARCHIVE_UNREADABLE": lambda: b"PK\x03\x04 synthetic bytes that are not a zip archive",
}


@pytest.mark.parametrize("rule", sorted(CASES))
def test_rule_fires_and_capsule_is_rejected(rule):
    report, inbox = reconcile_capsule(CASES[rule](), request(), local())
    assert rule in {item["rule"] for item in report["findings"]}
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    assert inbox["admitted_tasks"] == []


# --- the summary never calls a quarantined task accepted, approved or assigned (audit O2) ---

_FORBIDDEN = (r"kabul edil", r"onaylan", r"\batan(an|dı|mış)\b", r"\baccepted\b", r"\bapproved\b",
              r"\bassigned\b")


def _scenarios():
    capsule = canonical_capsule()
    yield "valid", (capsule, *reversed(full_local(capsule)))
    mismatch = canonical_capsule(synthetic_envelope([synthetic_task(candidate="SYNTH0099")]))
    p42 = phase42_record()
    yield "mismatch", (mismatch, request("PHASE42_TASK_RECORDS_ONLY", p42["register_sha256"]),
                       local("PHASE42_TASK_RECORDS_ONLY", p42, None))
    yield "unavailable", (capsule, request(), local())
    yield "rejected", (capsule + b"JUNK", request(), local())


@pytest.mark.parametrize("name, inputs", list(_scenarios()))
def test_summary_wording_claims_no_acceptance(name, inputs):
    report, inbox = reconcile_capsule(*inputs)
    text = html.unescape(render_reconciliation_summary(report, inbox).decode("utf-8")).lower()
    for pattern in _FORBIDDEN:
        assert not re.search(pattern, text), (name, pattern)
    assert "karantinadaki inbox kaydına alınan görev sayısı (kabul, onay veya atama değildir): " + str(
        inbox["admitted_task_count"]) in text
