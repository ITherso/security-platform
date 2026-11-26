"""Snapshot V3 (ADR 0004 section 1.3): EdrAgentStatusV3, the separate V3 envelope, the schema_version dispatch, and
the V1/V2 bodies and digests kept unchanged.

Pure contract tests. V1 and V2 stay in tests/unit/test_snapshot_contracts.py and test_snapshot_v2_contracts.py,
whose V3 twins are here (the non-promotable claims, the envelope extras, the policy gate's envelope refusals).
V3 ingestion through the real API and PostgreSQL is in tests/integration/test_stage3_contracts.py.
"""
import hashlib
import json
import re
from typing import get_args
from uuid import uuid4

from pydantic import ValidationError
import pytest

from security_platform import contracts
from security_platform.contracts import (CAPABILITY_STATES, EDR_V2_COUNTER_KEYS, EDR_V3_COUNTER_KEYS,
    ISOLATION_STATES, MAX_HEARTBEAT_INTERVAL_SECONDS, MAX_RESPONSE_KEY_IDS, MAX_SEQUENCE, MAX_SNAPSHOT_BYTES,
    MAX_SNAPSHOT_SEQUENCE, MIN_HEARTBEAT_INTERVAL_SECONDS, PREVIOUS_RUN_ENDS, PRODUCT_IDS, RESPONSE_ACTIONS,
    RESPONSE_CHANNEL_STATES, RULE_SET_STATES, SERVICE_CONFIG_STATES, SNAPSHOT_MODELS, AntivirusStatus,
    EdrAgentStatus, EdrAgentStatusV3, HostBasedFirewallStatus, SnapshotEnvelope, SnapshotEnvelopeV3, TermivarStatus,
    canonical_json, parse_snapshot, snapshot_digest)
from test_snapshot_v2_contracts import V1_FULL, V1_STAGE1, v1_products, v2
from test_snapshot_v2_contracts import agent_status as v2_agent_status


MESSAGE_ID = "00000000-0000-4000-8000-000000000004"
# The V3 fields after the V2 ones, in declaration order.
V3_FIELDS = ("rule_set_state", "rule_set_id", "realtime_scan_state", "file_change_sensor_state",
             "command_line_sensor_state", "persistence_watch_state", "scans_completed", "scans_detected",
             "scans_no_verdict", "scan_jobs_dropped", "scan_cache_hits", "etw_events_lost", "file_change_gaps",
             "cmdline_unavailable", "response_channel_state", "response_actions_enabled", "response_key_ids",
             "last_action_seq", "isolation_state", "isolation_until", "isolation_checked_at", "quarantine_items",
             "service_config_state", "previous_run_end", "heartbeat_interval_seconds", "behavior_rules_version")
STATE_FIELDS = {"rule_set_state": RULE_SET_STATES, "realtime_scan_state": CAPABILITY_STATES,
                "file_change_sensor_state": CAPABILITY_STATES, "command_line_sensor_state": CAPABILITY_STATES,
                "persistence_watch_state": CAPABILITY_STATES, "response_channel_state": RESPONSE_CHANNEL_STATES,
                "isolation_state": ISOLATION_STATES, "service_config_state": SERVICE_CONFIG_STATES,
                "previous_run_end": PREVIOUS_RUN_ENDS}
SENSOR_STATES = ("started", "lost", "failed", "stopped", "disabled", "unknown")
SENSOR_CODES = ("session_name_invalid", "session_in_use", "access_denied", "session_start_failed",
                "session_stop_failed", "unknown")


def agent_v3(**changes):
    status = {"product_id": "edr_agent", "status": "running", "version": "0.4.0",
              "source_observed_at": "2026-11-26T10:00:00Z", "agent_started_at": "2026-11-26T08:00:00.5Z",
              "engine_id": "edr-agent/0.4.0", "sensor_state": "started", "sensor_error_code": None,
              **{name: index for index, name in enumerate(EDR_V3_COUNTER_KEYS)},
              "rule_set_state": "compiled", "rule_set_id": "c" * 64, "realtime_scan_state": "running",
              "file_change_sensor_state": "not_available", "command_line_sensor_state": "degraded",
              "persistence_watch_state": "running", "response_channel_state": "awaiting_tenant_binding",
              "response_actions_enabled": ["scan_path"], "response_key_ids": [], "last_action_seq": None,
              "isolation_state": "inactive", "isolation_until": None, "isolation_checked_at": "2026-11-26T09:59:00Z",
              "quarantine_items": 0, "service_config_state": "as_installed", "previous_run_end": "clean",
              "heartbeat_interval_seconds": 60, "behavior_rules_version": "altay-behavior/v1"}
    status.update(changes)
    return status


