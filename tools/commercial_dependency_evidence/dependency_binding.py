"""Match complete old metadata projections; never resolve versions or ordinals."""
from __future__ import annotations

from .evidence_contracts import InputError, record_digest
from .workspace_inheritance import LEGACY_FIELDS


BINDING_STATUSES = ("declaration_record_matched", "ambiguous_record_binding", "insufficient_source_evidence")
BINDING_MATCHED_FIELDS = ("manifest_id", "review_scope", *LEGACY_FIELDS)
BINDING_MISSING_FIELDS = (
    "dependency_kind", "target_condition", "optional", "features", "default_features",
    "workspace_inherited", "dependency_key", "declaring_package_name", "git_reference_sha256",
)
BINDING_REASON_CODES = ("unique_legacy_projection_match", "multiple_legacy_projection_matches",
                        "no_legacy_projection_match", "legacy_projection_unavailable")


def binding_fingerprint(row: dict) -> str:
    return record_digest({name: value for name, value in row.items() if name != "binding_fingerprint"})


def build_bindings(declarations: list[dict], phase24_records: list[dict], manifest_catalog: list[dict]) -> list[dict]:
    manifests = {row["manifest_id"]: row for row in manifest_catalog}
    result = []
    for declaration in declarations:
        manifest = manifests.get(declaration["manifest_id"])
        if (manifest is None or manifest["sha256"] != declaration["manifest_sha256"]
                or manifest["source_file_ref"] != declaration["phase24_file_ref"]):
            raise InputError("direct_dependency_binding_manifest_identity_mismatch")
        legacy = declaration["legacy_projection"]
        candidates = []
        if legacy is not None:
            expected = {"manifest_id": declaration["manifest_id"], "review_scope": manifest["context"], **legacy}
            candidates = [row["dependency_id"] for row in phase24_records
                          if row["relation"] == "direct_declaration"
                          and all(row[name] == expected[name] for name in BINDING_MATCHED_FIELDS)]
        status = ("declaration_record_matched" if len(candidates) == 1 else "ambiguous_record_binding"
                  if candidates else "insufficient_source_evidence")
        reason = ("legacy_projection_unavailable" if legacy is None else "unique_legacy_projection_match"
                  if len(candidates) == 1 else "multiple_legacy_projection_matches" if candidates else "no_legacy_projection_match")
        row = {"declaration_id": declaration["declaration_id"], "status": status,
               "matched_record_id": candidates[0] if len(candidates) == 1 else None,
               "candidate_record_ids": candidates, "matched_fields": list(BINDING_MATCHED_FIELDS) if candidates else [],
               "missing_fields": list(BINDING_MISSING_FIELDS), "reason_codes": [reason]}
        row["binding_fingerprint"] = binding_fingerprint(row)
        result.append(row)
    return result


__all__ = ("build_bindings", "binding_fingerprint")
