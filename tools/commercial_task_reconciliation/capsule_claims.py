"""Interpret the four capsule members as untrusted, capsule-declared claims.

Every rule applied here calls an existing Phase43 owner function: the owner
strict JSON parser, owner validators for each field, owner response-contract
validation and the owner inner-manifest builder. Nothing is repaired, and the
Phase43 recipient reader (run separately) remains the compatibility authority.
"""
from __future__ import annotations

import hashlib
import re

from exchange_contracts import (
    COMMON_FIELDS as OWNER_COMMON_FIELDS, DEMO_LABEL as OWNER_DEMO_LABEL,
    LIMITATIONS as OWNER_LIMITATIONS, MAX_TASKS, PORTABLE_REQUEST_SCHEMA, RESPONSE_CONTRACT_SCHEMA,
    CAPSULE_SCHEMA, TASK_FIELDS, InputError, common as owner_common, digest_id, exchange_counts, fixed,
    identifier, json_bytes, parse_json, sha256, task_id, validate_portable_request, validate_response_contract,
)
from portable_capsule import MEMBER_LIMITS, PAYLOAD_NAMES, README_BYTES, ZIP_NAMES, capsule_manifest_data
from reconciliation_contracts import (
    MAX_LISTED_NAMES, Consistency, ContentState, Correspondence, Encoding, EntryShape, FieldState,
    OwnerContract, Presence, SchemaState, ValueDisclosure, ValueKind, safe_field_name,
)
from reconciliation_findings import finding

# The closed Phase43 envelope field list. validate_portable_request owns it;
# the engine re-checks this tuple against every owner-accepted envelope.
ENVELOPE_FIELDS = (*OWNER_COMMON_FIELDS, "source_phase42_register_sha256", "source_phase42_manifest_sha256",
                   "request_reference", "tasks", "counts", "limitations")
IDENTITY_FIELDS = ("task_id", "reference_id", "candidate_id", "file_id", "binding_digest")
_REQUEST_MEMBER, _CONTRACT_MEMBER, _README_MEMBER, _MANIFEST_MEMBER = ZIP_NAMES
_SCHEMAS = {_REQUEST_MEMBER: PORTABLE_REQUEST_SCHEMA, _CONTRACT_MEMBER: RESPONSE_CONTRACT_SCHEMA,
            _MANIFEST_MEMBER: CAPSULE_SCHEMA}


def owner_code(error: InputError) -> str:
    text = str(error)
    return text if re.fullmatch(r"[A-Za-z0-9_]{1,160}", text) else "owner_code_unrepresentable"


def _owner_rule(call) -> str | None:
    try:
        call()
    except InputError as error:
        return owner_code(error)
    return None


# Field rules: every callable is an existing Phase43 owner validator.
_ENVELOPE_RULES = {
    "schema_version": lambda v: fixed(v, PORTABLE_REQUEST_SCHEMA, "portable_schema"),
    "demo_label": lambda v: fixed(v, OWNER_DEMO_LABEL, "portable_demo_label"),
    "demo_only": lambda v: fixed(v, True, "portable_demo_only"),
    "trust_flags": lambda v: fixed(v, owner_common(PORTABLE_REQUEST_SCHEMA)["trust_flags"], "portable_trust_flags"),
    "source_phase42_register_sha256": lambda v: sha256(v, "portable_source_register"),
    "source_phase42_manifest_sha256": lambda v: sha256(v, "portable_source_manifest"),
    "request_reference": lambda v: identifier(v, "portable_request_reference"),
    "limitations": lambda v: fixed(v, list(OWNER_LIMITATIONS), "limitations"),
}
_TASK_RULES = {
    "task_id": task_id,
    "reference_id": lambda v: digest_id(v, "rust-ref-", "portable_reference_id"),
    "candidate_id": lambda v: identifier(v, "portable_candidate_id"),
    "file_id": lambda v: digest_id(v, "candidate-file-", "portable_file_id"),
    "binding_digest": lambda v: sha256(v, "inherited_binding_digest"),
    "slot_status": lambda v: fixed(v, "awaiting_external_response", "portable_slot_status"),
    "response_status": lambda v: fixed(v, "unsubmitted", "portable_response_status"),
    "candidate_present": lambda v: fixed(v, False, "portable_unverified_pending_state"),
    "observation_verified": lambda v: fixed(v, False, "portable_unverified_pending_state"),
    "task_completed": lambda v: fixed(v, False, "portable_unverified_pending_state"),
}