def v3(*products, **changes):
    body = {"schema_version": 3, "message_id": MESSAGE_ID, "sequence": 7, "source_observed_at": "2026-11-26T10:00:00Z",
            "products": list(products) if products else [agent_v3()]}
    body.update(changes)
    return body


def agent(**changes):
    """The validated V3 agent status of a one-product V3 body."""
    return SnapshotEnvelopeV3.model_validate(v3(agent_v3(**changes))).products[0]


def rejected(body, reason=None):
    with pytest.raises(ValidationError) as caught:
        SnapshotEnvelopeV3.model_validate(body)
    if reason is not None:
        assert reason in str(caught.value)


def errors(function, value):
    with pytest.raises(ValidationError) as caught:
        function(value)
    return [(error["type"], error["loc"], error["msg"]) for error in caught.value.errors()]


# --- EdrAgentStatusV3

def test_v3_fields_are_the_v2_fields_without_rule_file_present_plus_the_v3_fields():
    assert set(EdrAgentStatusV3.model_fields) == (set(EdrAgentStatus.model_fields) - {"rule_file_present"}) | set(
        V3_FIELDS)
    assert tuple(EdrAgentStatusV3.model_fields)[-len(V3_FIELDS):] == V3_FIELDS
    assert "rule_file_present" not in EdrAgentStatusV3.model_fields
    assert get_args(EdrAgentStatusV3.model_fields["product_id"].annotation) == ("edr_agent",)
    # A separate class: the V2 model, and so the V1/V2 digests, are untouched.
    assert not issubclass(EdrAgentStatusV3, EdrAgentStatus) and "rule_set_state" not in EdrAgentStatus.model_fields


def test_shared_fields_keep_the_v2_types_and_defaults():
    for name, field in EdrAgentStatus.model_fields.items():
        if name != "rule_file_present":
            other = EdrAgentStatusV3.model_fields[name]
            assert (other.annotation, other.default, other.metadata) == (field.annotation, field.default,
                                                                         field.metadata), name


def test_minimal_v3_status_has_unknown_states_empty_lists_and_nulls():
    minimal = EdrAgentStatusV3.model_validate({"product_id": "edr_agent"}).model_dump(mode="json")
    expected = {name: None for name in EdrAgentStatusV3.model_fields}
    expected.update(product_id="edr_agent", status="unknown", sensor_state="unknown", source="self_reported",
                    producer_verification="not_verified", response_actions_enabled=[], response_key_ids=[],
                    **{name: "unknown" for name in STATE_FIELDS})
    assert minimal == expected


def test_v3_closed_sets_counters_and_bounds_are_pinned():
    assert RULE_SET_STATES == ("compiled", "missing", "invalid", "unreadable", "unknown")
    assert CAPABILITY_STATES == ("running", "degraded", "stopped", "failed", "not_available", "unknown")
    assert RESPONSE_CHANNEL_STATES == ("ready", "not_configured", "awaiting_tenant_binding", "journal_invalid",
                                       "unknown")
    assert RESPONSE_ACTIONS == ("scan_path", "terminate_process", "quarantine_file", "restore_file", "isolate_host",
                                "release_host")
    assert ISOLATION_STATES == ("inactive", "active", "partial", "unknown")
    assert SERVICE_CONFIG_STATES == ("as_installed", "changed", "unknown")
    assert PREVIOUS_RUN_ENDS == ("clean", "unclean", "first_start", "unknown")
    assert EDR_V2_COUNTER_KEYS == ("events_queue_dropped", "events_write_failed", "events_unmapped", "events_skipped",
                                   "events_evicted", "events_discarded", "events_degraded", "outbox_backlog")
    # The V2 counters are EdrAgentStatus's, in its order.
    assert EDR_V2_COUNTER_KEYS == tuple(name for name in EdrAgentStatus.model_fields if name.startswith(
        ("events_", "outbox_")))
    assert EDR_V3_COUNTER_KEYS == EDR_V2_COUNTER_KEYS + (
        "scans_completed", "scans_detected", "scans_no_verdict", "scan_jobs_dropped", "scan_cache_hits",
        "etw_events_lost", "file_change_gaps", "cmdline_unavailable")
    assert set(EDR_V3_COUNTER_KEYS) <= set(EdrAgentStatusV3.model_fields)
    assert (MIN_HEARTBEAT_INTERVAL_SECONDS, MAX_HEARTBEAT_INTERVAL_SECONDS, MAX_RESPONSE_KEY_IDS) == (30, 3600, 4)
    assert contracts.BEHAVIOR_RULES_VERSION_PATTERN == r"^altay-behavior/v[1-9][0-9]{0,5}$"
    for name, values in STATE_FIELDS.items():
        assert get_args(EdrAgentStatusV3.model_fields[name].annotation) == values, name
        assert EdrAgentStatusV3.model_fields[name].default == "unknown"
    actions = EdrAgentStatusV3.model_fields["response_actions_enabled"].annotation
    assert get_args(get_args(actions)[0]) == RESPONSE_ACTIONS


