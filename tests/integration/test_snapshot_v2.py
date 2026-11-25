"""Snapshot V2 on real PostgreSQL: migration 0004, the edr_agent product in the device detail, the
replay and sequence rules across V1 and V2, and the envelope's source_observed_at window. HTTP acceptance runs
through the real app and signed JWTs.

The pure contract is tested in tests/unit/test_snapshot_v2_contracts.py.
"""
import json
import re
from uuid import UUID, uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from security_platform.contracts import MAX_SNAPSHOT_SEQUENCE, PRODUCT_IDS, SnapshotEnvelope
from security_platform.models import ProductState
from security_platform.services import enrollment, inventory, snapshots
from security_platform.services.common import Conflict, ServiceError
from test_api import api_context, api_database, auth, enroll  # noqa: F401  (shared HTTP fixtures)
from test_events import migration_module
from test_services import NOW, enrolled, pg_service_databases, service_tenants  # noqa: F401  (shared DB fixtures)


pytestmark = pytest.mark.integration
COUNTERS = ("events_queue_dropped", "events_write_failed", "events_unmapped", "events_skipped", "events_evicted",
            "events_discarded", "events_degraded", "outbox_backlog")
V1_PRODUCTS = ("hostbasedfirewall", "termivar", "antivirus")


def agent_status(**changes):
    status = {"product_id": "edr_agent", "status": "running", "version": "0.3.0",
              "source_observed_at": "2030-01-02T03:00:00Z", "agent_started_at": "2030-01-02T01:00:00Z",
              "engine_id": "edr-agent/0.3.0", "rule_file_present": False, "sensor_state": "disabled",
              **{name: 0 for name in COUNTERS}}
    status.update(changes)
    return status


def v1_products():
    return [{"product_id": "hostbasedfirewall", "status": "running", "firewall_mode": "enforce"},
            {"product_id": "termivar", "status": "experimental", "report_presence": "none"},
            {"product_id": "antivirus", "status": "planned", "availability": "unavailable"}]


def body(sequence, *, schema_version=2, products=None, message_id=None, **changes):
    return {"schema_version": schema_version, "message_id": message_id or str(uuid4()), "sequence": sequence,
            "source_observed_at": "2030-01-02T03:00:00Z",
            "products": [agent_status()] if products is None else products, **changes}


def send(runtime, secret, message, *, now=NOW):
    with runtime.session() as session:
        principal = enrollment.authenticate_device(session, secret, now=now)
        return snapshots.ingest_snapshot(session, principal, message, now=now)


def detail(runtime, operator, tenant, device, *, now=NOW):
    with runtime.session() as session:
        return inventory.get_device(session, operator, tenant, UUID(device["device_id"]), now=now)


def product_check(connection):
    """The product names of the live ck_product_id, in order."""
    definition = connection.scalar(text(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_product_id' "
        "AND conrelid = 'public.product_states'::regclass"))
    return tuple(re.findall(r"'(\w+)'", definition))


# --- migration 0004

def test_migrated_database_is_at_0004_with_the_widened_product_check(pg_service_databases):
    owner, _ = pg_service_databases
    with owner.engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0004_edr_agent_product"
        assert product_check(connection) == PRODUCT_IDS