def _kind(value: object) -> ValueKind:
    if value is None:
        return ValueKind.NULL
    return {bool: ValueKind.BOOLEAN, int: ValueKind.INTEGER, str: ValueKind.STRING,
            list: ValueKind.ARRAY, dict: ValueKind.OBJECT}[type(value)]


def not_evaluated(path: str) -> dict:
    return {"path": path, "presence": Presence.NOT_EVALUATED.value, "value_kind": ValueKind.NOT_EVALUATED.value,
            "state": FieldState.NOT_EVALUATED.value, "value_disclosure": ValueDisclosure.NOT_APPLICABLE.value,
            "value": None, "string_length": None, "string_sha256": None, "item_count": None,
            "owner_rule_code": None}


def field_record(path: str, container: dict, key: str, rule) -> dict:
    """Classify one declared field without collapsing absent/null/empty/false/0."""
    if key not in container:
        return {**not_evaluated(path), "presence": Presence.ABSENT.value, "value_kind": ValueKind.ABSENT.value,
                "state": FieldState.ABSENT.value}
    value = container[key]
    kind = _kind(value)
    code = None
    if kind == ValueKind.NULL:
        state = FieldState.NULL
    elif kind == ValueKind.STRING and value == "":
        state = FieldState.EMPTY_STRING
    elif kind == ValueKind.ARRAY and not value:
        state = FieldState.EMPTY_ARRAY
    elif kind == ValueKind.OBJECT and not value:
        state = FieldState.EMPTY_OBJECT
    elif rule is None:
        state = FieldState.NOT_EVALUATED
    else:
        code = _owner_rule(lambda: rule(value))
        state = FieldState.VALID if code is None else FieldState.INVALID
    if kind in (ValueKind.ARRAY, ValueKind.OBJECT):
        disclosure = ValueDisclosure.WITHHELD_COMPOSITE
    elif kind == ValueKind.STRING and state not in (FieldState.VALID, FieldState.EMPTY_STRING):
        disclosure = ValueDisclosure.WITHHELD_INVALID_STRING
    else:
        disclosure = ValueDisclosure.ECHOED
    return {
        "path": path, "presence": Presence.PRESENT.value, "value_kind": kind.value, "state": state.value,
        "value_disclosure": disclosure.value,
        "value": value if disclosure == ValueDisclosure.ECHOED else None,
        "string_length": len(value) if kind == ValueKind.STRING else None,
        "string_sha256": (hashlib.sha256(value.encode("utf-8", "surrogatepass")).hexdigest()
                          if kind == ValueKind.STRING else None),
        "item_count": len(value) if kind in (ValueKind.ARRAY, ValueKind.OBJECT) else None,
        "owner_rule_code": code,
    }


def _unexpected(container: dict, expected: tuple) -> dict:
    extra = [key for key in container if key not in expected]
    listed = sorted({name for name in extra if safe_field_name(name)})[:MAX_LISTED_NAMES]
    return {"count": len(extra), "listed_names": listed, "unlisted_count": len(extra) - len(listed)}


