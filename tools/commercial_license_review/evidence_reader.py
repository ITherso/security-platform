"""Read bounded explicitly chosen evidence; retain identities, never source bodies."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tomllib

from commercial_handoff.input_loader import check_existing_path
from commercial_composition.license_evidence import _metadata_declarations
from commercial_composition.source_inventory import read_explicit_text
from .evidence_contracts import InputError, relative_path


def _labels(raw: bytes, kind: str) -> tuple[list[str], str]:
    text = raw.decode("utf-8", "strict")
    if kind in ("package_metadata", "source_manifest_declaration"):
        try:
            # Reuse only the bounded declaration helper, not a dependency parser.
            metadata = tomllib.loads(text)
            declarations, _ = _metadata_declarations(metadata, workspace=True)
        except (tomllib.TOMLDecodeError, ValueError, TypeError, RecursionError):
            return [], "uninterpreted_text"
        labels = list(dict.fromkeys(label for label, _ in declarations))
        if len(labels) > 8:
            raise InputError("license_review_evidence_label_limit")
        return labels, "metadata_declaration_observed" if labels else "uninterpreted_text"
    if kind in ("first_party_license_file", "dependency_license_file"):
        # An actual header label only, not interpretation of all license terms.
        if text.splitlines() and text.splitlines()[0].strip() == "MIT License":
            return ["MIT"], "license_header_observed"
    return [], "uninterpreted_text"


def read_evidence_sources(scope: dict, base, roots: dict[str, str]) -> list[dict]:
    if set(roots) != {"termivar", "platform"}:
        raise InputError("license_review_explicit_evidence_roots_required")
    locations = {root_id: Path(value).absolute() for root_id, value in roots.items()}
    for path in locations.values():
        check_existing_path(path, directory=True)
    if len({os.path.normcase(str(p)) for p in locations.values()}) != 2:
        raise InputError("license_review_duplicate_evidence_root")
    cache, total, result = {}, 0, []
    limits = scope["review_constraints"]
    for source in scope["evidence_sources"]:
        metadata = {"evidence_id": source["evidence_id"], "kind": source["kind"],
                    "file_present": False, "bytes": None, "sha256": None,
                    "expected_sha256": source["expected_sha256"],
                    "integrity_status": "not_read", "format_status": "missing_file",
                    "observed_license_labels": [], "baseline_file_refs": [],
                    "source_verified": False}
        if source["kind"] == "missing_evidence":
            result.append(metadata)
            continue
        path_text = relative_path(source["path"], "evidence_path")
        root_id = source["root_id"]
        key = (root_id, path_text)
        if key not in cache:
            root = locations[root_id]
            path = root.joinpath(*path_text.split("/"))
            if os.path.commonpath((str(root), str(path))) != str(root):
                raise InputError("license_review_evidence_root_escape")
            try:
                info = check_existing_path(path, directory=False)
                if total + info.st_size > limits["max_total_evidence_bytes"]:
                    raise InputError("license_review_total_evidence_byte_limit")
                body, _ = read_explicit_text(path, limits["max_evidence_file_bytes"])
            except FileNotFoundError:
                body = None
            if body is not None:
                total += len(body)
                if total > limits["max_total_evidence_bytes"]:
                    raise InputError("license_review_total_evidence_byte_limit")
            cache[key] = body
        body = cache[key]
        if body is None:
            result.append(metadata)
            continue
        digest = hashlib.sha256(body).hexdigest()
        expected = source["expected_sha256"]
        labels, format_status = _labels(body, source["kind"])
        refs = [row["file_id"] for row in base.inventory["files"]
                if row["root_id"] == root_id and row["path"] == path_text
                and row["bytes"] == len(body) and row["sha256"] == digest]
        metadata.update({"file_present": True, "bytes": len(body), "sha256": digest,
                         "integrity_status": "no_expected_hash" if expected is None else
                         "expected_hash_matched" if expected == digest else "expected_hash_mismatch",
                         "format_status": format_status, "observed_license_labels": labels,
                         "baseline_file_refs": refs})
        result.append(metadata)
    return result
