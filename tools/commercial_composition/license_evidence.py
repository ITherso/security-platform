"""Scoped local declarations only; license evidence never grants redistribution."""
from __future__ import annotations

from dataclasses import dataclass
import re
import tomllib
from typing import TYPE_CHECKING

from .composition_contracts import InputError

if TYPE_CHECKING:
    from .source_inventory import SourceContext


_LEVELS = (
    "local_license_file", "package_metadata_declaration",
    "source_manifest_declaration", "not_available", "conflicting_declarations",
)
_LEVEL_ORDER = {name: index for index, name in enumerate(_LEVELS[:3])}
_SIMPLE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_FILE_ID = re.compile(r"F[0-9]{4}\Z")


def _unique(values):
    return tuple(dict.fromkeys(values))


def _declaration(value: object) -> str:
    # Record a bounded metadata label/expression, not arbitrary license prose or a URL.
    if (type(value) is not str or not 0 < len(value) <= 256
            or value != value.strip()
            or re.fullmatch(r"[A-Za-z0-9 .()+:/_-]+", value) is None
            or "://" in value):
        raise InputError("composition_unsupported_license_declaration")
    return value


@dataclass(frozen=True, slots=True)
class LicenseEvidence:
    evidence_id: str
    subject_type: str
    subject_id: str
    evidence_level: str
    declared_license: str | None
    source_file_refs: tuple[str, ...]
    uncertainty_codes: tuple[str, ...]
    human_review_required: bool = True
    redistribution_authorized: bool = False

    def to_dict(self) -> dict:
        if (type(self.evidence_id) is not str
                or re.fullmatch(r"L[0-9]{4,6}", self.evidence_id) is None
                or not 1 <= int(self.evidence_id[1:]) <= 10064
                or self.subject_type not in ("component", "dependency")
                or type(self.subject_id) is not str or _SIMPLE.fullmatch(self.subject_id) is None
                or self.evidence_level not in _LEVELS
                or type(self.source_file_refs) is not tuple
                or type(self.uncertainty_codes) is not tuple
                or len(self.source_file_refs) > 5000 or len(self.uncertainty_codes) > 64
                or any(type(ref) is not str or _FILE_ID.fullmatch(ref) is None
                       or not 1 <= int(ref[1:]) <= 5000
                       for ref in self.source_file_refs)
                or any(type(code) is not str or _SIMPLE.fullmatch(code) is None
                       for code in self.uncertainty_codes)
                or len(set(self.source_file_refs)) != len(self.source_file_refs)
                or len(set(self.uncertainty_codes)) != len(self.uncertainty_codes)
                or self.human_review_required is not True
                or self.redistribution_authorized is not False):
            raise InputError("composition_invalid_license_evidence")
        if self.declared_license is not None:
            _declaration(self.declared_license)
        if (self.evidence_level == "not_available" and self.declared_license is not None
                or self.evidence_level in _LEVELS[:3]
                and (self.declared_license is None or not self.source_file_refs)
                or self.evidence_level == "conflicting_declarations" and not self.uncertainty_codes):
            raise InputError("composition_inconsistent_license_evidence")
        return {
            "evidence_id": self.evidence_id, "subject_type": self.subject_type,
            "subject_id": self.subject_id, "evidence_level": self.evidence_level,
            "declared_license": self.declared_license,
            "source_file_refs": list(self.source_file_refs),
            "uncertainty_codes": list(self.uncertainty_codes),
            "human_review_required": True, "redistribution_authorized": False,
        }


def _manifest(ctx: SourceContext, root_id: str, path: str) -> dict:
    try:
        return tomllib.loads(ctx.raw(root_id, path).decode("utf-8", "strict"))
    except (UnicodeError, tomllib.TOMLDecodeError):
        raise InputError("composition_invalid_license_manifest") from None


def _metadata_declarations(data: dict, *, workspace: bool) -> tuple[list[tuple[str, str]], list[str]]:
    declarations, uncertainties = [], []
    package = data.get("package", {})
    project = data.get("project", {})
    if type(package) is not dict or type(project) is not dict:
        raise InputError("composition_invalid_license_metadata")
    for section in (package, project):
        if "license" not in section:
            continue
        value = section["license"]
        if type(value) is str:
            declarations.append((_declaration(value), "package_metadata_declaration"))
        elif type(value) is dict and value == {"workspace": True}:
            uncertainties.append("workspace_license_inheritance_declared")
        elif type(value) is dict and set(value) <= {"file", "text"}:
            # Do not follow metadata paths, copy license prose, or silently infer a label.
            uncertainties.append("license_metadata_form_not_interpreted")
        else:
            raise InputError("composition_unsupported_license_metadata")
    if workspace:
        section = data.get("workspace", {})
        if type(section) is not dict or type(section.get("package", {})) is not dict:
            raise InputError("composition_invalid_workspace_license_metadata")
        value = section.get("package", {}).get("license")
        if value is not None:
            declarations.append((_declaration(value), "source_manifest_declaration"))
    return declarations, uncertainties


