"""Import five explicit Phase24 output files, never the original source tree."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from commercial_handoff.input_loader import check_existing_path, explicit_relative_path
from commercial_composition.artifact_manifest import identity, manifest_data
from commercial_composition.composition_contracts import validate_documents as validate_composition
from commercial_composition.release_constraints import build_constraints
from commercial_composition.source_inventory import read_explicit_text, _same_api_identity
from .evidence_contracts import InputError, json_bytes, parse_json


@dataclass(frozen=True, slots=True)
class CompositionContext:
    inventory: dict
    dependencies: dict
    constraints: dict
    reference: dict
    _selected_paths: tuple[tuple[Path, tuple], ...]

    def check_stability(self) -> None:
        for path, expected in self._selected_paths:
            current = check_existing_path(path, directory=False)
            if _same_api_identity(current) != expected:
                raise InputError("license_review_composition_changed")


def load_composition(scope: dict) -> CompositionContext:
    raw, paths = {}, []
    limits = {"inventory": 1024 * 1024, "dependencies": 1024 * 1024,
              "constraints": 1024 * 1024, "summary": 512 * 1024, "manifest": 64 * 1024}
    for role, maximum in limits.items():
        path = explicit_relative_path(scope["composition_inputs"][role])
        raw[role], metadata = read_explicit_text(path, maximum)
        paths.append((path, metadata))
        if identity(raw[role]) != scope["composition_reference"][role]:
            raise InputError("license_review_composition_identity_mismatch")
    inventory, dependencies, constraints = (parse_json(raw[role], maximum=1024 * 1024)
                                           for role in ("inventory", "dependencies", "constraints"))
    validate_composition(inventory, dependencies, constraints)
    if not 1 <= len(dependencies["license_evidence"]) <= 1024:
        raise InputError("license_review_source_record_count_limit")
    reference = {"candidate_reference": inventory["candidate_reference"],
                 "source_commits": {row["root_id"]: row["pinned_commit"]
                                    for row in inventory["source_roots"]},
                 **{role: identity(value) for role, value in raw.items()}}
    if reference != scope["composition_reference"]:
        raise InputError("license_review_composition_reference_mismatch")
    if json_bytes(constraints) != json_bytes(build_constraints(inventory, dependencies)):
        raise InputError("license_review_source_constraints_mismatch")
    payloads = {"composition-inventory.json": raw["inventory"],
                "dependency-license-ledger.json": raw["dependencies"],
                "release-constraints.json": raw["constraints"],
                "composition-summary.md": raw["summary"]}
    if json_bytes(parse_json(raw["manifest"], maximum=64 * 1024)) != json_bytes(
            manifest_data(inventory, dependencies, constraints, payloads)):
        raise InputError("license_review_composition_manifest_mismatch")
    context = CompositionContext(inventory, dependencies, constraints, reference, tuple(paths))
    context.check_stability()
    return context
