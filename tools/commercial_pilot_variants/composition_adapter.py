"""Read only explicitly selected Phase24 bytes; no source-tree discovery."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import copy

from commercial_handoff.input_loader import check_existing_path, explicit_relative_path
from commercial_composition.artifact_manifest import identity, manifest_data
from commercial_composition.composition_contracts import validate_documents
from commercial_composition.release_constraints import build_constraints
from commercial_composition.source_inventory import read_explicit_text, _same_api_identity
from .variant_contracts import InputError, json_bytes, parse_json

COMPOSITION_SCHEMAS = {
    "inventory": "termivar-offline-composition/v1",
    "dependencies": "termivar-offline-dependency-license-ledger/v1",
    "constraints": "termivar-offline-release-constraints/v1",
    "summary": None, "manifest": "termivar-offline-composition-manifest/v1",
}
EVIDENCE_SCHEMAS = {
    "ledger": "termivar-license-evidence-ledger/v1",
    "queue": "termivar-license-review-queue/v1",
    "conflicts": "termivar-license-binding-conflicts/v1",
    "summary": None, "manifest": "termivar-license-evidence-manifest/v1",
}


@dataclass(slots=True)
class ReadBudget:
    consumed: int = 0
    maximum: int = 6 * 1024 * 1024
    identities: set = field(default_factory=set)
    paths: list = field(default_factory=list)

    def read(self, path: Path, maximum: int) -> bytes:
        remaining = self.maximum - self.consumed
        if remaining <= 0:
            raise InputError("pilot_variant_source_budget_exceeded")
        raw, metadata = read_explicit_text(path, min(maximum, remaining))
        physical = metadata[:2]
        if physical in self.identities:
            raise InputError("pilot_variant_input_alias_rejected")
        self.identities.add(physical)
        self.paths.append((path, metadata))
        self.consumed += len(raw)
        return raw

    def check_stability(self) -> None:
        for path, metadata in self.paths:
            current = check_existing_path(path, directory=False)
            if _same_api_identity(current) != metadata:
                raise InputError("pilot_variant_source_changed_before_publication")


def read_group(paths: dict, expected: dict, schemas: dict, budget: ReadBudget) -> tuple[dict, dict]:
    if set(paths) != set(schemas) or set(expected) != set(schemas):
        raise InputError("pilot_variant_explicit_source_roles_required")
    raw, documents = {}, {}
    for role, schema in schemas.items():
        maximum = 64 * 1024 if role == "manifest" else 512 * 1024 if role == "summary" else 1024 * 1024
        raw[role] = budget.read(explicit_relative_path(paths[role]), maximum)
        descriptor = {"schema_version": schema, **identity(raw[role])}
        if descriptor != expected[role]:
            raise InputError("pilot_variant_source_identity_mismatch")
        if role != "summary":
            documents[role] = parse_json(raw[role], maximum=maximum)
            if type(documents[role]) is not dict or documents[role].get("schema_version") != schema:
                raise InputError("pilot_variant_unsupported_source_contract")
    return raw, documents


@dataclass(frozen=True, slots=True)
class CompositionContext:
    inventory: dict
    dependencies: dict
    constraints: dict
    reference: dict
    descriptors: dict


def load_composition(scope: dict, paths: dict, budget: ReadBudget) -> CompositionContext:
    raw, docs = read_group(paths, scope["composition_sources"], COMPOSITION_SCHEMAS, budget)
    inventory, dependencies, constraints = (docs[key] for key in ("inventory", "dependencies", "constraints"))
    validate_documents(inventory, dependencies, constraints)
    if len(inventory["components"]) > 64 or len(dependencies["dependencies"]) + len(dependencies["license_evidence"]) > 2000:
        raise InputError("pilot_variant_source_record_budget_exceeded")
    if json_bytes(constraints) != json_bytes(build_constraints(inventory, dependencies)):
        raise InputError("pilot_variant_composition_constraint_projection_mismatch")
    payloads = {"composition-inventory.json": raw["inventory"],
                "dependency-license-ledger.json": raw["dependencies"],
                "release-constraints.json": raw["constraints"],
                "composition-summary.md": raw["summary"]}
    if json_bytes(docs["manifest"]) != json_bytes(manifest_data(inventory, dependencies, constraints, payloads)):
        raise InputError("pilot_variant_composition_manifest_mismatch")
    reference = {"candidate_reference": inventory["candidate_reference"],
                 "source_commits": {row["root_id"]: row["pinned_commit"] for row in inventory["source_roots"]},
                 **{key: identity(value) for key, value in raw.items()}}
    return CompositionContext(inventory, dependencies, constraints, reference,
                              copy.deepcopy(scope["composition_sources"]))