@pytest.mark.parametrize("field", sorted(STATE_FIELDS))
def test_v3_states_accept_exactly_their_closed_set(field):
    values = STATE_FIELDS[field]
    for value in values:
        assert getattr(agent(**{field: value}), field) == value
    for value in ("protected", "enabled", "loaded", "verified", "Unknown", values[0].upper(), values[0] + " ", "",
                  None, 1, True):
        rejected(v3(agent_v3(**{field: value})))


@pytest.mark.parametrize("counter", EDR_V3_COUNTER_KEYS + ("last_action_seq", "quarantine_items"))
def test_v3_counters_are_strict_safe_integers_or_null(counter):
    for value in (0, 1, MAX_SNAPSHOT_SEQUENCE, None):
        assert getattr(agent(**{counter: value}), counter) == value
    for value in (-1, 2**53, MAX_SEQUENCE, True, False, 1.0, "1", float("nan"), float("inf"), [1]):
        rejected(v3(agent_v3(**{counter: value})))


def test_rule_set_id_is_64_lowercase_hex_or_null():
    for value in ("0" * 64, "c" * 64, None):
        assert agent(rule_set_id=value).rule_set_id == value
    for value in ("C" * 64, "c" * 63, "c" * 65, "g" * 64, "c" * 64 + "\n", "", 7):
        rejected(v3(agent_v3(rule_set_id=value)))


def test_response_actions_are_a_unique_sorted_closed_list():
    everything = sorted(RESPONSE_ACTIONS)
    for value in ([], ["scan_path"], ["isolate_host", "release_host"], everything):
        assert agent(response_actions_enabled=value).response_actions_enabled == value
    # Sorted means sorted text; the catalog order of RESPONSE_ACTIONS is not.
    assert list(RESPONSE_ACTIONS) != everything
    for value in (list(RESPONSE_ACTIONS), ["scan_path", "isolate_host"], ["scan_path", "scan_path"]):
        rejected(v3(agent_v3(response_actions_enabled=value)), "response_actions_not_unique_and_sorted")
    for value in (["shell"], ["run_command"], ["Scan_Path"], [""], [None], [1], None, "scan_path",
                  everything + ["terminate_process"]):
        rejected(v3(agent_v3(response_actions_enabled=value)))


def test_response_key_ids_are_at_most_four_unique_sorted_digests():
    keys = sorted(hashlib.sha256(bytes([index])).hexdigest() for index in range(MAX_RESPONSE_KEY_IDS + 1))
    for value in ([], keys[:1], keys[:MAX_RESPONSE_KEY_IDS]):
        assert agent(response_key_ids=value).response_key_ids == value
    rejected(v3(agent_v3(response_key_ids=keys)))
    for value in (keys[1::-1], [keys[0], keys[0]]):
        rejected(v3(agent_v3(response_key_ids=value)), "response_key_ids_not_unique_and_sorted")
    for value in ([keys[0].upper()], ["a" * 63], ["g" * 64], [None], None, keys[0]):
        rejected(v3(agent_v3(response_key_ids=value)))


def test_heartbeat_interval_is_the_agents_own_range_or_null():
    for value in (MIN_HEARTBEAT_INTERVAL_SECONDS, 60, MAX_HEARTBEAT_INTERVAL_SECONDS, None):
        assert agent(heartbeat_interval_seconds=value).heartbeat_interval_seconds == value
    for value in (29, 3601, 0, -1, True, 30.0, "60", 2**53):
        rejected(v3(agent_v3(heartbeat_interval_seconds=value)))


