"""Closed altay-edr-event/v1 and altay-edr-event/v2 batches.

A device credential authenticates the sender, never its claims: every event
stays self_reported and not_verified, and a batch carries no trust field.
v1 is unchanged: its models, canonical bytes, digests and error codes are the
ones of Stage 2. v2 (ADR 0004 section 1.2) is a separate batch class whose
events are discriminated by kind; a body chooses its version by its integer
schema_version, and a batch is homogeneous.
"""
from datetime import datetime
import hashlib
import json
import re
from typing import Annotated, Literal, Union

from pydantic import AfterValidator, Discriminator, Field, Tag, TypeAdapter, field_validator, model_validator

# observed_at must satisfy MIN_OBSERVED_AT <= value < MAX_OBSERVED_AT, the same
# bound as the endpoint_events CHECK. The window lives in contracts.py, which
# this module already imports, because the snapshot envelope's
# source_observed_at shares it; it is re-exported here for existing imports.
from security_platform.contracts import (MAX_OBSERVED_AT, MAX_SEQUENCE, MIN_OBSERVED_AT, Count, DigestText,
                                         StrictDTO, UTCText, bounded_utc_text, canonical_uuid, utc_text)


EVENT_SCHEMA = "altay-edr-event/v1"
MAX_EVENT_BATCH_BYTES = 16 * 1024
MAX_BATCH_EVENTS = 200
# Equals the endpoint_events payload CHECK, so a contract-valid event can
# always be stored instead of failing as a database error.
MAX_STORED_EVENT_BYTES = 4096
MAX_UINT32 = 2**32 - 1
UInt32 = Annotated[int, Field(strict=True, ge=0, le=MAX_UINT32)]
# The largest event_seq: 2^53-1, the operator console's safe-integer limit
# (Number.MAX_SAFE_INTEGER). The numbers the Platform derives from event_seq
# stay within it too: timeline event_seq and next_before_seq, alert
# first/last_event_seq, and event_loss missing_events, a sum of gaps between
# one device's strictly increasing accepted values (at most 2^53-3).
# batch_sequence keeps MAX_SEQUENCE; the snapshot sequence has its own
# MAX_SNAPSHOT_SEQUENCE (2^53-1, contracts.py) since Snapshot V2.
MAX_EVENT_SEQ = 2**53 - 1
EventSequence = Annotated[int, Field(strict=True, ge=1, le=MAX_EVENT_SEQ)]
SensorErrorCode = Literal["session_name_invalid", "session_in_use", "access_denied", "session_start_failed",
                          "session_stop_failed", "unknown"]
# Control and format characters (bidirectional overrides, zero-width marks):
# the Unicode 16.0.0 general categories Cc and Cf as inclusive code point
# ranges, generated once from unicodedata and frozen here. A Python whose
# Unicode database differs therefore cannot silently change which events are
# refused; tests/unit/test_event_contracts.py compares the table with the
# running interpreter's database and fails on any difference. Lone surrogates
# never reach this check: pydantic refuses them as strings.
REFUSED_TEXT_UNICODE_VERSION = "16.0.0"
REFUSED_TEXT_RANGES = (
    (0x0000, 0x001F), (0x007F, 0x009F), (0x00AD, 0x00AD), (0x0600, 0x0605), (0x061C, 0x061C), (0x06DD, 0x06DD),
    (0x070F, 0x070F), (0x0890, 0x0891), (0x08E2, 0x08E2), (0x180E, 0x180E), (0x200B, 0x200F), (0x202A, 0x202E),
    (0x2060, 0x2064), (0x2066, 0x206F), (0xFEFF, 0xFEFF), (0xFFF9, 0xFFFB), (0x110BD, 0x110BD),
    (0x110CD, 0x110CD), (0x13430, 0x1343F), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A), (0xE0001, 0xE0001),
    (0xE0020, 0xE007F),
)
_REFUSED_TEXT = re.compile("[" + "".join(f"\\U{first:08x}-\\U{last:08x}" for first, last in REFUSED_TEXT_RANGES)
                           + "]")


def _plain_text(value):
    if _REFUSED_TEXT.search(value):
        raise ValueError("invalid_image_text")
    return value


