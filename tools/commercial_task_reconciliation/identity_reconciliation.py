"""Compare capsule-declared identities with the explicit local reference snapshot.

Local records are consulted only for a structurally valid capsule (accepted
by the Phase43 owner reader). A rejected capsule yields NOT_COMPARABLE rows
and no local values at all. Local values are echoed only when they equal the
capsule value or were already recorded as disclosed by Phase43.
"""
from __future__ import annotations

from exchange_contracts import TASK_FIELDS
from portable_capsule import ZIP_NAMES
from reconciliation_contracts import (
    Comparison, FieldState, LocalDisclosure, Lookup, ReconciliationState, ReferenceSource,
    uses_phase42, uses_phase43,
)
from reconciliation_findings import finding

P42 = ReferenceSource.PHASE42_LOCAL_TASK_RECORD.value
P43 = ReferenceSource.PHASE43_LOCAL_DISCLOSURE_RECORD.value
_SOURCE_TAG = {P42: "phase42", P43: "phase43"}
CAPSULE_FIELDS = {
    P42: ("source_phase42_register_sha256", "source_phase42_manifest_sha256"),
    P43: ("capsule_sha256", *("member_sha256:" + name for name in ZIP_NAMES),
          "source_phase42_register_sha256", "source_phase42_manifest_sha256", "request_reference", "task_id_list"),
}
TASK_ROW_FIELDS = {
    P42: (*TASK_FIELDS, "binding_tuple", "binding_digest_owner_task", "binding_triple_owner_task"),
    P43: (*TASK_FIELDS, "binding_tuple"),
}


def _tuple(task: dict) -> str:
    return "|".join((task["reference_id"], task["candidate_id"], task["file_id"], task["binding_digest"]))


def _row(subject, field, source, capsule_value, capsule_state, local_value, disclosure, result) -> dict:
    return {"subject": subject, "field": field, "reference_source": source,
            "capsule_value": capsule_value if capsule_state == FieldState.VALID else None,
            "capsule_value_state": capsule_state, "local_value": local_value if disclosure == LocalDisclosure.ECHOED else None,
            "local_value_disclosure": disclosure, "result": result}


def _not_comparable_rows(task_fields: list) -> tuple[list, list]:
    """Rows for a rejected capsule: capsule facts only, local records untouched."""
    rows, lookups = [], []
    for source in (P42, P43):
        for field in CAPSULE_FIELDS[source]:
            rows.append(_row("capsule", field, source, None, FieldState.NOT_EVALUATED.value, None,
                             LocalDisclosure.NOT_AVAILABLE.value, Comparison.NOT_COMPARABLE.value))
    for task in task_fields:
        subject = "task[" + str(task["position"]) + "]"
        task_ref = task["fields"].get("task_id", (None, None))[1]
        lookups.append({"subject": subject, "task_id": task_ref, "phase42_lookup": Lookup.NOT_PERFORMED.value,
                        "phase43_lookup": Lookup.NOT_PERFORMED.value})
        for source in (P42, P43):
            for field in TASK_ROW_FIELDS[source]:
                state, value = task["fields"].get(field, (FieldState.NOT_EVALUATED.value, None))
                rows.append(_row(subject, field, source, value, state, None,
                                 LocalDisclosure.NOT_AVAILABLE.value, Comparison.NOT_COMPARABLE.value))
    return rows, lookups


def _compare(subject, field, source, capsule_value, local_value, available: bool, disclosed: bool) -> dict:
    if not available:
        return _row(subject, field, source, capsule_value, FieldState.VALID.value, None,
                    LocalDisclosure.NOT_AVAILABLE.value, Comparison.UNAVAILABLE.value)
    if type(capsule_value) is type(local_value) and capsule_value == local_value:
        return _row(subject, field, source, capsule_value, FieldState.VALID.value, local_value,
                    LocalDisclosure.ECHOED.value, Comparison.MATCH.value)
    disclosure = LocalDisclosure.ECHOED if disclosed else LocalDisclosure.WITHHELD_NOT_PREVIOUSLY_DISCLOSED
    return _row(subject, field, source, capsule_value, FieldState.VALID.value, local_value,
                disclosure.value, Comparison.MISMATCH.value)