def _field_findings(record: dict, identity: bool) -> list:
    state = record["state"]
    if state in (FieldState.VALID, FieldState.NOT_EVALUATED):
        return []
    path = record["path"]
    if path.endswith(":schema_version") and state == FieldState.INVALID:
        return [finding("SCHEMA_UNSUPPORTED", path, "schema_version is not the supported Phase43 version",
                        PORTABLE_REQUEST_SCHEMA)]
    if path.endswith(":schema_version") and state == FieldState.ABSENT:
        return [finding("SCHEMA_ABSENT", path, "schema_version is absent")]
    observed = {
        FieldState.ABSENT: "the field is absent",
        FieldState.NULL: "the field is explicitly null",
        FieldState.EMPTY_STRING: "the field is an empty string",
        FieldState.EMPTY_ARRAY: "the field is an empty list",
        FieldState.EMPTY_OBJECT: "the field is an empty object",
        FieldState.INVALID: "the " + record["value_kind"].lower() + " value is rejected by owner rule "
                            + str(record["owner_rule_code"]),
    }[FieldState(state)]
    return [finding(("IDENTITY_" if identity else "FIELD_") + state, path, observed)]


def _parse_json_member(name: str, raw: bytes | None) -> tuple[dict, object, list]:
    """Return (content record, parsed value or None, findings)."""
    record = {"name": name, "content_state": ContentState.NOT_EVALUATED.value, "owner_rejection_code": None,
              "schema_state": SchemaState.NOT_EVALUATED.value, "declared_schema": None,
              "canonical_encoding": Encoding.NOT_EVALUATED.value, "owner_contract": OwnerContract.NOT_EVALUATED.value}
    if raw is None:
        return record, None, []
    try:
        value = parse_json(raw, maximum=MEMBER_LIMITS[name])
    except InputError as error:
        code = owner_code(error)
        state = (ContentState.DUPLICATE_JSON_KEY if code.endswith("duplicate_json_key") else
                 ContentState.MALFORMED_JSON if code.endswith("strict_json") else ContentState.JSON_CONTRACT_VIOLATION)
        record.update(content_state=state.value, owner_rejection_code=code)
        rule = {ContentState.DUPLICATE_JSON_KEY: "MEMBER_DUPLICATE_JSON_KEY",
                ContentState.MALFORMED_JSON: "MEMBER_MALFORMED_JSON"}.get(state, "MEMBER_JSON_CONTRACT_VIOLATION")
        return record, None, [finding(rule, name, "the owner JSON parser rejected the member with " + code)]
    record["content_state"] = ContentState.PARSED.value
    findings = []
    if type(value) is not dict:
        findings.append(finding("MEMBER_NOT_JSON_OBJECT", name, "the top-level JSON value is not an object"))
        record["schema_state"] = SchemaState.ABSENT.value
    elif "schema_version" not in value:
        record["schema_state"] = SchemaState.ABSENT.value
    else:
        declared = value["schema_version"]
        supported = declared == _SCHEMAS[name]
        record["declared_schema"] = declared if supported else None
        record["schema_state"] = (SchemaState.SUPPORTED if supported else SchemaState.UNSUPPORTED).value
    try:
        canonical = raw == json_bytes(value, maximum=MEMBER_LIMITS[name])
    except InputError:
        canonical = False
    record["canonical_encoding"] = (Encoding.CANONICAL if canonical else Encoding.NONCANONICAL).value
    if not canonical:
        findings.append(finding("MEMBER_NONCANONICAL_ENCODING", name, "the member bytes are not canonical owner JSON"))
    if name != _REQUEST_MEMBER and type(value) is dict:
        if record["schema_state"] == SchemaState.ABSENT:
            findings.append(finding("SCHEMA_ABSENT", name, "schema_version is absent"))
        elif record["schema_state"] == SchemaState.UNSUPPORTED:
            findings.append(finding("SCHEMA_UNSUPPORTED", name, "schema_version is not the supported Phase43 version",
                                    _SCHEMAS[name]))
    return record, value, findings