def masked_image_path(value):
    """Require ``*`` as the name of the component after every ``Users`` component.

    Components are split on ``\\`` and ``/`` (Win32 accepts both), so a
    forward-slash path cannot carry an unmasked profile folder. A component is
    ``Users`` only as a whole, matched ASCII case-insensitively; ``Users:x``
    names a stream, which has no children. For every ``Users`` component that
    is not the last one, the next component's part before its first ``:`` must
    be exactly ``*``; from that ``:`` on the component is kept, so an NTFS
    stream on a profile folder stays visible as ``*:payload.exe``. A file
    directly under ``Users`` is masked to ``*`` too: the rule cannot tell it
    from a profile folder. A path ending in ``Users`` has nothing to mask, and
    a bare name such as ``Registry`` has no ``Users`` component.
    """
    _plain_text(value)
    components = value.replace("/", "\\").split("\\")
    for index, component in enumerate(components[:-1]):
        if (component.isascii() and component.lower() == "users"
                and components[index + 1].partition(":")[0] != "*"):
            raise ValueError("unmasked_user_folder")
    return value


def short_image_name(value):
    """The kernel's short image name, as the agent sends it.

    The kernel name keeps only the low byte of each UTF-16 unit of the file
    name, so it can contain ``\\`` or ``/``. The agent replaces each of them
    with U+FFFD before sending and sends null when the result is empty. The
    separator ban stays: it stops a full, unmasked path from being carried in
    this field.
    """
    _plain_text(value)
    if "\\" in value or "/" in value:
        raise ValueError("invalid_short_image")
    return value


def _encoded(value, separators):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=separators,
                      allow_nan=False).encode("utf-8")


def stored_event_bytes(event):
    """Byte length of PostgreSQL's jsonb text for the stored event payload.

    jsonb renders objects with ", " and ": " separators and escapes only what
    JSON requires; the contract forbids control characters, so the only
    escapes are quote and backslash, exactly as json.dumps writes them.
    """
    return len(_encoded(event.model_dump(mode="json"), (", ", ": ")))


class _Event(StrictDTO):
    event_seq: EventSequence
    observed_at: UTCText

    @field_validator("observed_at")
    @classmethod
    def validate_observed_time(cls, value):
        normalized = utc_text(value)
        if not MIN_OBSERVED_AT <= datetime.fromisoformat(normalized.replace("Z", "+00:00")) < MAX_OBSERVED_AT:
            raise ValueError("observed_at_out_of_range")
        return normalized

    @model_validator(mode="after")
    def bounded_stored_form(self):
        if stored_event_bytes(self) > MAX_STORED_EVENT_BYTES:
            raise ValueError("event_too_large")
        return self


class ProcessStarted(_Event):
    kind: Literal["process_started"]
    pid: UInt32
    parent_pid: UInt32
    session_id: UInt32
    image: Annotated[str, Field(min_length=1, max_length=1024)]

    @field_validator("image")
    @classmethod
    def validate_image(cls, value):
        return masked_image_path(value)


class ProcessStopped(_Event):
    kind: Literal["process_stopped"]
    pid: UInt32
    exit_code: UInt32 | None = None
    image: Annotated[str, Field(min_length=1, max_length=260)] | None = None

    @field_validator("image")
    @classmethod
    def validate_image(cls, value):
        return short_image_name(value) if value is not None else None


class SensorState(_Event):
    kind: Literal["sensor_state"]
    state: Literal["started", "lost", "failed", "stopped"]
    error_code: SensorErrorCode | None = None

    @model_validator(mode="after")
    def error_only_for_failures(self):
        if self.state in {"started", "stopped"} and self.error_code is not None:
            raise ValueError("unexpected_error_code")
        return self


DeviceEvent = Annotated[ProcessStarted | ProcessStopped | SensorState, Field(discriminator="kind")]
EVENT_MODELS = {"process_started": ProcessStarted, "process_stopped": ProcessStopped, "sensor_state": SensorState}
COMMON_EVENT_FIELDS = ("kind", "event_seq", "observed_at")
# The v1 fields of each v1 kind, in declaration order. EVENT_FIELDS (below the
# v2 models) is the per-kind superset over v1 and v2 that the timeline shows.
EVENT_FIELDS_V1 = {kind: tuple(name for name in model.model_fields if name not in COMMON_EVENT_FIELDS)
                   for kind, model in EVENT_MODELS.items()}


class EventBatch(StrictDTO):
    schema_version: Literal[1]
    batch_id: Annotated[str, Field(min_length=36, max_length=36)]
    batch_sequence: Annotated[int, Field(strict=True, ge=1, le=MAX_SEQUENCE)]
    events: Annotated[list[DeviceEvent], Field(min_length=1, max_length=MAX_BATCH_EVENTS)]

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_schema_version(cls, value):
        if type(value) is not int:
            raise ValueError("invalid_schema_version")
        return value

    @field_validator("batch_id")
    @classmethod
    def validate_batch_id(cls, value):
        return canonical_uuid(value)

    @model_validator(mode="after")
    def increasing_event_sequence(self):
        if any(left.event_seq >= right.event_seq for left, right in zip(self.events, self.events[1:])):
            raise ValueError("event_seq_not_increasing")
        return self


