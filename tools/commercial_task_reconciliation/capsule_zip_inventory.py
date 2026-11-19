"""Bounded diagnostic inventory of untrusted capsule bytes; opens no paths.

This layer only describes the ZIP container. It never extracts to disk,
never decompresses non-STORED members, and reads member bytes only when the
whole container passed every safety gate. The Phase43 recipient reader stays
the authority on Phase43 compatibility; this inventory explains failures.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import io
import re
import stat
import struct
import zipfile

from exchange_contracts import MAX_CAPSULE_BYTES, MAX_EXPANDED_BYTES
from portable_capsule import MEMBER_LIMITS, ZIP_NAMES
from reconciliation_contracts import (
    MAX_LISTED_MEMBERS, SAFE_INTEGER, ArchiveState, Compression, Encryption, EntryType, NameHazard, NameState,
    Ordering, Presence, SizeState, Verdict, safe_member_name,
)
from reconciliation_findings import finding

_ZIP_ERRORS = (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, UnicodeError, ValueError, RuntimeError,
               TypeError, KeyError, IndexError, RecursionError, EOFError, OverflowError,
               NotImplementedError, struct.error)
_UNEXPECTED_MEMBER_LIMIT = max(MEMBER_LIMITS.values())
_ZIP32_MARKER = 0xFFFFFFFF


def _representable(value: int) -> int | None:
    return value if 0 <= value <= SAFE_INTEGER else None


def _zip64_or_extra(info: zipfile.ZipInfo) -> bool:
    return bool(info.extra) or any(value >= _ZIP32_MARKER for value in
                                   (info.file_size, info.compress_size, info.header_offset))


def _hazards(name: str, all_names: list) -> list:
    found = set()
    if name == "":
        found.add(NameHazard.EMPTY_NAME)
    if len(name) > 128:
        found.add(NameHazard.OVERLONG_NAME)
    if name.startswith(("/", "\\")) or re.match(r"[A-Za-z]:", name):
        found.add(NameHazard.ABSOLUTE_PATH)
    if ".." in re.split(r"[/\\]", name):
        found.add(NameHazard.PATH_TRAVERSAL)
    if "\\" in name:
        found.add(NameHazard.BACKSLASH_SEPARATOR)
    if name.endswith("/"):
        found.add(NameHazard.DIRECTORY_ENTRY)
    if "/" in name.rstrip("/"):
        found.add(NameHazard.NESTED_PATH)
    if any(ord(char) < 32 or ord(char) == 127 for char in name):
        found.add(NameHazard.CONTROL_CHARACTER)
    if any(ord(char) > 126 for char in name):
        found.add(NameHazard.NON_ASCII)
    if any(other != name and other.casefold() == name.casefold() for other in all_names):
        found.add(NameHazard.CASEFOLD_COLLISION)
    return sorted(item.value for item in found)


def _entry_type(info: zipfile.ZipInfo) -> EntryType:
    mode = info.external_attr >> 16
    kind = stat.S_IFMT(mode)
    if info.filename.endswith("/") or info.external_attr & 0x10 or kind == stat.S_IFDIR:
        return EntryType.DIRECTORY
    if kind == stat.S_IFLNK:
        return EntryType.SYMLINK
    if kind == stat.S_IFREG:
        return EntryType.REGULAR_FILE
    return EntryType.UNSPECIFIED if kind == 0 else EntryType.OTHER


def _subject(position: int, name: str, occurrences: int) -> str:
    """Controlled subject: an expected unique name, otherwise the position."""
    return name if name in ZIP_NAMES and occurrences == 1 else "member#" + str(position)


def _size_state(info: zipfile.ZipInfo, limit: int, compression: Compression) -> SizeState:
    if info.file_size > SAFE_INTEGER or info.compress_size > SAFE_INTEGER:
        return SizeState.DECLARED_SIZE_UNREPRESENTABLE
    if info.file_size > limit:
        return SizeState.OVER_LIMIT
    if info.file_size == 0:
        return SizeState.EMPTY
    if compression == Compression.STORED and info.file_size != info.compress_size:
        return SizeState.SIZE_FIELDS_INCONSISTENT
    return SizeState.WITHIN_LIMIT


def _new_archive(state: ArchiveState) -> dict:
    return {"archive_state": state.value, "member_count": None, "listed_member_count": 0,
            "omitted_member_count": 0, "declared_expanded_bytes": None,
            "member_order": Ordering.NOT_EVALUATED.value, "archive_comment": Presence.NOT_EVALUATED.value,
            "container_verdict": Verdict.REJECTED.value}


def _required(names: list | None) -> list:
    if names is None:
        return [{"name": name, "presence": Presence.NOT_EVALUATED.value} for name in ZIP_NAMES]
    counts = Counter(names)
    return [{"name": name, "presence": (Presence.ABSENT if counts[name] == 0 else
                                        Presence.PRESENT if counts[name] == 1 else Presence.DUPLICATED).value}
            for name in ZIP_NAMES]


def inventory_capsule(raw: bytes) -> dict:
    """Return container facts, findings and (only if safe) the four member bytes."""
    if type(raw) is not bytes:
        raise TypeError("capsule bytes required")
    findings: list = []
    if len(raw) == 0:
        findings.append(finding("ARCHIVE_EMPTY", "capsule", "the archive input has 0 bytes"))
        return {"archive": _new_archive(ArchiveState.EMPTY_INPUT), "members": [],
                "required_members": _required(None), "contents": None, "findings": findings}
    if len(raw) > MAX_CAPSULE_BYTES:
        findings.append(finding("ARCHIVE_SIZE_LIMIT", "capsule",
                                "the archive input has " + str(len(raw)) + " bytes; the ZIP was not parsed"))
        return {"archive": _new_archive(ArchiveState.SIZE_LIMIT_EXCEEDED), "members": [],
                "required_members": _required(None), "contents": None, "findings": findings}
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r", allowZip64=False) as archive:
            infos = archive.infolist()
            comment = archive.comment
            names = [info.orig_filename for info in infos]
            occurrences = Counter(names)
            first_index = {}
            for index, name in enumerate(names):
                first_index.setdefault(name, index)
            members, listed = [], infos[:MAX_LISTED_MEMBERS]
            for position, info in enumerate(listed):
                name = info.orig_filename
                hazards = _hazards(name, names)
                expected = name in ZIP_NAMES
                compression = Compression.STORED if info.compress_type == zipfile.ZIP_STORED else Compression.NOT_STORED
                encryption = Encryption.ENCRYPTED if info.flag_bits & 0x1 else Encryption.NOT_ENCRYPTED
                entry_type = _entry_type(info)
                limit = MEMBER_LIMITS[name] if expected else _UNEXPECTED_MEMBER_LIMIT
                size_state = _size_state(info, limit, compression)
                members.append({
                    "position": position, "name": safe_member_name(name),
                    "name_length": len(name), "name_sha256": hashlib.sha256(name.encode("utf-8", "surrogatepass")).hexdigest(),
                    "name_state": (NameState.EXPECTED if expected else NameState.UNEXPECTED).value,
                    "name_hazards": hazards, "occurrence_count": occurrences[name],
                    "declared_size": _representable(info.file_size),
                    "compressed_size": _representable(info.compress_size),
                    "compression": compression.value, "encryption": encryption.value,
                    "entry_type": entry_type.value, "size_state": size_state.value,
                })
                subject = _subject(position, name, occurrences[name])
                if not expected:
                    findings.append(finding("MEMBER_UNEXPECTED", subject,
                                            "member at position " + str(position) + " has an unexpected name"
                                            + ("" if safe_member_name(name) is None else ": " + name)))
                for hazard in hazards:
                    findings.append(finding("MEMBER_NAME_" + hazard, subject,
                                            "member name at position " + str(position) + " has hazard " + hazard))
                if _zip64_or_extra(info):
                    findings.append(finding("MEMBER_ZIP64_OR_EXTRA_FIELD", subject,
                                            "the entry carries an extra field or a ZIP64 size/offset marker"))
                if compression != Compression.STORED:
                    findings.append(finding("MEMBER_NOT_STORED", subject,
                                            "compression method " + str(info.compress_type) + " is not ZIP_STORED"))
                if encryption == Encryption.ENCRYPTED:
                    findings.append(finding("MEMBER_ENCRYPTED", subject, "the encryption flag bit is set"))
                if entry_type != EntryType.REGULAR_FILE:
                    findings.append(finding("MEMBER_NOT_REGULAR_FILE", subject, "entry type is " + entry_type.value))
                if size_state == SizeState.DECLARED_SIZE_UNREPRESENTABLE:
                    findings.append(finding("MEMBER_OVERSIZED", subject,
                                            "declared size exceeds the representable integer range"))
                elif size_state == SizeState.OVER_LIMIT:
                    findings.append(finding("MEMBER_OVERSIZED", subject,
                                            "declared size " + str(info.file_size) + " exceeds the limit " + str(limit)))
                elif size_state == SizeState.EMPTY:
                    findings.append(finding("MEMBER_EMPTY", subject, "declared size is 0"))
                elif size_state == SizeState.SIZE_FIELDS_INCONSISTENT:
                    findings.append(finding("MEMBER_SIZE_FIELDS_INCONSISTENT", subject,
                                            "declared size " + str(info.file_size) + " differs from stored size "
                                            + str(info.compress_size)))
            # One finding per duplicated name among the listed members, and a
            # single aggregate for the rest, so the finding count stays bounded.
            unlisted_duplicates = 0
            for name, total in sorted(occurrences.items(), key=lambda item: first_index[item[0]]):
                if total < 2:
                    continue
                if first_index[name] < MAX_LISTED_MEMBERS:
                    findings.append(finding("MEMBER_DUPLICATE", "member#" + str(first_index[name]),
                                            "the same member name occurs " + str(total) + " times"))
                else:
                    unlisted_duplicates += 1
            if unlisted_duplicates:
                findings.append(finding("MEMBER_DUPLICATE", "unlisted_members",
                                        str(unlisted_duplicates) + " further names occur more than once"))
            for entry in _required(names):
                if entry["presence"] == Presence.ABSENT:
                    findings.append(finding("REQUIRED_MEMBER_ABSENT", entry["name"], "the member is absent"))
            expanded = sum(info.file_size for info in infos)
            if expanded > MAX_EXPANDED_BYTES:
                findings.append(finding("ARCHIVE_EXPANDED_LIMIT", "capsule",
                                        "declared expanded size is " + str(expanded) + " bytes"))
            if len(infos) > MAX_LISTED_MEMBERS:
                findings.append(finding("ARCHIVE_MEMBER_COUNT_LIMIT", "capsule",
                                        str(len(infos)) + " members; only the first " + str(MAX_LISTED_MEMBERS)
                                        + " are listed and none were read"))
            order = Ordering.CANONICAL if tuple(names) == ZIP_NAMES else Ordering.NONCANONICAL
            if order == Ordering.NONCANONICAL and sorted(names) == sorted(ZIP_NAMES):
                findings.append(finding("MEMBER_ORDER_NONCANONICAL", "capsule", "the four members are out of order"))
            if comment:
                findings.append(finding("ARCHIVE_COMMENT_PRESENT", "capsule",
                                        "archive comment has " + str(len(comment)) + " bytes"))
            archive_facts = {
                "archive_state": ArchiveState.READABLE.value, "member_count": len(infos),
                "listed_member_count": len(listed), "omitted_member_count": len(infos) - len(listed),
                "declared_expanded_bytes": _representable(expanded), "member_order": order.value,
                "archive_comment": (Presence.PRESENT if comment else Presence.ABSENT).value,
                "container_verdict": (Verdict.REJECTED if findings else Verdict.ACCEPTABLE).value,
            }
            contents = None
            if not findings:
                # Every gate passed: exactly four unique, flat, regular, STORED,
                # unencrypted members within limits. Only now are bytes read.
                contents = {}
                for info in infos:
                    limit = MEMBER_LIMITS[info.orig_filename]
                    try:
                        with archive.open(info, "r") as stream:
                            data = stream.read(limit + 1)
                    except _ZIP_ERRORS:
                        data = None
                    if data is None or len(data) != info.file_size or len(data) > limit:
                        findings.append(finding("MEMBER_READ_ERROR", info.orig_filename,
                                                "the member could not be read with matching size and CRC"))
                        data = None
                    contents[info.orig_filename] = data
                if findings:
                    archive_facts["container_verdict"] = Verdict.REJECTED.value
            return {"archive": archive_facts, "members": members, "required_members": _required(names),
                    "contents": contents, "findings": findings}
    except _ZIP_ERRORS:
        findings.append(finding("ARCHIVE_UNREADABLE", "capsule", "the ZIP structure could not be parsed"))
        return {"archive": _new_archive(ArchiveState.UNREADABLE), "members": [],
                "required_members": _required(None), "contents": None, "findings": findings}


__all__ = ("inventory_capsule",)
