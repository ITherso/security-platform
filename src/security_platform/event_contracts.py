"""Closed altay-edr-event/v1 batches.

A device credential authenticates the sender, never its claims: every event
stays self_reported and not_verified, and a batch carries no trust field.
"""
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from security_platform.contracts import MAX_SEQUENCE, StrictDTO, UTCText, canonical_uuid, utc_text


EVENT_SCHEMA = "altay-edr-event/v1"
MAX_EVENT_BATCH_BYTES = 16 * 1024
MAX_BATCH_EVENTS = 200
# Equals the endpoint_events payload CHECK, so a contract-valid event can
# always be stored instead of failing as a database error.
MAX_STORED_EVENT_BYTES = 4096
# observed_at must satisfy MIN_OBSERVED_AT <= value < MAX_OBSERVED_AT, the
# same bound as the endpoint_events CHECK. PostgreSQL returns timestamptz in
# the session time zone and the driver cannot load a year after 9999 or before
# 1, so an accepted value near either end of the 4-digit range would make
# every timeline page holding it fail in a non-UTC session. Every instant in
# this window loads in every zone.
MIN_OBSERVED_AT = datetime(1970, 1, 1, tzinfo=timezone.utc)
MAX_OBSERVED_AT = datetime(9999, 1, 1, tzinfo=timezone.utc)
MAX_UINT32 = 2**32 - 1
UInt32 = Annotated[int, Field(strict=True, ge=0, le=MAX_UINT32)]
EventSequence = Annotated[int, Field(strict=True, ge=1, le=MAX_SEQUENCE)]
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
EVENT_FIELDS = {kind: tuple(name for name in model.model_fields if name not in COMMON_EVENT_FIELDS)
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


def canonical_event_batch(batch: EventBatch) -> bytes:
    encoded = _encoded(batch.model_dump(mode="json"), (",", ":"))
    if len(encoded) > MAX_EVENT_BATCH_BYTES:
        raise EventBatchTooLarge("event_batch_too_large")
    return encoded


def event_batch_digest(batch: EventBatch) -> str:
    return hashlib.sha256(canonical_event_batch(batch)).hexdigest()
