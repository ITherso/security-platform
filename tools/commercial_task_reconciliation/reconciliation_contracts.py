"""Closed Phase44 untrusted-capsule reconciliation v1 models; stdlib only.

These models describe an offline, local import of an untrusted Phase43
portable capsule. They are not producer proof, authorization, dispatch,
assignment, approval, submission or acceptance records. Phase43 contract
rules stay with the Phase43 owner modules; this file only defines the new
Phase44 request, report, inbox, manifest and inspection shapes.
"""
from __future__ import annotations

from enum import StrEnum
import re

from exchange_contracts import InputError, json_bytes

REQUEST_SCHEMA = "termivar-offline-task-capsule-reconciliation-request/v1"
REPORT_SCHEMA = "termivar-offline-task-capsule-reconciliation-report/v1"
INBOX_SCHEMA = "termivar-offline-untrusted-task-inbox-record/v1"
OUTPUT_MANIFEST_SCHEMA = "termivar-offline-task-capsule-reconciliation-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-task-capsule-reconciliation-inspection/v1"
DEMO_LABEL = ("OFFLINE DEMONSTRATION — UNTRUSTED CAPSULE RECONCILIATION ONLY — "
              "NO TASK DISPATCH, ASSIGNMENT, APPROVAL, EXECUTION OR SUBMISSION")
COMMON_FIELDS = ("schema_version", "demo_label", "demo_only", "trust_state", "non_claims", "limitations")

MAX_REQUEST_BYTES = 8 * 1024
MAX_REPORT_BYTES = 512 * 1024
MAX_INBOX_BYTES = 64 * 1024
MAX_SUMMARY_BYTES = 256 * 1024
MAX_OUTPUT_MANIFEST_BYTES = 32 * 1024
MAX_INSPECTION_BYTES = 32 * 1024
MAX_LISTED_MEMBERS = 16
MAX_LISTED_NAMES = 16
MAX_FINDINGS = 400
MAX_COMPARISONS = 400