def _manifest(raw_contents: dict, manifest: object, envelope: dict | None, contract: dict | None) -> tuple[dict, list]:
    result = {"manifest_state": ContentState.NOT_EVALUATED.value, "entries": [], "unknown_entry_count": 0,
              "duplicate_entry_count": 0, "malformed_entry_count": 0,
              "fixed_fields": Correspondence.NOT_EVALUATED.value}
    findings = []
    actual = {name: raw_contents.get(name) for name in PAYLOAD_NAMES}
    if type(manifest) is not dict:
        result["entries"] = [{"member": name, "declared_bytes": None, "declared_sha256": None,
                              "actual_bytes": None if actual[name] is None else len(actual[name]),
                              "actual_sha256": None if actual[name] is None else hashlib.sha256(actual[name]).hexdigest(),
                              "result": Correspondence.NOT_EVALUATED.value} for name in PAYLOAD_NAMES]
        return result, findings
    result["manifest_state"] = ContentState.PARSED.value
    files = manifest.get("files")
    declared: dict = {name: [] for name in PAYLOAD_NAMES}
    if type(files) is not list:
        findings.append(finding("MANIFEST_FILES_NOT_LIST", _MANIFEST_MEMBER, "files is absent or not a list"))
        files = []
    unknown = malformed = 0
    for entry in files:
        if (type(entry) is not dict or set(entry) != {"name", "bytes", "sha256"} or type(entry["name"]) is not str):
            malformed += 1
            continue
        if entry["name"] in declared:
            declared[entry["name"]].append(entry)
        else:
            unknown += 1
    duplicates = sum(len(items) - 1 for items in declared.values() if len(items) > 1)
    result.update(unknown_entry_count=unknown, duplicate_entry_count=duplicates, malformed_entry_count=malformed)
    if malformed:
        findings.append(finding("MANIFEST_MALFORMED_ENTRY", _MANIFEST_MEMBER, str(malformed) + " malformed entries"))
    if unknown:
        findings.append(finding("MANIFEST_UNKNOWN_ENTRY", _MANIFEST_MEMBER, str(unknown) + " entries name other members"))
    for name in PAYLOAD_NAMES:
        raw = actual[name]
        actual_bytes = None if raw is None else len(raw)
        actual_sha = None if raw is None else hashlib.sha256(raw).hexdigest()
        items = declared[name]
        entry_bytes = entry_sha = None
        if len(items) == 1:
            item = items[0]
            entry_bytes = item["bytes"] if type(item["bytes"]) is int and 0 <= item["bytes"] <= 2**53 - 1 else None
            entry_sha = item["sha256"] if _owner_rule(lambda: sha256(item["sha256"], "x")) is None else None
        if not items:
            outcome = Correspondence.NOT_DECLARED
            findings.append(finding("MANIFEST_ENTRY_NOT_DECLARED", name, "the inner manifest has no entry for the member"))
        elif len(items) > 1:
            outcome = Correspondence.NOT_COMPARABLE
            findings.append(finding("MANIFEST_DUPLICATE_ENTRY", name, str(len(items)) + " entries name the member"))
        elif raw is None:
            outcome = Correspondence.NOT_COMPARABLE
        elif entry_bytes == actual_bytes and entry_sha == actual_sha:
            outcome = Correspondence.MATCH
        else:
            outcome = Correspondence.MISMATCH
            findings.append(finding("MANIFEST_HASH_MISMATCH", name,
                                    "declared identity differs from actual bytes " + str(actual_bytes)
                                    + " / SHA256 " + str(actual_sha), "declared bytes and SHA256 equal to the actual member"))
        result["entries"].append({"member": name, "declared_bytes": entry_bytes, "declared_sha256": entry_sha,
                                  "actual_bytes": actual_bytes, "actual_sha256": actual_sha, "result": outcome.value})
    if envelope is not None and contract is not None and all(actual[name] is not None for name in PAYLOAD_NAMES):
        try:
            expected = capsule_manifest_data(envelope, contract, dict(actual))
            same = json_bytes(expected) == json_bytes(manifest)
        except InputError:
            same = False
        result["fixed_fields"] = (Correspondence.MATCH if same else Correspondence.MISMATCH).value
        if not same:
            findings.append(finding("MANIFEST_OWNER_MISMATCH", _MANIFEST_MEMBER,
                                    "the inner manifest differs from the Phase43 owner manifest for these payloads"))
    return result, findings


