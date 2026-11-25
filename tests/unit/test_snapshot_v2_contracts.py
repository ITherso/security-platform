"""Snapshot V2: the edr_agent product, the shared V1/V2 envelope, the 2^53-1 snapshot sequence and the
envelope's source_observed_at window.

Pure contract tests. Real PostgreSQL ingestion, migration 0004 and the HTTP route are in
tests/integration/test_snapshot_v2.py; the console's mirror of this contract is checked in
tests/unit/test_console_edr_agent.py.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from typing import get_args

from pydantic import ValidationError
import pytest

from security_platform import contracts, event_contracts
from security_platform.contracts import (MAX_SEQUENCE, MAX_SNAPSHOT_BYTES, MAX_SNAPSHOT_SEQUENCE, PRODUCT_IDS,
    EdrAgentStatus, SnapshotEnvelope, canonical_json, snapshot_digest)
from security_platform.event_contracts import SensorErrorCode as EventSensorErrorCode
from security_platform.models import ProductState


PROJECT = Path(__file__).resolve().parents[2]
MESSAGE_ID = "00000000-0000-4000-8000-000000000003"
COUNTERS = ("events_queue_dropped", "events_write_failed", "events_unmapped", "events_skipped", "events_evicted",
            "events_discarded", "events_degraded", "outbox_backlog")
# The specification's field set: the edr_agent fields plus the inherited ReportedProduct fields.
EDR_FIELDS = {"product_id", "status", "agent_started_at", "engine_id", "rule_file_present", "sensor_state",
              "sensor_error_code", *COUNTERS, "catalog_available", "source", "producer_verification", "version",
              "source_observed_at"}
SENSOR_STATES = ("started", "lost", "failed", "stopped", "disabled", "unknown")
SENSOR_CODES = ("session_name_invalid", "session_in_use", "access_denied", "session_start_failed",
                "session_stop_failed", "unknown")


def agent_status(**changes):
    status = {"product_id": "edr_agent", "status": "running", "version": "0.3.0",
              "source_observed_at": "2026-11-24T10:00:00Z", "agent_started_at": "2026-11-24T08:00:00.5Z",
              "engine_id": "edr-agent/0.3.0", "rule_file_present": True, "sensor_state": "started",
              "sensor_error_code": None, **{name: index for index, name in enumerate(COUNTERS)}}
    status.update(changes)
    return status


def v2(*products, **changes):
    body = {"schema_version": 2, "message_id": MESSAGE_ID, "sequence": 7, "source_observed_at": "2026-11-24T10:00:00Z",
            "products": list(products) if products else [agent_status()]}
    body.update(changes)
    return body


def v1_products():
    return [{"product_id": "hostbasedfirewall", "status": "running", "firewall_mode": "enforce"},
            {"product_id": "termivar", "status": "experimental", "report_presence": "none"},
            {"product_id": "antivirus", "status": "planned", "availability": "unavailable"}]


def rejected(body, reason=None):
    with pytest.raises(ValidationError) as caught:
        SnapshotEnvelope.model_validate(body)
    if reason is not None:
        assert reason in str(caught.value)


# --- the edr_agent product

def test_edr_agent_status_has_exactly_the_specified_fields_and_unknown_defaults():
    assert set(EdrAgentStatus.model_fields) == EDR_FIELDS
    minimal = EdrAgentStatus.model_validate({"product_id": "edr_agent"}).model_dump(mode="json")
    assert minimal == {"product_id": "edr_agent", "status": "unknown", "sensor_state": "unknown",
                       "source": "self_reported", "producer_verification": "not_verified",
                       **{name: None for name in EDR_FIELDS - {"product_id", "status", "sensor_state", "source",
                                                                 "producer_verification"}}}


def test_reference_v2_body_has_a_pinned_canonical_form():
    model = SnapshotEnvelope.model_validate(v2())
    canonical = canonical_json(model)
    assert canonical == (
        b'{"message_id":"00000000-0000-4000-8000-000000000003","products":[{"agent_started_at":'
        b'"2026-11-24T08:00:00.500000Z","catalog_available":null,"engine_id":"edr-agent/0.3.0","events_degraded":6,'
        b'"events_discarded":5,"events_evicted":4,"events_queue_dropped":0,"events_skipped":3,"events_unmapped":2,'
        b'"events_write_failed":1,"outbox_backlog":7,"producer_verification":"not_verified","product_id":"edr_agent",'
        b'"rule_file_present":true,"sensor_error_code":null,"sensor_state":"started","source":"self_reported",'
        b'"source_observed_at":"2026-11-24T10:00:00.000000Z","status":"running","version":"0.3.0"}],'
        b'"schema_version":2,"sequence":7,"source_observed_at":"2026-11-24T10:00:00.000000Z"}')
    assert snapshot_digest(model) == hashlib.sha256(canonical).hexdigest() == (
        "7ac17abca2ed25cb0933044178d1bcad1461451b9f38ad3e933e2b599f2be5ec")
    # Key order is irrelevant: the Platform canonicalises the parsed model.
    reordered = json.loads(json.dumps(dict(reversed(list(v2(dict(reversed(list(agent_status().items())))).items())))))
    assert snapshot_digest(SnapshotEnvelope.model_validate(reordered)) == snapshot_digest(model)


@pytest.mark.parametrize("changes", [
    {"catalog_available": True}, {"catalog_available": False}, {"source": "verified"},
    {"producer_verification": "verified"}, {"status": "protected"}, {"status": "active"}, {"status": "stopped"},
    {"protection_active": True}, {"realtime_protection": True}, {"real_time_protection": True},
    {"rules_loaded": True}, {"rule_file_loaded": True}, {"loaded_rules": 3}, {"protected": True},
    {"sensor_state": "running"}, {"sensor_state": "protected"}, {"sensor_state": None},
    {"sensor_error_code": "raw ETW failure text"}, {"rule_file_present": "yes"}, {"rule_file_present": 1},
    {"version": "C:\\private\\agent"}, {"version": "0.3.0 beta"}, {"version": ""},
    {"agent_started_at": "2026-11-24T08:00:00"}, {"agent_started_at": "2026-11-24T08:00:00+03:00"},
    {"agent_started_at": 1764000000}, {"agent_started_at": "2026-02-30T00:00:00Z"},
    {"agent_started_at": "2026-11-24T08:00:00.1234567Z"}, {"source_observed_at": "yesterday"},
    {"product_id": "edr"}, {"product_id": "EDR_AGENT"},
])
def test_edr_agent_claims_and_closed_types_cannot_be_promoted(changes):
    rejected(v2(agent_status(**changes)))


@pytest.mark.parametrize("state", SENSOR_STATES)
@pytest.mark.parametrize("code", SENSOR_CODES)
def test_sensor_error_code_is_allowed_only_with_lost_or_failed(state, code):
    body = v2(agent_status(sensor_state=state, sensor_error_code=code))
    if state in ("lost", "failed"):
        assert SnapshotEnvelope.model_validate(body).products[0].sensor_error_code == code
    else:
        rejected(body, "sensor_error_code_requires_lost_or_failed")
    # Without a code every state is valid, lost and failed included.
    assert SnapshotEnvelope.model_validate(v2(agent_status(sensor_state=state))).products[0].sensor_error_code is None


def test_edr_sensor_codes_are_the_event_contract_codes():
    assert get_args(contracts.EdrSensorErrorCode) == get_args(EventSensorErrorCode) == SENSOR_CODES
    assert get_args(contracts.EdrSensorState) == SENSOR_STATES


@pytest.mark.parametrize("counter", COUNTERS)
def test_counters_are_strict_safe_integers_or_null(counter):
    for value in (0, 1, MAX_SNAPSHOT_SEQUENCE, None):
        assert getattr(SnapshotEnvelope.model_validate(v2(agent_status(**{counter: value}))).products[0],
                       counter) == value
    for value in (-1, 2**53, MAX_SEQUENCE, True, False, 1.0, "1", float("nan"), float("inf"), [1]):
        rejected(v2(agent_status(**{counter: value})))


@pytest.mark.parametrize("engine_id", ["edr-agent/0.3.0", "edr-agent/0.3.0 scanner/1.2.3", "A" * 128,
                                       "x+y_z.w-1", "0", "edr-agent/0.3.0 "])
def test_engine_id_accepts_the_ascii_pattern(engine_id):
    assert SnapshotEnvelope.model_validate(v2(agent_status(engine_id=engine_id))).products[0].engine_id == engine_id


@pytest.mark.parametrize("engine_id", ["", " x", "-x", "/x", "x\n", "x\r", "x\t", "\u00e7ekirdek", "x\u00e9",
                                       "x\u200b", "\uff10", "A" * 129, "x;y", "x\\y", "x:y", "x@y", 7])
def test_engine_id_rejects_non_ascii_control_and_other_characters(engine_id):
    rejected(v2(agent_status(engine_id=engine_id)))


# --- the envelope

def test_v2_carries_every_product_and_v1_products_alone():
    four = SnapshotEnvelope.model_validate(v2(*v1_products(), agent_status()))
    assert [product.product_id for product in four.products] == list(PRODUCT_IDS)
    assert SnapshotEnvelope.model_validate(v2(*v1_products())).products[2].product_id == "antivirus"
    assert SnapshotEnvelope.model_validate({**v2(), "products": []}).products == []


@pytest.mark.parametrize("products", [[agent_status()], v1_products() + [agent_status()],
                                      [v1_products()[0], agent_status()]])
def test_edr_agent_requires_schema_version_2(products):
    rejected({**v2(), "schema_version": 1, "products": products}, "edr_agent_requires_schema_version_2")


def test_products_stay_unique_and_bounded_in_both_versions():
    rejected(v2(agent_status(), agent_status()), "duplicate_product")
    # max_length=4 is checked before uniqueness, and the published schema says so.
    with pytest.raises(ValidationError) as five:
        SnapshotEnvelope.model_validate(v2(*v1_products(), agent_status(), v1_products()[0]))
    assert [error["type"] for error in five.value.errors()] == ["too_long"]
    assert SnapshotEnvelope.model_json_schema()["properties"]["products"]["maxItems"] == 4
    rejected({**v2(), "schema_version": 1, "products": v1_products() + [v1_products()[0]]})
    assert len(SnapshotEnvelope.model_validate({**v2(), "schema_version": 1, "products": v1_products()}).products) == 3


@pytest.mark.parametrize("schema_version", [1, 2])
def test_snapshot_sequence_is_bounded_at_2_53_minus_1_in_both_versions(schema_version):
    body = {**v2(*v1_products()), "schema_version": schema_version}
    assert MAX_SNAPSHOT_SEQUENCE == 2**53 - 1 == 9007199254740991
    assert SnapshotEnvelope.model_validate({**body, "sequence": MAX_SNAPSHOT_SEQUENCE}).sequence == MAX_SNAPSHOT_SEQUENCE
    assert SnapshotEnvelope.model_validate({**body, "sequence": 1}).sequence == 1
    for sequence in (MAX_SNAPSHOT_SEQUENCE + 1, MAX_SEQUENCE, MAX_SEQUENCE + 1, 0, -1):
        rejected({**body, "sequence": sequence})


def test_other_sequences_keep_max_sequence():
    assert contracts.MAX_SEQUENCE == 2**63 - 1 > MAX_SNAPSHOT_SEQUENCE


# The envelope's source_observed_at is stored in devices.source_observed_at (timestamptz). A non-UTC session cannot
# load an instant outside 1970-01-01T00:00:00Z <= t < 9999-01-01T00:00:00Z back, so, like the sequence cap, both
# versions refuse it: a V1 tightening for values no real sender produces.

@pytest.mark.parametrize("schema_version", [1, 2])
@pytest.mark.parametrize("value,normalized", [
    ("1970-01-01T00:00:00Z", "1970-01-01T00:00:00.000000Z"),
    ("9998-12-31T23:59:59.999999Z", "9998-12-31T23:59:59.999999Z"),
    # The bound applies to the normalized instant.
    ("1969-12-31T24:00:00Z", "1970-01-01T00:00:00.000000Z"),
    (None, None),
])
def test_envelope_source_observed_at_accepts_its_window_and_null(schema_version, value, normalized):
    body = {**v2(*v1_products()), "schema_version": schema_version, "source_observed_at": value}
    assert SnapshotEnvelope.model_validate(body).source_observed_at == normalized


@pytest.mark.parametrize("schema_version", [1, 2])
@pytest.mark.parametrize("value", [
    "1969-12-31T23:59:59.999999Z", "0001-01-01T00:00:00Z", "9999-01-01T00:00:00Z", "9998-12-31T24:00:00Z",
    "9999-12-31T23:59:59Z", "9999-12-31T23:59:59.999999Z",
])
def test_envelope_source_observed_at_outside_1970_to_9999_is_refused(schema_version, value):
    # 9998-12-31T24:00:00Z normalizes to 9999-01-01T00:00:00Z, the first refused instant.
    rejected({**v2(*v1_products()), "schema_version": schema_version, "source_observed_at": value},
             "source_observed_at_out_of_range")


def test_snapshot_envelope_and_events_share_one_observed_at_window():
    # Defined in contracts.py; event_contracts re-exports the same objects for its existing importers.
    assert (contracts.MIN_OBSERVED_AT, contracts.MAX_OBSERVED_AT) == (datetime(1970, 1, 1, tzinfo=timezone.utc),
                                                                      datetime(9999, 1, 1, tzinfo=timezone.utc))
    assert event_contracts.MIN_OBSERVED_AT is contracts.MIN_OBSERVED_AT
    assert event_contracts.MAX_OBSERVED_AT is contracts.MAX_OBSERVED_AT


def test_product_times_keep_the_plain_utc_rule():
    # Only the envelope field is bounded: a product's times are text inside the JSONB payload and load in any zone.
    status = agent_status(source_observed_at="9999-12-31T23:59:59.999999Z", agent_started_at="0001-01-01T00:00:00Z")
    firewall = {**v1_products()[0], "source_observed_at": "1969-12-31T23:59:59Z"}
    model = SnapshotEnvelope.model_validate(v2(firewall, status))
    assert [product.source_observed_at for product in model.products] == ["1969-12-31T23:59:59.000000Z",
                                                                          "9999-12-31T23:59:59.999999Z"]
    assert model.products[1].agent_started_at == "0001-01-01T00:00:00.000000Z"
    assert model.source_observed_at == "2026-11-24T10:00:00.000000Z"


@pytest.mark.parametrize("schema_version", [True, False, "2", 2.0, 3, 0, -2, None])
def test_schema_version_is_a_strict_1_or_2(schema_version):
    rejected(v2(schema_version=schema_version))


@pytest.mark.parametrize("field", ["tenant_id", "device_id", "protection_active", "rules_loaded", "command"])
def test_v2_envelope_has_no_extra_fields(field):
    rejected(v2(**{field: True}))


def test_largest_v2_snapshot_fits_the_body_and_payload_bounds():
    errors = list(get_args(contracts.ErrorCode))[:16]
    products = [
        {"product_id": "hostbasedfirewall", "status": "unavailable", "installed": False, "reported_running": False,
         "reported_stale": True, "firewall_mode": "unknown", "error_codes": errors, "catalog_available": False,
         "version": "V" * 64, "source_observed_at": "2026-11-24T10:00:00.123456Z"},
        {"product_id": "termivar", "status": "experimental", "scanner_installed": False, "execution_available": False,
         "report_presence": "present", "catalog_available": False, "version": "T" * 64,
         "source_observed_at": "2026-11-24T10:00:00.123456Z",
         "latest_report": {"digest": "f" * 64, "report_schema": "venom-rendered-assessment/v1",
                           "imported_at": "2026-11-24T10:00:00.123456Z", "subject_count": 1024, "item_count": 4096,
                           "counts": {"informational": 4096, "needs_review": 0, "confirmed": 0},
                           "severity_counts": {"unassigned": 4096, "info": 0, "low": 0, "medium": 0, "high": 0,
                                               "critical": 0}}},
        {"product_id": "antivirus", "status": "unknown", "availability": "unknown", "execution_available": False,
         "catalog_available": False, "source_observed_at": "2026-11-24T10:00:00.123456Z"},
        agent_status(version="E" * 64, engine_id="G" * 128, sensor_state="failed",
                     sensor_error_code="session_start_failed", source_observed_at="2026-11-24T10:00:00.123456Z",
                     **{name: MAX_SNAPSHOT_SEQUENCE for name in COUNTERS}),
    ]
    model = SnapshotEnvelope.model_validate(v2(*products, sequence=MAX_SNAPSHOT_SEQUENCE))
    assert len(canonical_json(model)) < MAX_SNAPSHOT_BYTES // 4
    for product in model.products:
        # The stored payload and its PostgreSQL CHECK bound (ck_product_payload_bytes).
        assert len(json.dumps(product.model_dump(mode="json")).encode("utf-8")) < 16384 // 4


# --- V1 compatibility: bodies that were valid before stay valid with the same canonical JSON and digest, except the two
# tightenings above (a sequence above 2^53-1, an envelope source_observed_at outside its window)

V1_FULL = {
    "schema_version": 1, "message_id": "00000000-0000-4000-8000-000000000001", "sequence": 42,
    "source_observed_at": "2026-11-24T10:00:00Z",
    "products": [
        {"product_id": "hostbasedfirewall", "status": "running", "installed": True, "reported_running": True,
         "reported_stale": False, "firewall_mode": "enforce", "error_codes": ["config_error", "telemetry_error"],
         "catalog_available": True, "version": "1.4.4", "source_observed_at": "2026-11-24T09:59:59.5Z"},
        {"product_id": "termivar", "status": "experimental", "scanner_installed": None, "execution_available": False,
         "report_presence": "present", "catalog_available": True,
         "latest_report": {"digest": "a" * 64, "report_schema": "venom-rendered-assessment/v1",
                           "imported_at": "2023-11-14T22:13:20.25Z", "subject_count": 1, "item_count": 4,
                           "counts": {"informational": 3, "needs_review": 1, "confirmed": 0},
                           "severity_counts": {"unassigned": 4, "info": 0, "low": 0, "medium": 0, "high": 0,
                                               "critical": 0}}},
        {"product_id": "antivirus", "status": "planned", "availability": "unavailable", "execution_available": False},
    ],
}
# The Stage 1 agent heartbeat: compact, sorted keys, no products and no source_observed_at.
V1_STAGE1 = b'{"message_id":"00000000-0000-4000-8000-000000000002","products":[],"schema_version":1,"sequence":7}'


@pytest.mark.parametrize("body,canonical,digest", [
    (V1_FULL,
     b'{"message_id":"00000000-0000-4000-8000-000000000001","products":[{"catalog_available":true,"error_codes":'
     b'["config_error","telemetry_error"],"firewall_mode":"enforce","installed":true,"producer_verification":'
     b'"not_verified","product_id":"hostbasedfirewall","reported_running":true,"reported_stale":false,"source":'
     b'"self_reported","source_observed_at":"2026-11-24T09:59:59.500000Z","status":"running","version":"1.4.4"},'
     b'{"catalog_available":true,"execution_available":false,"latest_report":{"counts":{"confirmed":0,'
     b'"informational":3,"needs_review":1},"digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
     b'"imported_at":"2023-11-14T22:13:20.250000Z","item_count":4,"producer_verification":"not_verified",'
     b'"report_schema":"venom-rendered-assessment/v1","scope":"offline_report_summary","severity_counts":'
     b'{"critical":0,"high":0,"info":0,"low":0,"medium":0,"unassigned":4},"source":"self_reported","subject_count":1},'
     b'"producer_verification":"not_verified","product_id":"termivar","report_presence":"present",'
     b'"scanner_installed":null,"source":"self_reported","source_observed_at":null,"status":"experimental",'
     b'"version":null},{"availability":"unavailable","catalog_available":null,"execution_available":false,'
     b'"producer_verification":"not_verified","product_id":"antivirus","source":"self_reported",'
     b'"source_observed_at":null,"status":"planned","version":null}],"schema_version":1,"sequence":42,'
     b'"source_observed_at":"2026-11-24T10:00:00.000000Z"}',
     "2f1ead0b66ab96f74bb059967cd69757845c592af2a9c8be34ac852b25f51495"),
    (json.loads(V1_STAGE1),
     b'{"message_id":"00000000-0000-4000-8000-000000000002","products":[],"schema_version":1,"sequence":7,'
     b'"source_observed_at":null}',
     "b517d12011cf681a111d88f320da0eaae1001b90cd40a5b6bf357c47b43c128c"),
])
def test_v1_bodies_keep_the_canonical_json_and_digest_of_45e0482(body, canonical, digest):
    # Both values were computed with the V1-only contract at 45e0482, before Snapshot V2.
    model = SnapshotEnvelope.model_validate(json.loads(json.dumps(body)))
    assert canonical_json(model) == canonical
    assert snapshot_digest(model) == hashlib.sha256(canonical).hexdigest() == digest


# --- one product list everywhere

def test_product_ids_match_the_union_the_database_check_and_migration_0004():
    union = get_args(get_args(contracts.ProductStatus)[0])
    assert tuple(get_args(model.model_fields["product_id"].annotation)[0] for model in union) == PRODUCT_IDS
    assert contracts.V1_PRODUCT_IDS == set(PRODUCT_IDS) - {"edr_agent"}
    [check] = [item for item in ProductState.__table__.constraints if getattr(item, "name", None) == "ck_product_id"]
    assert tuple(re.findall(r"'(\w+)'", str(check.sqltext))) == PRODUCT_IDS
    spec = importlib.util.spec_from_file_location("migration_0004_unit",
                                                  PROJECT / "migrations/versions/0004_edr_agent_product.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert (migration.revision, migration.down_revision) == ("0004_edr_agent_product", "0003_alerts")
    # Only the product CHECK changes: drop it and add the wider one; the downgrade restores the V1 list.
    assert [statement.split()[:5] for statement in migration.DDL_STATEMENTS] == [
        ["ALTER", "TABLE", "product_states", "DROP", "CONSTRAINT"], ["ALTER", "TABLE", "product_states", "ADD", "CONSTRAINT"]]
    assert tuple(re.findall(r"'(\w+)'", migration.DDL_STATEMENTS[1])) == PRODUCT_IDS
    assert re.findall(r"'(\w+)'", migration.DOWNGRADE_STATEMENTS[0]) == ["edr_agent"]
    assert tuple(re.findall(r"'(\w+)'", migration.DOWNGRADE_STATEMENTS[2])) == ("hostbasedfirewall", "termivar",
                                                                                "antivirus")
