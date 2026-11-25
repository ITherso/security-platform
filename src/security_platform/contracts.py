"""Closed V1/V2 device reports. Identity authenticates a sender, never its claims."""
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_SNAPSHOT_BYTES = 16 * 1024
# Event batch_sequence, the timeline's before_seq and other users keep this bound.
MAX_SEQUENCE = 2**63 - 1
# The snapshot sequence of both schema versions: 2^53-1, the operator console's
# safe-integer limit (Number.MAX_SAFE_INTEGER). The console rejects a whole
# response holding a larger integer, and the device list carries last_sequence.
# This tightens V1 (once 2^63-1); no honest sender comes near either bound.
MAX_SNAPSHOT_SEQUENCE = 2**53 - 1
# A device time stored in a timestamptz column must satisfy
# MIN_OBSERVED_AT <= value < MAX_OBSERVED_AT: an event's observed_at (the same
# bound as the endpoint_events CHECK, event_contracts.py) and a snapshot
# envelope's source_observed_at (devices.source_observed_at; a tightening of V1
# like MAX_SNAPSHOT_SEQUENCE). PostgreSQL returns timestamptz in the session
# time zone and the driver cannot load a year after 9999 or before 1, so an
# accepted value near either end of the 4-digit range would make every load of
# the row holding it (a timeline page; a device list page, the device detail,
# the device's own requests, its revocation) fail in a non-UTC session. Every
# instant in this window loads in every zone. Times kept as text inside a JSONB
# payload (a product's source_observed_at, agent_started_at) load in any zone
# and are not bounded.
MIN_OBSERVED_AT = datetime(1970, 1, 1, tzinfo=timezone.utc)
MAX_OBSERVED_AT = datetime(9999, 1, 1, tzinfo=timezone.utc)
UTCText = Annotated[str, Field(min_length=20, max_length=32)]
VersionText = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._+\-]*$")]
# ASCII only: the character classes hold ASCII letters, digits and . _ + / space -.
EngineText = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._+/ -]*$")]
Count = Annotated[int, Field(strict=True, ge=0, le=4096)]
# A counter the console can read exactly; a sender saturates at the bound instead of overflowing it.
SafeCount = Annotated[int, Field(strict=True, ge=0, le=2**53 - 1)]
DigestText = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ErrorCode = Literal["config_error", "policy_error", "temp_error", "runtime_error", "telemetry_error",
    "history_error", "network_profile_error", "recovery_error", "application_rule_recovery_error",
    "liveness_error", "application_usage_error", "maintenance", "health_unavailable", "unknown_error"]
KNOWN_ERROR_CODES = frozenset(ErrorCode.__args__)


def canonical_uuid(value: str) -> str:
    if not isinstance(value, str) or len(value) != 36:
        raise ValueError("invalid_uuid")
    try:
        parsed = str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise ValueError("invalid_uuid") from exc
    if parsed != value:
        raise ValueError("invalid_uuid")
    return value


def utc_text(value: str) -> str:
    if (not isinstance(value, str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value)):
        raise ValueError("invalid_utc_timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_utc_timestamp") from exc
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class DispositionCounts(StrictDTO):
    informational: Count
    needs_review: Count
    confirmed: Count


class SeverityCounts(StrictDTO):
    unassigned: Count
    info: Count
    low: Count
    medium: Count
    high: Count
    critical: Count


class TermivarSummary(StrictDTO):
    digest: DigestText
    report_schema: Literal["venom-rendered-assessment/v1"]
    imported_at: UTCText
    subject_count: Annotated[int, Field(strict=True, ge=1, le=1024)]
    item_count: Count
    counts: DispositionCounts
    severity_counts: SeverityCounts
    source: Literal["self_reported"] = "self_reported"
    producer_verification: Literal["not_verified"] = "not_verified"
    scope: Literal["offline_report_summary"] = "offline_report_summary"

    @field_validator("imported_at")
    @classmethod
    def validate_time(cls, value):
        return utc_text(value)

    @model_validator(mode="after")
    def reconcile_counts(self):
        if (sum(self.counts.model_dump().values()) != self.item_count
                or sum(self.severity_counts.model_dump().values()) != self.item_count):
            raise ValueError("inconsistent_report_counts")
        return self


class ReportedProduct(StrictDTO):
    catalog_available: bool | None = None
    source: Literal["self_reported"] = "self_reported"
    producer_verification: Literal["not_verified"] = "not_verified"
    version: VersionText | None = None
    source_observed_at: UTCText | None = None

    @field_validator("source_observed_at")
    @classmethod
    def validate_observed_time(cls, value):
        return utc_text(value) if value is not None else None


class HostBasedFirewallStatus(ReportedProduct):
    product_id: Literal["hostbasedfirewall"]
    status: Literal["running", "observing", "degraded", "stopped", "unavailable", "unknown"] = "unknown"
    installed: bool | None = None
    reported_running: bool | None = None
    reported_stale: bool | None = None
    firewall_mode: Literal["enforce", "sniff", "unknown"] = "unknown"
    error_codes: Annotated[list[ErrorCode], Field(max_length=16)] | None = None

    @field_validator("error_codes")
    @classmethod
    def unique_errors(cls, value):
        if value is not None and len(set(value)) != len(value):
            raise ValueError("duplicate_error_code")
        return value


