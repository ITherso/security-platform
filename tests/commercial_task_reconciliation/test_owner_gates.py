"""Gates enforced by the unchanged Phase43 owner, pinned from Phase44.

Phase44 container diagnostics are a subset of the owner checks. For every
ZIP variant below Phase44 itself reports no blocking finding of its own, so
the rejection rests on the Phase43 recipient reader alone (its metadata
check and its byte-exact rebuild comparison); the test asserts that premise.
Each variant must stay INCOMPATIBLE with the exact owner code, be a
STRUCTURAL_REJECTION and admit no task. The owner strict-JSON parser is
pinned directly; hostile JSON members are rejected by the owner and are also
flagged by Phase44's own member diagnostics. No Phase43 file is modified;
the owner is only called.
"""
from __future__ import annotations

import io
import struct
import zipfile

import pytest

from exchange_contracts import InputError, parse_json
from portable_capsule import REGULAR_FILE_ATTRIBUTES, ZIP_NAMES
from reconciliation_engine import reconcile_capsule
from synthetic_fixtures import (
    canonical_capsule, canonical_members, local, rehash_manifest, request, synthetic_envelope, zip_members,
)

METADATA = "task_exchange_capsule_member_metadata_rejected"
NOT_CANONICAL = "task_exchange_capsule_archive_not_canonical"


def write_capsule(index: int | None = None, **attributes) -> bytes:
    """The owner's STORED layout, with selected ZipInfo attributes changed on one member."""
    members = canonical_members()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for position, name in enumerate(ZIP_NAMES):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system, info.create_version, info.extract_version = 3, 20, 20
            info.external_attr = REGULAR_FILE_ATTRIBUTES
            info.compress_type = zipfile.ZIP_STORED
            if position == index:
                for key, value in attributes.items():
                    setattr(info, key, value)
            archive.writestr(info, members[name])
    return buffer.getvalue()


def _directory(raw: bytes) -> tuple[int, int, list]:
    """(EOCD offset, central directory offset, [(CD entry offset, local header offset)])."""
    eocd = raw.rfind(b"PK\x05\x06")
    count, _size, offset = struct.unpack("<HII", raw[eocd + 10:eocd + 20])
    rows, position = [], offset
    for _ in range(count):
        name_length, extra_length, comment_length = struct.unpack("<HHH", raw[position + 28:position + 34])
        rows.append((position, struct.unpack("<I", raw[position + 42:position + 46])[0]))
        position += 46 + name_length + extra_length + comment_length
    return eocd, offset, rows


def set_flag_bits(raw: bytes, index: int, bits: int) -> bytes:
    """zipfile resets flag_bits on write, so flags are patched in both headers."""
    out = bytearray(raw)
    _eocd, _offset, rows = _directory(raw)
    directory_entry, local_header = rows[index]
    struct.pack_into("<H", out, local_header + 6, bits)
    struct.pack_into("<H", out, directory_entry + 8, bits)
    return bytes(out)


def local_header_extra(raw: bytes, index: int, extra: bytes) -> bytes:
    """Add an extra field to one local header only; the central directory stays clean."""
    eocd, offset, rows = _directory(raw)
    _entry, local_header = rows[index]
    name_length, extra_length = struct.unpack("<HH", raw[local_header + 26:local_header + 30])
    cut = local_header + 30 + name_length + extra_length
    out = bytearray(raw[:cut] + extra + raw[cut:])
    struct.pack_into("<H", out, local_header + 28, extra_length + len(extra))
    shift = len(extra)
    for directory_entry, header in rows:
        if header > local_header:
            struct.pack_into("<I", out, directory_entry + shift + 42, header + shift)
    struct.pack_into("<I", out, eocd + shift + 16, offset + shift)
    return bytes(out)


def test_writer_reproduces_the_owner_capsule_exactly():
    # Without this, a variant could be rejected for a reason other than the one under test.
    assert write_capsule() == canonical_capsule()
    assert set_flag_bits(canonical_capsule(), 0, 0) == canonical_capsule()


OWNER_ONLY_VARIANTS = {
    "trailing_bytes": (lambda: canonical_capsule() + b"JUNK", NOT_CANONICAL),
    "prefix_bytes": (lambda: b"JUNK" + canonical_capsule(), NOT_CANONICAL),
    "concatenated_archives": (lambda: canonical_capsule(synthetic_envelope(reference="synthetic-other"))
                              + canonical_capsule(), NOT_CANONICAL),
    "local_header_extra_only": (lambda: local_header_extra(canonical_capsule(), 1, b"\xfe\xca\x00\x00"),
                                NOT_CANONICAL),
    "internal_attr": (lambda: write_capsule(2, internal_attr=1), NOT_CANONICAL),
    "create_version": (lambda: write_capsule(0, create_version=45), NOT_CANONICAL),
    "flag_utf8_bit": (lambda: set_flag_bits(canonical_capsule(), 0, 0x800), METADATA),
    "flag_bit_1": (lambda: set_flag_bits(canonical_capsule(), 2, 0x2), METADATA),
    "member_comment": (lambda: write_capsule(1, comment=b"x"), METADATA),
    "member_date_time": (lambda: write_capsule(0, date_time=(1981, 1, 1, 0, 0, 0)), METADATA),
    "member_create_system": (lambda: write_capsule(3, create_system=0), METADATA),
    "member_external_attr": (lambda: write_capsule(2, external_attr=0o100755 << 16), METADATA),
}