class EventBatchTooLarge(ValueError):
    """The canonical form of a schema-valid batch exceeds MAX_EVENT_BATCH_BYTES."""


def canonical_event_batch(batch: "EventBatch | EventBatchV2") -> bytes:
    """Sorted keys, compact separators, raw UTF-8, explicit nulls; one rule for v1 and v2 (v1 bytes unchanged)."""
    encoded = _encoded(batch.model_dump(mode="json"), (",", ":"))
    if len(encoded) > MAX_EVENT_BATCH_BYTES:
        raise EventBatchTooLarge("event_batch_too_large")
    return encoded


def event_batch_digest(batch: "EventBatch | EventBatchV2") -> str:
    return hashlib.sha256(canonical_event_batch(batch)).hexdigest()


# --- altay-edr-event/v2 (ADR 0004 section 1.2) -------------------------------------------------------------
#
# Every closed set below is the single source: the endpoint_events kind CHECK (migration 0005, which hardcodes
# its copy and is compared with EVENT_KINDS by a parity test) and the operator console mirror it. A v2 event
# never carries a command line, a user name, a SID, file content or free text; sha256 and size exist only in
# scan_detected, and StrictDTO's extra="forbid" refuses any other key.

EVENT_SCHEMA_V2 = "altay-edr-event/v2"
EVENT_KINDS_V1 = ("process_started", "process_stopped", "sensor_state")
EVENT_KINDS = EVENT_KINDS_V1 + ("scan_detected", "behavior_match", "persistence_change", "agent_state",
                                "tamper_signal", "coverage_gap")
SCAN_TRIGGERS = ("process_start", "startup_scan", "file_change", "remote_scan", "persistence_target")
SCAN_HIT_SEVERITIES = ("low", "medium", "high")
MAX_SCAN_HITS = 8
BEHAVIOR_RULES = ("encoded_powershell", "powershell_download_cradle", "certutil_download_or_decode",
                  "mshta_remote_or_script", "regsvr32_scriptlet", "rundll32_script", "bitsadmin_transfer",
                  "shadow_copy_deletion", "defender_tampering_command", "event_log_clearing_command")
COMMAND_LINE_SOURCES = ("kernel_logger", "process_query")
PERSISTENCE_LOCATIONS = ("run_key", "run_once_key", "service", "scheduled_task", "startup_folder")
PERSISTENCE_SCOPES = ("machine", "user")
PERSISTENCE_CHANGES = ("added", "modified", "removed")
# Each subject with the states it may report, in this order.
AGENT_STATE_SUBJECTS = {
    "service": ("started", "stopping"),
    "rule_set": ("compiled", "missing", "invalid", "unreadable"),
    "realtime_scan": ("running", "degraded", "stopped", "failed"),
    "file_change_sensor": ("running", "degraded", "stopped", "failed", "not_available"),
    "command_line_sensor": ("running", "degraded", "stopped", "failed", "not_available"),
    "persistence_watch": ("running", "degraded", "stopped", "failed", "not_available", "baseline_created"),
    "response_channel": ("ready", "not_configured", "awaiting_tenant_binding", "journal_invalid"),
    "isolation": ("active", "renewed", "released", "expired", "released_locally", "reverted_no_contact",
                  "reapplied"),
    "quarantine": ("restored_locally",),
}
# Every state of any subject, in first-seen order; the (subject, state) pair is checked separately.
AGENT_STATES = tuple(dict.fromkeys(state for states in AGENT_STATE_SUBJECTS.values() for state in states))
AGENT_STATE_CODES = ("first_start", "clean_stop", "unclean_stop")
TAMPER_SIGNALS = ("service_config_changed", "service_dacl_changed", "data_dir_acl_changed",
                  "isolation_filters_missing", "isolation_filters_disabled", "isolation_released_locally",
                  "event_log_cleared", "response_trust_changed", "previous_run_unclean", "quarantine_changed")
TAMPER_DETAILS = ("security", "system")
COVERAGE_SOURCES = ("process_sensor", "file_change_sensor", "command_line_sensor", "agent_records")
COVERAGE_REASONS = ("etw_events_lost", "usn_journal_reset", "usn_entries_deleted", "volume_unmonitored",
                    "queue_overflow")
