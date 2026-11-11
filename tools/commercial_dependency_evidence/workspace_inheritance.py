"""Pure source-template inheritance; never activate Cargo features or targets."""
from __future__ import annotations

from copy import deepcopy

from commercial_composition.dependency_reader import _row as legacy_row
from .evidence_contracts import InputError, record_digest


SOURCE_DECLARATION_FIELDS = (
    "declaration_id", "manifest_id", "manifest_sha256", "phase24_file_ref", "scope",
    "declaring_package_name", "dependency_key", "declared_package_name", "declared_requirement",
    "dependency_kind", "target_condition", "toml_field_path", "workspace_inherited", "optional",
    "features", "default_features", "source_locator_kind", "source_locator_sha256",
    "git_reference_sha256", "activation_status", "target_evaluation",
)
LEGACY_FIELDS = ("ecosystem", "name", "version", "declared_requirement", "source_type",
                 "source_checksum", "source_identity_sha256", "relation", "directness", "local_package_artifact")
DECLARATION_LIMITATIONS = (
    "static_source_declaration_not_dependency_resolution", "activation_not_evaluated", "target_not_evaluated",
    "workspace_pool_not_all_crate_dependencies", "workspace_definition_unavailable", "workspace_definition_ambiguous",
    "workspace_membership_not_established",
)
INHERITANCE_STATUSES = ("not_requested", "workspace_inherited_declaration", "insufficient_source_evidence")
INHERITANCE_REASONS = ("not_requested", "explicit_workspace_template", "workspace_root_unavailable",
                       "workspace_template_unavailable", "workspace_root_ambiguous", "workspace_membership_not_established")
DECLARATION_STATUSES = ("direct_manifest_declaration", "workspace_inherited_declaration", "conditional_declaration",
                        "source_scope_only", "insufficient_source_evidence")


def declaration_location_id(manifest_sha256: str, toml_field_path: list[str]) -> str:
    return "decl-" + record_digest({"manifest_sha256": manifest_sha256, "toml_field_path": toml_field_path})


def declaration_fingerprint(row: dict) -> str:
    return record_digest({name: row[name] for name in SOURCE_DECLARATION_FIELDS})


def _legacy(source: dict, *, shared: bool) -> dict:
    locator = source["source_locator_kind"]
    requirement = source["declared_requirement"]
    source_type = ("unknown" if locator == "path" else "git" if locator == "git" else
                   "registry" if requirement is not None or locator is not None else "unknown")
    if source_type == "unknown" and locator is None:
        raise InputError("direct_dependency_source_locator_missing")
    return legacy_row("rust", source["declared_package_name"] or source["dependency_key"],
                      requirement=requirement, source_type=source_type,
                      source_identity=source["source_locator_sha256"],
                      directness="unknown" if shared else "direct_in_selected_manifest")


def _literal_member_path(value: str) -> bool:
    return (not any(char in value for char in "\\:*?[]{}!") and not value.startswith("/")
            and all(part not in ("", ".", "..") for part in value.split("/")))


def _membership_established(root: dict, child: dict) -> bool:
    """Only exact explicit relative members; no glob, path or Cargo evaluation."""
    paths = root["workspace_members"] + root["workspace_exclude"]
    if (child["package_workspace_declared"] or any(not _literal_member_path(path) for path in paths)
            or "/" not in child["path"]):
        return False
    directory = child["path"].rsplit("/", 1)[0]
    return directory in root["workspace_members"] and directory not in root["workspace_exclude"]


def rebuild_inheritance(manifests: list[dict], declarations: list[dict]) -> list[dict]:
    """Recompute source metadata relationships; no raw TOML or source reads."""
    by_manifest = {row["manifest_id"]: row for row in manifests}
    templates = {}
    for row in declarations:
        if row["scope"] == "workspace_pool":
            key = (row["manifest_id"], row["dependency_key"])
            if key in templates:
                raise InputError("direct_dependency_duplicate_workspace_template")
            templates[key] = row
    result = []
    for row in declarations:
        manifest = by_manifest.get(row["manifest_id"])
        if (manifest is None or row["manifest_sha256"] != manifest["sha256"]
                or row["phase24_file_ref"] != manifest["phase24_file_ref"]):
            raise InputError("direct_dependency_manifest_identity_mismatch")
        source = {name: deepcopy(row[name]) for name in SOURCE_DECLARATION_FIELDS}
        source["declaration_id"] = declaration_location_id(source["manifest_sha256"], source["toml_field_path"])
        inheritance, reason, template_id, effective = "not_requested", "not_requested", None, source
        limits = ["static_source_declaration_not_dependency_resolution", "activation_not_evaluated"]
        if source["target_condition"] is not None:
            limits.append("target_not_evaluated")
        if source["scope"] == "workspace_pool":
            limits.append("workspace_pool_not_all_crate_dependencies")
            if source["workspace_inherited"]:
                raise InputError("direct_dependency_workspace_template_cannot_inherit_itself")
        elif source["workspace_inherited"]:
            roots = [item for item in manifests if item["root_id"] == manifest["root_id"]
                     and item["pinned_commit"] == manifest["pinned_commit"]
                     and item["path"] == "Cargo.toml" and item["is_workspace"]]
            inheritance = "insufficient_source_evidence"
            reason = "workspace_root_ambiguous" if len(roots) > 1 else "workspace_root_unavailable"
            effective = None
            if len(roots) == 1:
                template = templates.get((roots[0]["manifest_id"], source["dependency_key"]))
                if not _membership_established(roots[0], manifest):
                    reason = "workspace_membership_not_established"
                elif template is not None:
                    inheritance, reason = "workspace_inherited_declaration", "explicit_workspace_template"
                    template_id, effective = template["declaration_id"], template
                else:
                    reason = "workspace_template_unavailable"
            if effective is None:
                limits.append("workspace_membership_not_established" if reason == "workspace_membership_not_established"
                              else "workspace_definition_ambiguous" if len(roots) > 1 else "workspace_definition_unavailable")
        legacy = None if effective is None else _legacy(effective, shared=source["scope"] == "workspace_pool")
        conditional = (source["optional"] is True or source["dependency_kind"] in ("dev", "build")
                       or source["target_condition"] is not None)
        status = ("insufficient_source_evidence" if legacy is None else "source_scope_only"
                  if source["scope"] == "workspace_pool" else "conditional_declaration" if conditional else
                  "workspace_inherited_declaration" if source["workspace_inherited"] else "direct_manifest_declaration")
        result.append({**source, "source_fingerprint": declaration_fingerprint(source),
                       "package_name": (legacy["name"] if legacy is not None else
                                        source["declared_package_name"] or source["dependency_key"]),
                       "workspace_template_id": template_id, "inheritance_status": inheritance,
                       "inheritance_reason_code": reason, "legacy_projection": legacy,
                       "evidence_status": status, "limitations": limits})
    return result


__all__ = ("rebuild_inheritance", "declaration_location_id", "declaration_fingerprint")