@pytest.mark.parametrize("value", ["altay-behavior/v1", "altay-behavior/v42", "altay-behavior/v999999", None])
def test_behavior_rules_version_accepts_the_pattern(value):
    assert agent(behavior_rules_version=value).behavior_rules_version == value


@pytest.mark.parametrize("value", ["altay-behavior/v0", "altay-behavior/v01", "altay-behavior/v1000000",
                                   "Altay-behavior/v1", "altay-behavior/V1", "altay-behavior/v1 ", " altay-behavior/v1",
                                   "altay-behavior/v1\n", "altay-behaviour/v1", "altay-behavior/1", "altay-behavior/v",
                                   "altay-behavior/v1.0", "", 1])
def test_behavior_rules_version_refuses_other_text(value):
    rejected(v3(agent_v3(behavior_rules_version=value)))


@pytest.mark.parametrize("field", ["isolation_until", "isolation_checked_at"])
@pytest.mark.parametrize("value,normalized", [
    ("2026-11-26T10:00:00Z", "2026-11-26T10:00:00.000000Z"), ("1970-01-01T00:00:00Z", "1970-01-01T00:00:00.000000Z"),
    ("1969-12-31T24:00:00Z", "1970-01-01T00:00:00.000000Z"),
    ("9998-12-31T23:59:59.999999Z", "9998-12-31T23:59:59.999999Z"), (None, None),
])
def test_isolation_times_are_utc_text_in_the_observed_at_window(field, value, normalized):
    assert getattr(agent(**{field: value}), field) == normalized


@pytest.mark.parametrize("field", ["isolation_until", "isolation_checked_at"])
@pytest.mark.parametrize("value", ["1969-12-31T23:59:59.999999Z", "0001-01-01T00:00:00Z", "9999-01-01T00:00:00Z",
                                   "9998-12-31T24:00:00Z", "9999-12-31T23:59:59.999999Z"])
def test_isolation_times_outside_the_window_are_refused(field, value):
    rejected(v3(agent_v3(**{field: value})), f"{field}_out_of_range")


@pytest.mark.parametrize("field", ["isolation_until", "isolation_checked_at"])
@pytest.mark.parametrize("value", ["2026-11-26T10:00:00", "2026-11-26T13:00:00+03:00", "2026-02-30T00:00:00Z",
                                   "2026-11-26T10:00:00.1234567Z", 1764150000, ""])
def test_isolation_times_refuse_other_forms(field, value):
    rejected(v3(agent_v3(**{field: value})))


def test_agent_times_keep_the_plain_utc_rule_of_v2():
    # As in V2, the product's own times are JSONB text and are not bounded; only the isolation times are.
    status = agent(source_observed_at="9999-12-31T23:59:59.999999Z", agent_started_at="0001-01-01T00:00:00Z")
    assert (status.source_observed_at, status.agent_started_at) == ("9999-12-31T23:59:59.999999Z",
                                                                    "0001-01-01T00:00:00.000000Z")


@pytest.mark.parametrize("value", [True, False])
def test_catalog_claim_is_refused_as_in_v2(value):
    rejected(v3(agent_v3(catalog_available=value)), "edr_agent_catalog_claim_not_supported")


@pytest.mark.parametrize("state", SENSOR_STATES)
@pytest.mark.parametrize("code", SENSOR_CODES)
def test_sensor_error_code_is_allowed_only_with_lost_or_failed_as_in_v2(state, code):
    if state in ("lost", "failed"):
        assert agent(sensor_state=state, sensor_error_code=code).sensor_error_code == code
    else:
        rejected(v3(agent_v3(sensor_state=state, sensor_error_code=code)), "sensor_error_code_requires_lost_or_failed")
    assert agent(sensor_state=state).sensor_error_code is None