def reconcile_identities(structurally_valid: bool, task_fields: list, represented: dict | None,
                         capsule_sha256: str, member_sha256: dict, local_record: dict) -> tuple[dict, list]:
    """Return the local_reconciliation report section and its findings.

    ``task_fields`` lists, per interpreted task entry, ``{position, fields:
    {field: (state, value-if-valid)}}``; it is used only for rejected capsules.
    ``represented`` is the Phase43 owner-reader envelope of a valid capsule.
    """
    mode = local_record["mode"]
    findings = []
    if not structurally_valid:
        rows, lookups = _not_comparable_rows(task_fields)
        findings.append(finding("RECONCILIATION_NOT_PERFORMED", "capsule",
                                "structural rejection precludes consulting local records"))
        return {"state": ReconciliationState.NOT_PERFORMED_STRUCTURAL_REJECTION.value, "task_lookups": lookups,
                "comparisons": rows}, findings
    p42 = local_record["phase42"] if uses_phase42(mode) else None
    p43 = local_record["phase43"] if uses_phase43(mode) else None
    for source, group in ((P42, p42), (P43, p43)):
        if group is None:
            findings.append(finding("LOCAL_RECORDS_NOT_SUPPLIED", _SOURCE_TAG[source],
                                    "no explicit " + _SOURCE_TAG[source] + " local record group was supplied"))
    local42 = {task["task_id"]: task for task in p42["tasks"]} if p42 else {}
    by_digest = {task["binding_digest"]: task["task_id"] for task in p42["tasks"]} if p42 else {}
    by_triple = {(t["reference_id"], t["candidate_id"], t["file_id"]): t["task_id"] for t in p42["tasks"]} if p42 else {}
    disclosed = {task["task_id"]: task for task in p43["tasks"]} if p43 else {}

    def disclosed_value(task_ref: str | None, field: str):
        task = disclosed.get(task_ref)
        if task is None:
            return None, False
        if field == "binding_tuple":
            return _tuple(task), True
        return task.get(field), field in task

    tasks = represented["tasks"]
    rows, lookups = [], []
    capsule42 = {"source_phase42_register_sha256": represented["source_phase42_register_sha256"],
                 "source_phase42_manifest_sha256": represented["source_phase42_manifest_sha256"]}
    local42_capsule = ({"source_phase42_register_sha256": p42["register_sha256"],
                        "source_phase42_manifest_sha256": p42["manifest_sha256"]} if p42 else {})
    # These two local values are the byte identities of the explicit local
    # input files; the report and manifest record them as run provenance.
    for field in CAPSULE_FIELDS[P42]:
        rows.append(_compare("capsule", field, P42, capsule42[field], local42_capsule.get(field),
                             p42 is not None, True))
    capsule43 = {"capsule_sha256": capsule_sha256, **{"member_sha256:" + n: member_sha256[n] for n in ZIP_NAMES},
                 **capsule42, "request_reference": represented["request_reference"],
                 "task_id_list": ",".join(task["task_id"] for task in tasks)}
    local43_capsule = {}
    if p43:
        local43_capsule = {"capsule_sha256": p43["capsule_sha256"],
                           **{"member_sha256:" + m["name"]: m["sha256"] for m in p43["capsule_members"]},
                           "source_phase42_register_sha256": p43["source_phase42_register_sha256"],
                           "source_phase42_manifest_sha256": p43["source_phase42_manifest_sha256"],
                           "request_reference": p43["request_reference"],
                           "task_id_list": ",".join(p43["task_ids"])}
    for field in CAPSULE_FIELDS[P43]:
        rows.append(_compare("capsule", field, P43, capsule43[field], local43_capsule.get(field), p43 is not None, True))
    for task in tasks:
        task_ref = task["task_id"]
        subject = "task:" + task_ref
        found42 = task_ref in local42
        found43 = task_ref in disclosed
        lookups.append({"subject": subject, "task_id": task_ref,
                        "phase42_lookup": (Lookup.NOT_SUPPLIED if p42 is None else
                                           Lookup.FOUND if found42 else Lookup.NOT_FOUND).value,
                        "phase43_lookup": (Lookup.NOT_SUPPLIED if p43 is None else
                                           Lookup.FOUND if found43 else Lookup.NOT_FOUND).value})
        local_task = local42.get(task_ref)
        for field in TASK_ROW_FIELDS[P42]:
            if field == "binding_tuple":
                capsule_value, local_value, available = _tuple(task), local_task and _tuple(local_task), found42
                shared_value, shared = disclosed_value(task_ref, field)
            elif field == "binding_digest_owner_task":
                owner = by_digest.get(task["binding_digest"])
                capsule_value, local_value, available = task_ref, owner, owner is not None
                shared_value, shared = (owner, owner in disclosed) if owner is not None else (None, False)
            elif field == "binding_triple_owner_task":
                owner = by_triple.get((task["reference_id"], task["candidate_id"], task["file_id"]))
                capsule_value, local_value, available = task_ref, owner, owner is not None
                shared_value, shared = (owner, owner in disclosed) if owner is not None else (None, False)
            else:
                capsule_value, local_value, available = task[field], local_task and local_task[field], found42
                if not found42:
                    local_value = None
                shared_value, shared = disclosed_value(task_ref, field)
            if field == "binding_tuple" and not found42:
                local_value = None
            echo = shared and type(shared_value) is type(local_value) and shared_value == local_value
            row = _compare(subject, field, P42, capsule_value, local_value, p42 is not None and available, echo)
            rows.append(row)
            if field in ("binding_digest_owner_task", "binding_triple_owner_task") and p42 is not None and owner is None:
                findings.append(finding("LOCAL_BINDING_NOT_FOUND", subject + "." + field + ":phase42",
                                        "the claimed binding is not recorded in the local Phase42 task records"))
        if p42 is not None and not found42:
            findings.append(finding("LOCAL_TASK_NOT_FOUND", subject + ":phase42",
                                    "the claimed task is not in the supplied local Phase42 task records"))
        disclosed_task = disclosed.get(task_ref)
        for field in TASK_ROW_FIELDS[P43]:
            capsule_value = _tuple(task) if field == "binding_tuple" else task[field]
            local_value = None
            if disclosed_task is not None:
                local_value = _tuple(disclosed_task) if field == "binding_tuple" else disclosed_task[field]
            rows.append(_compare(subject, field, P43, capsule_value, local_value, found43, True))
        if p43 is not None and not found43:
            findings.append(finding("LOCAL_TASK_NOT_FOUND", subject + ":phase43",
                                    "the claimed task is not in the supplied local Phase43 disclosure record"))
    for row in rows:
        if row["result"] != Comparison.MISMATCH:
            continue
        tag = _SOURCE_TAG[row["reference_source"]]
        rule = ("AMBIGUOUS_BINDING_OWNER" if row["field"].endswith("_owner_task") else
                "IDENTITY_MISMATCH" if row["reference_source"] == P42 else "DISCLOSURE_MISMATCH")
        findings.append(finding(rule, row["subject"] + "." + row["field"] + ":" + tag,
                                "the capsule value differs from the local " + tag + " value in comparison row "
                                + row["subject"] + "/" + row["field"] + ("" if row["local_value_disclosure"]
                                == LocalDisclosure.ECHOED else "; the local value is withheld as not previously disclosed"),
                                "the capsule value equal to the local " + tag + " value"))
    return {"state": ReconciliationState.PERFORMED.value, "task_lookups": lookups, "comparisons": rows}, findings


__all__ = ("reconcile_identities", "CAPSULE_FIELDS", "TASK_ROW_FIELDS", "P42", "P43")