def _tasks(value: object) -> tuple[list, dict, list, list]:
    """Return task records, declaration facts, declared identities, findings."""
    findings, records, identities = [], [], []
    if type(value) is not list:
        return records, {"actual": None, "interpreted": 0}, identities, findings
    if len(value) > MAX_TASKS:
        findings.append(finding("TASK_COUNT_LIMIT", _REQUEST_MEMBER + ":tasks",
                                str(len(value)) + " task entries; only the first " + str(MAX_TASKS) + " were interpreted"))
    for position, item in enumerate(value[:MAX_TASKS]):
        base = _REQUEST_MEMBER + ":tasks[" + str(position) + "]"
        if type(item) is not dict:
            findings.append(finding("TASK_ENTRY_NOT_OBJECT", base, "the task entry is a " + _kind(item).value.lower()))
            records.append({"position": position, "entry_shape": EntryShape.NOT_OBJECT.value,
                            "fields": [not_evaluated(base + "." + key) for key in TASK_FIELDS],
                            "unexpected_fields": {"count": 0, "listed_names": [], "unlisted_count": 0}})
            identities.append({"position": position, **{key: None for key in IDENTITY_FIELDS}})
            continue
        fields = [field_record(base + "." + key, item, key, _TASK_RULES[key]) for key in TASK_FIELDS]
        for record, key in zip(fields, TASK_FIELDS):
            findings.extend(_field_findings(record, key in IDENTITY_FIELDS))
        unexpected = _unexpected(item, TASK_FIELDS)
        if unexpected["count"]:
            findings.append(finding("FIELD_UNEXPECTED", base, str(unexpected["count"]) + " unexpected task fields"))
        records.append({"position": position, "entry_shape": EntryShape.OBJECT.value, "fields": fields,
                        "unexpected_fields": unexpected})
        valid = {record["path"].rsplit(".", 1)[1]: record["value"] for record in fields if record["state"] == FieldState.VALID}
        identities.append({"position": position, **{key: valid.get(key) for key in IDENTITY_FIELDS}})
    return records, {"actual": len(value), "interpreted": min(len(value), MAX_TASKS)}, identities, findings


def _declaration(envelope: dict, records: list, facts: dict, identities: list, tasks_state: str) -> tuple[dict, list]:
    findings = []
    counts = envelope.get("counts") if type(envelope) is dict else None
    declared = counts.get("selected_task_count") if type(counts) is dict else None
    declared = declared if type(declared) is int else None
    issues = False
    if facts["actual"] is not None and declared is not None and declared != facts["actual"]:
        issues = True
        findings.append(finding("TASK_COUNT_DECLARATION_MISMATCH", _REQUEST_MEMBER + ":counts.selected_task_count",
                                "declares " + str(declared) + " tasks; the list contains " + str(facts["actual"]),
                                "counts.selected_task_count equal to " + str(facts["actual"])))
    ids = [item["task_id"] for item in identities if item["task_id"] is not None]
    if len(set(ids)) != len(ids):
        issues = True
        findings.append(finding("TASK_DUPLICATE_REFERENCE", _REQUEST_MEMBER + ":tasks", "a task ID is declared more than once"))
    digests = [item["binding_digest"] for item in identities if item["binding_digest"] is not None]
    triples = [(item["reference_id"], item["candidate_id"], item["file_id"]) for item in identities
               if None not in (item["reference_id"], item["candidate_id"], item["file_id"])]
    if len(set(digests)) != len(digests) or len(set(triples)) != len(triples):
        issues = True
        findings.append(finding("TASK_DUPLICATE_BINDING", _REQUEST_MEMBER + ":tasks",
                                "the same binding is declared by more than one task entry"))
    if ids != sorted(ids):
        issues = True
        findings.append(finding("TASK_ORDER_NONCANONICAL", _REQUEST_MEMBER + ":tasks", "task IDs are not ascending"))
    if facts["actual"] is None:
        consistency = Consistency.NOT_EVALUATED
    elif issues or any(record["entry_shape"] != EntryShape.OBJECT for record in records) or facts["actual"] > MAX_TASKS:
        consistency = Consistency.INCONSISTENT
    else:
        consistency = Consistency.CONSISTENT if declared is not None else Consistency.NOT_EVALUATED
    return {"tasks_field_state": tasks_state, "declared_task_count": declared, "actual_task_entry_count": facts["actual"],
            "interpreted_task_entry_count": facts["interpreted"], "consistency": consistency.value}, findings