# The V3 twin of tests/unit/test_snapshot_v2_contracts.py::test_edr_agent_claims_and_closed_types_cannot_be_promoted
# (ADR 0004 section 9): V3 brings none of those claims back. rule_file_present is not a V3 field at all.
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
    # V3 only
    {"rule_file_present": True}, {"rule_file_present": False}, {"rule_file_present": None},
    {"rule_set_state": "loaded"}, {"rule_set_state": "protected"}, {"realtime_scan_state": "protected"},
    {"realtime_scan_state": "blocking"}, {"isolation_state": "isolated"}, {"isolation_state": "verified"},
    {"response_channel_state": "verified"}, {"previous_run_end": "crashed"}, {"service_config_state": "hardened"},
    {"engine_id": "edr-agent/çanary"}, {"behavior_rules_version": "rules_loaded"},
])
def test_v3_agent_claims_and_closed_types_cannot_be_promoted(changes):
    rejected(v3(agent_v3(**changes)))


PROTECTION = re.compile(r"protect|rules_loaded|realtime_protection", re.IGNORECASE)
WORDING = re.compile(r"protect|rules_loaded|realtime_protection|blocked|prevented|verified", re.IGNORECASE)


def test_no_v3_field_name_or_state_claims_protection():
    for model in (EdrAgentStatusV3, SnapshotEnvelopeV3, HostBasedFirewallStatus, TermivarStatus, AntivirusStatus):
        assert [name for name in model.model_fields if WORDING.search(name)] == [], model.__name__
    states = [*RULE_SET_STATES, *CAPABILITY_STATES, *RESPONSE_CHANNEL_STATES, *RESPONSE_ACTIONS, *ISOLATION_STATES,
              *SERVICE_CONFIG_STATES, *PREVIOUS_RUN_ENDS, *EDR_V3_COUNTER_KEYS]
    assert [value for value in states if WORDING.search(value)] == []
    # The labels stay fixed: every V3 value is self-reported and not verified.
    assert get_args(EdrAgentStatusV3.model_fields["source"].annotation) == ("self_reported",)
    assert get_args(EdrAgentStatusV3.model_fields["producer_verification"].annotation) == ("not_verified",)


@pytest.mark.parametrize("key", ["protection_active", "protected", "realtime_protection", "real_time_protection",
                                 "realtime_protection_state", "rules_loaded", "rules_loaded_count",
                                 "tamper_protection", "Protection", "PROTECTED_STATE", "self_protect"])
def test_keys_claiming_protection_are_refused_in_v3(key):
    assert PROTECTION.search(key)
    for value in (True, False, None, "running", 1):
        rejected(v3(agent_v3(**{key: value})))


# --- the V3 envelope

@pytest.mark.parametrize("schema_version", [True, False, "3", 3.0, 1, 2, 4, 0, -3, None])
def test_v3_schema_version_is_a_strict_3(schema_version):
    rejected(v3(schema_version=schema_version))


@pytest.mark.parametrize("changes", [
    {"sequence": True}, {"sequence": 0}, {"sequence": -1}, {"sequence": MAX_SNAPSHOT_SEQUENCE + 1},
    {"sequence": MAX_SEQUENCE}, {"sequence": 1.0}, {"sequence": "1"}, {"sequence": None},
    {"message_id": "not-a-uuid"}, {"message_id": "A" * 36}, {"message_id": "0000000A-0000-4000-8000-00000000000B"},
    {"message_id": None}, {"source_observed_at": "2026-11-26T10:00:00"}, {"source_observed_at": 1700000000},
    {"source_observed_at": "2026-11-26T10:00:00+03:00"}, {"metadata": {"secret": "MUST_NOT_ACCEPT"}},
    {"products": None}, {"products": {"edr_agent": {}}},
])
def test_v3_envelope_strict_types_and_closed_fields(changes):
    rejected(v3(**changes))


def test_v3_sequence_is_bounded_at_2_53_minus_1():
    for sequence in (1, MAX_SNAPSHOT_SEQUENCE):
        assert SnapshotEnvelopeV3.model_validate(v3(sequence=sequence)).sequence == sequence


@pytest.mark.parametrize("value,normalized", [
    ("1970-01-01T00:00:00Z", "1970-01-01T00:00:00.000000Z"),
    ("9998-12-31T23:59:59.999999Z", "9998-12-31T23:59:59.999999Z"),
    ("1969-12-31T24:00:00Z", "1970-01-01T00:00:00.000000Z"), (None, None),
])
def test_v3_envelope_source_observed_at_accepts_its_window_and_null(value, normalized):
    assert SnapshotEnvelopeV3.model_validate(v3(source_observed_at=value)).source_observed_at == normalized