def test_migration_0004_downgrades_and_upgrades_in_a_rolled_back_transaction(service_tenants):
    owner, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    module = migration_module("0004_edr_agent_product")
    assert (module.revision, module.down_revision) == ("0004_edr_agent_product", "0003_alerts")
    send(runtime, device["credential_secret"], body(1, products=v1_products() + [agent_status()]))
    device_id = UUID(device["device_id"])

    def stored(connection):
        return sorted(connection.scalars(text("SELECT product_id FROM product_states WHERE device_id = :device"),
                                         {"device": device_id}).all())

    def insert_agent(connection):
        connection.execute(text(
            "INSERT INTO product_states (tenant_id, device_id, product_id, snapshot_sequence, received_at, payload) "
            "VALUES (:tenant, :device, 'edr_agent', 1, :at, CAST('{}' AS jsonb))"),
            {"tenant": a, "device": device_id, "at": NOW})

    with owner.engine.connect() as connection:
        transaction = connection.begin()
        try:
            assert product_check(connection) == PRODUCT_IDS and stored(connection) == sorted(PRODUCT_IDS)
            with Operations.context(MigrationContext.configure(connection)):
                module.downgrade()
                # The narrower CHECK is back; the agent's rows went first and the V1 products stayed.
                assert product_check(connection) == V1_PRODUCTS
                assert stored(connection) == sorted(V1_PRODUCTS)
                with pytest.raises(IntegrityError):
                    with connection.begin_nested():
                        insert_agent(connection)
                module.upgrade()
                assert product_check(connection) == PRODUCT_IDS
                insert_agent(connection)
                assert stored(connection) == sorted(PRODUCT_IDS)
        finally:
            transaction.rollback()
    with owner.engine.connect() as connection:
        assert product_check(connection) == PRODUCT_IDS


@pytest.mark.parametrize("product_id,accepted", [("edr_agent", True), ("edr", False), ("EDR_AGENT", False)])
def test_product_check_accepts_exactly_the_contract_products(service_tenants, product_id, accepted):
    owner, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    row = ProductState(tenant_id=a, device_id=UUID(device["device_id"]), product_id=product_id,
                       snapshot_sequence=1, received_at=NOW, payload={})
    if accepted:
        with owner.session_factory() as session:
            session.add(row)
            session.flush()
            session.rollback()
    else:
        with pytest.raises(IntegrityError):
            with owner.session() as session:
                session.add(row)


# --- the device detail

def test_agent_status_is_listed_like_the_other_products(service_tenants):
    _, runtime, a, _, admin, viewer = service_tenants
    device = enrolled(runtime, admin, a)
    status = agent_status(sensor_state="failed", sensor_error_code="access_denied", rule_file_present=True,
                          events_unmapped=3, outbox_backlog=MAX_SNAPSHOT_SEQUENCE)
    message = body(4, products=v1_products() + [status])
    accepted = send(runtime, device["credential_secret"], message)
    view = detail(runtime, viewer, a, device)
    assert view["last_sequence"] == 4 and view["missing_products"] == []
    assert [product["product_id"] for product in view["products"]] == sorted(PRODUCT_IDS)
    [agent] = [product for product in view["products"] if product["product_id"] == "edr_agent"]
    # Its view is the payload, as for every other product; only Termivar adds report_import_age.
    assert set(agent) == {"product_id", "snapshot_sequence", "received_at", "observation", "state"}
    assert agent["state"] == SnapshotEnvelope.model_validate(message).products[3].model_dump(mode="json")
    assert agent["state"]["agent_started_at"] == "2030-01-02T01:00:00.000000Z"
    assert agent["state"]["source"] == "self_reported" and agent["state"]["producer_verification"] == "not_verified"
    assert agent["snapshot_sequence"] == 4 and agent["received_at"] == accepted["received_at"]
    # source_observed_at 03:00:00 read at NOW (03:04:05).
    assert agent["observation"] == {"age_seconds": 245, "clock_state": "not_verified"}


@pytest.mark.parametrize("products,missing", [
    (v1_products(), ["edr_agent"]),
    ([agent_status()], ["antivirus", "hostbasedfirewall", "termivar"]),
    ([], ["antivirus", "edr_agent", "hostbasedfirewall", "termivar"]),
])
def test_missing_products_include_the_agent(service_tenants, products, missing):
    _, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    send(runtime, device["credential_secret"], body(1, products=products))
    assert detail(runtime, admin, a, device)["missing_products"] == missing


def test_never_seen_device_lists_every_product_as_missing(service_tenants):
    _, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    view = detail(runtime, admin, a, device)
    assert view["connection_status"] == "never_seen" and view["products"] == []
    assert view["missing_products"] == sorted(PRODUCT_IDS)


