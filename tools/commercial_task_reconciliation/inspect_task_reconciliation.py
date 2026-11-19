"""Independently inspect published reconciliation outputs against their explicit inputs.

The inspector does not trust the builder's in-memory result. It re-reads the
four output files and every explicit input, validates each output model,
recomputes byte identities, reruns the unchanged Phase43 recipient reader,
re-derives eligibility from the report's own evidence with a separate rule
implementation, checks the disclosure boundary, and finally regenerates the
whole reconciliation to require byte-identical outputs. Any disagreement
rejects the inspection (exit 2) and nothing is published.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconciliation_paths  # noqa: E402

reconciliation_paths.install()

from exchange_contracts import TASK_FIELDS, InputError, json_bytes, parse_json  # noqa: E402
from recipient_reader import inspect_task_exchange_capsule, read_portable_task_request  # noqa: E402
from reconciliation_contracts import (  # noqa: E402
    INSPECTION_CHECKS, INSPECTION_SCHEMA, INSPECTION_SCOPE, LIFECYCLE_FOR_STATUS, OUTPUT_NAMES, OUTPUT_PAYLOAD_NAMES,
    CheckResult, Eligibility, common, validate_inbox, validate_inspection, validate_output_manifest, validate_report,
)
from reconciliation_engine import reconcile_capsule  # noqa: E402
from reconciliation_inputs import add_input_arguments, load_inputs  # noqa: E402
from reconciliation_manifest import OUTPUT_LIMITS, input_identities, output_documents, publish_inspection  # noqa: E402
from reconciliation_renderer import render_reconciliation_summary  # noqa: E402

# Deliberately restated here instead of imported from the engine: the
# inspector's rule must agree with the builder's, not reuse it.
_STRUCTURAL = frozenset({"INPUT_SIZE", "ARCHIVE_STRUCTURE", "MEMBER_NAME", "MEMBER_METADATA", "MEMBER_CONTENT",
                         "SCHEMA", "MANIFEST_CORRESPONDENCE", "FIELD_STRUCTURE", "TASK_DECLARATION", "OWNER_READER"})
_FORBIDDEN_KEYS = frozenset({"candidate_response", "observed_sha256", "observed_byte_size", "projections",
                             "reference_packets", "source_locator", "locator_value", "analyst", "analyst_id"})


def disagree(code: str):
    raise InputError("task_reconciliation_inspection_disagreement_" + code)


def _identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def independent_status(report: dict) -> str:
    blocking = any(item["severity"] == "BLOCKING" and item["category"] in _STRUCTURAL for item in report["findings"])
    results = [row["result"] for row in report["local_reconciliation"]["comparisons"]]
    if report["phase43_reader"]["compatibility"] != "COMPATIBLE" or blocking:
        return "STRUCTURAL_REJECTION"
    if "MISMATCH" in results:
        return "IDENTITY_MISMATCH"
    if not results or "UNAVAILABLE" in results or "NOT_COMPARABLE" in results:
        return "LOCAL_RECONCILIATION_UNAVAILABLE"
    return "STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW"


def _keys(value: object):
    if type(value) is dict:
        for key, child in value.items():
            yield key
            yield from _keys(child)
    elif type(value) is list:
        for child in value:
            yield from _keys(child)


_P42 = "PHASE42_LOCAL_TASK_RECORD"
_P43 = "PHASE43_LOCAL_DISCLOSURE_RECORD"
_ABSENT = object()


def _same(left: object, right: object) -> bool:
    return type(left) is type(right) and left == right


def _binding_tuple(task: dict) -> str:
    return "|".join((task["reference_id"], task["candidate_id"], task["file_id"], task["binding_digest"]))


def _local_expectations(local_record: dict, owner_tasks: list) -> dict:
    """Map (source, subject, field) to (local value, echo allowed on non-MATCH).

    Restated from the disclosure rule rather than imported from the builder:
    a Phase43 disclosure-record value and an explicit input identity were
    already disclosed; a Phase42 task value counts as disclosed only when the
    Phase43 record states the same value for the same task and field, and a
    binding owner only when that owner task is in the Phase43 record.
    ``owner_tasks`` come from the inspector's own run of the owner reader.
    """
    expected = {}
    p42, p43 = local_record["phase42"], local_record["phase43"]
    disclosed = {task["task_id"]: task for task in p43["tasks"]} if p43 is not None else {}

    def disclosed_value(task_ref: str, field: str) -> object:
        task = disclosed.get(task_ref)
        if task is None:
            return _ABSENT
        return _binding_tuple(task) if field == "binding_tuple" else task.get(field, _ABSENT)

    if p43 is not None:
        capsule_values = {
            "capsule_sha256": p43["capsule_sha256"],
            **{"member_sha256:" + item["name"]: item["sha256"] for item in p43["capsule_members"]},
            "source_phase42_register_sha256": p43["source_phase42_register_sha256"],
            "source_phase42_manifest_sha256": p43["source_phase42_manifest_sha256"],
            "request_reference": p43["request_reference"], "task_id_list": ",".join(p43["task_ids"]),
        }
        for field, value in capsule_values.items():
            expected[(_P43, "capsule", field)] = (value, True)
        for task in owner_tasks:
            if task["task_id"] in disclosed:
                for field in (*TASK_FIELDS, "binding_tuple"):
                    expected[(_P43, "task:" + task["task_id"], field)] = (disclosed_value(task["task_id"], field), True)
    if p42 is not None:
        # The two Phase42 source digests are the explicit input-file identities.
        expected[(_P42, "capsule", "source_phase42_register_sha256")] = (p42["register_sha256"], True)
        expected[(_P42, "capsule", "source_phase42_manifest_sha256")] = (p42["manifest_sha256"], True)
        local42 = {task["task_id"]: task for task in p42["tasks"]}
        by_digest = {task["binding_digest"]: task["task_id"] for task in p42["tasks"]}
        by_triple = {(t["reference_id"], t["candidate_id"], t["file_id"]): t["task_id"] for t in p42["tasks"]}
        for task in owner_tasks:
            task_ref, subject = task["task_id"], "task:" + task["task_id"]
            local_task = local42.get(task_ref)
            if local_task is not None:
                for field in (*TASK_FIELDS, "binding_tuple"):
                    value = _binding_tuple(local_task) if field == "binding_tuple" else local_task[field]
                    expected[(_P42, subject, field)] = (value, _same(disclosed_value(task_ref, field), value))
            owners = (("binding_digest_owner_task", by_digest.get(task["binding_digest"])),
                      ("binding_triple_owner_task",
                       by_triple.get((task["reference_id"], task["candidate_id"], task["file_id"]))))
            for field, owner in owners:
                if owner is not None:
                    expected[(_P42, subject, field)] = (owner, owner in disclosed)
    return expected


def _check_disclosure(report: dict, inbox: dict, manifest: dict, local_record: dict, owner_tasks: list) -> None:
    """Structural disclosure check on the only places that may carry local data.

    The builder writes local record data only into comparison ``local_value``,
    ``local_reference`` and the manifest ``inputs``; every other output string
    is capsule-derived or a fixed template. So the inspector checks those
    places exactly (no substring search over output bytes, which would
    misread capsule-supplied text as a leak):
    - no forbidden keys anywhere;
    - local_reference holds only explicit input-file identities;
    - a rejected capsule carries no local value at all;
    - every echoed local value equals the value the local record holds for
      that exact (source, subject, field) row, MATCH rows included;
    - a non-MATCH echo is only a value the disclosure rule allows for that
      row (see ``_local_expectations``);
    - task lookups name only capsule-declared tasks, never local enumeration.
    """
    for model in (report, inbox, manifest):
        if any(key in _FORBIDDEN_KEYS for key in _keys(model)):
            disagree("forbidden_disclosure_key")
    provenance = {item["sha256"] for item in manifest["inputs"]}
    for group in ("phase42", "phase43"):
        entry = report["local_reference"][group]
        if entry is not None and not set(entry.values()) <= provenance:
            disagree("local_reference_not_input_identity")
    rejected = report["local_reconciliation"]["state"] != "PERFORMED"
    expected = {} if rejected else _local_expectations(local_record, owner_tasks)
    for row in report["local_reconciliation"]["comparisons"]:
        if rejected and (row["local_value"] is not None or row["local_value_disclosure"] != "NOT_AVAILABLE"):
            disagree("rejected_capsule_local_value")
        if row["local_value_disclosure"] != "ECHOED":
            continue
        key = (row["reference_source"], row["subject"], row["field"])
        if key not in expected:
            disagree("echoed_value_without_local_record")
        value, disclosable = expected[key]
        if not _same(row["local_value"], value):
            disagree("echoed_value_differs_from_local_record")
        if row["result"] == "MATCH":
            if not _same(row["local_value"], row["capsule_value"]):
                disagree("match_local_value_differs")
        elif not disclosable:
            disagree("undisclosed_local_value_echoed")
    identity = report["capsule_identity"]
    claimed = {task["task_id"] for task in identity["declared_tasks"] + identity["represented_tasks"]}
    for lookup in report["local_reconciliation"]["task_lookups"]:
        if lookup["task_id"] is not None and lookup["task_id"] not in claimed:
            disagree("lookup_names_unclaimed_task")


def inspect_task_reconciliation(args) -> dict:
    from phase42_adapter import InputBudget

    inputs = load_inputs(args)
    # Outputs get their own bounded budget; the input budget stays as in import.
    output_budget = InputBudget(maximum=sum(OUTPUT_LIMITS.values()) + len(OUTPUT_LIMITS))
    raws = {}
    for name, path in zip(OUTPUT_NAMES, (args.inbox, args.report, args.summary, args.manifest)):
        raws[name] = output_budget.read_text(path, OUTPUT_LIMITS[name])
    mode = inputs.request["local_reference_mode"]
    inbox = validate_inbox(parse_json(raws[OUTPUT_NAMES[0]], maximum=OUTPUT_LIMITS[OUTPUT_NAMES[0]]))
    report = validate_report(parse_json(raws[OUTPUT_NAMES[1]], maximum=OUTPUT_LIMITS[OUTPUT_NAMES[1]]))
    manifest = validate_output_manifest(parse_json(raws[OUTPUT_NAMES[3]], maximum=OUTPUT_LIMITS[OUTPUT_NAMES[3]]), mode)
    for name, model in ((OUTPUT_NAMES[0], inbox), (OUTPUT_NAMES[1], report), (OUTPUT_NAMES[3], manifest)):
        if raws[name] != json_bytes(model, maximum=OUTPUT_LIMITS[name]):
            disagree("non_canonical_" + name.replace("-", "_").replace(".", "_"))
    if [item for item in manifest["files"]] != [{"name": name, **_identity(raws[name])} for name in OUTPUT_PAYLOAD_NAMES]:
        disagree("output_manifest_identity")
    if manifest["inputs"] != input_identities(inputs.capsule, inputs.request_raw, inputs.local):
        disagree("input_identity")
    capsule_identity = _identity(inputs.capsule)
    if not (report["capsule"] == inbox["capsule"] == manifest["capsule"] == capsule_identity):
        disagree("capsule_identity")
    if report["request_reference"] != inputs.request["request_reference"] or not (
            report["request_reference"] == inbox["request_reference"] == manifest["request_reference"]):
        disagree("request_reference")
    if report["local_reference"]["mode"] != mode:
        disagree("local_reference_mode")
    try:
        owner_envelope, _contract, _artifacts = read_portable_task_request(inspect_task_exchange_capsule(inputs.capsule))
        owner, owner_tasks = "COMPATIBLE", owner_envelope["tasks"]
    except InputError:
        owner, owner_tasks = "INCOMPATIBLE", []
    if report["phase43_reader"]["compatibility"] != owner:
        disagree("phase43_owner_reader")
    status = independent_status(report)
    if not (status == report["eligibility"]["status"] == inbox["eligibility_status"] == manifest["eligibility_status"]):
        disagree("eligibility")
    for row in report["local_reconciliation"]["comparisons"]:
        if row["result"] == "MISMATCH" and not any(
                item["finding_id"].startswith("P44-") and item["subject"].startswith(row["subject"] + "." + row["field"] + ":")
                for item in report["findings"]):
            disagree("mismatch_without_finding")
    if inbox["lifecycle_stage"] != LIFECYCLE_FOR_STATUS[Eligibility(status)].value:
        disagree("lifecycle")
    admitted = [{key: task[key] for key in ("task_id", "reference_id", "candidate_id", "file_id", "binding_digest")}
                for task in inbox["admitted_tasks"]]
    represented = [{key: task[key] for key in ("task_id", "reference_id", "candidate_id", "file_id", "binding_digest")}
                   for task in report["capsule_identity"]["represented_tasks"]]
    if status == "STRUCTURAL_REJECTION":
        if admitted:
            disagree("rejected_capsule_admitted")
    elif admitted != represented:
        disagree("inbox_report_tasks")
    local_record = inputs.local.record()
    _check_disclosure(report, inbox, manifest, local_record, owner_tasks)
    if raws[OUTPUT_NAMES[2]] != render_reconciliation_summary(report, inbox):
        disagree("summary")
    regenerated_report, regenerated_inbox = reconcile_capsule(inputs.capsule, inputs.request, inputs.local)
    regenerated = output_documents(regenerated_report, regenerated_inbox,
                                   input_identities(inputs.capsule, inputs.request_raw, inputs.local))
    if regenerated != raws:
        disagree("regeneration")
    inputs.budget.check_stability()
    output_budget.check_stability()
    return validate_inspection({
        **common(INSPECTION_SCHEMA), "request_reference": report["request_reference"], "capsule": capsule_identity,
        "reported_eligibility_status": report["eligibility"]["status"],
        "independently_derived_eligibility_status": status, "eligibility_agreement": "AGREES",
        "phase43_reader_independent_result": owner, "regenerated_outputs": "BYTE_IDENTICAL",
        "output_artifacts": [{"name": name, **_identity(raws[name])} for name in OUTPUT_NAMES],
        "inputs": manifest["inputs"],
        "checks": [{"check": name, "result": CheckResult.PASSED.value} for name in INSPECTION_CHECKS],
        "inspection_scope": INSPECTION_SCOPE,
    }, mode)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "task_reconciliation_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Independent offline inspection of reconciliation outputs; authorizes nothing.",
                       allow_abbrev=False)
    add_input_arguments(parser)
    for name in ("inbox", "report", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        inspection = inspect_task_reconciliation(args)
        publish_inspection(args.output, inspection)
    except FileNotFoundError:
        print("task_reconciliation_inspection: missing_explicit_input_or_output_file", file=sys.stderr)
        return 2
    except InputError as error:
        disagreement = str(error).startswith("task_reconciliation_inspection_disagreement_")
        print("task_reconciliation_inspection: " + ("outputs_disagree_with_independent_recomputation"
                                                    if disagreement else "input_or_contract_rejected"), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("task_reconciliation_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created reconciliation inspection; eligibility_agreement=AGREES; regenerated_outputs=BYTE_IDENTICAL")
    print("reported_eligibility_status=" + inspection["reported_eligibility_status"])
    print("producer_authenticated=false; task_dispatched=false; task_assigned=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("independent_status", "inspect_task_reconciliation", "main")
