"""Closed V1 device reports. Identity authenticates a sender, never its claims."""
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_SNAPSHOT_BYTES = 16 * 1024
MAX_SEQUENCE = 2**63 - 1
UTCText = Annotated[str, Field(min_length=20, max_length=32)]
VersionText = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._+\-]*$")]
Count = Annotated[int, Field(strict=True, ge=0, le=4096)]
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


ProductStatus = Annotated[HostBasedFirewallStatus | TermivarStatus | AntivirusStatus, Field(discriminator="product_id")]


class SnapshotEnvelope(StrictDTO):
    schema_version: Literal[1]
    message_id: Annotated[str, Field(min_length=36, max_length=36)]
    sequence: Annotated[int, Field(strict=True, ge=1, le=MAX_SEQUENCE)]
    source_observed_at: UTCText | None = None
    products: Annotated[list[ProductStatus], Field(max_length=3)]

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
        return utc_text(value) if value is not None else None

    @model_validator(mode="after")
    def unique_products(self):
        if len({product.product_id for product in self.products}) != len(self.products):
            raise ValueError("duplicate_product")
        return self


def canonical_json(snapshot: SnapshotEnvelope) -> bytes:
    encoded = json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_SNAPSHOT_BYTES:
        raise ValueError("snapshot_too_large")
    return encoded


def snapshot_digest(snapshot: SnapshotEnvelope) -> str:
    return hashlib.sha256(canonical_json(snapshot)).hexdigest()
