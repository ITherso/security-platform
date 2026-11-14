"""Inspect five new exchange outputs and the capsule's four in-memory members."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
for _path in (_HERE.parent, _HERE.parent / "commercial_reference_capsule",
              _HERE.parent / "commercial_capsule_derivation",
              _HERE.parent / "commercial_capsule_tabular",
              _HERE.parent / "commercial_tabular_inbox",
              _HERE.parent / "commercial_file_reference_index",
              _HERE.parent / "commercial_co_reference",
              _HERE.parent / "commercial_cohort_query",
              _HERE.parent / "commercial_evidence_followup",
              _HERE.parent / "commercial_response_slots",
              _HERE.parent / "commercial_deferred_intake", _HERE):
    sys.path.insert(0, str(_path))

from exchange_contracts import (
    INSPECTION_SCHEMA, MAX_CAPSULE_BYTES, MAX_INDEX_BYTES, MAX_RECEIPT_BYTES,
    MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES, MAX_TOTAL_INPUT_BYTES, InputError,
    common, json_bytes, parse_json, validate_index, validate_receipt, validate_relationships,
)
from phase42_adapter import InputBudget
from recipient_reader import inspect_task_exchange_capsule, read_portable_task_request
from output_renderer import render_task_exchange_summary
from artifact_manifest import manifest_data, publish_inspection


def _identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect_task_exchange(capsule_path: str, index_path: str, receipt_path: str,
                           summary_path: str, manifest_path: str) -> dict:
    """Check new outputs without reading original Phase42 source artifacts."""
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    raw_capsule = budget.read_binary(capsule_path, MAX_CAPSULE_BYTES)
    portable = inspect_task_exchange_capsule(raw_capsule)
    envelope, _response_contract, inner_artifacts = read_portable_task_request(portable)
    raw_index = budget.read_text(index_path, MAX_INDEX_BYTES)
    raw_receipt = budget.read_text(receipt_path, MAX_RECEIPT_BYTES)
    index = validate_index(parse_json(raw_index, maximum=MAX_INDEX_BYTES))
    receipt = validate_receipt(parse_json(raw_receipt, maximum=MAX_RECEIPT_BYTES))
    envelope, index, receipt = validate_relationships(envelope, index, receipt)
    capsule_sha256 = hashlib.sha256(raw_capsule).hexdigest()
    if index["capsule_sha256"] != capsule_sha256:
        raise InputError("task_exchange_inspection_actual_capsule_digest_mismatch")
    if raw_index != json_bytes(index, maximum=MAX_INDEX_BYTES):
        raise InputError("task_exchange_inspection_index_not_canonical")
    if raw_receipt != json_bytes(receipt, maximum=MAX_RECEIPT_BYTES):
        raise InputError("task_exchange_inspection_receipt_not_canonical")
    raw_summary = budget.read_text(summary_path, MAX_SUMMARY_BYTES)
    if raw_summary != render_task_exchange_summary(envelope, index, receipt):
        raise InputError("task_exchange_inspection_summary_mismatch")
    raw_manifest = budget.read_text(manifest_path, MAX_MANIFEST_BYTES)
    actual_manifest = parse_json(raw_manifest, maximum=MAX_MANIFEST_BYTES)
    payloads = {
        "task-exchange-capsule.zip": raw_capsule,
        "task-exchange-index.json": raw_index,
        "task-exchange-source-receipt.json": raw_receipt,
        "task-exchange-summary.md": raw_summary,
    }
    expected_manifest = manifest_data(raw_capsule, index, receipt, payloads)
    if (raw_manifest != json_bytes(actual_manifest, maximum=MAX_MANIFEST_BYTES)
            or json_bytes(actual_manifest, maximum=MAX_MANIFEST_BYTES)
            != json_bytes(expected_manifest, maximum=MAX_MANIFEST_BYTES)):
        raise InputError("task_exchange_inspection_manifest_mismatch")
    budget.check_stability()
    return {
        **common(INSPECTION_SCHEMA),
        "source_phase42_register_sha256": envelope["source_phase42_register_sha256"],
        "source_phase42_manifest_sha256": envelope["source_phase42_manifest_sha256"],
        "source_artifacts": [dict(item) for item in receipt["source_artifacts"]],
        "source_counts": deepcopy(receipt["source_counts"]),
        "exchange_counts": dict(index["counts"]),
        "capsule_sha256": capsule_sha256,
        "capsule_member_count": len(inner_artifacts),
        "portable_capsule_members": inner_artifacts,
        "task_ids": list(index["task_ids"]),
        "request_reference": envelope["request_reference"],
        "task_exchange_artifacts": [
            {"name": name, **_identity(body)}
            for name, body in (*payloads.items(), ("manifest.json", raw_manifest))
        ],
        "internal_content_status": "content_consistent",
        "original_Phase42_files_read": False,
        "task_dispatched": False,
        "analyst_assigned": False,
        "candidate_response_processed": False,
        "source_observation_verified": False,
        "source_producer_verified": False,
        "recipient_authorized": False,
        "human_acceptance_verified": False,
        "second_host_acceptance_performed": False,
        "inspection_scope": "five_new_task_exchange_outputs_and_capsule_internal_correspondence_only",
        "integrity_limit": (
            "Only the five new exchange outputs and four in-memory capsule members are checked. "
            "Minimal tasks and response definitions are internally consistent; source truth, original binding "
            "preimage, producer identity, dispatch, recipient authorization and real second-host acceptance are not verified."
        ),
    }


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "task_exchange_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(
        description="Inspect five new outputs and a portable task capsule; no sending or recipient authorization.",
        allow_abbrev=False,
    )
    for name in ("capsule", "index", "receipt", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_task_exchange(args.capsule, args.index, args.receipt,
                                       args.summary, args.manifest)
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("task_exchange_inspection: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("task_exchange_inspection: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("task_exchange_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created task exchange inspection; internal_content_status=content_consistent")
    print(report["demo_label"])
    print("task_dispatched=false; recipient_authorized=false; second_host_acceptance_performed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("inspect_task_exchange",)
