"""Source-bound Phase42 snapshot and narrow stable binary input extension."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import os
import stat

from phase41_adapter import InputBudget as OwnerInputBudget
from intake_contracts import (
    COMMON_FIELDS as SOURCE_COMMON_FIELDS,
    FALSE_FLAGS as SOURCE_FALSE_FLAGS,
    MANIFEST_SCHEMA as OLD_MANIFEST_SCHEMA,
    common as source_common,
    parse_json as source_parse_json,
    json_bytes as source_json_bytes,
    validate_relationships as source_validate_relationships,
    classification_from_intake as source_classification_from_intake,
)
from commercial_deferred_intake.output_renderer import render_intake_summary
from commercial_deferred_intake.artifact_manifest import manifest_data as source_manifest_data
from capsule_contracts import InputError as CapsuleInputError
from commercial_composition.composition_contracts import InputError as CompositionInputError
from commercial_handoff.schema import InputError as HandoffInputError
from commercial_handoff.input_loader import check_existing_path, explicit_relative_path
from commercial_composition.source_inventory import _identity, _same_api_identity

from exchange_contracts import (
    FALSE_FLAGS, InputError, MAX_CAPSULE_BYTES, MAX_TOTAL_INPUT_BYTES,
    SOURCE_NAMES, SOURCE_LIMITS, SOURCE_SCHEMAS, closed, fixed, validate_source_artifacts,
)


_OWNER_ERRORS = tuple(dict.fromkeys((CapsuleInputError, CompositionInputError, HandoffInputError)))
_OWNER_TEXT_ERRORS = (*_OWNER_ERRORS, UnicodeError)
_MANIFEST_FIELDS = (*SOURCE_COMMON_FIELDS, "files", "source_phase41_slots_sha256",
                    "source_phase41_manifest_sha256", "source_artifacts", "source_schema_versions",
                    "source_counts", "intake_register_sha256", "intake_counts", "classification_counts",
                    "request", "manifest_self_excluded", "integrity_scope")


class InputBudget(OwnerInputBudget):
    """Keep the owner text accounting and add only bounded stable ZIP bytes.

    This producer-side class is not imported by the standalone recipient.
    Known legacy contract/path errors cross one explicit exception boundary.
    """

    __slots__ = ()

    def __init__(self, maximum: int = MAX_TOTAL_INPUT_BYTES):
        try:
            super().__init__(maximum=maximum)
        except _OWNER_ERRORS:
            raise InputError("task_exchange_input_budget_rejected") from None

    def read_text(self, raw_path: str, maximum: int) -> bytes:
        try:
            return super().read_text(raw_path, maximum)
        except _OWNER_TEXT_ERRORS:
            raise InputError("task_exchange_text_input_rejected") from None

    def read_binary(self, raw_path: str, maximum: int = MAX_CAPSULE_BYTES) -> bytes:
        """Read one explicit regular single-link file without UTF-8 decoding."""
        if type(maximum) is not int or not 0 < maximum <= MAX_CAPSULE_BYTES:
            raise InputError("task_exchange_binary_input_limit_rejected")
        try:
            remaining = self.maximum - self.consumed
            if remaining <= 1:
                raise InputError("task_exchange_total_input_budget_exceeded")
            limit = min(maximum, remaining - 1)
            # On failure the reservation is retained, matching the owner.
            reservation = self._reserve(limit + 1)
            path = explicit_relative_path(raw_path)
            checked = check_existing_path(path, directory=False)
            if not 0 < checked.st_size <= limit or checked.st_nlink != 1:
                raise InputError("task_exchange_binary_size_or_hardlink_rejected")
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags)
            with os.fdopen(descriptor, "rb") as stream:
                opened = os.fstat(stream.fileno())
                # lstat/fstat ctime meanings differ on Windows. Only the
                # existing cross-API identity excludes ctime here.
                if (not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(checked)
                        or getattr(opened, "st_file_attributes", 0)
                        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
                    raise InputError("task_exchange_binary_identity_rejected")
                raw = stream.read(limit + 1)
                after_open = os.fstat(stream.fileno())
            after_path = check_existing_path(path, directory=False)
            if (len(raw) != checked.st_size or len(raw) > limit
                    or _same_api_identity(after_open) != _same_api_identity(opened)
                    or _same_api_identity(after_path) != _same_api_identity(checked)):
                raise InputError("task_exchange_binary_changed_during_read")
            self._finish(reservation, len(raw))
            self._remember(path, _same_api_identity(checked))
            return raw
        except _OWNER_ERRORS:
            raise InputError("task_exchange_binary_input_rejected") from None

    def check_stability(self) -> None:
        try:
            super().check_stability()
        except _OWNER_ERRORS:
            raise InputError("task_exchange_input_changed_before_publication") from None


def _source_models(artifact_bytes: tuple) -> tuple[dict, dict, dict, list]:
    if type(artifact_bytes) is not tuple or len(artifact_bytes) != len(SOURCE_NAMES):
        raise InputError("task_exchange_exact_five_immutable_Phase42_sources_required")
    raw = dict(zip(SOURCE_NAMES, artifact_bytes))
    for name, body in raw.items():
        if type(body) is not bytes or not 0 < len(body) <= SOURCE_LIMITS[name]:
            raise InputError("task_exchange_source_byte_type_or_limit_rejected")
    fixed(list(FALSE_FLAGS), list(SOURCE_FALSE_FLAGS), "source_trust_flag_names")
    artifacts = validate_source_artifacts([
        {"name": name, "bytes": len(raw[name]), "sha256": hashlib.sha256(raw[name]).hexdigest(),
         "schema_version": SOURCE_SCHEMAS[name]}
        for name in SOURCE_NAMES
    ])
    manifest = source_parse_json(raw["manifest.json"], maximum=SOURCE_LIMITS["manifest.json"])
    closed(manifest, _MANIFEST_FIELDS, "source_Phase42_manifest_fields")
    fixed({key: manifest[key] for key in SOURCE_COMMON_FIELDS},
          source_common(OLD_MANIFEST_SCHEMA), "source_Phase42_manifest_common")
    fixed(manifest["files"], [{"name": item["name"], "bytes": item["bytes"], "sha256": item["sha256"]}
                               for item in artifacts[:-1]], "actual_Phase42_payload_bytes")
    intake, classification, receipt = source_validate_relationships(
        source_parse_json(raw["deferred-intake-register.json"], maximum=SOURCE_LIMITS["deferred-intake-register.json"]),
        source_parse_json(raw["intake-classification.json"], maximum=SOURCE_LIMITS["intake-classification.json"]),
        source_parse_json(raw["intake-source-receipt.json"], maximum=SOURCE_LIMITS["intake-source-receipt.json"]),
    )
    fixed(classification, source_classification_from_intake(intake), "original_intake_classification_correspondence")
    if raw["deferred-intake-register.json"] != source_json_bytes(intake, maximum=SOURCE_LIMITS["deferred-intake-register.json"]):
        raise InputError("task_exchange_source_register_must_be_canonical")
    if raw["intake-summary.md"] != render_intake_summary(intake, classification, receipt):
        raise InputError("task_exchange_source_summary_correspondence_rejected")
    payloads = {name: raw[name] for name in SOURCE_NAMES[:-1]}
    if (source_json_bytes(manifest, maximum=SOURCE_LIMITS["manifest.json"])
            != source_json_bytes(source_manifest_data(intake, classification, receipt, payloads), maximum=SOURCE_LIMITS["manifest.json"])):
        raise InputError("task_exchange_source_full_manifest_correspondence_rejected")
    # Source Phase42 validates recorded metadata correspondence. Its inherited
    # binding remains opaque; no original Phase40 preimage is reconstructed.
    return intake, classification, receipt, artifacts


def _validated_source(artifact_bytes: tuple) -> tuple[dict, dict, dict, list]:
    try:
        return _source_models(artifact_bytes)
    except _OWNER_TEXT_ERRORS:
        raise InputError("task_exchange_Phase42_owner_contract_rejected") from None


@dataclass(frozen=True, slots=True, repr=False)
class ValidatedPhase42Source:
    """Exact five immutable source bytes, not a producer validation marker."""

    artifact_bytes: tuple[bytes, bytes, bytes, bytes, bytes] = field(repr=False)

    def __post_init__(self) -> None:
        _validated_source(self.artifact_bytes)


def read_source(snapshot: ValidatedPhase42Source) -> tuple[dict, dict, dict, list]:
    if type(snapshot) is not ValidatedPhase42Source:
        raise InputError("task_exchange_exact_validated_Phase42_source_required")
    intake, classification, receipt, artifacts = _validated_source(snapshot.artifact_bytes)
    return deepcopy(intake), deepcopy(classification), deepcopy(receipt), deepcopy(artifacts)


def load_source(register_path: str, classification_path: str, receipt_path: str,
                summary_path: str, manifest_path: str, budget: InputBudget) -> ValidatedPhase42Source:
    """Only five explicit bounded stable reads; later readers stay in memory."""
    if type(budget) is not InputBudget:
        raise InputError("task_exchange_exact_input_budget_required")
    paths = (register_path, classification_path, receipt_path, summary_path, manifest_path)
    raw = tuple(budget.read_text(path, SOURCE_LIMITS[name]) for name, path in zip(SOURCE_NAMES, paths))
    budget.check_stability()
    return ValidatedPhase42Source(raw)


__all__ = ("InputBudget", "ValidatedPhase42Source", "load_source", "read_source")