@pytest.mark.parametrize("variant", sorted(OWNER_ONLY_VARIANTS))
def test_owner_only_zip_gates_reject_and_admit_nothing(variant):
    build, owner_code = OWNER_ONLY_VARIANTS[variant]
    capsule = build()
    assert capsule != canonical_capsule()
    report, inbox = reconcile_capsule(capsule, request(), local())
    assert report["phase43_reader"] == {"compatibility": "INCOMPATIBLE", "owner_rejection_code": owner_code}
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    assert report["eligibility"]["manual_review"] == "NOT_ELIGIBLE"
    assert report["capsule_identity"]["represented_state"] == "NOT_ESTABLISHED"
    assert report["local_reconciliation"]["state"] == "NOT_PERFORMED_STRUCTURAL_REJECTION"
    assert inbox["lifecycle_stage"] == "REJECTED_NOT_ADMITTED"
    assert inbox["admitted_tasks"] == [] and inbox["admitted_task_count"] == 0
    rules = {item["rule"] for item in report["findings"]}
    assert {"OWNER_READER_REJECTED", "RECONCILIATION_NOT_PERFORMED", "MANUAL_REVIEW_REQUIRED"} <= rules
    # Owner-only premise: Phase44's own diagnostics do not flag this variant.
    assert {item["rule"] for item in report["findings"] if item["severity"] == "BLOCKING"} == {"OWNER_READER_REJECTED"}
    assert ("P44-OWNER_READER_REJECTED:capsule" in report["eligibility"]["basis_finding_ids"])


STRICT_JSON = {
    "utf8_bom": (b'\xef\xbb\xbf{"a": 1}', "utf8_bom"),
    "nan": (b'{"a": NaN}', "non_integer_number"),
    "infinity": (b'{"a": -Infinity}', "non_integer_number"),
    "float": (b'{"a": 1.5}', "non_integer_number"),
    "exponent": (b'{"a": 1e3}', "non_integer_number"),
    "negative": (b'{"a": -1}', "safe_integer"),
    "two_pow_53": (b'{"a": 9007199254740992}', "safe_integer"),
    "seventeen_digits": (b'{"a": 10000000000000000}', "integer_size"),
    "lone_surrogate": (b'{"a": "\\ud800"}', "strict_json"),
    "invalid_utf8": (b'{"a": "\xff"}', "strict_json"),
    "duplicate_key": (b'{"a": 1, "a": 1}', "duplicate_json_key"),
    "depth_13": (b"[" * 14 + b"]" * 14, "tree_limit"),
    "empty": (b"", "json_bytes"),
    "trailing_garbage": (b'{"a": 1} x', "strict_json"),
}


@pytest.mark.parametrize("case", sorted(STRICT_JSON))
def test_owner_strict_json_parser_rejects(case):
    raw, code = STRICT_JSON[case]
    with pytest.raises(InputError) as error:
        parse_json(raw, maximum=1024)
    assert str(error.value) == "task_exchange_invalid_" + code


def test_owner_strict_json_parser_accepts_its_bounds():
    assert parse_json(b'{"a": 9007199254740991}', maximum=1024) == {"a": 2**53 - 1}
    assert parse_json(b"[" * 13 + b"]" * 13, maximum=1024) is not None
    assert parse_json(b'{"a": [0, true, false, null, ""]}', maximum=1024) == {"a": [0, True, False, None, ""]}


@pytest.mark.parametrize("case", ["utf8_bom", "nan", "float", "negative", "two_pow_53", "seventeen_digits",
                                  "lone_surrogate", "duplicate_key", "depth_13"])
def test_hostile_json_member_is_rejected_by_owner_and_admits_nothing(case):
    raw, code = STRICT_JSON[case]
    members = rehash_manifest(dict(canonical_members(), **{"task-request.json": raw + b"\n"}))
    report, inbox = reconcile_capsule(zip_members(members), request(), local())
    assert report["phase43_reader"] == {"compatibility": "INCOMPATIBLE",
                                        "owner_rejection_code": "task_exchange_invalid_" + code}
    assert report["member_contents"][0]["owner_rejection_code"] == "task_exchange_invalid_" + code
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    assert inbox["admitted_tasks"] == []
