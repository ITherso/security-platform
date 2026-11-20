"""Output byte identities, the output manifest and exclusive new-directory publication."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import tempfile

from exchange_contracts import InputError, json_bytes
from local_task_records import LocalReference
from reconciliation_contracts import (
    INTEGRITY_SCOPE, MAX_INBOX_BYTES, MAX_INSPECTION_BYTES, MAX_OUTPUT_MANIFEST_BYTES, MAX_REPORT_BYTES,
    MAX_SUMMARY_BYTES, OUTPUT_MANIFEST_SCHEMA, OUTPUT_NAMES, OUTPUT_PAYLOAD_NAMES, common, fail,
    validate_inbox, validate_output_manifest, validate_report,
)
from reconciliation_renderer import render_reconciliation_summary

OUTPUT_LIMITS = dict(zip(OUTPUT_NAMES, (MAX_INBOX_BYTES, MAX_REPORT_BYTES, MAX_SUMMARY_BYTES, MAX_OUTPUT_MANIFEST_BYTES)))


def byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def input_identities(capsule: bytes, request_raw: bytes, local: LocalReference) -> list:
    record = local.record()
    inputs = [{"role": "untrusted_capsule", **byte_identity(capsule)},
              {"role": "reconciliation_request", **byte_identity(request_raw)}]
    for group in ("phase42", "phase43"):
        if record[group] is not None:
            inputs.extend(dict(item) for item in record[group]["inputs"])
    return inputs


def output_documents(report: dict, inbox: dict, inputs: list) -> dict[str, bytes]:
    """Canonical bytes of the four outputs; the manifest excludes itself."""
    report, inbox = validate_report(report), validate_inbox(inbox)
    payloads = {
        OUTPUT_PAYLOAD_NAMES[0]: json_bytes(inbox, maximum=MAX_INBOX_BYTES),
        OUTPUT_PAYLOAD_NAMES[1]: json_bytes(report, maximum=MAX_REPORT_BYTES),
        OUTPUT_PAYLOAD_NAMES[2]: render_reconciliation_summary(report, inbox),
    }
    manifest = validate_output_manifest({
        **common(OUTPUT_MANIFEST_SCHEMA), "request_reference": report["request_reference"],
        "capsule": dict(report["capsule"]), "eligibility_status": report["eligibility"]["status"],
        "files": [{"name": name, **byte_identity(raw)} for name, raw in payloads.items()],
        "inputs": inputs, "manifest_self_excluded": True, "integrity_scope": INTEGRITY_SCOPE,
    }, report["local_reference"]["mode"])
    documents = {**payloads, OUTPUT_NAMES[3]: json_bytes(manifest, maximum=MAX_OUTPUT_MANIFEST_BYTES)}
    for name, raw in documents.items():
        if not 0 < len(raw) <= OUTPUT_LIMITS[name]:
            fail("output_size")
    return documents


def _parent_info(output: Path, missing_code: str):
    """Owner path rules for the existing parent; a missing parent gets its own code."""
    from capsule_manifest import check_path

    try:
        return check_path(output.parent, directory=True)
    except FileNotFoundError:
        raise InputError(missing_code) from None


def _discard(stage: Path, stage_info, written: list) -> None:
    """Remove only files this run created in its own stage directory, then that directory.

    A file is removed only while the stage is still the directory this run
    created and the path is still the regular file this run wrote (same
    device and inode). Nothing else is deleted; rmdir refuses a non-empty
    directory. Cleanup errors never replace the original error.
    """
    from capsule_manifest import InputError as OwnerPublicationError, same_directory

    try:
        if stage_info is not None:
            same_directory(stage, stage_info)
        for path, identity in reversed(written):
            info = path.lstat()
            if stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) == identity:
                path.unlink()
        stage.rmdir()
    except (OSError, OwnerPublicationError):
        pass


def _publish_new(parent: Path, parent_info, documents: dict[str, bytes], output: Path, exists_code: str,
                 single_file: bool = False) -> None:
    """Stage every document beside ``output``, then publish with one rename; no hard links.

    The stage is a fresh ``tempfile.mkdtemp`` directory in the output's own
    parent, so the rename stays on one volume and is atomic there; on Windows
    a rename onto an existing target is refused. Each document is written
    with exclusive create, flushed and fsynced. Directory outputs rename the
    whole stage to ``output``; the single inspection file renames its staged
    file. On any failure only what this run wrote is removed and the error is
    raised again, so no empty or partial output blocks a retry.
    """
    from capsule_manifest import check_path, same_directory

    stage = Path(tempfile.mkdtemp(prefix=".task-reconciliation-", dir=parent))
    stage_info, written = None, []
    try:
        stage_info = check_path(stage, directory=True)
        for name, raw in documents.items():
            same_directory(stage, stage_info)
            with (stage / name).open("xb") as stream:
                opened = os.fstat(stream.fileno())
                written.append((stage / name, (opened.st_dev, opened.st_ino)))
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        same_directory(parent, parent_info)
        same_directory(stage, stage_info)
        if os.path.lexists(output):
            fail(exists_code)
        try:
            os.rename(written[0][0] if single_file else stage, output)
        except OSError:
            # A target that appeared after the check is reported when the
            # rename refuses it (Windows); cleanup never touches it. POSIX
            # rename may instead replace an empty directory or, for the
            # single inspection file, a file created in that short window.
            if os.path.lexists(output):
                fail(exists_code)
            raise
    except BaseException:
        _discard(stage, stage_info, written)
        raise
    if single_file:
        # The staged file was renamed away; only the empty stage directory remains.
        _discard(stage, stage_info, [])


def publish_outputs(raw_output_dir: str, documents: dict[str, bytes]) -> None:
    """Publish into a new directory: owner path rules, Phase44 stage-and-rename publisher."""
    from capsule_manifest import InputError as OwnerPublicationError, explicit_path

    if type(documents) is not dict or tuple(documents) != OUTPUT_NAMES:
        fail("output_inventory")
    try:
        output = explicit_path(raw_output_dir)
        parent = _parent_info(output, "task_reconciliation_output_parent_missing")
        if os.path.lexists(output):
            fail("output_directory_must_be_new")
        _publish_new(output.parent, parent, documents, output, "output_directory_must_be_new")
    except OwnerPublicationError:
        raise InputError("task_reconciliation_publication_path_or_state_rejected") from None


def publish_inspection(raw_output: str, report: dict) -> None:
    from capsule_manifest import InputError as OwnerPublicationError, explicit_path

    try:
        output = explicit_path(raw_output)
        if output.suffix.lower() != ".json":
            fail("inspection_json_required")
        parent = _parent_info(output, "task_reconciliation_inspection_output_parent_missing")
        if os.path.lexists(output):
            fail("inspection_output_must_be_new")
        _publish_new(output.parent, parent, {output.name: json_bytes(report, maximum=MAX_INSPECTION_BYTES)},
                     output, "inspection_output_must_be_new", single_file=True)
    except OwnerPublicationError:
        raise InputError("task_reconciliation_inspection_publication_rejected") from None


__all__ = ("OUTPUT_LIMITS", "byte_identity", "input_identities", "output_documents", "publish_inspection",
           "publish_outputs")
