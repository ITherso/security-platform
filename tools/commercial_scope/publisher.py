"""Fixed inventory, no-overwrite publication; completion manifest is last."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from commercial_handoff.schema import InputError

from . import DEMO_LABEL
from .scope_contracts import LoadedProposal, json_bytes
from .source_manifest import SourceSnapshot, source_snapshot_to_dict


OUTPUT_NAMES = (
    "capability-catalog.json", "scope-preflight.json",
    "assessment-plan-proposal.json", "assessment-plan-summary.md",
)
MANIFEST_NAME = "manifest.json"


def publish_scope(output: Path, documents: dict[str, bytes],
                  proposal: LoadedProposal, snapshot: SourceSnapshot) -> None:
    """Publish new payloads and a last-written manifest, never adopt a directory.

    The unchanged Phase16 directory identity checks are reused. Only this run's
    fixed staging filenames are cleaned. Failure can leave a partial new output;
    neither crash recovery nor hostile-race safety has been accepted by tests.
    """
    if type(documents) is not dict or set(documents) != set(OUTPUT_NAMES):
        raise InputError("scope_invalid_output_inventory")
    for name in OUTPUT_NAMES:
        cap = 128 * 1024 if name.endswith(".md") else 256 * 1024
        if type(documents[name]) is not bytes or not 0 < len(documents[name]) <= cap:
            raise InputError("scope_invalid_output_payload")
    manifest = {
        "schema_version": "termivar-assessment-scope-output-manifest/v1",
        "demo_label": DEMO_LABEL,
        "demo_only": True, "execution_authorized": False,
        "authorization_verified": False, "production_ready": False,
        "proposal": {"schema_version": proposal.document.schema_version,
                     "proposal_id": proposal.document.proposal_id,
                     "bytes": proposal.byte_length, "sha256": proposal.sha256},
        "native_source": source_snapshot_to_dict(snapshot),
        "files": [{"name": name, "bytes": len(documents[name]),
                   "sha256": hashlib.sha256(documents[name]).hexdigest()}
                  for name in OUTPUT_NAMES],
        "output_files": [*OUTPUT_NAMES, MANIFEST_NAME],
        "manifest_self_excluded": True,
        "integrity_limit": "SHA256 binds selected bytes only; it authenticates neither producer, source history, authorization nor runtime success.",
        "completion_marker": "Published last. Compare every payload to its size and digest; a manifest alone is not authentication or runtime acceptance.",
    }
    raw = json_bytes(manifest, maximum=64 * 1024)
    payloads = {**documents, MANIFEST_NAME: raw}
    names = (*OUTPUT_NAMES, MANIFEST_NAME)
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".scope-planner-stage-", dir=output.parent))
    stage_info = check_existing_path(stage, directory=True)
    try:
        for name in names:
            _same_directory(stage, stage_info)
            with (stage / name).open("xb") as stream:
                stream.write(payloads[name])
                stream.flush()
                os.fsync(stream.fileno())
        _same_directory(output.parent, parent_info)
        output.mkdir(exist_ok=False)
        output_info = check_existing_path(output, directory=True)
        for name in names:
            _same_directory(output.parent, parent_info)
            _same_directory(output, output_info)
            _same_directory(stage, stage_info)
            os.link(stage / name, output / name, follow_symlinks=False)
    finally:
        try:
            _same_directory(stage, stage_info)
            for name in names:
                candidate = stage / name
                if os.path.lexists(candidate):
                    check_existing_path(candidate, directory=False)
                    candidate.unlink()
            stage.rmdir()
        except (OSError, InputError):
            pass