def _component_evidence(ctx: SourceContext, component: dict, files: dict) -> LicenseEvidence:
    declarations, refs, uncertainties = [], [], ["redistribution_not_reviewed"]
    sources = [item for item in ctx.scope["license_evidence_sources"]
               if component["component_id"] in item["applies_to"]]
    if any(item["root_id"] != component["root_id"] for item in sources):
        raise InputError("composition_cross_repository_license_attribution")
    parsed = set()
    workspace_declaration_present = False
    for source in sources:
        root_id, path = source["root_id"], source["path"]
        ref = ctx.file_ref(root_id, path)
        if ref not in files:
            raise InputError("composition_unknown_license_file_reference")
        refs.append(ref)
        if source["kind"] == "local_license_file":
            lines = ctx.raw(root_id, path).decode("utf-8", "strict").splitlines()
            # Only a label actually present in the selected file is recognized.
            if lines and lines[0].strip() == "MIT License":
                declarations.append(("MIT", "local_license_file"))
                uncertainties.append("license_text_label_not_legal_validation")
            else:
                uncertainties.append("local_license_text_not_classified")
        elif source["kind"] == "source_manifest_declaration":
            found, notes = _metadata_declarations(_manifest(ctx, root_id, path), workspace=True)
            workspace_declaration_present |= any(level == "source_manifest_declaration" for _, level in found)
            declarations.extend(found)
            uncertainties.extend(notes)
            parsed.add((root_id, path))
        else:
            raise InputError("composition_unsupported_license_evidence_source")
    # Explicit component Cargo/project manifests can expose contrary declarations.
    # No source lookup is discovered from package URLs or license-file metadata.
    for ref in component["source_file_refs"]:
        item = files[ref]
        path = item["path"]
        key = (item["root_id"], path)
        if key in parsed or path.rsplit("/", 1)[-1] not in ("Cargo.toml", "pyproject.toml"):
            continue
        found, notes = _metadata_declarations(_manifest(ctx, *key), workspace=False)
        if found or notes:
            refs.append(ref)
            declarations.extend(found)
            uncertainties.extend(notes)
        parsed.add(key)
    if "workspace_license_inheritance_declared" in uncertainties and not workspace_declaration_present:
        uncertainties.append("workspace_license_declaration_unavailable")
    labels = _unique(label for label, _ in declarations)
    if len(labels) > 1:
        level, declared = "conflicting_declarations", None
        uncertainties.append("conflicting_license_declarations")
    elif labels:
        declared = labels[0]
        level = min((level for label, level in declarations if label == declared), key=_LEVEL_ORDER.__getitem__)
        uncertainties.append("scoped_declaration_not_dependency_license_clearance")
    else:
        level, declared = "not_available", None
        uncertainties.append("license_not_declared")
    return LicenseEvidence("L0000", "component", component["component_id"], level,
                           declared, _unique(refs), _unique(uncertainties))


def build_license_evidence(ctx: SourceContext, inventory: dict, ledger: dict) -> list[dict]:
    """One record per selected component/dependency; never inspect package caches."""
    files = {item["file_id"]: item for item in inventory["files"]}
    manifests = {item["manifest_id"]: item for item in ledger["manifest_records"]}
    rows = []
    for component in inventory["components"]:
        evidence = _component_evidence(ctx, component, files)
        rows.append(LicenseEvidence("L" + str(len(rows) + 1).zfill(4), evidence.subject_type,
                                    evidence.subject_id, evidence.evidence_level,
                                    evidence.declared_license, evidence.source_file_refs,
                                    evidence.uncertainty_codes).to_dict())
    for dependency in ledger["dependencies"]:
        source = manifests[dependency["manifest_id"]]
        ref = ctx.file_ref(source["root_id"], source["path"])
        if ref not in files:
            raise InputError("composition_unknown_dependency_license_source")
        # Cargo.lock/requirements pins and dependency declarations do not establish
        # a dependency's license. A first-party MIT label must not leak into them.
        note = ("license_not_declared_in_lock" if dependency["relation"] == "lock_record"
                else "dependency_license_not_declared")
        rows.append(LicenseEvidence(
            "L" + str(len(rows) + 1).zfill(4), "dependency", dependency["dependency_id"],
            "not_available", None, (ref,),
            (note, "package_artifact_not_selected_or_verified", "redistribution_not_reviewed"),
        ).to_dict())
    return rows


__all__ = ("LicenseEvidence", "build_license_evidence")
