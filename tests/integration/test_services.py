"""Real PostgreSQL service transactions; HTTP/JWT acceptance is tested separately."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import threading
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from security_platform.auth.principals import OperatorPrincipal
from security_platform.contracts import SnapshotEnvelope
from security_platform.db import Database
from security_platform.models import AuditEvent, Device, DeviceCredential, EnrollmentGrant, Membership, ProductState
from security_platform.services import administration, audit, enrollment, inventory, snapshots
from security_platform.services.common import DEFAULT_LIMITS, CapacityError, Conflict, Forbidden, NotFound, Unauthorized


pytestmark = pytest.mark.integration
NOW = datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.fixture(scope="session")
def pg_service_databases():
    migration = os.environ.get("SP_MIGRATION_DATABASE_URL")
    runtime = os.environ.get("SP_DATABASE_URL")
    config_path = Path(__file__).resolve().parents[3] / ".tooling" / "platform-test-env.json"
    if (not migration or not runtime) and config_path.exists():
        saved = json.loads(config_path.read_text(encoding="utf-8"))
        if saved.get("ready") is False:
            pytest.skip("Local PostgreSQL fixture is still being prepared")
        migration, runtime = saved["migration_url"], saved["runtime_url"]
    if not migration or not runtime:
        pytest.skip("Real PostgreSQL service DSNs are not configured")
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", migration.replace("%", "%%"))
    command.upgrade(config, "head")
    owner, app = Database(migration), Database(runtime)
    yield owner, app
    owner.close()
    app.close()


@pytest.fixture
def service_tenants(pg_service_databases):
    owner, runtime = pg_service_databases
    issuer = "https://service-fixture.example"
    admin = OperatorPrincipal(issuer=issuer, subject=str(uuid4()))
    viewer = OperatorPrincipal(issuer=issuer, subject=str(uuid4()))
    with owner.session() as session:
        a = UUID(administration.create_tenant(session, "Service A", now=NOW)["id"])
        b = UUID(administration.create_tenant(session, "Service B", now=NOW)["id"])
        administration.set_membership(session, a, issuer, admin.subject, "tenant_admin", now=NOW)
        administration.set_membership(session, a, issuer, viewer.subject, "viewer", now=NOW)
        administration.set_membership(session, b, issuer, admin.subject, "viewer", now=NOW)
    return owner, runtime, a, b, admin, viewer


def grant(runtime, admin, tenant, *, limits=DEFAULT_LIMITS, now=NOW):
    with runtime.session() as session:
        return enrollment.create_grant(session, admin, tenant, limits=limits, now=now)


def enrolled(runtime, admin, tenant, *, limits=DEFAULT_LIMITS, now=NOW):
    created = grant(runtime, admin, tenant, limits=limits, now=now)
    with runtime.session() as session:
        principal = enrollment.authenticate_grant(session, created["enrollment_token"], now=now)
        return enrollment.enroll_device(session, principal, label="Fixture device", limits=limits, now=now)


def snapshot(sequence=1, *, message_id=None, products=None, source_observed_at=None):
    return SnapshotEnvelope.model_validate({"schema_version": 1, "message_id": message_id or str(uuid4()),
        "sequence": sequence, "source_observed_at": source_observed_at,
        "products": products if products is not None else [{"product_id": "hostbasedfirewall",
            "status": "running", "firewall_mode": "enforce", "reported_running": True}]})


def send(runtime, secret, message, *, now=NOW):
    with runtime.session() as session:
        principal = enrollment.authenticate_device(session, secret, now=now)
        return snapshots.ingest_snapshot(session, principal, message, now=now)


def test_fresh_memberships_scope_roles_and_revocation(service_tenants):
    owner, runtime, a, b, admin, viewer = service_tenants
    with runtime.session() as session:
        assert {row["id"] for row in inventory.list_tenants(session, admin)["items"]} == {str(a), str(b)}
        with pytest.raises(Forbidden):
            enrollment.create_grant(session, admin, b, now=NOW)
    with runtime.session() as session:
        with pytest.raises(Forbidden):
            enrollment.create_grant(session, viewer, a, now=NOW)
    with runtime.session() as session:
        with pytest.raises(NotFound):
            inventory.list_devices(session, viewer, b)
    with owner.session() as session:
        administration.revoke_membership(session, a, admin.issuer, admin.subject, now=NOW)
    with runtime.session() as session:
        with pytest.raises(NotFound):
            inventory.list_devices(session, admin, a)


def test_enrollment_consumes_once_and_no_plaintext_in_database(service_tenants):
    owner, runtime, a, _, admin, _ = service_tenants
    created = grant(runtime, admin, a)
    with runtime.session() as session:
        principal = enrollment.authenticate_grant(session, created["enrollment_token"], now=NOW)
        device = enrollment.enroll_device(session, principal, label="Fixture", now=NOW)
    with runtime.session() as session:
        with pytest.raises(Unauthorized):
            enrollment.authenticate_grant(session, created["enrollment_token"], now=NOW)
    with owner.session() as session:
        saved = session.scalar(select(EnrollmentGrant).where(EnrollmentGrant.id == UUID(created["grant_id"])))
        credential = session.scalar(select(DeviceCredential).where(DeviceCredential.device_id == UUID(device["device_id"])))
        assert len(saved.token_digest) == len(credential.token_digest) == 64
        assert created["enrollment_token"] not in repr(vars(saved))
        assert device["credential_secret"] not in repr(vars(credential))
    with runtime.session() as session:
        detail = inventory.get_device(session, admin, a, UUID(device["device_id"]), now=NOW)
        assert detail["connection_status"] == "never_seen"
        assert detail["products"] == []


def test_concurrent_enrollment_creates_exactly_one_device(service_tenants):
    owner, runtime, a, _, admin, _ = service_tenants
    created = grant(runtime, admin, a)
    barrier = threading.Barrier(2)

    def attempt():
        try:
            with runtime.session() as session:
                principal = enrollment.authenticate_grant(session, created["enrollment_token"], now=NOW)
                barrier.wait(timeout=5)
                return enrollment.enroll_device(session, principal, label="Parallel fixture", now=NOW)
        except Unauthorized:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(result is not None for result in results) == 1
    with owner.session() as session:
        assert session.scalar(select(func.count()).select_from(Device).where(Device.tenant_id == a)) == 1
        assert session.scalar(select(func.count()).select_from(DeviceCredential).where(DeviceCredential.tenant_id == a)) == 1


def test_failed_enrollment_audit_rolls_back_device_credential_and_consumption(service_tenants, monkeypatch):
    owner, runtime, a, _, admin, _ = service_tenants
    created = grant(runtime, admin, a)
    def fail(*args, **kwargs):
        raise RuntimeError("Injected audit failure")
    monkeypatch.setattr(enrollment, "write_event", fail)
    with pytest.raises(RuntimeError):
        with runtime.session() as session:
            principal = enrollment.authenticate_grant(session, created["enrollment_token"], now=NOW)
            enrollment.enroll_device(session, principal, label="Must rollback", now=NOW)
    with owner.session() as session:
        assert session.scalar(select(func.count()).select_from(Device).where(Device.tenant_id == a)) == 0
        assert session.scalar(select(func.count()).select_from(DeviceCredential).where(DeviceCredential.tenant_id == a)) == 0
        assert session.scalar(select(EnrollmentGrant).where(EnrollmentGrant.id == UUID(created["grant_id"]))).consumed_at is None


def test_concurrent_rotation_old_credential_has_one_success(service_tenants):
    owner, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    barrier = threading.Barrier(2)
    def attempt():
        try:
            with runtime.session() as session:
                principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
                barrier.wait(timeout=5)
                return enrollment.rotate_credential(session, principal, now=NOW + timedelta(seconds=1))
        except Unauthorized:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(result is not None for result in results) == 1
    with runtime.session() as session:
        with pytest.raises(Unauthorized):
            enrollment.authenticate_device(session, device["credential_secret"], now=NOW + timedelta(seconds=1))
    with owner.session() as session:
        assert session.scalar(select(func.count()).select_from(DeviceCredential).where(
            DeviceCredential.tenant_id == a, DeviceCredential.revoked_at.is_(None))) == 1


def test_snapshot_exact_retry_does_not_refresh_time_or_increment_counts(service_tenants):
    _, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    message = snapshot()
    first = send(runtime, device["credential_secret"], message)
    retry = send(runtime, device["credential_secret"], message, now=NOW + timedelta(seconds=10))
    assert retry == first
    with runtime.session() as session:
        detail = inventory.get_device(session, admin, a, UUID(device["device_id"]), now=NOW + timedelta(seconds=400))
        assert detail["connection_status"] == "stale"
        assert detail["last_received_at"] == first["received_at"]
        assert len(detail["products"]) == 1


def test_conflicts_stale_order_and_omitted_products_are_atomic(service_tenants):
    _, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    initial = snapshot(5)
    send(runtime, device["credential_secret"], initial)
    for rejected in (snapshot(4), snapshot(5), snapshot(6, message_id=initial.message_id),
                     snapshot(5, message_id=initial.message_id, products=[])):
        with pytest.raises(Conflict):
            send(runtime, device["credential_secret"], rejected)
    send(runtime, device["credential_secret"], snapshot(6, products=[]), now=NOW + timedelta(seconds=1))
    with runtime.session() as session:
        detail = inventory.get_device(session, admin, a, UUID(device["device_id"]), now=NOW)
        assert detail["last_sequence"] == 6 and detail["products"] == []
        assert detail["missing_products"] == ["antivirus", "hostbasedfirewall", "termivar"]


def test_sequence_survives_rotation_and_source_future_never_controls_freshness(service_tenants):
    _, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    message = snapshot(20, source_observed_at="2099-01-01T00:00:00Z")
    send(runtime, device["credential_secret"], message)
    with runtime.session() as session:
        principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
        rotated = enrollment.rotate_credential(session, principal, now=NOW)
    with pytest.raises(Conflict):
        send(runtime, rotated["credential_secret"], snapshot(1))
    assert send(runtime, rotated["credential_secret"], message, now=NOW + timedelta(seconds=1))["sequence"] == 20
    with runtime.session() as session:
        detail = inventory.get_device(session, admin, a, UUID(device["device_id"]), now=NOW + timedelta(seconds=400))
        assert detail["connection_status"] == "stale"
        assert detail["source_observation"] == {"age_seconds": None, "clock_state": "future"}


def test_revocation_is_rechecked_after_authentication_in_snapshot_transaction(service_tenants):
    _, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    with runtime.session() as session:
        principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
    with runtime.session() as session:
        enrollment.revoke_device(session, admin, a, UUID(device["device_id"]), now=NOW)
    with runtime.session() as session:
        with pytest.raises(Unauthorized):
            snapshots.ingest_snapshot(session, principal, snapshot(), now=NOW)


def test_credential_expiry_is_not_extended_by_snapshot(service_tenants):
    owner, runtime, a, _, admin, _ = service_tenants
    limits = replace(DEFAULT_LIMITS, credential_ttl_seconds=60)
    device = enrolled(runtime, admin, a, limits=limits)
    send(runtime, device["credential_secret"], snapshot(), now=NOW + timedelta(seconds=59))
    with owner.session() as session:
        credential = session.scalar(select(DeviceCredential).where(DeviceCredential.id == UUID(device["credential_id"])))
        assert credential.expires_at == NOW + timedelta(seconds=60)
    with pytest.raises(Unauthorized):
        send(runtime, device["credential_secret"], snapshot(2), now=NOW + timedelta(seconds=60))


@pytest.mark.parametrize("kind", ["credential", "product"])
def test_composite_tenant_device_foreign_key_rejects_cross_company_rows(service_tenants, kind):
    owner, runtime, a, b, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    with pytest.raises(IntegrityError):
        with owner.session() as session:
            if kind == "credential":
                session.add(DeviceCredential(tenant_id=b, device_id=UUID(device["device_id"]), token_digest="a" * 64,
                    created_at=NOW, expires_at=NOW + timedelta(days=1)))
            else:
                session.add(ProductState(tenant_id=b, device_id=UUID(device["device_id"]), product_id="antivirus",
                    snapshot_sequence=1, received_at=NOW, payload={}))


def test_audit_retention_is_tenant_scoped_and_does_not_block_revocation(service_tenants):
    owner, runtime, a, b, admin, _ = service_tenants
    limits = replace(DEFAULT_LIMITS, max_audits=5)
    device = enrolled(runtime, admin, a, limits=limits)
    with owner.session() as session:
        other_before = session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.tenant_id == b))
    for _ in range(7):
        grant(runtime, admin, a, limits=limits)
    with runtime.session() as session:
        enrollment.revoke_device(session, admin, a, UUID(device["device_id"]), limits=limits, now=NOW)
        listing = audit.list_audit(session, admin, a, limit=5, limits=limits)
        assert len(listing["items"]) == 5
        assert any(event["action"] == "device_revoked" for event in listing["items"])
        assert "credential_secret" not in json.dumps(listing)
    with owner.session() as session:
        assert session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.tenant_id == b)) == other_before


def test_bounded_grants_devices_and_credential_history(service_tenants):
    owner, runtime, a, _, admin, _ = service_tenants
    limits = replace(DEFAULT_LIMITS, max_devices=1, max_active_grants=1, max_grant_records=2, max_credential_records=2)
    created = grant(runtime, admin, a, limits=limits)
    with pytest.raises(CapacityError):
        grant(runtime, admin, a, limits=limits)
    with runtime.session() as session:
        principal = enrollment.authenticate_grant(session, created["enrollment_token"], now=NOW)
        device = enrollment.enroll_device(session, principal, label="Bounded", limits=limits, now=NOW)
    for index in range(4):
        with runtime.session() as session:
            principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
            device = enrollment.rotate_credential(session, principal, limits=limits, now=NOW + timedelta(seconds=index))
    with owner.session() as session:
        assert session.scalar(select(func.count()).select_from(DeviceCredential).where(DeviceCredential.tenant_id == a)) == 2
    second = grant(runtime, admin, a, limits=limits)
    with pytest.raises(CapacityError):
        with runtime.session() as session:
            principal = enrollment.authenticate_grant(session, second["enrollment_token"], now=NOW)
            enrollment.enroll_device(session, principal, label="Over cap", limits=limits, now=NOW)
    with runtime.session() as session:
        enrollment.revoke_grant(session, admin, a, UUID(second["grant_id"]), limits=limits, now=NOW)
    for _ in range(5):
        current = grant(runtime, admin, a, limits=limits)
        with runtime.session() as session:
            enrollment.revoke_grant(session, admin, a, UUID(current["grant_id"]), limits=limits, now=NOW)
    with owner.session() as session:
        assert session.scalar(select(func.count()).select_from(EnrollmentGrant).where(EnrollmentGrant.tenant_id == a)) <= 2


def test_expired_revoked_and_wrong_purpose_credentials_are_rejected(service_tenants):
    _, runtime, a, _, admin, _ = service_tenants
    created = grant(runtime, admin, a)
    with runtime.session() as session:
        enrollment.revoke_grant(session, admin, a, UUID(created["grant_id"]), now=NOW)
    with runtime.session() as session:
        with pytest.raises(Unauthorized):
            enrollment.authenticate_grant(session, created["enrollment_token"], now=NOW)
    expired = grant(runtime, admin, a)
    with runtime.session() as session:
        with pytest.raises(Unauthorized):
            enrollment.authenticate_grant(session, expired["enrollment_token"], now=NOW + timedelta(seconds=601))
    device = enrolled(runtime, admin, a)
    for token, authenticate in ((device["credential_secret"], enrollment.authenticate_grant),
                                (expired["enrollment_token"], enrollment.authenticate_device)):
        with runtime.session() as session:
            with pytest.raises(Unauthorized):
                authenticate(session, token, now=NOW)


def test_parallel_snapshot_sequence_serializes_to_latest_whole_state(service_tenants):
    _, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    barrier = threading.Barrier(2)
    def attempt(sequence):
        try:
            with runtime.session() as session:
                principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
                message = snapshot(sequence, products=[{"product_id": "antivirus", "status": "planned", "availability": "unavailable"}]
                                   if sequence == 2 else [])
                barrier.wait(timeout=5)
                return snapshots.ingest_snapshot(session, principal, message, now=NOW)
        except Conflict:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [1, 2]))
    assert any(result is not None and result["sequence"] == 2 for result in results)
    with runtime.session() as session:
        detail = inventory.get_device(session, admin, a, UUID(device["device_id"]), now=NOW)
        assert detail["last_sequence"] == 2
        assert len(detail["products"]) == 1 and detail["products"][0]["product_id"] == "antivirus"
        assert detail["products"][0]["snapshot_sequence"] == 2


def test_rotation_audit_failure_rolls_back_revocation_and_new_credential(service_tenants, monkeypatch):
    owner, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    def fail(*args, **kwargs):
        raise RuntimeError("Injected rotation audit failure")
    monkeypatch.setattr(enrollment, "write_event", fail)
    with pytest.raises(RuntimeError):
        with runtime.session() as session:
            principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
            enrollment.rotate_credential(session, principal, now=NOW)
    with runtime.session() as session:
        assert enrollment.authenticate_device(session, device["credential_secret"], now=NOW).device_id == UUID(device["device_id"])
    with owner.session() as session:
        assert session.scalar(select(func.count()).select_from(DeviceCredential).where(DeviceCredential.tenant_id == a)) == 1