# 0..2^53-1: the operator console's safe-integer range (like MAX_EVENT_SEQ).
SafeUInt = Annotated[int, Field(strict=True, ge=0, le=MAX_EVENT_SEQ)]
# The v1 path rules, as Annotated types so that every path field of every v2 kind uses them.
MaskedPath = Annotated[str, Field(min_length=1, max_length=1024), AfterValidator(masked_image_path)]
ShortImageName = Annotated[str, Field(min_length=1, max_length=260), AfterValidator(short_image_name)]
UUIDText = Annotated[str, Field(min_length=36, max_length=36), AfterValidator(canonical_uuid)]
HitRule = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")]
StrictBool = Annotated[bool, Field(strict=True)]


class _EventV2(_Event):
    """The v2 time rule: create_time and parent_create_time follow observed_at's (canonical UTC text, 1970-9999)."""

    @field_validator("create_time", "parent_create_time", check_fields=False)
    @classmethod
    def validate_process_time(cls, value, info):
        return bounded_utc_text(value, f"{info.field_name}_out_of_range") if value is not None else None


class ProcessStartedV2(_EventV2):
    """v1's process_started plus the payload's CreateTime (required) and the parent's, when the agent knows it."""
    kind: Literal["process_started"]
    pid: UInt32
    parent_pid: UInt32
    session_id: UInt32
    image: MaskedPath
    create_time: UTCText
    parent_create_time: UTCText | None = None


class ProcessStoppedV2(_EventV2):
    kind: Literal["process_stopped"]
    pid: UInt32
    exit_code: UInt32 | None = None
    image: ShortImageName | None = None
    create_time: UTCText | None = None


class ScanHit(StrictDTO):
    """One matching rule: its name and severity only, never its description or strings."""
    rule: HitRule
    severity: Literal[SCAN_HIT_SEVERITIES]


class ScanDetected(_EventV2):
    """A file the agent's scanner matched; size and sha256 are carried in this kind only (ADR 1.4)."""
    kind: Literal["scan_detected"]
    trigger: Literal[SCAN_TRIGGERS]
    path: MaskedPath
    size: SafeUInt
    sha256: DigestText
    rule_set_id: DigestText
    hits: Annotated[list[ScanHit], Field(min_length=1, max_length=MAX_SCAN_HITS)]
    omitted_hits: Count
    pid: UInt32 | None = None
    create_time: UTCText | None = None
    action_id: UUIDText | None = None

    @model_validator(mode="after")
    def unique_hits_and_process_identity(self):
        if len({hit.rule for hit in self.hits}) != len(self.hits):
            raise ValueError("duplicate_hit_rule")
        if self.create_time is not None and self.pid is None:
            raise ValueError("create_time_requires_pid")
        return self


class BehaviorMatch(_EventV2):
    """A behavior rule the agent evaluated in memory; the event carries the rule id, never the command line."""
    kind: Literal["behavior_match"]
    rule: Literal[BEHAVIOR_RULES]
    rule_version: Annotated[int, Field(strict=True, ge=1, le=65535)]
    pid: UInt32
    create_time: UTCText
    image: MaskedPath
    parent_image: MaskedPath | None = None
    found_at_start: StrictBool
    command_line_source: Literal[COMMAND_LINE_SOURCES]


class PersistenceChange(_EventV2):
    """A change of a persistence entry, named by its salted entry_id; never a value name, command text or SID."""
    kind: Literal["persistence_change"]
    location: Literal[PERSISTENCE_LOCATIONS]
    scope: Literal[PERSISTENCE_SCOPES]
    change: Literal[PERSISTENCE_CHANGES]
    entry_id: DigestText
    target_image: MaskedPath | None = None
    found_at_start: StrictBool


class AgentState(_EventV2):
    kind: Literal["agent_state"]
    subject: Literal[tuple(AGENT_STATE_SUBJECTS)]
    state: Literal[AGENT_STATES]
    code: Literal[AGENT_STATE_CODES] | None = None
    rule_set_id: DigestText | None = None

    @model_validator(mode="after")
    def state_of_subject(self):
        if self.state not in AGENT_STATE_SUBJECTS[self.subject]:
            raise ValueError("state_not_allowed_for_subject")
        if self.code is not None and (self.subject, self.state) != ("service", "started"):
            raise ValueError("code_requires_service_started")
        if self.rule_set_id is not None and self.subject != "rule_set":
            raise ValueError("rule_set_id_requires_rule_set")
        return self


