"""Closed V1/V2/V3 device reports. Identity authenticates a sender, never its claims.

Snapshot V1 and V2 share SnapshotEnvelope and are unchanged. Snapshot V3 (ADR 0004 section 1.3) is a separate
envelope class: canonical JSON includes defaults, so adding fields to the V2 models would change the V1 and V2
digests.
"""
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import (BaseModel, ConfigDict, Discriminator, Field, Tag, TypeAdapter, field_validator,
                      model_validator)


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


def bounded_utc_text(value: str, error: str) -> str:
    """utc_text inside MIN_OBSERVED_AT <= t < MAX_OBSERVED_AT (the bound applies to the normalized instant).

    The rule of an event's observed_at and of the envelope's source_observed_at, written once for the Stage 3
    times (v2 create_time and parent_create_time, the V3 envelope and isolation times); the V1/V2 and v1 checks
    keep their own unchanged code.
    """
    normalized = utc_text(value)
    if not MIN_OBSERVED_AT <= datetime.fromisoformat(normalized.replace("Z", "+00:00")) < MAX_OBSERVED_AT:
        raise ValueError(error)
    return normalized


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


# --- Snapshot V3 (ADR 0004 section 1.3) --------------------------------------------------------------------
#
# Every agent-reported value stays self_reported/not_verified. A state says what the agent's own loop reported
# about one of its parts, never that the device is protected: no field name claims protection, loaded rules or
# real-time protection, and StrictDTO's extra="forbid" refuses any such key.

# The V2 counters, in EdrAgentStatus's order, then the eight V3 counters. Each saturates at 2^53-1 (SafeCount).
EDR_V2_COUNTER_KEYS = ("events_queue_dropped", "events_write_failed", "events_unmapped", "events_skipped",
                       "events_evicted", "events_discarded", "events_degraded", "outbox_backlog")
EDR_V3_COUNTER_KEYS = EDR_V2_COUNTER_KEYS + ("scans_completed", "scans_detected", "scans_no_verdict",
                                             "scan_jobs_dropped", "scan_cache_hits", "etw_events_lost",
                                             "file_change_gaps", "cmdline_unavailable")
RULE_SET_STATES = ("compiled", "missing", "invalid", "unreadable", "unknown")
CAPABILITY_STATES = ("running", "degraded", "stopped", "failed", "not_available", "unknown")
RESPONSE_CHANNEL_STATES = ("ready", "not_configured", "awaiting_tenant_binding", "journal_invalid", "unknown")
RESPONSE_ACTIONS = ("scan_path", "terminate_process", "quarantine_file", "restore_file", "isolate_host",
                    "release_host")
MAX_RESPONSE_KEY_IDS = 4
ISOLATION_STATES = ("inactive", "active", "partial", "unknown")
SERVICE_CONFIG_STATES = ("as_installed", "changed", "unknown")
PREVIOUS_RUN_ENDS = ("clean", "unclean", "first_start", "unknown")
# The agent's own accepted range for its heartbeat interval.
MIN_HEARTBEAT_INTERVAL_SECONDS, MAX_HEARTBEAT_INTERVAL_SECONDS = 30, 3600
BEHAVIOR_RULES_VERSION_PATTERN = r"^altay-behavior/v[1-9][0-9]{0,5}$"
CapabilityState = Literal[CAPABILITY_STATES]


def _unique_sorted(value, error):
    if list(value) != sorted(set(value)):
        raise ValueError(error)
    return value