class TermivarStatus(ReportedProduct):
    product_id: Literal["termivar"]
    status: Literal["experimental", "unknown"] = "unknown"
    scanner_installed: bool | None = None
    execution_available: bool | None = None
    report_presence: Literal["present", "none", "unknown"] = "unknown"
    latest_report: TermivarSummary | None = None

    @model_validator(mode="after")
    def no_execution_claim(self):
        if self.execution_available is True:
            raise ValueError("execution_not_supported")
        if (self.report_presence == "present") != (self.latest_report is not None):
            raise ValueError("inconsistent_report_presence")
        return self


class AntivirusStatus(ReportedProduct):
    product_id: Literal["antivirus"]
    status: Literal["planned", "unknown"] = "unknown"
    availability: Literal["unavailable", "unknown"] = "unknown"
    execution_available: bool | None = None

    @model_validator(mode="after")
    def no_active_av_claim(self):
        if self.catalog_available is True or self.execution_available is True or self.version is not None:
            raise ValueError("antivirus_not_implemented")
        return self


EdrSensorState = Literal["started", "lost", "failed", "stopped", "disabled", "unknown"]
# The same six codes as event_contracts.SensorErrorCode (a unit test compares them).
EdrSensorErrorCode = Literal["session_name_invalid", "session_in_use", "access_denied", "session_start_failed",
                             "session_stop_failed", "unknown"]


class EdrAgentStatus(ReportedProduct):
    """The Altay EDR agent's own self-reported state (Snapshot V2); no claim of protection or loaded rules."""
    # status=running says only that the agent's service loop reported it. rule_file_present says only
    # that the rule file exists, never that rules are loaded. Counters count since the agent process
    # started. version is the agent version and source_observed_at the time the agent built this
    # status. No field claims protection, real-time protection or loaded rules; StrictDTO's
    # extra="forbid" keeps any such key out.
    product_id: Literal["edr_agent"]
    status: Literal["running", "unknown"] = "unknown"
    agent_started_at: UTCText | None = None
    engine_id: EngineText | None = None
    rule_file_present: bool | None = None
    sensor_state: EdrSensorState = "unknown"
    sensor_error_code: EdrSensorErrorCode | None = None
    events_queue_dropped: SafeCount | None = None
    events_write_failed: SafeCount | None = None
    events_unmapped: SafeCount | None = None
    events_skipped: SafeCount | None = None
    events_evicted: SafeCount | None = None
    events_discarded: SafeCount | None = None
    events_degraded: SafeCount | None = None
    outbox_backlog: SafeCount | None = None

    @field_validator("agent_started_at")
    @classmethod
    def validate_started_time(cls, value):
        return utc_text(value) if value is not None else None

    @model_validator(mode="after")
    def no_catalog_claim_and_code_only_when_unstable(self):
        if self.catalog_available is not None:
            raise ValueError("edr_agent_catalog_claim_not_supported")
        if self.sensor_error_code is not None and self.sensor_state not in ("lost", "failed"):
            raise ValueError("sensor_error_code_requires_lost_or_failed")
        return self


ProductStatus = Annotated[HostBasedFirewallStatus | TermivarStatus | AntivirusStatus | EdrAgentStatus,
                          Field(discriminator="product_id")]
# Every product a snapshot may carry; also the device detail's missing_products universe and
# the product_states.ck_product_id list (migration 0004).
PRODUCT_IDS = ("hostbasedfirewall", "termivar", "antivirus", "edr_agent")
# Products a schema_version 1 snapshot may carry: V1 is unchanged.
V1_PRODUCT_IDS = frozenset({"hostbasedfirewall", "termivar", "antivirus"})


class SnapshotEnvelope(StrictDTO):
    """V1 and V2 share one body. V2 only adds the edr_agent product; sequence and replay rules are common."""
    schema_version: Literal[1, 2]
    message_id: Annotated[str, Field(min_length=36, max_length=36)]
    sequence: Annotated[int, Field(strict=True, ge=1, le=MAX_SNAPSHOT_SEQUENCE)]
    source_observed_at: UTCText | None = None
    products: Annotated[list[ProductStatus], Field(max_length=len(PRODUCT_IDS))]

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_schema_version(cls, value):
        if type(value) is not int:
            raise ValueError("invalid_schema_version")
        return value

    @field_validator("message_id")
    @classmethod
    def validate_message_id(cls, value):
        return canonical_uuid(value)

    @field_validator("source_observed_at")
    @classmethod
    def validate_observed_time(cls, value):
        if value is None:
            return None
        normalized = utc_text(value)
        # Stored in devices.source_observed_at (timestamptz); see MIN_OBSERVED_AT. No real sender leaves the window.
        if not MIN_OBSERVED_AT <= datetime.fromisoformat(normalized.replace("Z", "+00:00")) < MAX_OBSERVED_AT:
            raise ValueError("source_observed_at_out_of_range")
        return normalized

    @model_validator(mode="after")
    def unique_products(self):
        if len({product.product_id for product in self.products}) != len(self.products):
            raise ValueError("duplicate_product")
        if self.schema_version == 1 and (len(self.products) > len(V1_PRODUCT_IDS)
                                         or any(product.product_id not in V1_PRODUCT_IDS for product in self.products)):
            raise ValueError("edr_agent_requires_schema_version_2")
        return self


def canonical_json(snapshot: SnapshotEnvelope) -> bytes:
    encoded = json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_SNAPSHOT_BYTES:
        raise ValueError("snapshot_too_large")
    return encoded


def snapshot_digest(snapshot: SnapshotEnvelope) -> str:
    return hashlib.sha256(canonical_json(snapshot)).hexdigest()
