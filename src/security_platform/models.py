"""Tenant-scoped SQL constraints supplement authorization in the service layer."""
import uuid

from sqlalchemy import (CHAR, BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint,
                        Index, Integer, JSON, SmallInteger, String, Text, UniqueConstraint, Uuid, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from security_platform.db import Base


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (CheckConstraint("event_retention_days BETWEEN 1 AND 90", name="ck_tenant_event_retention"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    event_retention_days: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("30"))


class Principal(Base):
    __tablename__ = "principals"
    __table_args__ = (UniqueConstraint("issuer", "subject", name="uq_principal_identity"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    issuer: Mapped[str] = mapped_column(String(512), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (CheckConstraint("role IN ('tenant_admin','viewer')", name="ck_membership_role"),)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), primary_key=True)
    principal_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("principals.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class EnrollmentGrant(Base):
    __tablename__ = "enrollment_grants"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_grant_tenant_identity"),
        ForeignKeyConstraint(["tenant_id", "created_by"], ["memberships.tenant_id", "memberships.principal_id"],
                             name="fk_grant_creator_membership"),
        Index("ix_grant_tenant_created", "tenant_id", "created_at", "id"),
        CheckConstraint("expires_at > created_at", name="ck_grant_expiry"),
        CheckConstraint("length(token_digest) = 64", name="ck_grant_digest"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_device_tenant_identity"),
        CheckConstraint("last_sequence IS NULL OR last_sequence >= 1", name="ck_device_sequence"),
        CheckConstraint("(last_sequence IS NULL AND last_message_id IS NULL AND last_content_digest IS NULL AND last_received_at IS NULL) OR "
                        "(last_sequence IS NOT NULL AND last_message_id IS NOT NULL AND last_content_digest IS NOT NULL AND last_received_at IS NOT NULL)",
                        name="ck_device_snapshot_consistency"),
        Index("ix_device_tenant_created", "tenant_id", "created_at", "id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    last_sequence: Mapped[int | None] = mapped_column(BigInteger)
    last_message_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    last_content_digest: Mapped[str | None] = mapped_column(String(64))
    last_received_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    source_observed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class DeviceCredential(Base):
    __tablename__ = "device_credentials"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "device_id"], ["devices.tenant_id", "devices.id"], name="fk_credential_tenant_device"),
        Index("ix_credential_device", "tenant_id", "device_id"),
        CheckConstraint("expires_at > created_at", name="ck_credential_expiry"),
        CheckConstraint("length(token_digest) = 64", name="ck_credential_digest"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class ProductState(Base):
    __tablename__ = "product_states"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "device_id"], ["devices.tenant_id", "devices.id"], name="fk_product_tenant_device"),
        # contracts.PRODUCT_IDS; migration 0004 added 'edr_agent' (Snapshot V2).
        CheckConstraint("product_id IN ('hostbasedfirewall','termivar','antivirus','edr_agent')", name="ck_product_id"),
        CheckConstraint("snapshot_sequence >= 1", name="ck_product_sequence"),
        CheckConstraint("octet_length(payload::text) <= 16384", name="ck_product_payload_bytes"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    product_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    snapshot_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    received_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)


class DeviceEventCursor(Base):
    """Last accepted event batch of one device; serialised by the device row lock."""
    __tablename__ = "device_event_cursors"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "device_id"], ["devices.tenant_id", "devices.id"],
                             name="fk_event_cursor_tenant_device"),
        CheckConstraint("last_batch_sequence >= 1", name="ck_event_cursor_batch_sequence"),
        CheckConstraint("last_batch_digest ~ '^[0-9a-f]{64}$'", name="ck_event_cursor_digest"),
        CheckConstraint("last_event_seq >= 1", name="ck_event_cursor_event_seq"),
        CheckConstraint("stored_events >= 0", name="ck_event_cursor_stored_events"),
        CheckConstraint("cap_deleted_events >= 0", name="ck_event_cursor_cap_deleted_events"),
        CheckConstraint("suppressed_alerts >= 0", name="ck_event_cursor_suppressed_alerts"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    last_batch_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    last_batch_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    last_event_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_received_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    stored_events: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    # Rows the per-device cap deleted at ingestion, in total; retention prune leaves it alone.
    cap_deleted_events: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    # Alerts the per-device open-alert cap kept from opening, in total.
    suppressed_alerts: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))