class EdrAgentStatusV3(ReportedProduct):
    """The Altay EDR agent's own self-reported state (Snapshot V3): every V2 field except rule_file_present,
    plus the Stage 3 states and counters.

    rule_set_state=compiled says only that this agent process compiled a rule set (rule_set_id names it),
    never that the device is protected. A capability state says what that part of the agent reported about
    itself. The scanner scans after start and does not block. Counters count since the agent process started.
    """
    product_id: Literal["edr_agent"]
    status: Literal["running", "unknown"] = "unknown"
    agent_started_at: UTCText | None = None
    engine_id: EngineText | None = None
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
    rule_set_state: Literal[RULE_SET_STATES] = "unknown"
    rule_set_id: DigestText | None = None
    realtime_scan_state: CapabilityState = "unknown"
    file_change_sensor_state: CapabilityState = "unknown"
    command_line_sensor_state: CapabilityState = "unknown"
    persistence_watch_state: CapabilityState = "unknown"
    scans_completed: SafeCount | None = None
    scans_detected: SafeCount | None = None
    scans_no_verdict: SafeCount | None = None
    scan_jobs_dropped: SafeCount | None = None
    scan_cache_hits: SafeCount | None = None
    etw_events_lost: SafeCount | None = None
    file_change_gaps: SafeCount | None = None
    cmdline_unavailable: SafeCount | None = None
    response_channel_state: Literal[RESPONSE_CHANNEL_STATES] = "unknown"
    response_actions_enabled: Annotated[list[Literal[RESPONSE_ACTIONS]],
                                        Field(max_length=len(RESPONSE_ACTIONS))] = Field(default_factory=list)
    response_key_ids: Annotated[list[DigestText], Field(max_length=MAX_RESPONSE_KEY_IDS)] = Field(
        default_factory=list)
    last_action_seq: SafeCount | None = None
    isolation_state: Literal[ISOLATION_STATES] = "unknown"
    isolation_until: UTCText | None = None
    isolation_checked_at: UTCText | None = None
    quarantine_items: SafeCount | None = None
    service_config_state: Literal[SERVICE_CONFIG_STATES] = "unknown"
    previous_run_end: Literal[PREVIOUS_RUN_ENDS] = "unknown"
    heartbeat_interval_seconds: Annotated[int, Field(strict=True, ge=MIN_HEARTBEAT_INTERVAL_SECONDS,
                                                     le=MAX_HEARTBEAT_INTERVAL_SECONDS)] | None = None
    behavior_rules_version: Annotated[str, Field(pattern=BEHAVIOR_RULES_VERSION_PATTERN)] | None = None

    @field_validator("agent_started_at")
    @classmethod
    def validate_started_time(cls, value):
        return utc_text(value) if value is not None else None

    @field_validator("isolation_until", "isolation_checked_at")
    @classmethod
    def validate_isolation_time(cls, value, info):
        return bounded_utc_text(value, f"{info.field_name}_out_of_range") if value is not None else None

    @field_validator("response_actions_enabled")
    @classmethod
    def unique_sorted_actions(cls, value):
        return _unique_sorted(value, "response_actions_not_unique_and_sorted")

    @field_validator("response_key_ids")
    @classmethod
    def unique_sorted_keys(cls, value):
        return _unique_sorted(value, "response_key_ids_not_unique_and_sorted")

    @model_validator(mode="after")
    def no_catalog_claim_and_code_only_when_unstable(self):
        if self.catalog_available is not None:
            raise ValueError("edr_agent_catalog_claim_not_supported")
        if self.sensor_error_code is not None and self.sensor_state not in ("lost", "failed"):
            raise ValueError("sensor_error_code_requires_lost_or_failed")
        return self


ProductStatusV3 = Annotated[HostBasedFirewallStatus | TermivarStatus | AntivirusStatus | EdrAgentStatusV3,
                            Field(discriminator="product_id")]


class SnapshotEnvelopeV3(StrictDTO):
    """Snapshot V3: the V1/V2 envelope rules (message_id, sequence, source_observed_at window, unique products)
    with the V3 edr_agent product. It is a whole state, like V1 and V2: omitted products are replaced."""
    schema_version: Literal[3]
    message_id: Annotated[str, Field(min_length=36, max_length=36)]
    sequence: Annotated[int, Field(strict=True, ge=1, le=MAX_SNAPSHOT_SEQUENCE)]
    source_observed_at: UTCText | None = None
    products: Annotated[list[ProductStatusV3], Field(max_length=len(PRODUCT_IDS))]

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
        return bounded_utc_text(value, "source_observed_at_out_of_range") if value is not None else None

    @model_validator(mode="after")
    def unique_products(self):
        if len({product.product_id for product in self.products}) != len(self.products):
            raise ValueError("duplicate_product")
        return self


def canonical_json(snapshot: "SnapshotEnvelope | SnapshotEnvelopeV3") -> bytes:
    encoded = json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_SNAPSHOT_BYTES:
        raise ValueError("snapshot_too_large")
    return encoded


def snapshot_digest(snapshot: "SnapshotEnvelope | SnapshotEnvelopeV3") -> str:
    return hashlib.sha256(canonical_json(snapshot)).hexdigest()


SNAPSHOT_MODELS = {1: SnapshotEnvelope, 2: SnapshotEnvelope, 3: SnapshotEnvelopeV3}


def _snapshot_tag(value):
    """The envelope class a body names by its schema_version; only an int (never a bool) of a known version."""
    version = value.get("schema_version") if isinstance(value, dict) else getattr(value, "schema_version", None)
    model = SNAPSHOT_MODELS.get(version) if type(version) is int else None
    return model.__name__ if model is not None else None


# The device snapshot route's body: V1/V2 (one class) or V3, chosen by schema_version. A non-int, bool or
# unknown version fails as invalid_schema_version.
DeviceSnapshot = Annotated[Union[Annotated[SnapshotEnvelope, Tag("SnapshotEnvelope")],
                                 Annotated[SnapshotEnvelopeV3, Tag("SnapshotEnvelopeV3")]],
                           Discriminator(_snapshot_tag, custom_error_type="invalid_schema_version",
                                         custom_error_message="invalid_schema_version")]
_DEVICE_SNAPSHOT = TypeAdapter(DeviceSnapshot)


def parse_snapshot(value) -> "SnapshotEnvelope | SnapshotEnvelopeV3":
    """Validate a body as the envelope version it names; a V1 or V2 body validates exactly as SnapshotEnvelope."""
    return _DEVICE_SNAPSHOT.validate_python(value)