def _summary(envelope_fields: list, task_records: list, envelope_unexpected: dict) -> dict:
    groups = {key: [] for key in ("present_valid", "absent", "null", "empty_string", "empty_array", "empty_object",
                                  "invalid", "not_evaluated", "unexpected")}
    target = {FieldState.VALID: "present_valid", FieldState.ABSENT: "absent", FieldState.NULL: "null",
              FieldState.EMPTY_STRING: "empty_string", FieldState.EMPTY_ARRAY: "empty_array",
              FieldState.EMPTY_OBJECT: "empty_object", FieldState.INVALID: "invalid",
              FieldState.NOT_EVALUATED: "not_evaluated"}
    containers = [(_REQUEST_MEMBER + ":", envelope_unexpected)]
    for record in envelope_fields + [field for task in task_records for field in task["fields"]]:
        groups[target[FieldState(record["state"])]].append(record["path"])
    for task in task_records:
        containers.append((_REQUEST_MEMBER + ":tasks[" + str(task["position"]) + "].", task["unexpected_fields"]))
    for prefix, unexpected in containers:
        groups["unexpected"].extend(prefix + name for name in unexpected["listed_names"])
        if unexpected["unlisted_count"]:
            groups["unexpected"].append(prefix + "unlisted_unexpected_fields=" + str(unexpected["unlisted_count"]))
    return {key: sorted(set(values)) for key, values in groups.items()}