@pytest.mark.parametrize("value", ["1969-12-31T23:59:59.999999Z", "0001-01-01T00:00:00Z", "9999-01-01T00:00:00Z",
                                   "9998-12-31T24:00:00Z", "9999-12-31T23:59:59.999999Z"])
def test_v3_envelope_source_observed_at_outside_the_window_is_refused(value):
    rejected(v3(source_observed_at=value), "source_observed_at_out_of_range")


# The V3 twin of tests/unit/test_snapshot_v2_contracts.py::test_v2_envelope_has_no_extra_fields (ADR 0004 section 9).
@pytest.mark.parametrize("field", ["tenant_id", "device_id", "protection_active", "rules_loaded", "command"])
def test_v3_envelope_has_no_extra_fields(field):
    rejected(v3(**{field: True}))


# The V3 twin of the policy gate's envelope refusals,
# tests/policy_contracts/test_surface_preservation.py::test_inventory_snapshot_rejects_policy_or_execution_fields.
@pytest.mark.parametrize("field", ["desired_policy", "command", "policy", "apply", "execution_authorized"])
def test_v3_snapshot_rejects_policy_or_execution_fields(field):
    for value in (False, True, None, {}, "apply"):
        body = {"schema_version": 3, "message_id": str(uuid4()), "sequence": 1, "products": [], field: value}
        with pytest.raises(ValidationError):
            SnapshotEnvelopeV3.model_validate(body)
        with pytest.raises(ValidationError):
            parse_snapshot(body)


def test_v3_carries_every_product_once():
    four = SnapshotEnvelopeV3.model_validate(v3(*v1_products(), agent_v3()))
    assert [product.product_id for product in four.products] == list(PRODUCT_IDS)
    assert [type(product) for product in four.products] == [HostBasedFirewallStatus, TermivarStatus, AntivirusStatus,
                                                           EdrAgentStatusV3]
    assert SnapshotEnvelopeV3.model_validate(v3(*v1_products())).products[2].product_id == "antivirus"
    assert SnapshotEnvelopeV3.model_validate(v3(products=[])).products == []
    rejected(v3(agent_v3(), agent_v3()), "duplicate_product")
    rejected(v3(v1_products()[0], v1_products()[0]), "duplicate_product")
    with pytest.raises(ValidationError) as five:
        SnapshotEnvelopeV3.model_validate(v3(*v1_products(), agent_v3(), v1_products()[0]))
    assert [error["type"] for error in five.value.errors()] == ["too_long"]
    assert SnapshotEnvelopeV3.model_json_schema()["properties"]["products"]["maxItems"] == 4
    rejected(v3({"product_id": "made-up-product"}))


# The V1/V2 product claims of tests/unit/test_snapshot_contracts.py stay refused in V3, whose other products are the
# V1 models themselves.
@pytest.mark.parametrize("product,changes", [
    (0, {"reported_running": 1}), (0, {"firewall_mode": "protected"}), (0, {"error_codes": ["raw secret error"]}),
    (0, {"error_codes": ["config_error", "config_error"]}), (0, {"producer_verification": "verified"}),
    (1, {"execution_available": True}), (1, {"target": "https://internal.example"}),
    (1, {"report_presence": "present"}), (2, {"status": "running"}), (2, {"catalog_available": True}),
    (2, {"execution_available": True}), (2, {"version": "active-av-1"}),
])
def test_v1_product_claims_stay_refused_in_v3(product, changes):
    products = v1_products()
    products[product].update(changes)
    rejected(v3(*products))


def test_the_v2_and_v3_agent_shapes_are_distinct():
    # A V2 agent status is not a V3 one (rule_file_present), and a V3 status is not a V2 one.
    rejected(v3(v2_agent_status()))
    with pytest.raises(ValidationError):
        SnapshotEnvelope.model_validate(v2(agent_v3()))
    v2_state = SnapshotEnvelope.model_validate(v2()).products[0].model_dump(mode="json")
    v3_state = SnapshotEnvelopeV3.model_validate(v3()).products[0].model_dump(mode="json")
    minimal = SnapshotEnvelopeV3.model_validate(v3({"product_id": "edr_agent"})).products[0].model_dump(mode="json")
    # The console tells the stored states apart by their key sets: V3 has rule_set_state and no rule_file_present.
    assert "rule_file_present" in v2_state and "rule_set_state" not in v2_state
    for state in (v3_state, minimal):
        assert "rule_set_state" in state and "rule_file_present" not in state
        assert set(state) == set(EdrAgentStatusV3.model_fields)