_SAFE_MEMBER_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_SAFE_FIELD_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
_SAFE_SCHEMA = re.compile(r"[a-z0-9][a-z0-9.-]{0,95}/v[0-9]{1,3}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_FINDING_ID = re.compile(r"P44-[A-Z0-9_]{3,64}:[A-Za-z0-9_.:\[\]#-]{1,160}")

NON_CLAIMS = (
    "producer_authenticated", "cryptographic_trust_established", "secure_transport_verified",
    "source_provenance_verified", "real_world_observation_verified", "task_dispatched",
    "task_assigned", "task_approved", "task_accepted", "task_executed", "task_completed",
    "response_submitted", "external_submission_performed", "production_acceptance",
)
LIMITATIONS = (
    "untrusted_import_not_authenticated", "valid_structure_is_not_trust",
    "hash_correspondence_is_not_producer_authentication", "local_records_are_recorded_metadata_not_source_truth",
    "no_dispatch_assignment_approval_execution_or_submission", "manual_review_required_before_any_further_use",
    "original_binding_preimage_not_reconstructed", "minimization_is_not_anonymization",
)


class TrustState(StrEnum):
    UNTRUSTED = "UNTRUSTED_IMPORT_NOT_AUTHENTICATED"


class LocalReferenceMode(StrEnum):
    NONE = "NO_LOCAL_RECORDS"
    PHASE42_ONLY = "PHASE42_TASK_RECORDS_ONLY"
    PHASE43_ONLY = "PHASE43_DISCLOSURE_RECORDS_ONLY"
    BOTH = "PHASE42_TASK_RECORDS_AND_PHASE43_DISCLOSURE_RECORDS"


class ArchiveState(StrEnum):
    READABLE = "READABLE"
    EMPTY_INPUT = "EMPTY_INPUT"
    SIZE_LIMIT_EXCEEDED = "SIZE_LIMIT_EXCEEDED"
    UNREADABLE = "UNREADABLE"


class Verdict(StrEnum):
    ACCEPTABLE = "ACCEPTABLE"
    REJECTED = "REJECTED"
    NOT_EVALUATED = "NOT_EVALUATED"


class Ordering(StrEnum):
    CANONICAL = "CANONICAL"
    NONCANONICAL = "NONCANONICAL"
    NOT_EVALUATED = "NOT_EVALUATED"


class Presence(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    DUPLICATED = "DUPLICATED"
    NOT_EVALUATED = "NOT_EVALUATED"


class NameState(StrEnum):
    EXPECTED = "EXPECTED"
    UNEXPECTED = "UNEXPECTED"


class NameHazard(StrEnum):
    ABSOLUTE_PATH = "ABSOLUTE_PATH"
    PATH_TRAVERSAL = "PATH_TRAVERSAL"
    BACKSLASH_SEPARATOR = "BACKSLASH_SEPARATOR"
    NESTED_PATH = "NESTED_PATH"
    DIRECTORY_ENTRY = "DIRECTORY_ENTRY"
    CONTROL_CHARACTER = "CONTROL_CHARACTER"
    NON_ASCII = "NON_ASCII"
    EMPTY_NAME = "EMPTY_NAME"
    OVERLONG_NAME = "OVERLONG_NAME"
    CASEFOLD_COLLISION = "CASEFOLD_COLLISION"


class Compression(StrEnum):
    STORED = "STORED"
    NOT_STORED = "NOT_STORED"


class Encryption(StrEnum):
    NOT_ENCRYPTED = "NOT_ENCRYPTED"
    ENCRYPTED = "ENCRYPTED"


class EntryType(StrEnum):
    REGULAR_FILE = "REGULAR_FILE"
    DIRECTORY = "DIRECTORY"
    SYMLINK = "SYMLINK"
    OTHER = "OTHER"
    UNSPECIFIED = "UNSPECIFIED"


class SizeState(StrEnum):
    WITHIN_LIMIT = "WITHIN_LIMIT"
    OVER_LIMIT = "OVER_LIMIT"
    EMPTY = "EMPTY"
    SIZE_FIELDS_INCONSISTENT = "SIZE_FIELDS_INCONSISTENT"
    DECLARED_SIZE_UNREPRESENTABLE = "DECLARED_SIZE_UNREPRESENTABLE"


class ContentState(StrEnum):
    NOT_EVALUATED = "NOT_EVALUATED"
    PARSED = "PARSED"
    MALFORMED_JSON = "MALFORMED_JSON"
    DUPLICATE_JSON_KEY = "DUPLICATE_JSON_KEY"
    JSON_CONTRACT_VIOLATION = "JSON_CONTRACT_VIOLATION"
    FIXED_TEXT_MATCH = "FIXED_TEXT_MATCH"
    FIXED_TEXT_MISMATCH = "FIXED_TEXT_MISMATCH"
    READ_ERROR = "READ_ERROR"


class SchemaState(StrEnum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    ABSENT = "ABSENT"
    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OwnerContract(StrEnum):
    OWNER_VALID = "OWNER_VALID"
    OWNER_REJECTED = "OWNER_REJECTED"
    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Encoding(StrEnum):
    CANONICAL = "CANONICAL"
    NONCANONICAL = "NONCANONICAL"
    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ValueKind(StrEnum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    NULL = "NULL"
    ARRAY = "ARRAY"
    OBJECT = "OBJECT"
    ABSENT = "ABSENT"
    NOT_EVALUATED = "NOT_EVALUATED"


class FieldState(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    NULL = "NULL"
    EMPTY_STRING = "EMPTY_STRING"
    EMPTY_ARRAY = "EMPTY_ARRAY"
    EMPTY_OBJECT = "EMPTY_OBJECT"
    ABSENT = "ABSENT"
    NOT_EVALUATED = "NOT_EVALUATED"


class ValueDisclosure(StrEnum):
    ECHOED = "ECHOED"
    WITHHELD_INVALID_STRING = "WITHHELD_INVALID_STRING"
    WITHHELD_COMPOSITE = "WITHHELD_COMPOSITE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EntryShape(StrEnum):
    OBJECT = "OBJECT"
    NOT_OBJECT = "NOT_OBJECT"


class Correspondence(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    NOT_DECLARED = "NOT_DECLARED"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    NOT_EVALUATED = "NOT_EVALUATED"


class Compatibility(StrEnum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"


class Consistency(StrEnum):
    CONSISTENT = "CONSISTENT"
    INCONSISTENT = "INCONSISTENT"
    NOT_EVALUATED = "NOT_EVALUATED"


class RepresentedState(StrEnum):
    ESTABLISHED_BY_PHASE43_OWNER_READER = "ESTABLISHED_BY_PHASE43_OWNER_READER"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


class Comparison(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"


class ReferenceSource(StrEnum):
    PHASE42_LOCAL_TASK_RECORD = "PHASE42_LOCAL_TASK_RECORD"
    PHASE43_LOCAL_DISCLOSURE_RECORD = "PHASE43_LOCAL_DISCLOSURE_RECORD"


class LocalDisclosure(StrEnum):
    ECHOED = "ECHOED"
    WITHHELD_NOT_PREVIOUSLY_DISCLOSED = "WITHHELD_NOT_PREVIOUSLY_DISCLOSED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class Lookup(StrEnum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    NOT_SUPPLIED = "NOT_SUPPLIED"
    NOT_PERFORMED = "NOT_PERFORMED"


class ReconciliationState(StrEnum):
    PERFORMED = "PERFORMED"
    NOT_PERFORMED_STRUCTURAL_REJECTION = "NOT_PERFORMED_STRUCTURAL_REJECTION"


class Eligibility(StrEnum):
    STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW = "STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW"
    STRUCTURAL_REJECTION = "STRUCTURAL_REJECTION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    LOCAL_RECONCILIATION_UNAVAILABLE = "LOCAL_RECONCILIATION_UNAVAILABLE"


class ManualReview(StrEnum):
    ELIGIBLE_FOR_MANUAL_REVIEW = "ELIGIBLE_FOR_MANUAL_REVIEW"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


class ManualReviewRequirement(StrEnum):
    REQUIRED = "REQUIRED"


class Lifecycle(StrEnum):
    QUARANTINED_AWAITING_MANUAL_REVIEW = "QUARANTINED_AWAITING_MANUAL_REVIEW"
    QUARANTINED_HELD_IDENTITY_MISMATCH = "QUARANTINED_HELD_IDENTITY_MISMATCH"
    QUARANTINED_HELD_LOCAL_RECONCILIATION_UNAVAILABLE = "QUARANTINED_HELD_LOCAL_RECONCILIATION_UNAVAILABLE"
    REJECTED_NOT_ADMITTED = "REJECTED_NOT_ADMITTED"


class FactOrigin(StrEnum):
    CAPSULE_DECLARED_STRUCTURALLY_VALID_NOT_AUTHENTICATED = "CAPSULE_DECLARED_STRUCTURALLY_VALID_NOT_AUTHENTICATED"


class Severity(StrEnum):
    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFORMATIONAL = "INFORMATIONAL"


class Category(StrEnum):
    INPUT_SIZE = "INPUT_SIZE"
    ARCHIVE_STRUCTURE = "ARCHIVE_STRUCTURE"
    MEMBER_NAME = "MEMBER_NAME"
    MEMBER_METADATA = "MEMBER_METADATA"
    MEMBER_CONTENT = "MEMBER_CONTENT"
    SCHEMA = "SCHEMA"
    MANIFEST_CORRESPONDENCE = "MANIFEST_CORRESPONDENCE"
    FIELD_STRUCTURE = "FIELD_STRUCTURE"
    TASK_DECLARATION = "TASK_DECLARATION"
    OWNER_READER = "OWNER_READER"
    LOCAL_IDENTITY = "LOCAL_IDENTITY"
    LOCAL_DISCLOSURE = "LOCAL_DISCLOSURE"
    LOCAL_AVAILABILITY = "LOCAL_AVAILABILITY"
    TRUST_BOUNDARY = "TRUST_BOUNDARY"


class Agreement(StrEnum):
    AGREES = "AGREES"


class Regeneration(StrEnum):
    BYTE_IDENTICAL = "BYTE_IDENTICAL"


class CheckResult(StrEnum):
    PASSED = "PASSED"


STRUCTURAL_CATEGORIES = frozenset({
    Category.INPUT_SIZE, Category.ARCHIVE_STRUCTURE, Category.MEMBER_NAME, Category.MEMBER_METADATA,
    Category.MEMBER_CONTENT, Category.SCHEMA, Category.MANIFEST_CORRESPONDENCE,
    Category.FIELD_STRUCTURE, Category.TASK_DECLARATION, Category.OWNER_READER,
})
SEVERITY_RANK = {Severity.BLOCKING: 0, Severity.WARNING: 1, Severity.INFORMATIONAL: 2}
LIFECYCLE_FOR_STATUS = {
    Eligibility.STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW: Lifecycle.QUARANTINED_AWAITING_MANUAL_REVIEW,
    Eligibility.IDENTITY_MISMATCH: Lifecycle.QUARANTINED_HELD_IDENTITY_MISMATCH,
    Eligibility.LOCAL_RECONCILIATION_UNAVAILABLE: Lifecycle.QUARANTINED_HELD_LOCAL_RECONCILIATION_UNAVAILABLE,
    Eligibility.STRUCTURAL_REJECTION: Lifecycle.REJECTED_NOT_ADMITTED,
}


def fail(code: str):
    raise InputError("task_reconciliation_invalid_" + code)


def closed(value: object, fields: tuple, code: str) -> dict:
    if type(value) is not dict or any(type(key) is not str for key in value) or set(value) != set(fields):
        fail(code)
    return value


def expect(value: object, expected: object, code: str) -> None:
    """Exact typed equality through canonical JSON; bool is never an int."""
    if type(value) is not type(expected) or json_bytes(value) != json_bytes(expected):
        fail(code)


def member(value: object, enum_type: type[StrEnum], code: str) -> str:
    if type(value) is not str or value not in {item.value for item in enum_type}:
        fail(code)
    return value


SAFE_INTEGER = 2**53 - 1      # the owner JSON parser/encoder integer bound


def count(value: object, code: str, maximum: int = SAFE_INTEGER) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        fail(code)
    return value


def optional_count(value: object, code: str) -> int | None:
    return None if value is None else count(value, code)


def digest(value: object, code: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        fail(code)
    return value


def optional_digest(value: object, code: str) -> str | None:
    return None if value is None else digest(value, code)


def text(value: object, code: str, maximum: int = 512) -> str:
    if type(value) is not str or not 0 < len(value) <= maximum or any(ord(char) < 32 for char in value):
        fail(code)
    return value


def scalar(value: object, code: str) -> object:
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is str and len(value) <= 512:
        return value
    fail(code)


def safe_member_name(value: object) -> str | None:
    return value if type(value) is str and _SAFE_MEMBER_NAME.fullmatch(value) else None


def safe_field_name(value: object) -> str | None:
    return value if type(value) is str and _SAFE_FIELD_NAME.fullmatch(value) else None


def safe_schema(value: object) -> str | None:
    return value if type(value) is str and _SAFE_SCHEMA.fullmatch(value) else None


def non_claims() -> dict:
    return {flag: False for flag in NON_CLAIMS}


def common(schema: str) -> dict:
    if schema not in (REPORT_SCHEMA, INBOX_SCHEMA, OUTPUT_MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "demo_label": DEMO_LABEL, "demo_only": True,
            "trust_state": TrustState.UNTRUSTED.value, "non_claims": non_claims(),
            "limitations": list(LIMITATIONS)}


def _common_row(value: object, schema: str, fields: tuple, maximum: int, code: str) -> dict:
    json_bytes(value, maximum=maximum)
    row = closed(value, (*COMMON_FIELDS, *fields), code + "_fields")
    expect({key: row[key] for key in COMMON_FIELDS}, common(schema), code + "_common_fields")
    return row


def _list(value: object, code: str, maximum: int, item=None) -> list:
    if type(value) is not list or len(value) > maximum:
        fail(code)
    if item is not None:
        for entry in value:
            item(entry)
    return value


def _identity(value: object, code: str) -> dict:
    row = closed(value, ("bytes", "sha256"), code)
    count(row["bytes"], code + "_bytes")
    digest(row["sha256"], code + "_sha256")
    return row


# ---------------------------------------------------------------- request

REQUEST_FIELDS = ("schema_version", "mode", "request_reference", "local_reference_mode",
                  "expected_local_phase42_register_sha256", "expected_local_phase43_index_sha256")


def uses_phase42(mode: str) -> bool:
    return mode in (LocalReferenceMode.PHASE42_ONLY, LocalReferenceMode.BOTH)


def uses_phase43(mode: str) -> bool:
    return mode in (LocalReferenceMode.PHASE43_ONLY, LocalReferenceMode.BOTH)


def validate_request(value: object) -> dict:
    from exchange_contracts import identifier

    json_bytes(value, maximum=MAX_REQUEST_BYTES)
    row = closed(value, REQUEST_FIELDS, "request_fields")
    expect(row["schema_version"], REQUEST_SCHEMA, "request_schema")
    expect(row["mode"], "demo", "request_mode")
    try:
        identifier(row["request_reference"], "request_reference")
    except InputError:
        fail("request_reference")
    mode = member(row["local_reference_mode"], LocalReferenceMode, "request_local_reference_mode")
    for key, used in (("expected_local_phase42_register_sha256", uses_phase42(mode)),
                      ("expected_local_phase43_index_sha256", uses_phase43(mode))):
        if used:
            digest(row[key], "request_expected_local_pin")
        elif row[key] is not None:
            fail("request_unused_local_pin_must_be_null")
    return dict(row)


# ---------------------------------------------------------------- report

ARCHIVE_FIELDS = ("archive_state", "member_count", "listed_member_count", "omitted_member_count",
                  "declared_expanded_bytes", "member_order", "archive_comment", "container_verdict")
MEMBER_FIELDS = ("position", "name", "name_length", "name_sha256", "name_state", "name_hazards",
                 "occurrence_count", "declared_size", "compressed_size", "compression", "encryption",
                 "entry_type", "size_state")
CONTENT_FIELDS = ("name", "content_state", "owner_rejection_code", "schema_state", "declared_schema",
                  "canonical_encoding", "owner_contract")
MANIFEST_ENTRY_FIELDS = ("member", "declared_bytes", "declared_sha256", "actual_bytes", "actual_sha256", "result")
MANIFEST_FIELDS = ("manifest_state", "entries", "unknown_entry_count", "duplicate_entry_count",
                   "malformed_entry_count", "fixed_fields")
FIELD_RECORD_FIELDS = ("path", "presence", "value_kind", "state", "value_disclosure", "value",
                       "string_length", "string_sha256", "item_count", "owner_rule_code")
UNEXPECTED_FIELDS = ("count", "listed_names", "unlisted_count")
TASK_RECORD_FIELDS = ("position", "entry_shape", "fields", "unexpected_fields")
DECLARATION_FIELDS = ("tasks_field_state", "declared_task_count", "actual_task_entry_count",
                      "interpreted_task_entry_count", "consistency")
PRESENCE_SUMMARY_FIELDS = ("present_valid", "absent", "null", "empty_string", "empty_array", "empty_object",
                           "invalid", "not_evaluated", "unexpected")
IDENTITY_TASK_FIELDS = ("position", "task_id", "reference_id", "candidate_id", "file_id", "binding_digest")
CAPSULE_IDENTITY_FIELDS = ("declared_schema", "declared_tasks", "source_declaration", "represented_state",
                           "represented_tasks", "claimed_vs_represented")
SOURCE_DECLARATION_FIELDS = ("source_phase42_register_sha256", "source_phase42_manifest_sha256", "request_reference")
LOCAL_REFERENCE_FIELDS = ("mode", "phase42", "phase43")
LOCAL_PHASE42_FIELDS = ("register_sha256", "manifest_sha256")
LOCAL_PHASE43_FIELDS = ("index_sha256", "capsule_sha256", "manifest_sha256")
LOOKUP_FIELDS = ("subject", "task_id", "phase42_lookup", "phase43_lookup")
COMPARISON_FIELDS = ("subject", "field", "reference_source", "capsule_value", "capsule_value_state",
                     "local_value", "local_value_disclosure", "result")
RECONCILIATION_FIELDS = ("state", "task_lookups", "comparisons")
FINDING_FIELDS = ("finding_id", "rule", "category", "severity", "subject", "observed_condition",
                  "expected_condition", "remediation")
ELIGIBILITY_FIELDS = ("status", "manual_review", "manual_review_requirement", "basis_finding_ids")
OWNER_READER_FIELDS = ("compatibility", "owner_rejection_code")
REPORT_FIELDS = ("request_reference", "capsule", "archive", "members", "required_members", "member_contents",
                 "manifest_correspondence", "phase43_reader", "envelope_fields", "envelope_unexpected_fields",
                 "tasks", "task_declaration", "field_presence_summary", "capsule_identity", "local_reference",
                 "local_reconciliation", "findings", "eligibility")


def _owner_code(value: object, code: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9_]{1,160}", value) is None:
        fail(code)
    return value


def _names(value: object, code: str, pattern) -> list:
    _list(value, code, MAX_LISTED_NAMES)
    for name in value:
        if type(name) is not str or pattern(name) is None:
            fail(code)
    if value != sorted(set(value)):
        fail(code + "_order")
    return value


def validate_field_record(value: object) -> dict:
    row = closed(value, FIELD_RECORD_FIELDS, "field_record_fields")
    text(row["path"], "field_record_path", 160)
    presence = member(row["presence"], Presence, "field_record_presence")
    kind = member(row["value_kind"], ValueKind, "field_record_kind")
    state = member(row["state"], FieldState, "field_record_state")
    disclosure = member(row["value_disclosure"], ValueDisclosure, "field_record_disclosure")
    scalar(row["value"], "field_record_value")
    optional_count(row["string_length"], "field_record_string_length")
    optional_digest(row["string_sha256"], "field_record_string_sha256")
    optional_count(row["item_count"], "field_record_item_count")
    _owner_code(row["owner_rule_code"], "field_record_owner_code")
    if presence == Presence.DUPLICATED:
        fail("field_record_presence")
    if (presence == Presence.ABSENT) != (state == FieldState.ABSENT) or (
            (presence == Presence.ABSENT) != (kind == ValueKind.ABSENT)):
        fail("field_record_absence")
    if (presence == Presence.NOT_EVALUATED) != (kind == ValueKind.NOT_EVALUATED) or (
            presence == Presence.NOT_EVALUATED and state != FieldState.NOT_EVALUATED):
        fail("field_record_not_evaluated")
    if presence != Presence.PRESENT and disclosure != ValueDisclosure.NOT_APPLICABLE:
        fail("field_record_absent_disclosure")
    if presence == Presence.PRESENT and disclosure == ValueDisclosure.NOT_APPLICABLE:
        fail("field_record_present_disclosure")
    if (kind == ValueKind.STRING) != (row["string_length"] is not None) or (
            (kind == ValueKind.STRING) != (row["string_sha256"] is not None)):
        fail("field_record_string_identity")
    if (kind in (ValueKind.ARRAY, ValueKind.OBJECT)) != (row["item_count"] is not None):
        fail("field_record_item_count_kind")
    if disclosure != ValueDisclosure.ECHOED and row["value"] is not None:
        fail("field_record_withheld_value")
    if (state == FieldState.NULL) != (kind == ValueKind.NULL):
        fail("field_record_null")
    if disclosure == ValueDisclosure.WITHHELD_INVALID_STRING and (
            kind != ValueKind.STRING or row["string_sha256"] is None or row["string_length"] is None):
        fail("field_record_withheld_string")
    if disclosure == ValueDisclosure.ECHOED and kind in (ValueKind.ARRAY, ValueKind.OBJECT):
        fail("field_record_composite_echo")
    if disclosure == ValueDisclosure.ECHOED and type(row["value"]) is not {
            ValueKind.STRING: str, ValueKind.INTEGER: int, ValueKind.BOOLEAN: bool,
            ValueKind.NULL: type(None)}.get(ValueKind(kind)):
        fail("field_record_echo_kind")
    if disclosure == ValueDisclosure.WITHHELD_COMPOSITE and kind not in (ValueKind.ARRAY, ValueKind.OBJECT):
        fail("field_record_withheld_composite")
    if state == FieldState.EMPTY_STRING and (kind != ValueKind.STRING or row["value"] != ""):
        fail("field_record_empty_string")
    if state == FieldState.EMPTY_ARRAY and (kind != ValueKind.ARRAY or row["item_count"] != 0):
        fail("field_record_empty_array")
    if state == FieldState.EMPTY_OBJECT and (kind != ValueKind.OBJECT or row["item_count"] != 0):
        fail("field_record_empty_object")
    return row


def _unexpected(value: object, code: str) -> dict:
    row = closed(value, UNEXPECTED_FIELDS, code)
    total = count(row["count"], code + "_count")
    _names(row["listed_names"], code + "_names", safe_field_name)
    if count(row["unlisted_count"], code + "_unlisted") + len(row["listed_names"]) != total:
        fail(code + "_total")
    return row


def validate_finding(value: object) -> dict:
    row = closed(value, FINDING_FIELDS, "finding_fields")
    if type(row["finding_id"]) is not str or _FINDING_ID.fullmatch(row["finding_id"]) is None:
        fail("finding_id")
    text(row["rule"], "finding_rule", 64)
    if row["finding_id"] != "P44-" + row["rule"] + ":" + row["subject"]:
        fail("finding_id_derivation")
    member(row["category"], Category, "finding_category")
    member(row["severity"], Severity, "finding_severity")
    text(row["subject"], "finding_subject", 160)
    text(row["observed_condition"], "finding_observed")
    if row["expected_condition"] is not None:
        text(row["expected_condition"], "finding_expected")
    text(row["remediation"], "finding_remediation")
    return row


def validate_comparison(value: object) -> dict:
    row = closed(value, COMPARISON_FIELDS, "comparison_fields")
    text(row["subject"], "comparison_subject", 160)
    text(row["field"], "comparison_field", 64)
    member(row["reference_source"], ReferenceSource, "comparison_source")
    scalar(row["capsule_value"], "comparison_capsule_value")
    member(row["capsule_value_state"], FieldState, "comparison_capsule_state")
    scalar(row["local_value"], "comparison_local_value")
    disclosure = member(row["local_value_disclosure"], LocalDisclosure, "comparison_local_disclosure")
    result = member(row["result"], Comparison, "comparison_result")
    if disclosure != LocalDisclosure.ECHOED and row["local_value"] is not None:
        fail("comparison_withheld_local_value")
    if row["capsule_value_state"] != FieldState.VALID and row["capsule_value"] is not None:
        fail("comparison_invalid_capsule_value_echo")
    if result == Comparison.MATCH and (row["capsule_value_state"] != FieldState.VALID
                                       or disclosure != LocalDisclosure.ECHOED
                                       or json_bytes(row["capsule_value"]) != json_bytes(row["local_value"])):
        fail("comparison_match_semantics")
    if result == Comparison.MISMATCH and row["capsule_value_state"] != FieldState.VALID:
        fail("comparison_mismatch_semantics")
    if result == Comparison.MISMATCH and disclosure == LocalDisclosure.ECHOED and (
            json_bytes(row["capsule_value"]) == json_bytes(row["local_value"])):
        fail("comparison_mismatch_equal_values")
    if result == Comparison.UNAVAILABLE and disclosure == LocalDisclosure.ECHOED:
        fail("comparison_unavailable_semantics")
    if result == Comparison.NOT_COMPARABLE and disclosure != LocalDisclosure.NOT_AVAILABLE:
        fail("comparison_not_comparable_semantics")
    return row


def _identity_task(value: object) -> dict:
    row = closed(value, IDENTITY_TASK_FIELDS, "identity_task_fields")
    count(row["position"], "identity_task_position", 64)
    for key in IDENTITY_TASK_FIELDS[1:]:
        if row[key] is not None:
            text(row[key], "identity_task_value", 160)
    return row


def validate_report(value: object) -> dict:
    row = _common_row(value, REPORT_SCHEMA, REPORT_FIELDS, MAX_REPORT_BYTES, "report")
    from exchange_contracts import identifier

    identifier(row["request_reference"], "report_request_reference")
    _identity(row["capsule"], "report_capsule")
    archive = closed(row["archive"], ARCHIVE_FIELDS, "report_archive_fields")
    member(archive["archive_state"], ArchiveState, "report_archive_state")
    optional_count(archive["member_count"], "report_member_count")
    count(archive["listed_member_count"], "report_listed_members", MAX_LISTED_MEMBERS)
    count(archive["omitted_member_count"], "report_omitted_members")
    optional_count(archive["declared_expanded_bytes"], "report_expanded_bytes")
    member(archive["member_order"], Ordering, "report_member_order")
    member(archive["archive_comment"], Presence, "report_archive_comment")
    member(archive["container_verdict"], Verdict, "report_container_verdict")
    members = _list(row["members"], "report_members", MAX_LISTED_MEMBERS)
    for item in members:
        entry = closed(item, MEMBER_FIELDS, "report_member_fields")
        count(entry["position"], "report_member_position")
        if entry["name"] is not None and safe_member_name(entry["name"]) is None:
            fail("report_member_unsafe_name_echo")
        count(entry["name_length"], "report_member_name_length", 65535)
        digest(entry["name_sha256"], "report_member_name_sha256")
        member(entry["name_state"], NameState, "report_member_name_state")
        _list(entry["name_hazards"], "report_member_hazards", len(NameHazard))
        for hazard in entry["name_hazards"]:
            member(hazard, NameHazard, "report_member_hazard")
        if entry["name_hazards"] != sorted(set(entry["name_hazards"])):
            fail("report_member_hazard_order")
        count(entry["occurrence_count"], "report_member_occurrences")
        optional_count(entry["declared_size"], "report_member_declared_size")
        optional_count(entry["compressed_size"], "report_member_compressed_size")
        member(entry["compression"], Compression, "report_member_compression")
        member(entry["encryption"], Encryption, "report_member_encryption")
        member(entry["entry_type"], EntryType, "report_member_entry_type")
        member(entry["size_state"], SizeState, "report_member_size_state")
    if len(members) != archive["listed_member_count"]:
        fail("report_listed_member_count")
    if archive["member_count"] is not None and archive["member_count"] != len(members) + archive["omitted_member_count"]:
        fail("report_member_total")
    for item in _list(row["required_members"], "report_required_members", 8):
        entry = closed(item, ("name", "presence"), "report_required_member_fields")
        if safe_member_name(entry["name"]) is None:
            fail("report_required_member_name")
        member(entry["presence"], Presence, "report_required_member_presence")
    for item in _list(row["member_contents"], "report_member_contents", 8):
        entry = closed(item, CONTENT_FIELDS, "report_content_fields")
        if safe_member_name(entry["name"]) is None:
            fail("report_content_name")
        member(entry["content_state"], ContentState, "report_content_state")
        _owner_code(entry["owner_rejection_code"], "report_content_owner_code")
        member(entry["schema_state"], SchemaState, "report_content_schema_state")
        if entry["declared_schema"] is not None and safe_schema(entry["declared_schema"]) is None:
            fail("report_content_declared_schema")
        member(entry["canonical_encoding"], Encoding, "report_content_encoding")
        member(entry["owner_contract"], OwnerContract, "report_content_owner_contract")
    manifest = closed(row["manifest_correspondence"], MANIFEST_FIELDS, "report_manifest_fields")
    member(manifest["manifest_state"], ContentState, "report_manifest_state")
    for item in _list(manifest["entries"], "report_manifest_entries", 8):
        entry = closed(item, MANIFEST_ENTRY_FIELDS, "report_manifest_entry_fields")
        if safe_member_name(entry["member"]) is None:
            fail("report_manifest_entry_member")
        optional_count(entry["declared_bytes"], "report_manifest_declared_bytes")
        optional_digest(entry["declared_sha256"], "report_manifest_declared_sha256")
        optional_count(entry["actual_bytes"], "report_manifest_actual_bytes")
        optional_digest(entry["actual_sha256"], "report_manifest_actual_sha256")
        member(entry["result"], Correspondence, "report_manifest_entry_result")
    for key in ("unknown_entry_count", "duplicate_entry_count", "malformed_entry_count"):
        count(manifest[key], "report_manifest_" + key)
    member(manifest["fixed_fields"], Correspondence, "report_manifest_fixed_fields")
    reader = closed(row["phase43_reader"], OWNER_READER_FIELDS, "report_owner_reader_fields")
    compatibility = member(reader["compatibility"], Compatibility, "report_owner_compatibility")
    _owner_code(reader["owner_rejection_code"], "report_owner_rejection_code")
    if (compatibility == Compatibility.COMPATIBLE) != (reader["owner_rejection_code"] is None):
        fail("report_owner_reader_semantics")
    _list(row["envelope_fields"], "report_envelope_fields", 32, validate_field_record)
    _unexpected(row["envelope_unexpected_fields"], "report_envelope_unexpected")
    for item in _list(row["tasks"], "report_tasks", 8):
        task = closed(item, TASK_RECORD_FIELDS, "report_task_fields")
        count(task["position"], "report_task_position", 64)
        member(task["entry_shape"], EntryShape, "report_task_shape")
        _list(task["fields"], "report_task_field_records", 16, validate_field_record)
        _unexpected(task["unexpected_fields"], "report_task_unexpected")
    declaration = closed(row["task_declaration"], DECLARATION_FIELDS, "report_declaration_fields")
    member(declaration["tasks_field_state"], FieldState, "report_declaration_tasks_state")
    optional_count(declaration["declared_task_count"], "report_declared_task_count")
    optional_count(declaration["actual_task_entry_count"], "report_actual_task_count")
    count(declaration["interpreted_task_entry_count"], "report_interpreted_task_count", 8)
    member(declaration["consistency"], Consistency, "report_declaration_consistency")
    summary = closed(row["field_presence_summary"], PRESENCE_SUMMARY_FIELDS, "report_presence_summary_fields")
    for key in PRESENCE_SUMMARY_FIELDS:
        _list(summary[key], "report_presence_summary_list", 400)
        for path in summary[key]:
            text(path, "report_presence_summary_path", 160)
        if summary[key] != sorted(set(summary[key])):
            fail("report_presence_summary_order")
    identity = closed(row["capsule_identity"], CAPSULE_IDENTITY_FIELDS, "report_identity_fields")
    if identity["declared_schema"] is not None and safe_schema(identity["declared_schema"]) is None:
        fail("report_identity_declared_schema")
    _list(identity["declared_tasks"], "report_identity_declared_tasks", 8, _identity_task)
    source = closed(identity["source_declaration"], SOURCE_DECLARATION_FIELDS, "report_identity_source_fields")
    optional_digest(source["source_phase42_register_sha256"], "report_identity_source_register")
    optional_digest(source["source_phase42_manifest_sha256"], "report_identity_source_manifest")
    if source["request_reference"] is not None:
        identifier(source["request_reference"], "report_identity_request_reference")
    represented = member(identity["represented_state"], RepresentedState, "report_identity_represented_state")
    _list(identity["represented_tasks"], "report_identity_represented_tasks", 8, _identity_task)
    if represented == RepresentedState.NOT_ESTABLISHED and identity["represented_tasks"]:
        fail("report_identity_unestablished_tasks")
    member(identity["claimed_vs_represented"], Correspondence, "report_identity_claimed_vs_represented")
    local = closed(row["local_reference"], LOCAL_REFERENCE_FIELDS, "report_local_reference_fields")
    mode = member(local["mode"], LocalReferenceMode, "report_local_reference_mode")
    if uses_phase42(mode):
        entry = closed(local["phase42"], LOCAL_PHASE42_FIELDS, "report_local_phase42_fields")
        for key in LOCAL_PHASE42_FIELDS:
            digest(entry[key], "report_local_phase42_digest")
    elif local["phase42"] is not None:
        fail("report_local_phase42_must_be_null")
    if uses_phase43(mode):
        entry = closed(local["phase43"], LOCAL_PHASE43_FIELDS, "report_local_phase43_fields")
        for key in LOCAL_PHASE43_FIELDS:
            digest(entry[key], "report_local_phase43_digest")
    elif local["phase43"] is not None:
        fail("report_local_phase43_must_be_null")
    reconciliation = closed(row["local_reconciliation"], RECONCILIATION_FIELDS, "report_reconciliation_fields")
    state = member(reconciliation["state"], ReconciliationState, "report_reconciliation_state")
    for item in _list(reconciliation["task_lookups"], "report_task_lookups", 8):
        entry = closed(item, LOOKUP_FIELDS, "report_lookup_fields")
        text(entry["subject"], "report_lookup_subject", 160)
        if entry["task_id"] is not None:
            text(entry["task_id"], "report_lookup_task_id", 16)
        member(entry["phase42_lookup"], Lookup, "report_lookup_phase42")
        member(entry["phase43_lookup"], Lookup, "report_lookup_phase43")
    comparisons = _list(reconciliation["comparisons"], "report_comparisons", MAX_COMPARISONS, validate_comparison)
    if state == ReconciliationState.NOT_PERFORMED_STRUCTURAL_REJECTION and any(
            item["result"] != Comparison.NOT_COMPARABLE for item in comparisons):
        fail("report_rejected_capsule_comparison_semantics")
    findings = _list(row["findings"], "report_findings", MAX_FINDINGS, validate_finding)
    ids = [item["finding_id"] for item in findings]
    if len(set(ids)) != len(ids):
        fail("report_duplicate_finding_id")
    if findings != sorted(findings, key=finding_sort_key):
        fail("report_finding_order")
    eligibility = closed(row["eligibility"], ELIGIBILITY_FIELDS, "report_eligibility_fields")
    status = member(eligibility["status"], Eligibility, "report_eligibility_status")
    review = member(eligibility["manual_review"], ManualReview, "report_manual_review")
    member(eligibility["manual_review_requirement"], ManualReviewRequirement, "report_manual_review_requirement")
    if (review == ManualReview.ELIGIBLE_FOR_MANUAL_REVIEW) != (status == Eligibility.STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW):
        fail("report_manual_review_semantics")
    basis = _list(eligibility["basis_finding_ids"], "report_basis_ids", MAX_FINDINGS)
    if any(item not in ids for item in basis) or basis != sorted(set(basis)):
        fail("report_basis_ids")
    if (state == ReconciliationState.PERFORMED) != (status != Eligibility.STRUCTURAL_REJECTION):
        fail("report_reconciliation_status_semantics")
    return row


def finding_sort_key(finding: dict) -> tuple:
    return (SEVERITY_RANK[Severity(finding["severity"])], finding["finding_id"])


# ---------------------------------------------------------------- inbox

INBOX_TASK_FIELDS = ("task_id", "reference_id", "candidate_id", "file_id", "binding_digest", "slot_status",
                     "response_status", "candidate_present", "observation_verified", "task_completed",
                     "fact_origin", "local_reconciliation")
INBOX_FIELDS = ("request_reference", "capsule", "lifecycle_stage", "eligibility_status", "manual_review",
                "manual_review_requirement", "admitted_task_count", "admitted_tasks")


def validate_inbox(value: object) -> dict:
    from exchange_contracts import TASK_FIELDS, exchange_counts, identifier

    row = _common_row(value, INBOX_SCHEMA, INBOX_FIELDS, MAX_INBOX_BYTES, "inbox")
    identifier(row["request_reference"], "inbox_request_reference")
    _identity(row["capsule"], "inbox_capsule")
    lifecycle = member(row["lifecycle_stage"], Lifecycle, "inbox_lifecycle")
    status = member(row["eligibility_status"], Eligibility, "inbox_eligibility")
    expect(lifecycle, LIFECYCLE_FOR_STATUS[Eligibility(status)].value, "inbox_lifecycle_status")
    review = member(row["manual_review"], ManualReview, "inbox_manual_review")
    if (review == ManualReview.ELIGIBLE_FOR_MANUAL_REVIEW) != (status == Eligibility.STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW):
        fail("inbox_manual_review_semantics")
    member(row["manual_review_requirement"], ManualReviewRequirement, "inbox_manual_review_requirement")
    tasks = _list(row["admitted_tasks"], "inbox_admitted_tasks", 8)
    if count(row["admitted_task_count"], "inbox_admitted_count", 8) != len(tasks):
        fail("inbox_admitted_count_total")
    if (status == Eligibility.STRUCTURAL_REJECTION) != (not tasks):
        fail("inbox_admission_semantics")
    portable = []
    for item in tasks:
        task = closed(item, INBOX_TASK_FIELDS, "inbox_task_fields")
        member(task["fact_origin"], FactOrigin, "inbox_fact_origin")
        member(task["local_reconciliation"], Comparison, "inbox_task_reconciliation")
        portable.append({key: task[key] for key in TASK_FIELDS})
    if portable:
        exchange_counts(portable)
    return row


# ---------------------------------------------------------------- output manifest

OUTPUT_PAYLOAD_NAMES = ("task-inbox-record.json", "capsule-reconciliation-report.json",
                        "capsule-reconciliation-summary.md")
OUTPUT_NAMES = (*OUTPUT_PAYLOAD_NAMES, "manifest.json")
INPUT_ROLES = (
    "untrusted_capsule", "reconciliation_request",
    "local_phase42_register", "local_phase42_classification", "local_phase42_intake_receipt",
    "local_phase42_intake_summary", "local_phase42_manifest",
    "local_phase43_capsule", "local_phase43_index", "local_phase43_receipt",
    "local_phase43_summary", "local_phase43_manifest",
)
OUTPUT_MANIFEST_FIELDS = ("request_reference", "capsule", "eligibility_status", "files", "inputs",
                          "manifest_self_excluded", "integrity_scope")
INTEGRITY_SCOPE = "three_new_reconciliation_outputs_and_explicit_input_byte_identities_only"


def input_roles_for(mode: str) -> tuple:
    roles = list(INPUT_ROLES[:2])
    if uses_phase42(mode):
        roles.extend(INPUT_ROLES[2:7])
    if uses_phase43(mode):
        roles.extend(INPUT_ROLES[7:])
    return tuple(roles)


def _named_identity(value: object, key: str, code: str) -> dict:
    row = closed(value, (key, "bytes", "sha256"), code)
    count(row["bytes"], code + "_bytes")
    digest(row["sha256"], code + "_sha256")
    return row


def validate_output_manifest(value: object, mode: str) -> dict:
    from exchange_contracts import identifier

    row = _common_row(value, OUTPUT_MANIFEST_SCHEMA, OUTPUT_MANIFEST_FIELDS, MAX_OUTPUT_MANIFEST_BYTES, "output_manifest")
    identifier(row["request_reference"], "output_manifest_request_reference")
    _identity(row["capsule"], "output_manifest_capsule")
    member(row["eligibility_status"], Eligibility, "output_manifest_eligibility")
    files = _list(row["files"], "output_manifest_files", 3)
    for item in files:
        _named_identity(item, "name", "output_manifest_file")
    expect([item["name"] for item in files], list(OUTPUT_PAYLOAD_NAMES), "output_manifest_file_names")
    inputs = _list(row["inputs"], "output_manifest_inputs", len(INPUT_ROLES))
    for item in inputs:
        _named_identity(item, "role", "output_manifest_input")
    expect([item["role"] for item in inputs], list(input_roles_for(mode)), "output_manifest_input_roles")
    expect(inputs[0]["sha256"], row["capsule"]["sha256"], "output_manifest_capsule_input")
    expect(row["manifest_self_excluded"], True, "output_manifest_self_excluded")
    expect(row["integrity_scope"], INTEGRITY_SCOPE, "output_manifest_scope")
    return row


# ---------------------------------------------------------------- inspection

INSPECTION_FIELDS = ("request_reference", "capsule", "reported_eligibility_status",
                     "independently_derived_eligibility_status", "eligibility_agreement",
                     "phase43_reader_independent_result", "regenerated_outputs", "output_artifacts",
                     "inputs", "checks", "inspection_scope")
INSPECTION_SCOPE = "reconciliation_outputs_rechecked_against_explicit_inputs_and_phase43_owner_reader_only"
INSPECTION_CHECKS = (
    "output_models_closed_and_canonical", "output_manifest_matches_actual_bytes",
    "input_identities_match_current_inputs", "capsule_identity_recomputed",
    "phase43_owner_reader_rerun_independently", "eligibility_rederived_from_report_evidence",
    "inbox_derived_from_report", "disclosure_boundary_checked", "summary_rerendered",
    "full_reconciliation_regenerated_byte_identical",
)


def validate_inspection(value: object, mode: str) -> dict:
    from exchange_contracts import identifier

    row = _common_row(value, INSPECTION_SCHEMA, INSPECTION_FIELDS, MAX_INSPECTION_BYTES, "inspection")
    identifier(row["request_reference"], "inspection_request_reference")
    _identity(row["capsule"], "inspection_capsule")
    reported = member(row["reported_eligibility_status"], Eligibility, "inspection_reported_status")
    expect(row["independently_derived_eligibility_status"], reported, "inspection_status_agreement")
    member(row["eligibility_agreement"], Agreement, "inspection_agreement")
    member(row["phase43_reader_independent_result"], Compatibility, "inspection_owner_result")
    member(row["regenerated_outputs"], Regeneration, "inspection_regeneration")
    artifacts = _list(row["output_artifacts"], "inspection_artifacts", 4)
    for item in artifacts:
        _named_identity(item, "name", "inspection_artifact")
    expect([item["name"] for item in artifacts], list(OUTPUT_NAMES), "inspection_artifact_names")
    inputs = _list(row["inputs"], "inspection_inputs", len(INPUT_ROLES))
    for item in inputs:
        _named_identity(item, "role", "inspection_input")
    expect([item["role"] for item in inputs], list(input_roles_for(mode)), "inspection_input_roles")
    checks = _list(row["checks"], "inspection_checks", len(INSPECTION_CHECKS))
    expect(checks, [{"check": name, "result": CheckResult.PASSED.value} for name in INSPECTION_CHECKS],
           "inspection_check_list")
    expect(row["inspection_scope"], INSPECTION_SCOPE, "inspection_scope")
    return row


__all__ = tuple(name for name in globals() if not name.startswith("_"))