# --- replay and sequence rules across versions

def test_replay_and_sequence_rules_are_shared_by_v1_and_v2(service_tenants):
    _, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    secret = device["credential_secret"]
    first = body(1, schema_version=1, products=v1_products())
    accepted = send(runtime, secret, first)
    # A V2 message cannot take the sequence or message ID of the accepted V1 message.
    for conflicting in (body(1), body(1, message_id=first["message_id"]), {**first, "schema_version": 2},
                        body(2, message_id=first["message_id"])):
        with pytest.raises(Conflict):
            send(runtime, secret, conflicting)
    # The stored acceptance for the exact V1 retry is unchanged.
    assert send(runtime, secret, first) == accepted
    second = body(2, products=v1_products() + [agent_status()])
    acknowledged = send(runtime, secret, second, now=NOW.replace(second=10))
    # An exact V2 retry returns the stored acceptance and does not refresh the device.
    assert send(runtime, secret, json.loads(json.dumps(second)), now=NOW.replace(second=40)) == acknowledged
    view = detail(runtime, admin, a, device, now=NOW.replace(second=50))
    assert view["last_received_at"] == acknowledged["received_at"] and view["missing_products"] == []
    # The same sequence and ID with V1 content (schema_version alone differs) is new content: 409.
    with pytest.raises(Conflict):
        send(runtime, secret, {**second, "schema_version": 1, "products": v1_products()})
    with pytest.raises(Conflict):
        send(runtime, secret, body(1, schema_version=1, products=v1_products()))
    # A later V1 message replaces the whole state, the agent's status included.
    send(runtime, secret, body(3, schema_version=1, products=v1_products()))
    assert detail(runtime, admin, a, device)["missing_products"] == ["edr_agent"]


def test_snapshot_sequence_ends_at_2_53_minus_1(service_tenants):
    _, runtime, a, _, admin, _ = service_tenants
    device = enrolled(runtime, admin, a)
    secret = device["credential_secret"]
    last = body(MAX_SNAPSHOT_SEQUENCE)
    accepted = send(runtime, secret, last)
    assert accepted["sequence"] == MAX_SNAPSHOT_SEQUENCE
    assert send(runtime, secret, last) == accepted
    for schema_version in (1, 2):
        with pytest.raises(ServiceError, match="^Invalid snapshot$"):
            send(runtime, secret, body(MAX_SNAPSHOT_SEQUENCE + 1, schema_version=schema_version, products=[]))
    view = detail(runtime, admin, a, device)
    assert view["last_sequence"] == MAX_SNAPSHOT_SEQUENCE
    assert all(product["snapshot_sequence"] == MAX_SNAPSHOT_SEQUENCE for product in view["products"])


# --- HTTP