def interpret_contents(contents: dict | None) -> dict:
    """Return declared facts and findings; NOT_EVALUATED everywhere when unread."""
    findings: list = []
    raw = contents or {}
    request_record, envelope, request_findings = _parse_json_member(_REQUEST_MEMBER, raw.get(_REQUEST_MEMBER))
    contract_record, contract_value, contract_findings = _parse_json_member(_CONTRACT_MEMBER, raw.get(_CONTRACT_MEMBER))
    manifest_record, manifest_value, manifest_findings = _parse_json_member(_MANIFEST_MEMBER, raw.get(_MANIFEST_MEMBER))
    findings += request_findings + contract_findings + manifest_findings
    readme = raw.get(_README_MEMBER)
    readme_record = {"name": _README_MEMBER, "content_state": ContentState.NOT_EVALUATED.value,
                     "owner_rejection_code": None, "schema_state": SchemaState.NOT_APPLICABLE.value,
                     "declared_schema": None, "canonical_encoding": Encoding.NOT_APPLICABLE.value,
                     "owner_contract": OwnerContract.NOT_APPLICABLE.value}
    if readme is not None:
        readme_record["content_state"] = (ContentState.FIXED_TEXT_MATCH if readme == README_BYTES
                                          else ContentState.FIXED_TEXT_MISMATCH).value
        if readme != README_BYTES:
            findings.append(finding("README_FIXED_TEXT_MISMATCH", _README_MEMBER, "README bytes differ from the fixed text"))
    if contents is not None:
        for record in (request_record, contract_record, readme_record, manifest_record):
            if contents.get(record["name"]) is None:
                record["content_state"] = ContentState.READ_ERROR.value
    owner_envelope = owner_contract = None
    for record, value, validator in ((request_record, envelope, validate_portable_request),
                                     (contract_record, contract_value, validate_response_contract)):
        if record["content_state"] != ContentState.PARSED:
            continue
        code = _owner_rule(lambda: validator(value))
        record["owner_contract"] = (OwnerContract.OWNER_VALID if code is None else OwnerContract.OWNER_REJECTED).value
        record["owner_rejection_code"] = code
        if code is not None:
            findings.append(finding("MEMBER_OWNER_CONTRACT_REJECTED", record["name"],
                                    "the Phase43 owner validator rejected the member with " + code))
        elif validator is validate_portable_request:
            owner_envelope = validate_portable_request(value)
        else:
            owner_contract = validate_response_contract(value)
    manifest_state, more = _manifest(raw, manifest_value, owner_envelope, owner_contract)
    findings += more
    if manifest_record["content_state"] == ContentState.PARSED:
        manifest_record["owner_contract"] = {
            Correspondence.MATCH: OwnerContract.OWNER_VALID, Correspondence.MISMATCH: OwnerContract.OWNER_REJECTED,
        }.get(Correspondence(manifest_state["fixed_fields"]), OwnerContract.NOT_EVALUATED).value
    if type(envelope) is dict:
        envelope_fields = []
        for key in ENVELOPE_FIELDS:
            if key == "tasks":
                rule = lambda v: exchange_counts(v)
            elif key == "counts":
                tasks = envelope.get("tasks")
                tasks_ok = _owner_rule(lambda: exchange_counts(tasks)) is None
                rule = (lambda v, t=tasks: fixed(v, exchange_counts(t), "portable_counts")) if tasks_ok else None
            else:
                rule = _ENVELOPE_RULES[key]
            record = field_record(_REQUEST_MEMBER + ":" + key, envelope, key, rule)
            envelope_fields.append(record)
            findings.extend(_field_findings(record, False))
        envelope_unexpected = _unexpected(envelope, ENVELOPE_FIELDS)
        if envelope_unexpected["count"]:
            findings.append(finding("FIELD_UNEXPECTED", _REQUEST_MEMBER,
                                    str(envelope_unexpected["count"]) + " unexpected envelope fields"))
        task_records, facts, identities, task_findings = _tasks(envelope.get("tasks"))
        findings += task_findings
        tasks_state = next(item["state"] for item in envelope_fields if item["path"].endswith(":tasks"))
        declaration, more = _declaration(envelope, task_records, facts, identities, tasks_state)
        findings += more
        values = {item["path"].split(":", 1)[1]: item for item in envelope_fields}
        source = {key: values[key]["value"] if values[key]["state"] == FieldState.VALID else None
                  for key in ("source_phase42_register_sha256", "source_phase42_manifest_sha256", "request_reference")}
        declared_schema = (envelope["schema_version"]
                           if envelope.get("schema_version") == PORTABLE_REQUEST_SCHEMA else None)
    else:
        envelope_fields = [not_evaluated(_REQUEST_MEMBER + ":" + key) for key in ENVELOPE_FIELDS]
        envelope_unexpected = {"count": 0, "listed_names": [], "unlisted_count": 0}
        task_records, identities = [], []
        declaration = {"tasks_field_state": FieldState.NOT_EVALUATED.value, "declared_task_count": None,
                       "actual_task_entry_count": None, "interpreted_task_entry_count": 0,
                       "consistency": Consistency.NOT_EVALUATED.value}
        source = {"source_phase42_register_sha256": None, "source_phase42_manifest_sha256": None, "request_reference": None}
        declared_schema = None
    return {
        "member_contents": [request_record, contract_record, readme_record, manifest_record],
        "manifest_correspondence": manifest_state,
        "envelope_fields": envelope_fields,
        "envelope_unexpected_fields": envelope_unexpected,
        "tasks": task_records,
        "task_declaration": declaration,
        "field_presence_summary": _summary(envelope_fields, task_records, envelope_unexpected),
        "declared_schema": declared_schema,
        "declared_tasks": identities,
        "source_declaration": source,
        "owner_member_envelope": owner_envelope,
        "findings": findings,
    }


__all__ = ("ENVELOPE_FIELDS", "IDENTITY_FIELDS", "interpret_contents", "owner_code")