class EndpointEvent(Base):
    """One self-reported event; observed_at is the device clock, received_at the server's."""
    __tablename__ = "endpoint_events"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "device_id"], ["devices.tenant_id", "devices.id"],
                             name="fk_endpoint_event_tenant_device"),
        CheckConstraint("event_seq >= 1", name="ck_endpoint_event_sequence"),
        CheckConstraint("kind IN ('process_started','process_stopped','sensor_state')", name="ck_endpoint_event_kind"),
        # The contract's observed_at window; every instant in it loads in any session time zone.
        CheckConstraint("observed_at >= '1970-01-01 00:00:00+00' AND observed_at < '9999-01-01 00:00:00+00'",
                        name="ck_endpoint_event_observed_at"),
        CheckConstraint("octet_length(payload::text) <= 4096", name="ck_endpoint_event_payload_bytes"),
        Index("ix_endpoint_events_tenant_received", "tenant_id", "received_at"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    event_seq: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)


class Alert(Base):
    """A server rule's match on a device's self-reported events; a rule match is not a diagnosis.

    While an alert is not closed, later matches of the same (rule, dedup_key)
    update it; the partial unique index below allows one such alert per key.
    """
    __tablename__ = "alerts"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "device_id"], ["devices.tenant_id", "devices.id"],
                             name="fk_alert_tenant_device"),
        ForeignKeyConstraint(["tenant_id", "acknowledged_by"], ["memberships.tenant_id", "memberships.principal_id"],
                             name="fk_alert_acknowledger_membership"),
        ForeignKeyConstraint(["tenant_id", "closed_by"], ["memberships.tenant_id", "memberships.principal_id"],
                             name="fk_alert_closer_membership"),
        CheckConstraint("rule IN ('user_writable_launch','office_browser_spawned_tool','sensor_unstable','event_loss')",
                        name="ck_alert_rule"),
        CheckConstraint("severity IN ('low','medium')", name="ck_alert_severity"),
        CheckConstraint("dedup_key ~ '^[0-9a-f]{64}$'", name="ck_alert_dedup_key"),
        CheckConstraint("status IN ('open','acknowledged','closed')", name="ck_alert_status"),
        CheckConstraint("occurrences >= 1", name="ck_alert_occurrences"),
        CheckConstraint("first_event_seq >= 1 AND last_event_seq >= first_event_seq", name="ck_alert_event_seq"),
        CheckConstraint("jsonb_typeof(evidence) = 'object'", name="ck_alert_evidence_object"),
        CheckConstraint("octet_length(evidence::text) <= 4096", name="ck_alert_evidence_bytes"),
        CheckConstraint("(acknowledged_at IS NULL) = (acknowledged_by IS NULL)", name="ck_alert_acknowledgement"),
        CheckConstraint("(closed_at IS NULL) = (closed_by IS NULL)", name="ck_alert_closure"),
        CheckConstraint("(status = 'open' AND acknowledged_at IS NULL AND closed_at IS NULL) OR "
                        "(status = 'acknowledged' AND acknowledged_at IS NOT NULL AND closed_at IS NULL) OR "
                        "(status = 'closed' AND closed_at IS NOT NULL)", name="ck_alert_lifecycle"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    rule: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    # Lowercase hex SHA-256 of the rule's key text.
    dedup_key: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    occurrences: Mapped[int] = mapped_column(BigInteger, nullable=False)
    first_event_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_event_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # The server's received_at of the first and the latest matching batch.
    first_seen_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    acknowledged_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    closed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("actor_type IN ('operator','device','local_admin')", name="ck_audit_actor"),
        CheckConstraint("outcome = 'success'", name="ck_audit_outcome"),
        Index("ix_audit_tenant_created", "tenant_id", "created_at", "id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="success")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)


Index("uq_credential_active_device", DeviceCredential.tenant_id, DeviceCredential.device_id,
      unique=True, postgresql_where=text("revoked_at IS NULL"))
# One alert that is not closed per (tenant, device, rule, key); the ingestion upsert's arbiter.
Index("uq_alert_not_closed_key", Alert.tenant_id, Alert.device_id, Alert.rule, Alert.dedup_key,
      unique=True, postgresql_where=text("status <> 'closed'"))
# The alert list: newest activity first, per tenant and per device.
Index("ix_alert_tenant_seen", Alert.tenant_id, Alert.last_seen_at.desc(), Alert.id.desc())
Index("ix_alert_device_seen", Alert.tenant_id, Alert.device_id, Alert.last_seen_at.desc(), Alert.id.desc())