# --- the dispatch, and V1/V2 unchanged

def test_dispatch_chooses_the_envelope_by_schema_version():
    assert SNAPSHOT_MODELS == {1: SnapshotEnvelope, 2: SnapshotEnvelope, 3: SnapshotEnvelopeV3}
    assert type(parse_snapshot(json.loads(json.dumps(V1_FULL)))) is SnapshotEnvelope
    assert type(parse_snapshot(v2())) is SnapshotEnvelope
    assert type(parse_snapshot(v3())) is SnapshotEnvelopeV3
    # V3 may also carry only the V1 products: the version names the envelope, not the products.
    assert type(parse_snapshot(v3(*v1_products()))) is SnapshotEnvelopeV3
    assert parse_snapshot(v3()) == SnapshotEnvelopeV3.model_validate(v3())


@pytest.mark.parametrize("version", [True, False, 0, -1, 4, 1.0, 2.0, 3.0, "1", "2", "3", None, [3], {"v": 3}])
def test_dispatch_refuses_every_other_version_as_invalid_schema_version(version):
    assert errors(parse_snapshot, v3(schema_version=version)) == [
        ("invalid_schema_version", (), "invalid_schema_version")]


@pytest.mark.parametrize("value", [{key: item for key, item in v3().items() if key != "schema_version"}, {}, [],
                                   "snapshot", None, 3])
def test_dispatch_refuses_a_body_without_a_version(value):
    assert errors(parse_snapshot, value) == [("invalid_schema_version", (), "invalid_schema_version")]


@pytest.mark.parametrize("body", [
    {**v2(), "sequence": 0}, {**v2(), "message_id": "not-a-uuid"}, {**v2(), "schema_version": 1},
    v2(v2_agent_status(catalog_available=True)), v2(v2_agent_status(protection_active=True)),
    v2(v2_agent_status(), v2_agent_status()), {**v2(), "command": False}, v2(agent_v3()),
], ids=["sequence", "message-id", "edr-in-v1", "catalog", "protection", "duplicate", "command", "v3-agent-in-v2"])
def test_a_v1_or_v2_body_fails_through_the_dispatch_exactly_as_through_the_envelope(body):
    direct = errors(SnapshotEnvelope.model_validate, body)
    assert errors(parse_snapshot, body) == [(kind, ("SnapshotEnvelope", *location), message)
                                            for kind, location, message in direct]


@pytest.mark.parametrize("body,digest", [
    (V1_FULL, "2f1ead0b66ab96f74bb059967cd69757845c592af2a9c8be34ac852b25f51495"),
    (json.loads(V1_STAGE1), "b517d12011cf681a111d88f320da0eaae1001b90cd40a5b6bf357c47b43c128c"),
    (v2(), "7ac17abca2ed25cb0933044178d1bcad1461451b9f38ad3e933e2b599f2be5ec"),
], ids=["v1-full", "v1-stage1", "v2-reference"])
def test_v1_and_v2_digests_are_unchanged_through_the_dispatch(body, digest):
    # The digests pinned in tests/unit/test_snapshot_v2_contracts.py, computed before Snapshot V3 existed.
    model = parse_snapshot(json.loads(json.dumps(body)))
    assert type(model) is SnapshotEnvelope
    assert snapshot_digest(model) == hashlib.sha256(canonical_json(model)).hexdigest() == digest
    assert canonical_json(model) == canonical_json(SnapshotEnvelope.model_validate(json.loads(json.dumps(body))))


