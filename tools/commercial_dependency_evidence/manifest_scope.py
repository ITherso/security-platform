"""Read four explicitly scoped native manifests, without following their paths."""
from __future__ import annotations

import os
from pathlib import Path
import copy

from commercial_handoff.input_loader import check_existing_path
from commercial_composition.artifact_manifest import identity
from .evidence_contracts import InputError


def load_manifests(scope: dict, context, termivar_root: str, budget) -> tuple[dict[str, bytes], list[dict]]:
    root = Path(os.path.abspath(termivar_root))
    check_existing_path(root, directory=True)
    files = {row["file_id"]: row for row in context.inventory["files"]}
    catalog = {row["manifest_id"]: row for row in context.manifest_catalog}
    raw_by_id, metadata = {}, []
    for selected in scope["manifest_sources"]:
        source = files.get(selected["phase24_file_ref"])
        old = catalog.get(selected["manifest_id"])
        if (source is None or old is None or selected["root_id"] != "termivar"
                or selected["format"] != "cargo_toml"
                or any(selected[key] != source[key] for key in ("root_id", "path", "bytes", "sha256"))
                or any(selected[key] != old[key] for key in ("root_id", "path", "bytes", "sha256", "format"))
                or selected["phase24_file_ref"] != old["source_file_ref"]
                or selected["pinned_commit"] != context.reference["source_commits"]["termivar"]):
            raise InputError("dependency_evidence_manifest_selection_not_source_bound")
        path = root.joinpath(*selected["path"].split("/"))
        if os.path.commonpath((str(root), str(path))) != str(root):
            raise InputError("dependency_evidence_manifest_root_escape")
        raw = budget.read(path, 256 * 1024)
        if identity(raw) != {key: selected[key] for key in ("bytes", "sha256")}:
            raise InputError("dependency_evidence_manifest_bytes_changed")
        raw_by_id[selected["manifest_id"]] = raw
        metadata.append(copy.deepcopy(selected))
    return raw_by_id, metadata
