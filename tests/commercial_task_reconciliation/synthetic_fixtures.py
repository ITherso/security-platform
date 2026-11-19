"""Synthetic fixtures for Phase44 reconciliation tests.

Every identity built here is synthetic (SYNTH* candidates, digests of fixed
"synthetic-*" labels). Nothing represents a real security observation, and
no previous-phase artifact is modified: the optional integration test only
reads copies of existing outputs.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "commercial_task_reconciliation"
sys.path.insert(0, str(TOOL))
import reconciliation_paths  # noqa: E402

reconciliation_paths.install()

from exchange_contracts import (  # noqa: E402
    LIMITATIONS, PORTABLE_REQUEST_SCHEMA, build_response_contract, common, json_bytes,
)
from portable_capsule import (  # noqa: E402
    MEMBER_LIMITS, README_BYTES, REGULAR_FILE_ATTRIBUTES, ZIP_NAMES, build_task_exchange_capsule,
    capsule_manifest_data,
)
from local_task_records import make_local_reference  # noqa: E402
from reconciliation_contracts import REQUEST_SCHEMA  # noqa: E402

WORKSPACE_OUTPUTS = ROOT.parent / "outputs"


def sha(label: str) -> str:
    return hashlib.sha256(("synthetic-" + label).encode("ascii")).hexdigest()


def synthetic_task(task_id: str = "F0007", candidate: str = "SYNTH0001", label: str = "a") -> dict:
    return {"task_id": task_id, "reference_id": "rust-ref-" + sha("ref-" + label),
            "candidate_id": candidate, "file_id": "candidate-file-" + sha("file-" + label),
            "binding_digest": sha("binding-" + label), "slot_status": "awaiting_external_response",
            "response_status": "unsubmitted", "candidate_present": False, "observation_verified": False,
            "task_completed": False}


def synthetic_envelope(tasks: list | None = None, reference: str = "synthetic-fixture-request") -> dict:
    tasks = tasks if tasks is not None else [synthetic_task()]
    return {**common(PORTABLE_REQUEST_SCHEMA), "source_phase42_register_sha256": sha("register"),
            "source_phase42_manifest_sha256": sha("manifest"), "request_reference": reference,
            "tasks": tasks, "counts": counts_for(len(tasks)), "limitations": list(LIMITATIONS)}


def counts_for(task_count: int) -> dict:
    """The six Phase43 counters for a task count (owner exchange_counts for valid tasks)."""
    return {"selected_task_count": task_count, "unsubmitted_request_count": task_count,
            "response_field_definition_count": 7, "submitted_response_count": 0,
            "verified_observation_count": 0, "completed_task_count": 0}


def canonical_capsule(envelope: dict | None = None) -> bytes:
    return build_task_exchange_capsule(envelope or synthetic_envelope(), build_response_contract())


def canonical_members(envelope: dict | None = None) -> dict:
    envelope = envelope or synthetic_envelope()
    contract = build_response_contract()
    payloads = {"task-request.json": json_bytes(envelope, maximum=MEMBER_LIMITS["task-request.json"]),
                "response-contract.json": json_bytes(contract, maximum=MEMBER_LIMITS["response-contract.json"]),
                "README.txt": README_BYTES}
    manifest = capsule_manifest_data(envelope, contract, payloads)
    return {**payloads, "capsule-manifest.json": json_bytes(manifest, maximum=MEMBER_LIMITS["capsule-manifest.json"])}


def rehash_manifest(members: dict) -> dict:
    """Recompute only the files list of the inner manifest (keeps other fields)."""
    import json

    manifest = json.loads(members["capsule-manifest.json"])
    manifest["files"] = [{"name": name, "bytes": len(members[name]),
                          "sha256": hashlib.sha256(members[name]).hexdigest()} for name in ZIP_NAMES[:3]]
    return {**members, "capsule-manifest.json": json_bytes(manifest)}


def raw_zip(entries: list, compression: int = zipfile.ZIP_STORED, comment: bytes = b"",
            external_attr: int = REGULAR_FILE_ATTRIBUTES) -> bytes:
    """Write synthetic ZIP entries verbatim (duplicates and odd names allowed)."""
    import warnings

    buffer = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
            archive.comment = comment
            for name, body in entries:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = external_attr
                info.compress_type = compression
                archive.writestr(info, body)
    return buffer.getvalue()


def zip_members(members: dict, order: tuple = ZIP_NAMES) -> bytes:
    return raw_zip([(name, members[name]) for name in order])


def request(mode: str = "NO_LOCAL_RECORDS", p42: str | None = None, p43: str | None = None,
            reference: str = "synthetic-reconciliation") -> dict:
    return {"schema_version": REQUEST_SCHEMA, "mode": "demo", "request_reference": reference,
            "local_reference_mode": mode, "expected_local_phase42_register_sha256": p42,
            "expected_local_phase43_index_sha256": p43}


def _inputs(roles: tuple, first: str, last: str, middle_label: str) -> list:
    rows = []
    for index, role in enumerate(roles):
        digest = first if index == 0 else last if index == len(roles) - 1 else sha(middle_label + role)
        rows.append({"role": role, "bytes": 100 + index, "sha256": digest})
    return rows


def phase42_record(tasks: list | None = None) -> dict:
    from local_task_records import PHASE42_ROLES

    return {"register_sha256": sha("register"), "manifest_sha256": sha("manifest"),
            "tasks": tasks if tasks is not None else [synthetic_task()],
            "inputs": _inputs(PHASE42_ROLES, sha("register"), sha("manifest"), "p42-")}


def phase43_record(capsule: bytes, envelope: dict | None = None) -> dict:
    from local_task_records import PHASE43_ROLES
    from recipient_reader import inspect_task_exchange_capsule, read_portable_task_request

    envelope_read, _contract, members = read_portable_task_request(inspect_task_exchange_capsule(capsule))
    envelope = envelope or envelope_read
    capsule_sha = hashlib.sha256(capsule).hexdigest()
    inputs = _inputs(PHASE43_ROLES, capsule_sha, sha("p43-manifest"), "p43-")
    inputs[1]["sha256"] = sha("p43-index")
    return {"index_sha256": sha("p43-index"), "capsule_sha256": capsule_sha, "manifest_sha256": sha("p43-manifest"),
            "capsule_members": [{"name": m["name"], "bytes": m["bytes"], "sha256": m["sha256"]} for m in members],
            "source_phase42_register_sha256": envelope["source_phase42_register_sha256"],
            "source_phase42_manifest_sha256": envelope["source_phase42_manifest_sha256"],
            "request_reference": envelope["request_reference"],
            "task_ids": [t["task_id"] for t in envelope["tasks"]], "tasks": envelope["tasks"], "inputs": inputs}


def local(mode: str = "NO_LOCAL_RECORDS", p42: dict | None = None, p43: dict | None = None):
    return make_local_reference({"mode": mode, "phase42": p42, "phase43": p43})


def full_local(capsule: bytes, p42_tasks: list | None = None):
    p42, p43 = phase42_record(p42_tasks), phase43_record(capsule)
    mode = "PHASE42_TASK_RECORDS_AND_PHASE43_DISCLOSURE_RECORDS"
    return local(mode, p42, p43), request(mode, p42["register_sha256"], p43["index_sha256"])
