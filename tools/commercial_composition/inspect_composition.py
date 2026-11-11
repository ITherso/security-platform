"""Inspect five explicit outputs without reading source roots or dependencies."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_case.bundle_reader import publish_inspection
from commercial_handoff.input_loader import explicit_relative_path
from commercial_composition.artifact_manifest import identity, manifest_data, read_payload
from commercial_composition.composition_contracts import (
    DEMO_LABEL, InputError, common, json_bytes, parse_json, validate_documents,
)
from commercial_composition.composition_renderer import render_summary
from commercial_composition.release_constraints import build_constraints


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "composition_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Inspect explicit composition files; no original-source revalidation.", allow_abbrev=False)
    for name in ("inventory", "dependencies", "constraints", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        inventory_raw = read_payload(explicit_relative_path(args.inventory), 4 * 1024 * 1024)
        dependencies_raw = read_payload(explicit_relative_path(args.dependencies), 4 * 1024 * 1024)
        constraints_raw = read_payload(explicit_relative_path(args.constraints), 4 * 1024 * 1024)
        summary_raw = read_payload(explicit_relative_path(args.summary), 512 * 1024)
        manifest_raw = read_payload(explicit_relative_path(args.manifest), 64 * 1024)
        inventory, ledger, constraints = (parse_json(r) for r in (inventory_raw, dependencies_raw, constraints_raw))
        validate_documents(inventory, ledger, constraints)
        if json_bytes(constraints) != json_bytes(build_constraints(inventory, ledger)):
            raise InputError("composition_constraint_projection_mismatch")
        if summary_raw != render_summary(inventory, ledger, constraints):
            raise InputError("composition_summary_projection_mismatch")
        payloads = {"composition-inventory.json": inventory_raw,
                    "dependency-license-ledger.json": dependencies_raw,
                    "release-constraints.json": constraints_raw,
                    "composition-summary.md": summary_raw}
        if json_bytes(parse_json(manifest_raw, maximum=64 * 1024)) != json_bytes(
                manifest_data(inventory, ledger, constraints, payloads)):
            raise InputError("composition_manifest_mismatch")
        report = {**common("termivar-offline-composition-inspection/v1", inventory["candidate_reference"]),
                  "internal_content_status": "content_consistent",
                  "input_files": [{"role": role, **identity(raw)} for role, raw in (
                      ("inventory", inventory_raw), ("dependencies", dependencies_raw),
                      ("constraints", constraints_raw), ("summary", summary_raw), ("manifest", manifest_raw))],
                  "inventory_counts": inventory["counts"], "dependency_counts": ledger["counts"],
                  "constraint_counts": constraints["counts"],
                  "source_roots_read": False, "source_scope_read": False,
                  "original_source_files_revalidated": False, "package_contents_read": False,
                  "git_commit_binding_verified": False,
                  "license_or_redistribution_review_performed": False,
                  "inspection_scope": "five_explicit_generated_files_and_pure_metadata_projections_only",
                  "integrity_limit": "Internal payload byte/model consistency only; not source, producer, license, dependency closure, build, runtime or release acceptance."}
        publish_inspection(args.output, report)
    except InputError as error:
        print("composition_inspection: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError):
        print("composition_inspection: local_inspection_failed; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created demo composition inspection; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("original_source_files_revalidated=false; redistribution_authorized=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
