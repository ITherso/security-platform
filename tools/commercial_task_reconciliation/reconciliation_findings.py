"""Stable Phase44 finding catalogue.

Every finding is derived from one fixed rule and one controlled subject, so
its identifier is stable for the same input. Remediation text is guidance
for a human reviewer; it never states that an operation was performed.
"""
from __future__ import annotations

from reconciliation_contracts import Category as C, Severity as S, fail, finding_sort_key, validate_finding

_RULES = {
    # rule: (category, severity, expected condition or None, remediation)
    "ARCHIVE_EMPTY": (C.INPUT_SIZE, S.BLOCKING, "a non-empty Phase43 portable capsule",
                      "Obtain the capsule again from its recorded export location and re-run this offline reconciliation."),
    "ARCHIVE_SIZE_LIMIT": (C.INPUT_SIZE, S.BLOCKING, "at most 131072 archive bytes",
                           "Do not process this archive further; request a capsule that fits the Phase43 limits."),
    "ARCHIVE_UNREADABLE": (C.ARCHIVE_STRUCTURE, S.BLOCKING, "a readable ZIP central directory",
                           "Treat the file as untrusted and unusable; obtain a fresh copy for a new reconciliation run."),
    "ARCHIVE_COMMENT_PRESENT": (C.ARCHIVE_STRUCTURE, S.BLOCKING, "an empty archive comment",
                                "Do not edit the archive by hand; request a canonical Phase43 capsule."),
    "ARCHIVE_MEMBER_COUNT_LIMIT": (C.ARCHIVE_STRUCTURE, S.BLOCKING, "exactly 4 members",
                                   "Reject this archive; a Phase43 capsule has exactly four members."),
    "ARCHIVE_EXPANDED_LIMIT": (C.INPUT_SIZE, S.BLOCKING, "at most 131072 declared expanded bytes",
                               "Do not expand this archive; request a capsule within the Phase43 limits."),
    "MEMBER_ORDER_NONCANONICAL": (C.ARCHIVE_STRUCTURE, S.BLOCKING,
                                  "task-request.json, response-contract.json, README.txt, capsule-manifest.json in order",
                                  "Request a canonical Phase43 capsule; member order is not repaired by this tool."),
    "MEMBER_UNEXPECTED": (C.MEMBER_NAME, S.BLOCKING, "only the four Phase43 member names",
                          "Reject this archive; an unexpected member must not be opened or extracted."),
    "MEMBER_DUPLICATE": (C.MEMBER_NAME, S.BLOCKING, "each member name exactly once",
                         "Reject this archive; duplicate entries make the represented content ambiguous."),
    "MEMBER_NAME_ABSOLUTE_PATH": (C.MEMBER_NAME, S.BLOCKING, "a plain relative member name",
                                  "Reject this archive and never extract it; absolute member paths are unsafe."),
    "MEMBER_NAME_PATH_TRAVERSAL": (C.MEMBER_NAME, S.BLOCKING, "a member name without '..' segments",
                                   "Reject this archive and never extract it; traversal names are unsafe."),
    "MEMBER_NAME_BACKSLASH_SEPARATOR": (C.MEMBER_NAME, S.BLOCKING, "no backslash in member names",
                                        "Reject this archive; backslash separators are not part of the Phase43 format."),
    "MEMBER_NAME_NESTED_PATH": (C.MEMBER_NAME, S.BLOCKING, "a flat member name without directories",
                                "Reject this archive; Phase43 capsules contain no directories."),
    "MEMBER_NAME_DIRECTORY_ENTRY": (C.MEMBER_NAME, S.BLOCKING, "regular file members only",
                                    "Reject this archive; directory entries are not part of the Phase43 format."),
    "MEMBER_NAME_CONTROL_CHARACTER": (C.MEMBER_NAME, S.BLOCKING, "printable ASCII member names",
                                      "Reject this archive; control characters in names are unsafe."),
    "MEMBER_NAME_NON_ASCII": (C.MEMBER_NAME, S.BLOCKING, "ASCII member names",
                              "Reject this archive; non-ASCII names are not part of the Phase43 format."),
    "MEMBER_NAME_EMPTY_NAME": (C.MEMBER_NAME, S.BLOCKING, "a non-empty member name",
                               "Reject this archive; an empty member name is not valid."),
    "MEMBER_NAME_OVERLONG_NAME": (C.MEMBER_NAME, S.BLOCKING, "a member name of at most 128 characters",
                                  "Reject this archive; overlong member names are not part of the Phase43 format."),
    "MEMBER_NAME_CASEFOLD_COLLISION": (C.MEMBER_NAME, S.BLOCKING, "names that stay distinct without case",
                                       "Reject this archive; case-insensitive name collisions are ambiguous."),
    "MEMBER_NOT_STORED": (C.MEMBER_METADATA, S.BLOCKING, "ZIP_STORED members",
                          "Do not decompress this member; request a canonical STORED Phase43 capsule."),
    "MEMBER_ENCRYPTED": (C.MEMBER_METADATA, S.BLOCKING, "unencrypted members",
                         "Reject this archive; encrypted members are not part of the Phase43 format."),
    "MEMBER_NOT_REGULAR_FILE": (C.MEMBER_METADATA, S.BLOCKING, "regular file entries",
                                "Reject this archive; links, directories or special entries are unsafe."),
    "MEMBER_OVERSIZED": (C.INPUT_SIZE, S.BLOCKING, "member sizes within the Phase43 member limits",
                         "Do not read this member; request a capsule within the Phase43 limits."),
    "MEMBER_EMPTY": (C.MEMBER_METADATA, S.BLOCKING, "a non-empty member",
                     "Request a complete Phase43 capsule; empty members are not repaired."),
    "MEMBER_SIZE_FIELDS_INCONSISTENT": (C.MEMBER_METADATA, S.BLOCKING, "equal stored and declared sizes",
                                        "Reject this archive; inconsistent size fields are not repaired."),
    "MEMBER_ZIP64_OR_EXTRA_FIELD": (C.MEMBER_METADATA, S.BLOCKING, "no ZIP64 markers and no extra fields",
                                    "Reject this archive; ZIP64 or extra-field metadata is not part of the Phase43 format."),
    "FINDINGS_TRUNCATED": (C.ARCHIVE_STRUCTURE, S.BLOCKING, "at most 400 findings for one capsule",
                           "Reject this archive; it produces more findings than one report lists."),
    "MEMBER_READ_ERROR": (C.MEMBER_CONTENT, S.BLOCKING, "a member readable with a correct CRC and size",
                          "Treat the member as corrupted; obtain a fresh copy of the capsule."),
    "REQUIRED_MEMBER_ABSENT": (C.ARCHIVE_STRUCTURE, S.BLOCKING, "the required Phase43 member",
                               "Request a complete Phase43 capsule; missing members are not reconstructed."),
    "MEMBER_MALFORMED_JSON": (C.MEMBER_CONTENT, S.BLOCKING, "strict UTF-8 JSON",
                              "Reject the member; malformed JSON is not repaired."),
    "MEMBER_DUPLICATE_JSON_KEY": (C.MEMBER_CONTENT, S.BLOCKING, "JSON objects without duplicate keys",
                                  "Reject the member; duplicate keys make the declared value ambiguous."),
    "MEMBER_JSON_CONTRACT_VIOLATION": (C.MEMBER_CONTENT, S.BLOCKING, "JSON within the Phase43 parser bounds",
                                       "Reject the member; it violates the owner JSON parser rules."),
    "MEMBER_NOT_JSON_OBJECT": (C.MEMBER_CONTENT, S.BLOCKING, "a JSON object",
                               "Reject the member; the Phase43 contract requires an object."),
    "MEMBER_NONCANONICAL_ENCODING": (C.MEMBER_CONTENT, S.BLOCKING, "canonical Phase43 JSON bytes",
                                     "Request a canonical capsule; whitespace or key order is not normalised here."),
    "MEMBER_OWNER_CONTRACT_REJECTED": (C.SCHEMA, S.BLOCKING, "a member accepted by the Phase43 owner validator",
                                       "Use the owner rejection code to locate the violated Phase43 rule."),
    "README_FIXED_TEXT_MISMATCH": (C.MEMBER_CONTENT, S.BLOCKING, "the fixed Phase43 README bytes",
                                   "Request a canonical capsule; README text is not rewritten by this tool."),
    "SCHEMA_ABSENT": (C.SCHEMA, S.BLOCKING, "a schema_version field",
                      "Reject the member; an unversioned document cannot be interpreted."),
    "SCHEMA_UNSUPPORTED": (C.SCHEMA, S.BLOCKING, "the supported Phase43 schema version",
                           "Do not interpret this member with a different schema; request a supported capsule."),
    "MANIFEST_FILES_NOT_LIST": (C.MANIFEST_CORRESPONDENCE, S.BLOCKING, "a files list in capsule-manifest.json",
                                "Reject the capsule; member hashes cannot be compared without a files list."),
    "MANIFEST_MALFORMED_ENTRY": (C.MANIFEST_CORRESPONDENCE, S.BLOCKING, "entries with exactly name, bytes and sha256",
                                 "Reject the capsule; malformed manifest entries are not repaired."),
    "MANIFEST_UNKNOWN_ENTRY": (C.MANIFEST_CORRESPONDENCE, S.BLOCKING, "entries only for the three payload members",
                               "Reject the capsule; the manifest declares members outside the Phase43 payload set."),
    "MANIFEST_DUPLICATE_ENTRY": (C.MANIFEST_CORRESPONDENCE, S.BLOCKING, "one manifest entry per payload member",
                                 "Reject the capsule; duplicate manifest entries are ambiguous."),
    "MANIFEST_ENTRY_NOT_DECLARED": (C.MANIFEST_CORRESPONDENCE, S.BLOCKING, "a manifest entry for the payload member",
                                    "Reject the capsule; an undeclared payload member is not bound by the manifest."),
    "MANIFEST_HASH_MISMATCH": (C.MANIFEST_CORRESPONDENCE, S.BLOCKING, "declared bytes and SHA256 equal to actual member bytes",
                               "Treat the member as altered relative to its manifest; do not use its content."),
    "MANIFEST_OWNER_MISMATCH": (C.MANIFEST_CORRESPONDENCE, S.BLOCKING, "a manifest equal to the Phase43 owner manifest",
                                "Reject the capsule; its inner manifest differs from the owner-derived manifest."),
    "IDENTITY_ABSENT": (C.FIELD_STRUCTURE, S.BLOCKING, "the required identity field",
                        "The capsule does not state this identity; obtain a complete capsule rather than inferring it."),
    "IDENTITY_NULL": (C.FIELD_STRUCTURE, S.BLOCKING, "a non-null identity value",
                      "The identity is explicitly null; do not substitute a local value for it."),
    "IDENTITY_EMPTY_STRING": (C.FIELD_STRUCTURE, S.BLOCKING, "a non-empty identity value",
                              "The identity is an empty string; do not substitute a local value for it."),
    "IDENTITY_EMPTY_ARRAY": (C.FIELD_STRUCTURE, S.BLOCKING, "a string identity value",
                             "The identity has the wrong type; obtain a canonical capsule."),
    "IDENTITY_EMPTY_OBJECT": (C.FIELD_STRUCTURE, S.BLOCKING, "a string identity value",
                              "The identity has the wrong type; obtain a canonical capsule."),
    "IDENTITY_INVALID": (C.FIELD_STRUCTURE, S.BLOCKING, "an identifier accepted by the Phase43 owner validator",
                         "The identity is malformed; it is withheld from this report and must not be used."),
    "FIELD_ABSENT": (C.FIELD_STRUCTURE, S.BLOCKING, "the required Phase43 field",
                     "Obtain a complete capsule; absent fields are not defaulted."),
    "FIELD_NULL": (C.FIELD_STRUCTURE, S.BLOCKING, "a non-null value",
                   "The field is explicitly null; it is not treated as absent, false or zero."),
    "FIELD_EMPTY_STRING": (C.FIELD_STRUCTURE, S.BLOCKING, "a non-empty value",
                           "The field is an empty string; it is not treated as absent or null."),
    "FIELD_EMPTY_ARRAY": (C.FIELD_STRUCTURE, S.BLOCKING, "a non-empty value of the Phase43 type",
                          "The field is an empty list; it is not treated as absent or zero."),
    "FIELD_EMPTY_OBJECT": (C.FIELD_STRUCTURE, S.BLOCKING, "a value of the Phase43 type",
                           "The field is an empty object; it is not treated as absent."),
    "FIELD_INVALID": (C.FIELD_STRUCTURE, S.BLOCKING, "a value accepted by the Phase43 owner validator",
                      "Use the owner rule code to locate the violated Phase43 rule."),
    "FIELD_UNEXPECTED": (C.FIELD_STRUCTURE, S.BLOCKING, "no fields outside the closed Phase43 model",
                         "Reject the capsule; unknown fields are neither interpreted nor echoed."),
    "TASK_ENTRY_NOT_OBJECT": (C.TASK_DECLARATION, S.BLOCKING, "each task entry is a JSON object",
                              "Reject the capsule; the task declaration is structurally inconsistent."),
    "TASK_COUNT_LIMIT": (C.TASK_DECLARATION, S.BLOCKING, "between 1 and 8 task entries",
                         "Reject the capsule; task entries beyond the limit were not interpreted."),
    "TASK_COUNT_DECLARATION_MISMATCH": (C.TASK_DECLARATION, S.BLOCKING, "counts.selected_task_count equal to the task entry count",
                                        "Reject the capsule; its declared count disagrees with its contents."),
    "TASK_DUPLICATE_REFERENCE": (C.TASK_DECLARATION, S.BLOCKING, "unique task IDs",
                                 "Reject the capsule; duplicate task references are ambiguous."),
    "TASK_DUPLICATE_BINDING": (C.TASK_DECLARATION, S.BLOCKING, "unique bindings per task",
                               "Reject the capsule; the same binding is claimed by several tasks."),
    "TASK_ORDER_NONCANONICAL": (C.TASK_DECLARATION, S.BLOCKING, "task IDs in ascending order",
                                "Request a canonical capsule; task order is not repaired."),
    "OWNER_READER_REJECTED": (C.OWNER_READER, S.BLOCKING, "acceptance by the Phase43 recipient reader",
                              "The capsule is not Phase43-compatible; use the owner code and the other findings to locate the cause."),
    "DIAGNOSTIC_OWNER_DISAGREEMENT": (C.OWNER_READER, S.BLOCKING, "agreement between Phase44 diagnostics and the Phase43 reader",
                                      "Escalate to a maintainer; the result is held fail-closed until the disagreement is explained."),
    "IDENTITY_MISMATCH": (C.LOCAL_IDENTITY, S.BLOCKING, "the capsule value equal to the local Phase42 task record",
                          "Hold the capsule; a reviewer should compare it with the local task record before any further use."),
    "AMBIGUOUS_BINDING_OWNER": (C.LOCAL_IDENTITY, S.BLOCKING, "the binding recorded locally for the same task",
                                "Hold the capsule; the binding belongs to a different local task and must be reviewed."),
    "DISCLOSURE_MISMATCH": (C.LOCAL_DISCLOSURE, S.BLOCKING, "the capsule value equal to the local Phase43 disclosure record",
                            "Hold the capsule; it does not correspond to what the local Phase43 record says was exported."),
    "LOCAL_RECORDS_NOT_SUPPLIED": (C.LOCAL_AVAILABILITY, S.WARNING, "local reference records supplied explicitly",
                                   "Re-run with the explicit local record group if full reconciliation is needed."),
    "LOCAL_TASK_NOT_FOUND": (C.LOCAL_AVAILABILITY, S.WARNING, "the claimed task in the supplied local records",
                             "Confirm with the record owner which local record group, if any, covers this task."),
    "LOCAL_BINDING_NOT_FOUND": (C.LOCAL_AVAILABILITY, S.WARNING, "the claimed binding in the supplied local records",
                                "Confirm with the record owner whether this binding was ever recorded locally."),
    "RECONCILIATION_NOT_PERFORMED": (C.TRUST_BOUNDARY, S.INFORMATIONAL, None,
                                     "Local records were not consulted because the capsule is structurally rejected."),
    "MANUAL_REVIEW_REQUIRED": (C.TRUST_BOUNDARY, S.INFORMATIONAL, None,
                               "A designated reviewer must decide on any further use; this report authorizes nothing."),
}


def finding(rule: str, subject: str, observed: str, expected: str | None = ...) -> dict:
    if rule not in _RULES:
        fail("unknown_finding_rule")
    category, severity, default_expected, remediation = _RULES[rule]
    return validate_finding({
        "finding_id": "P44-" + rule + ":" + subject, "rule": rule,
        "category": category.value, "severity": severity.value, "subject": subject,
        "observed_condition": observed,
        "expected_condition": default_expected if expected is ... else expected,
        "remediation": remediation,
    })


def ordered(findings: list) -> list:
    unique = {}
    for item in findings:
        if item["finding_id"] in unique:
            if unique[item["finding_id"]] != item:
                fail("conflicting_duplicate_finding")
            continue
        unique[item["finding_id"]] = item
    return sorted(unique.values(), key=finding_sort_key)


def rules() -> tuple:
    return tuple(_RULES)


__all__ = ("finding", "ordered", "rules")
