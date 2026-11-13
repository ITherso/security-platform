"""Inspect two capsules and their closed derivation relation without extraction.

Both capsule inputs pass through the existing public Phase33 inspection path
behind the narrow adapter. This module implements no ZIP reader, source scan,
guard evaluator or original-source verification.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(1, str(_HERE.parent / "commercial_reference_capsule"))
sys.path.insert(2, str(_HERE.parent))

from derivation_contracts import (
    INSPECTION_SCHEMA, MAX_LEDGER_BYTES, MAX_MANIFEST_BYTES, MAX_SUMMARY_BYTES,
    MAX_TOTAL_INPUT_BYTES, InputError, common, json_bytes, make_ledger,
    parse_json, validate_ledger,
)
from phase33_adapter import InputBudget, load_validated_source, read_validated_source
from derivation_renderer import render_summary
from artifact_manifest import manifest_data, publish_inspection


def _byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect_derivation(source_bundle: str, derived_bundle: str, ledger_path: str,
                       summary_path: str, manifest_path: str) -> dict:
    """Return bounded metadata about internal capsule/derivation consistency.

    The request comes only from a closed, validated ledger. No path or member
    name inside that ledger is followed, and no omitted reference is emitted.
    """
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    raw_ledger = budget.read_text(ledger_path, MAX_LEDGER_BYTES)
    ledger = validate_ledger(parse_json(raw_ledger, maximum=MAX_LEDGER_BYTES))
    request = ledger["request"]
    selected_ids = request["selected_reference_ids"]

    source_snapshot = load_validated_source(source_bundle, selected_ids, budget)
    source_model, source_identity = read_validated_source(source_snapshot)
    if source_identity["sha256"] != request["source_capsule_sha256"]:
        raise InputError("capsule_derivation_inspection_source_digest_mismatch")

    derived_snapshot = load_validated_source(derived_bundle, selected_ids, budget)
    derived_model, derived_identity = read_validated_source(derived_snapshot)
    # make_ledger applies the shared monotonic disclosure invariant to these
    # owner-validated models before constructing its closed expected metadata.
    expected_ledger = make_ledger(
        request, source_model, derived_model, source_identity, derived_identity)
    if (json_bytes(ledger, maximum=MAX_LEDGER_BYTES)
            != json_bytes(expected_ledger, maximum=MAX_LEDGER_BYTES)):
        raise InputError("capsule_derivation_inspection_ledger_mismatch")

    raw_summary = budget.read_text(summary_path, MAX_SUMMARY_BYTES)
    if raw_summary != render_summary(ledger):
        raise InputError("capsule_derivation_inspection_summary_mismatch")
    raw_manifest = budget.read_text(manifest_path, MAX_MANIFEST_BYTES)
    actual_manifest = parse_json(raw_manifest, maximum=MAX_MANIFEST_BYTES)
    payloads = {
        "derived-reference-capsule.zip": derived_snapshot.raw_bytes,
        "derivation-ledger.json": raw_ledger,
        "derivation-summary.md": raw_summary,
    }
    expected_manifest = manifest_data(ledger, payloads)
    if (json_bytes(actual_manifest, maximum=MAX_MANIFEST_BYTES)
            != json_bytes(expected_manifest, maximum=MAX_MANIFEST_BYTES)):
        raise InputError("capsule_derivation_inspection_manifest_mismatch")
    budget.check_stability()

    source_counts, derived_counts = source_model["counts"], derived_model["counts"]
    # Aggregate counts describe the relation without listing the identities or
    # positive projection fields of any reference omitted from the new capsule.
    return {
        **common(INSPECTION_SCHEMA, ledger["derivation_reference"]),
        "source_capsule": dict(source_identity),
        "derived_capsule": dict(derived_identity),
        "source_counts": dict(source_counts),
        "derived_counts": dict(derived_counts),
        "omitted_reference_count": (
            source_counts["requested_reference_count"]
            - derived_counts["requested_reference_count"]
        ),
        "internal_content_status": "content_consistent",
        "subset_relation": ledger["subset_relation"],
        "derivation_artifacts": [
            {"role": "ledger", **_byte_identity(raw_ledger)},
            {"role": "summary", **_byte_identity(raw_summary)},
            {"role": "manifest", **_byte_identity(raw_manifest)},
        ],
        "original_phase31_files_read": False,
        "original_phase32_files_read": False,
        "old_guard_reexecuted": False,
        "native_source_files_read": False,
        "original_source_artifact_bytes_independently_verified": False,
        "source_producer_verified": False,
        "legal_review_performed": False,
        "inspection_scope": "two_explicit_capsules_and_derivation_ledger_summary_manifest_only",
        "integrity_limit": (
            "Internal source-to-derived subset, selected projection equality, byte/model, ledger, "
            "summary and manifest correspondence only. No independent Phase31 guard, original source "
            "freshness, producer, compiler, ownership, human, legal or release verification."
        ),
    }


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "capsule_derivation_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(
        description="Two-capsule internal subset relation only; no original-source verification.",
        allow_abbrev=False,
    )
    for name in ("source-bundle", "derived-bundle", "ledger", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_derivation(
            args.source_bundle, args.derived_bundle, args.ledger, args.summary, args.manifest)
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("capsule_derivation_inspection: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("capsule_derivation_inspection: contract_or_boundary_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("capsule_derivation_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created offline capsule derivation inspection; internal_content_status=content_consistent")
    print(report["demo_label"])
    print("source_files_reobserved=false; upstream_guard_independently_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("inspect_derivation",)