def test_v2_snapshot_and_detail_over_http(pg_service_databases, api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers = auth(device["credential_secret"])
    message = body(1, products=v1_products() + [agent_status(sensor_state="lost", sensor_error_code="session_in_use")])
    raw = json.dumps(message, separators=(",", ":")).encode("utf-8")
    first = client.put("/api/v1/device/snapshot", content=raw, headers={**headers, "Content-Type": "application/json"})
    assert first.status_code == 200, first.text
    assert set(first.json()) == {"accepted", "message_id", "sequence", "received_at"}
    # The byte-identical resend gets the stored acceptance.
    again = client.put("/api/v1/device/snapshot", content=raw, headers={**headers, "Content-Type": "application/json"})
    assert again.status_code == 200 and again.json() == first.json()
    operator = auth(ctx["token"]())
    view = client.get(f"/api/v1/tenants/{ctx['a']}/devices/{device['device_id']}", headers=operator).json()
    assert view["missing_products"] == [] and view["last_sequence"] == 1
    [agent] = [product for product in view["products"] if product["product_id"] == "edr_agent"]
    assert agent["state"]["sensor_state"] == "lost" and agent["state"]["sensor_error_code"] == "session_in_use"
    assert agent["state"]["producer_verification"] == "not_verified"
    listing = client.get(f"/api/v1/tenants/{ctx['a']}/devices", headers=operator).json()["items"]
    assert [row["last_sequence"] for row in listing if row["id"] == device["device_id"]] == [1]


@pytest.mark.parametrize("message", [
    body(1, schema_version=1),
    body(1, products=[agent_status(sensor_state="started", sensor_error_code="access_denied")]),
    body(1, products=[agent_status(protection_active=True)]),
    body(1, products=[agent_status(rules_loaded=True)]),
    body(1, products=[agent_status(catalog_available=True)]),
    body(1, products=[agent_status(outbox_backlog=MAX_SNAPSHOT_SEQUENCE + 1)]),
    body(1, products=[agent_status(engine_id="edr-agent/çanary-private")]),
    body(MAX_SNAPSHOT_SEQUENCE + 1),
    body(1, schema_version=3),
    body(1, products=[agent_status(), agent_status()]),
])
def test_invalid_v2_bodies_are_422_without_echo_or_write(pg_service_databases, api_context, message):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    result = client.put("/api/v1/device/snapshot", json=message, headers=auth(device["credential_secret"]))
    assert result.status_code == 422
    assert "anary-private" not in result.text and "protection_active" not in result.text
    view = client.get(f"/api/v1/tenants/{ctx['a']}/devices/{device['device_id']}", headers=auth(ctx["token"]())).json()
    assert view["connection_status"] == "never_seen" and view["last_sequence"] is None


@pytest.mark.parametrize("schema_version,products", [(1, v1_products()), (2, v1_products() + [agent_status()])])
def test_envelope_time_outside_the_window_is_422_and_the_device_stays_usable(pg_service_databases, api_context,
                                                                            schema_version, products):
    """devices.source_observed_at is timestamptz; 9999-12-31T23:59:59Z is year 10000 in a session east of UTC.

    Once stored, every load of that device row failed with 503 in such a session (the review found this with the
    fixture's Europe/Bucharest sessions): the tenant's device list, the detail, the device's own requests and the
    operator's revoke. Both versions now refuse the time before anything is written.
    """
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers, operator = auth(device["credential_secret"]), auth(ctx["token"]())
    devices = f"/api/v1/tenants/{ctx['a']}/devices"
    path = f"{devices}/{device['device_id']}"

    def snapshot(sequence, **changes):
        message = body(sequence, schema_version=schema_version, products=products, **changes)
        return client.put("/api/v1/device/snapshot", json=message, headers=headers)

    def stored():
        view = client.get(path, headers=operator)
        assert view.status_code == 200, view.text
        data = view.json()
        return ([data[key] for key in ("last_sequence", "last_received_at", "source_observed_at", "missing_products")],
                [(item["product_id"], item["snapshot_sequence"], item["received_at"], item["state"])
                 for item in data["products"]])

    first = snapshot(1)
    assert first.status_code == 200, first.text
    before = stored()
    assert before[0][0] == 1 and before[0][2] == "2030-01-02T03:00:00Z"
    refused = snapshot(2, source_observed_at="9999-12-31T23:59:59Z")
    assert refused.status_code == 422 and refused.json() == {"detail": "invalid_request"}
    # Nothing was stored: the device row and its products, last_sequence included, are unchanged.
    assert stored() == before
    listing = client.get(devices, headers=operator)
    assert listing.status_code == 200, listing.text
    assert [row["last_sequence"] for row in listing.json()["items"] if row["id"] == device["device_id"]] == [1]
    following = snapshot(2)
    assert following.status_code == 200 and following.json()["sequence"] == 2, following.text
    revoked = client.post(f"{path}/revoke", json={}, headers=operator)
    assert revoked.status_code == 200, revoked.text
    assert client.get(path, headers=operator).json()["identity_status"] == "revoked"