def test_reference_v3_body_has_a_pinned_canonical_form():
    model = parse_snapshot(v3())
    canonical = canonical_json(model)
    assert canonical == (
        b'{"message_id":"00000000-0000-4000-8000-000000000004","products":[{"agent_started_at":'
        b'"2026-11-26T08:00:00.500000Z","behavior_rules_version":"altay-behavior/v1","catalog_available":null,'
        b'"cmdline_unavailable":15,"command_line_sensor_state":"degraded","engine_id":"edr-agent/0.4.0",'
        b'"etw_events_lost":13,"events_degraded":6,"events_discarded":5,"events_evicted":4,"events_queue_dropped":0,'
        b'"events_skipped":3,"events_unmapped":2,"events_write_failed":1,"file_change_gaps":14,'
        b'"file_change_sensor_state":"not_available","heartbeat_interval_seconds":60,'
        b'"isolation_checked_at":"2026-11-26T09:59:00.000000Z","isolation_state":"inactive","isolation_until":null,'
        b'"last_action_seq":null,"outbox_backlog":7,"persistence_watch_state":"running","previous_run_end":"clean",'
        b'"producer_verification":"not_verified","product_id":"edr_agent","quarantine_items":0,'
        b'"realtime_scan_state":"running","response_actions_enabled":["scan_path"],'
        b'"response_channel_state":"awaiting_tenant_binding","response_key_ids":[],'
        b'"rule_set_id":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","rule_set_state":"compiled",'
        b'"scan_cache_hits":12,"scan_jobs_dropped":11,"scans_completed":8,"scans_detected":9,"scans_no_verdict":10,'
        b'"sensor_error_code":null,"sensor_state":"started","service_config_state":"as_installed",'
        b'"source":"self_reported","source_observed_at":"2026-11-26T10:00:00.000000Z","status":"running",'
        b'"version":"0.4.0"}],"schema_version":3,"sequence":7,"source_observed_at":"2026-11-26T10:00:00.000000Z"}')
    assert snapshot_digest(model) == hashlib.sha256(canonical).hexdigest() == (
        "e19b3e464626bda89f757ae921e7fee6d478602e75e48cc04c6fae9825386454")
    # Key order is irrelevant, and a V2 body with the same identity is different content.
    reordered = json.loads(json.dumps(dict(reversed(list(v3(dict(reversed(list(agent_v3().items())))).items())))))
    assert snapshot_digest(parse_snapshot(reordered)) == snapshot_digest(model)
    same_identity = v2(*v1_products(), message_id=MESSAGE_ID)
    assert snapshot_digest(parse_snapshot(same_identity)) != snapshot_digest(parse_snapshot(v3(*v1_products())))


def test_largest_v3_snapshot_fits_the_body_and_payload_bounds():
    error_codes = list(get_args(contracts.ErrorCode))[:16]
    keys = sorted(hashlib.sha256(bytes([index])).hexdigest() for index in range(MAX_RESPONSE_KEY_IDS))
    products = [
        {"product_id": "hostbasedfirewall", "status": "unavailable", "installed": False, "reported_running": False,
         "reported_stale": True, "firewall_mode": "unknown", "error_codes": error_codes, "catalog_available": False,
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
        agent_v3(version="E" * 64, engine_id="G" * 128, sensor_state="failed", sensor_error_code="session_start_failed",
                 source_observed_at="2026-11-24T10:00:00.123456Z", agent_started_at="2026-11-24T10:00:00.123456Z",
                 rule_set_state="unreadable", realtime_scan_state="not_available",
                 file_change_sensor_state="not_available", command_line_sensor_state="not_available",
                 persistence_watch_state="not_available", response_channel_state="awaiting_tenant_binding",
                 response_actions_enabled=sorted(RESPONSE_ACTIONS), response_key_ids=keys,
                 last_action_seq=MAX_SNAPSHOT_SEQUENCE, isolation_state="inactive",
                 isolation_until="2026-11-24T10:00:00.123456Z", isolation_checked_at="2026-11-24T10:00:00.123456Z",
                 quarantine_items=MAX_SNAPSHOT_SEQUENCE, service_config_state="as_installed",
                 previous_run_end="first_start", heartbeat_interval_seconds=MAX_HEARTBEAT_INTERVAL_SECONDS,
                 behavior_rules_version="altay-behavior/v999999",
                 **{name: MAX_SNAPSHOT_SEQUENCE for name in EDR_V3_COUNTER_KEYS}),
    ]
    body = v3(*products, sequence=MAX_SNAPSHOT_SEQUENCE)
    model = SnapshotEnvelopeV3.model_validate(body)
    assert len(canonical_json(model)) < MAX_SNAPSHOT_BYTES // 2
    # The request boundary (16 KiB raw body) and the stored payload CHECK (ck_product_payload_bytes, 16 KiB).
    assert len(json.dumps(body).encode("utf-8")) < MAX_SNAPSHOT_BYTES // 2
    for product in model.products:
        assert len(json.dumps(product.model_dump(mode="json")).encode("utf-8")) < 16384 // 4