class TamperSignal(_EventV2):
    """Tamper evidence the agent reports about itself; a signal is not proof and nothing was prevented."""
    kind: Literal["tamper_signal"]
    signal: Literal[TAMPER_SIGNALS]
    detail: Literal[TAMPER_DETAILS] | None = None

    @model_validator(mode="after")
    def detail_only_for_event_log_cleared(self):
        if self.signal == "event_log_cleared" and self.detail is None:
            raise ValueError("detail_required_for_event_log_cleared")
        if self.signal != "event_log_cleared" and self.detail is not None:
            raise ValueError("detail_only_for_event_log_cleared")
        return self


class CoverageGap(_EventV2):
    kind: Literal["coverage_gap"]
    source: Literal[COVERAGE_SOURCES]
    reason: Literal[COVERAGE_REASONS]
    lost: SafeUInt | None = None


# sensor_state is unchanged in v2: the v2 union reuses the v1 model itself.
DeviceEventV2 = Annotated[ProcessStartedV2 | ProcessStoppedV2 | SensorState | ScanDetected | BehaviorMatch
                          | PersistenceChange | AgentState | TamperSignal | CoverageGap, Field(discriminator="kind")]
EVENT_MODELS_V2 = {"process_started": ProcessStartedV2, "process_stopped": ProcessStoppedV2,
                   "sensor_state": SensorState, "scan_detected": ScanDetected, "behavior_match": BehaviorMatch,
                   "persistence_change": PersistenceChange, "agent_state": AgentState, "tamper_signal": TamperSignal,
                   "coverage_gap": CoverageGap}
# The timeline's per-kind fields: the v1 fields first, then the fields that exist only in v2. A v1 row shows
# null for the latter. The console mirrors this table.
EVENT_FIELDS = {kind: tuple(dict.fromkeys(EVENT_FIELDS_V1.get(kind, ()) + tuple(
    name for name in EVENT_MODELS_V2[kind].model_fields if name not in COMMON_EVENT_FIELDS))) for kind in EVENT_KINDS}
# The timeline view's name of each EVENT_FIELDS entry, position by position (services/events._event_view; the
# console mirrors it). Equal to EVENT_FIELDS except in coverage_gap: the view item also carries the trust label
# `source`, so the gap's own `source` (the part of the agent that lost records) is shown as `gap_source`. The wire
# field and the stored payload keep `source` (ADR 0004 section 1.2).
EVENT_VIEW_FIELDS = {kind: tuple("gap_source" if (kind, name) == ("coverage_gap", "source") else name
                                 for name in fields) for kind, fields in EVENT_FIELDS.items()}


class EventBatchV2(StrictDTO):
    """The v2 batch: the v1 envelope rules (batch_id, batch_sequence, 1-200 events, increasing event_seq, the
    16 KiB canonical and 4 KiB stored-event bounds) with the nine v2 kinds."""
    schema_version: Literal[2]
    batch_id: Annotated[str, Field(min_length=36, max_length=36)]
    batch_sequence: Annotated[int, Field(strict=True, ge=1, le=MAX_SEQUENCE)]
    events: Annotated[list[DeviceEventV2], Field(min_length=1, max_length=MAX_BATCH_EVENTS)]

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_schema_version(cls, value):
        if type(value) is not int:
            raise ValueError("invalid_schema_version")
        return value

    @field_validator("batch_id")
    @classmethod
    def validate_batch_id(cls, value):
        return canonical_uuid(value)

    @model_validator(mode="after")
    def increasing_event_sequence(self):
        if any(left.event_seq >= right.event_seq for left, right in zip(self.events, self.events[1:])):
            raise ValueError("event_seq_not_increasing")
        return self


EVENT_BATCH_MODELS = {1: EventBatch, 2: EventBatchV2}


def _batch_tag(value):
    """The batch class a body names by its schema_version; only an int (never a bool) of a known version."""
    version = value.get("schema_version") if isinstance(value, dict) else getattr(value, "schema_version", None)
    model = EVENT_BATCH_MODELS.get(version) if type(version) is int else None
    return model.__name__ if model is not None else None


# The device event route's body: a v1 or a v2 batch, chosen by schema_version. A non-int, bool or unknown
# version fails as invalid_schema_version, before any event is looked at.
DeviceEventBatch = Annotated[Union[Annotated[EventBatch, Tag("EventBatch")], Annotated[EventBatchV2, Tag("EventBatchV2")]],
                             Discriminator(_batch_tag, custom_error_type="invalid_schema_version",
                                           custom_error_message="invalid_schema_version")]
_DEVICE_EVENT_BATCH = TypeAdapter(DeviceEventBatch)


def parse_event_batch(value) -> "EventBatch | EventBatchV2":
    """Validate a body as the batch version it names; a schema_version 1 body validates exactly as EventBatch."""
    return _DEVICE_EVENT_BATCH.validate_python(value)
