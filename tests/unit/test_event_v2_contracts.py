"""altay-edr-event/v2 (ADR 0004 section 1.2): the nine kinds and their closed sets, the cross-field rules,
privacy (ADR 1.4), the v2 batch envelope, the schema_version dispatch and the canonical form.

Pure contract tests. v1 is tested, unchanged, in tests/unit/test_event_contracts.py; this file also proves that
a v1 body keeps its result, bytes and digest through the version dispatch. Ingestion through the real API and
PostgreSQL, and migration 0005, are in tests/integration/test_stage3_contracts.py.
"""
import hashlib
import json
import re
from typing import get_args
from uuid import uuid4

from pydantic import ValidationError
import pytest

from security_platform import event_contracts
from security_platform.contracts import MAX_SEQUENCE
from security_platform.event_contracts import (AGENT_STATE_CODES, AGENT_STATE_SUBJECTS, AGENT_STATES, BEHAVIOR_RULES,
    COMMAND_LINE_SOURCES, COVERAGE_REASONS, COVERAGE_SOURCES, EVENT_BATCH_MODELS, EVENT_FIELDS, EVENT_FIELDS_V1,
    EVENT_KINDS, EVENT_KINDS_V1, EVENT_VIEW_FIELDS, EVENT_MODELS, EVENT_MODELS_V2, EVENT_SCHEMA, EVENT_SCHEMA_V2, MAX_BATCH_EVENTS,
    MAX_EVENT_BATCH_BYTES, MAX_EVENT_SEQ, MAX_SCAN_HITS, MAX_STORED_EVENT_BYTES, PERSISTENCE_CHANGES,
    PERSISTENCE_LOCATIONS, PERSISTENCE_SCOPES, SCAN_HIT_SEVERITIES, SCAN_TRIGGERS, TAMPER_DETAILS, TAMPER_SIGNALS,
    AgentState, BehaviorMatch, CoverageGap, EventBatch, EventBatchTooLarge, EventBatchV2, PersistenceChange,
    ProcessStarted, ProcessStartedV2, ProcessStopped, ProcessStoppedV2, ScanDetected, ScanHit, SensorState,
    TamperSignal, canonical_event_batch, event_batch_digest, parse_event_batch, stored_event_bytes)


MASKED = r"\Device\HarddiskVolume3\Users\*\Downloads\setup.exe"
PARENT = r"\Device\HarddiskVolume3\Windows\explorer.exe"
DIGEST = "0123456789abcdef" * 4
RULE_SET = "a" * 64
ENTRY = "b" * 64
CREATED = "2026-11-26T09:59:59.500000Z"
WIDE = "\U0001F600"  # four UTF-8 bytes, an ordinary symbol (category So)
COMMON = ("kind", "event_seq", "observed_at")


def started(seq=1, **changes):
    return {"kind": "process_started", "event_seq": seq, "observed_at": "2026-11-26T10:00:00Z", "pid": 4321,
            "parent_pid": 1234, "session_id": 1, "image": MASKED, "create_time": CREATED,
            "parent_create_time": "2026-11-26T08:00:00Z", **changes}


def stopped(seq=2, **changes):
    return {"kind": "process_stopped", "event_seq": seq, "observed_at": "2026-11-26T10:00:01Z", "pid": 4321,
            "exit_code": 0, "image": "setup.exe", "create_time": CREATED, **changes}


def sensor(seq=3, **changes):
    return {"kind": "sensor_state", "event_seq": seq, "observed_at": "2026-11-26T10:00:02Z", "state": "lost",
            "error_code": "session_in_use", **changes}


def scan(seq=4, **changes):
    return {"kind": "scan_detected", "event_seq": seq, "observed_at": "2026-11-26T10:00:03Z",
            "trigger": "process_start", "path": MASKED, "size": 68, "sha256": DIGEST, "rule_set_id": RULE_SET,
            "hits": [{"rule": "Sample_Rule", "severity": "medium"}], "omitted_hits": 0, "pid": 4321,
            "create_time": CREATED, "action_id": None, **changes}


def behavior(seq=5, **changes):
    return {"kind": "behavior_match", "event_seq": seq, "observed_at": "2026-11-26T10:00:04Z",
            "rule": "encoded_powershell", "rule_version": 1, "pid": 4321, "create_time": CREATED, "image": MASKED,
            "parent_image": PARENT, "found_at_start": False, "command_line_source": "kernel_logger", **changes}


def persistence(seq=6, **changes):
    return {"kind": "persistence_change", "event_seq": seq, "observed_at": "2026-11-26T10:00:05Z",
            "location": "run_key", "scope": "user", "change": "added", "entry_id": ENTRY, "target_image": MASKED,
            "found_at_start": False, **changes}


def agent(seq=7, **changes):
    return {"kind": "agent_state", "event_seq": seq, "observed_at": "2026-11-26T10:00:06Z", "subject": "service",
            "state": "started", "code": "first_start", "rule_set_id": None, **changes}


def tamper(seq=8, **changes):
    return {"kind": "tamper_signal", "event_seq": seq, "observed_at": "2026-11-26T10:00:07Z",
            "signal": "event_log_cleared", "detail": "security", **changes}


def gap(seq=9, **changes):
    return {"kind": "coverage_gap", "event_seq": seq, "observed_at": "2026-11-26T10:00:08Z",
            "source": "process_sensor", "reason": "etw_events_lost", "lost": 12, **changes}


# In EVENT_KINDS order.
FACTORIES = (started, stopped, sensor, scan, behavior, persistence, agent, tamper, gap)
FACTORY = dict(zip(EVENT_KINDS, FACTORIES))
V2_ONLY = FACTORIES[3:]
V2_ONLY_KINDS = EVENT_KINDS[3:]


def v1_started(seq=1, **changes):
    return {"kind": "process_started", "event_seq": seq, "observed_at": "2026-11-26T10:00:00Z", "pid": 4321,
            "parent_pid": 1234, "session_id": 1, "image": MASKED, **changes}


def v1_stopped(seq=2, **changes):
    return {"kind": "process_stopped", "event_seq": seq, "observed_at": "2026-11-26T10:00:01Z", "pid": 4321,
            "exit_code": 0, "image": "setup.exe", **changes}


V1_FACTORIES = (v1_started, v1_stopped, sensor)


def batch(*events, **changes):
    return {"schema_version": 2, "batch_id": str(uuid4()), "batch_sequence": 1,
            "events": list(events) or [factory() for factory in FACTORIES], **changes}


def v1_batch(*events, **changes):
    return {"schema_version": 1, "batch_id": str(uuid4()), "batch_sequence": 1,
            "events": list(events) or [factory() for factory in V1_FACTORIES], **changes}


def accepted(*events, **changes):
    return EventBatchV2.model_validate(batch(*events, **changes))


def refused(*events, reason=None, **changes):
    with pytest.raises(ValidationError) as caught:
        EventBatchV2.model_validate(batch(*events, **changes))
    if reason is not None:
        assert reason in str(caught.value)


def errors(function, value):
    with pytest.raises(ValidationError) as caught:
        function(value)
    return [(error["type"], error["loc"], error["msg"]) for error in caught.value.errors()]


# --- pinned names and closed sets

def test_versions_kinds_and_models_are_pinned():
    assert (EVENT_SCHEMA, EVENT_SCHEMA_V2) == ("altay-edr-event/v1", "altay-edr-event/v2")
    assert EVENT_KINDS_V1 == ("process_started", "process_stopped", "sensor_state")
    assert EVENT_KINDS == ("process_started", "process_stopped", "sensor_state", "scan_detected", "behavior_match",
                           "persistence_change", "agent_state", "tamper_signal", "coverage_gap")
    assert tuple(EVENT_MODELS) == EVENT_KINDS_V1 and tuple(EVENT_MODELS_V2) == EVENT_KINDS
    assert tuple(EVENT_MODELS_V2.values()) == (ProcessStartedV2, ProcessStoppedV2, SensorState, ScanDetected,
                                               BehaviorMatch, PersistenceChange, AgentState, TamperSignal, CoverageGap)
    # The v2 event union holds exactly these models, in this order.
    assert get_args(get_args(event_contracts.DeviceEventV2)[0]) == tuple(EVENT_MODELS_V2.values())
    # sensor_state is unchanged in v2: the v2 union holds the v1 model itself.
    assert EVENT_MODELS_V2["sensor_state"] is EVENT_MODELS["sensor_state"] is SensorState
    for kind, model in EVENT_MODELS_V2.items():
        assert get_args(model.model_fields["kind"].annotation) == (kind,)
    assert EVENT_BATCH_MODELS == {1: EventBatch, 2: EventBatchV2}
    # The v1 process models are untouched: v2 adds separate classes.
    assert set(ProcessStarted.model_fields) == {*COMMON, "pid", "parent_pid", "session_id", "image"}
    assert set(ProcessStopped.model_fields) == {*COMMON, "pid", "exit_code", "image"}


CLOSED_SETS = {
    "SCAN_TRIGGERS": ("process_start", "startup_scan", "file_change", "remote_scan", "persistence_target"),
    "SCAN_HIT_SEVERITIES": ("low", "medium", "high"),
    "BEHAVIOR_RULES": ("encoded_powershell", "powershell_download_cradle", "certutil_download_or_decode",
                       "mshta_remote_or_script", "regsvr32_scriptlet", "rundll32_script", "bitsadmin_transfer",
                       "shadow_copy_deletion", "defender_tampering_command", "event_log_clearing_command"),
    "COMMAND_LINE_SOURCES": ("kernel_logger", "process_query"),
    "PERSISTENCE_LOCATIONS": ("run_key", "run_once_key", "service", "scheduled_task", "startup_folder"),
    "PERSISTENCE_SCOPES": ("machine", "user"),
    "PERSISTENCE_CHANGES": ("added", "modified", "removed"),
    "AGENT_STATE_CODES": ("first_start", "clean_stop", "unclean_stop"),
    "TAMPER_SIGNALS": ("service_config_changed", "service_dacl_changed", "data_dir_acl_changed",
                       "isolation_filters_missing", "isolation_filters_disabled", "isolation_released_locally",
                       "event_log_cleared", "response_trust_changed", "previous_run_unclean", "quarantine_changed"),
    "TAMPER_DETAILS": ("security", "system"),
    "COVERAGE_SOURCES": ("process_sensor", "file_change_sensor", "command_line_sensor", "agent_records"),
    "COVERAGE_REASONS": ("etw_events_lost", "usn_journal_reset", "usn_entries_deleted", "volume_unmonitored",
                         "queue_overflow"),
}


@pytest.mark.parametrize("name", sorted(CLOSED_SETS))
def test_closed_sets_are_pinned(name):
    assert getattr(event_contracts, name) == CLOSED_SETS[name]


def test_agent_state_subjects_and_their_states_are_pinned_in_order():
    assert list(AGENT_STATE_SUBJECTS.items()) == [
        ("service", ("started", "stopping")),
        ("rule_set", ("compiled", "missing", "invalid", "unreadable")),
        ("realtime_scan", ("running", "degraded", "stopped", "failed")),
        ("file_change_sensor", ("running", "degraded", "stopped", "failed", "not_available")),
        ("command_line_sensor", ("running", "degraded", "stopped", "failed", "not_available")),
        ("persistence_watch", ("running", "degraded", "stopped", "failed", "not_available", "baseline_created")),
        ("response_channel", ("ready", "not_configured", "awaiting_tenant_binding", "journal_invalid")),
        ("isolation", ("active", "renewed", "released", "expired", "released_locally", "reverted_no_contact",
                       "reapplied")),
        ("quarantine", ("restored_locally",)),
    ]
    # AGENT_STATES is every state of any subject, once, in first-seen order.
    assert AGENT_STATES == tuple(dict.fromkeys(state for states in AGENT_STATE_SUBJECTS.values() for state in states))
    assert len(AGENT_STATES) == len(set(AGENT_STATES)) == 24


def literal_values(annotation):
    """The values of a Literal annotation, or of the Literal member of ``Literal[...] | None``."""
    values = []
    for member in (get_args(annotation) if type(None) in get_args(annotation) else (annotation,)):
        if member is not type(None):
            values.extend(get_args(member))
    return tuple(values)


@pytest.mark.parametrize("model,field,values", [
    (ScanDetected, "trigger", SCAN_TRIGGERS), (ScanHit, "severity", SCAN_HIT_SEVERITIES),
    (BehaviorMatch, "rule", BEHAVIOR_RULES), (BehaviorMatch, "command_line_source", COMMAND_LINE_SOURCES),
    (PersistenceChange, "location", PERSISTENCE_LOCATIONS), (PersistenceChange, "scope", PERSISTENCE_SCOPES),
    (PersistenceChange, "change", PERSISTENCE_CHANGES), (AgentState, "subject", tuple(AGENT_STATE_SUBJECTS)),
    (AgentState, "state", AGENT_STATES), (AgentState, "code", AGENT_STATE_CODES),
    (TamperSignal, "signal", TAMPER_SIGNALS), (TamperSignal, "detail", TAMPER_DETAILS),
    (CoverageGap, "source", COVERAGE_SOURCES), (CoverageGap, "reason", COVERAGE_REASONS),
    (SensorState, "state", ("started", "lost", "failed", "stopped")),
], ids=["trigger", "severity", "behavior-rule", "command-line-source", "location", "scope", "change", "subject",
        "state", "code", "signal", "detail", "gap-source", "gap-reason", "sensor-state"])
def test_every_closed_field_is_typed_by_its_single_source_tuple(model, field, values):
    assert literal_values(model.model_fields[field].annotation) == values


def test_event_fields_are_the_pinned_v1_v2_superset():
    assert EVENT_FIELDS == {
        "process_started": ("pid", "parent_pid", "session_id", "image", "create_time", "parent_create_time"),
        "process_stopped": ("pid", "exit_code", "image", "create_time"),
        "sensor_state": ("state", "error_code"),
        "scan_detected": ("trigger", "path", "size", "sha256", "rule_set_id", "hits", "omitted_hits", "pid",
                          "create_time", "action_id"),
        "behavior_match": ("rule", "rule_version", "pid", "create_time", "image", "parent_image", "found_at_start",
                           "command_line_source"),
        "persistence_change": ("location", "scope", "change", "entry_id", "target_image", "found_at_start"),
        "agent_state": ("subject", "state", "code", "rule_set_id"),
        "tamper_signal": ("signal", "detail"),
        "coverage_gap": ("source", "reason", "lost"),
    }
    assert tuple(EVENT_FIELDS) == EVENT_KINDS
    # Each v2 model declares exactly the fields of its kind, in this order, after the common ones; the v1
    # fields come first and are unchanged.
    for kind, model in EVENT_MODELS_V2.items():
        assert tuple(model.model_fields) == ("event_seq", "observed_at", "kind", *EVENT_FIELDS[kind]), kind
    for kind, fields in EVENT_FIELDS_V1.items():
        assert EVENT_FIELDS[kind][:len(fields)] == fields


def test_event_view_fields_rename_only_the_coverage_gap_source():
    # P1 brief, section 5 addendum: a timeline item carries the trust label `source`, so coverage_gap's own source
    # is shown as gap_source there. The wire field and the stored payload keep `source`.
    assert EVENT_VIEW_FIELDS == {**EVENT_FIELDS, "coverage_gap": ("gap_source", "reason", "lost")}
    assert tuple(EVENT_VIEW_FIELDS) == EVENT_KINDS
    assert "source" in CoverageGap.model_fields and "gap_source" not in CoverageGap.model_fields
    item_keys = {"event_seq", "kind", "observed_at", "received_at", "source", "producer_verification"}
    for kind, names in EVENT_VIEW_FIELDS.items():
        # One view name per payload field, position by position, and none collides with a key of the item itself.
        assert len(set(names)) == len(names) == len(EVENT_FIELDS[kind]), kind
        assert not item_keys & set(names), kind


REQUIRED = {
    "process_started": ("pid", "parent_pid", "session_id", "image", "create_time"),
    "process_stopped": ("pid",),
    "sensor_state": ("state",),
    "scan_detected": ("trigger", "path", "size", "sha256", "rule_set_id", "hits", "omitted_hits"),
    "behavior_match": ("rule", "rule_version", "pid", "create_time", "image", "found_at_start",
                       "command_line_source"),
    "persistence_change": ("location", "scope", "change", "entry_id", "found_at_start"),
    "agent_state": ("subject", "state"),
    "tamper_signal": ("signal",),
    "coverage_gap": ("source", "reason"),
}
# A base event of each kind whose optional fields may all be null.
NULL_SAFE = {"tamper_signal": {"signal": "service_config_changed", "detail": None}}


def test_required_and_optional_fields_are_pinned():
    for kind, model in EVENT_MODELS_V2.items():
        assert set(model.model_fields) == {*COMMON, *EVENT_FIELDS[kind]}
        required = {name for name, field in model.model_fields.items() if field.is_required()}
        assert required == {*COMMON, *REQUIRED[kind]}, kind
        # Every other field is "X | None = None", as v1 writes ProcessStopped.exit_code.
        assert all(model.model_fields[name].default is None for name in set(model.model_fields) - required), kind


@pytest.mark.parametrize("kind", EVENT_KINDS)
def test_every_v2_kind_validates_with_exactly_its_fields(kind):
    model = accepted(FACTORY[kind]())
    assert type(model.events[0]) is EVENT_MODELS_V2[kind]
    [event] = json.loads(canonical_event_batch(model))["events"]
    assert set(event) == {*COMMON, *EVENT_FIELDS[kind]}


def test_one_batch_carries_all_nine_kinds():
    model = EventBatchV2.model_validate(batch())
    assert [type(event) for event in model.events] == list(EVENT_MODELS_V2.values())
    assert set(EventBatchV2.model_fields) == {"schema_version", "batch_id", "batch_sequence", "events"}


@pytest.mark.parametrize("kind", EVENT_KINDS)
def test_required_fields_cannot_be_null_or_missing(kind):
    factory = FACTORY[kind]
    for field in (*COMMON, *REQUIRED[kind]):
        refused(factory(**{field: None}))
        refused({key: value for key, value in factory().items() if key != field})


@pytest.mark.parametrize("kind", EVENT_KINDS)
def test_omitted_optional_fields_are_stored_as_explicit_null(kind):
    event = FACTORY[kind](**NULL_SAFE.get(kind, {}))
    optional = [name for name in EVENT_FIELDS[kind] if name not in REQUIRED[kind]]
    trimmed = {key: value for key, value in event.items() if key not in optional}
    explicit = {**event, **{name: None for name in optional}}
    identity = str(uuid4())
    digests = set()
    for body in (trimmed, explicit):
        model = accepted(body, batch_id=identity)
        [stored] = json.loads(canonical_event_batch(model))["events"]
        assert set(stored) == {*COMMON, *EVENT_FIELDS[kind]}
        assert all(stored[name] is None for name in optional)
        digests.add(event_batch_digest(model))
    assert len(digests) == 1


# --- numbers

@pytest.mark.parametrize("factory,field", [(started, "pid"), (started, "parent_pid"), (started, "session_id"),
                                           (stopped, "pid"), (stopped, "exit_code"), (scan, "pid"),
                                           (behavior, "pid")])
def test_process_numbers_are_strict_unsigned_32_bit(factory, field):
    for value in (0, 2**32 - 1):
        assert getattr(accepted(factory(**{field: value})).events[0], field) == value
    for value in (-1, 2**32, True, False, 1.0, "1", [1]):
        refused(factory(**{field: value}))


@pytest.mark.parametrize("factory,field", [(scan, "size"), (gap, "lost")])
def test_sizes_and_lost_counts_are_strict_safe_integers(factory, field):
    for value in (0, 1, 2**53 - 1):
        assert getattr(accepted(factory(**{field: value})).events[0], field) == value
    for value in (-1, 2**53, 2**63, True, False, 1.0, "1", float("nan"), float("inf")):
        refused(factory(**{field: value}))


def test_omitted_hits_and_rule_version_are_bounded_strict_integers():
    for value in (0, 4096):
        assert accepted(scan(omitted_hits=value)).events[0].omitted_hits == value
    for value in (-1, 4097, True, 1.0, "0", None):
        refused(scan(omitted_hits=value))
    for value in (1, 65535):
        assert accepted(behavior(rule_version=value)).events[0].rule_version == value
    for value in (0, -1, 65536, True, 1.0, "1", None):
        refused(behavior(rule_version=value))


@pytest.mark.parametrize("factory,field,base", [
    (scan, "sha256", {}), (scan, "rule_set_id", {}), (persistence, "entry_id", {}),
    (agent, "rule_set_id", {"subject": "rule_set", "state": "compiled", "code": None}),
])
def test_digest_fields_are_64_lowercase_hex(factory, field, base):
    for value in ("0" * 64, "f" * 64, DIGEST):
        assert getattr(accepted(factory(**base, **{field: value})).events[0], field) == value
    for value in ("A" * 64, DIGEST.upper(), "a" * 63, "a" * 65, "g" * 64, "a" * 64 + "\n", " " + "a" * 63, "",
                  7, ["a" * 64]):
        refused(factory(**base, **{field: value}))


# --- paths, using the v1 validators

UNMASKED = [r"\Device\HarddiskVolume3\Users\ahmet\Downloads\a.exe", "C:/Users/ahmet/a.exe",
            r"C:\USERS\ahmet\a.exe", r"\Users\x\a.exe", r"\Device\HarddiskVolume3\Users\ahmet:stream\a.exe"]
BAD_TEXT = ["", "\\" + "a" * 1024, "a\x00.exe", "a\n.exe", "a\u202e.exe", "a\u200b.exe", "a\ufeff.exe", 7]


@pytest.mark.parametrize("factory,field", [(started, "image"), (scan, "path"), (behavior, "image"),
                                           (behavior, "parent_image"), (persistence, "target_image")])
def test_every_masked_path_uses_the_v1_rules(factory, field):
    for value in (MASKED, "\\" + "a" * 1023, r"\Device\HarddiskVolume3\Users\*:payload.exe", "Registry", r"\Users",
                  r"C:\Users\*\AppData\Local\çalış.exe", "C:/Users/*/a.exe"):
        assert getattr(accepted(factory(**{field: value})).events[0], field) == value
    for value in UNMASKED:
        refused(factory(**{field: value}), reason="unmasked_user_folder")
    for value in BAD_TEXT:
        refused(factory(**{field: value}))


def test_the_v2_stop_image_is_the_v1_short_name():
    for value in ("setup.exe", "araç.exe", "a" * 260, "\ufffd=45:A.exe", None):
        assert accepted(stopped(image=value)).events[0].image == value
    for value in ("a\\b.exe", "a/b.exe", MASKED, "a" * 261, "", "a\x00.exe", "a\u202e.exe"):
        refused(stopped(image=value))


# --- times: the observed_at rules for create_time and parent_create_time

TIME_FIELDS = [(started, "create_time"), (started, "parent_create_time"), (stopped, "create_time"),
               (scan, "create_time"), (behavior, "create_time")]
TIME_IDS = ["started-create", "started-parent", "stopped-create", "scan-create", "behavior-create"]


@pytest.mark.parametrize("factory,field", TIME_FIELDS, ids=TIME_IDS)
@pytest.mark.parametrize("value,normalized", [
    ("2026-11-26T10:00:00Z", "2026-11-26T10:00:00.000000Z"),
    ("2026-11-26T10:00:00.1Z", "2026-11-26T10:00:00.100000Z"),
    ("2026-11-26T10:00:00.123456Z", "2026-11-26T10:00:00.123456Z"),
    ("2026-12-31T24:00:00Z", "2027-01-01T00:00:00.000000Z"),
    ("1970-01-01T00:00:00Z", "1970-01-01T00:00:00.000000Z"),
    # The bound applies to the normalized instant.
    ("1969-12-31T24:00:00Z", "1970-01-01T00:00:00.000000Z"),
    ("9998-12-31T23:59:59.999999Z", "9998-12-31T23:59:59.999999Z"),
])
def test_process_times_are_canonical_utc_text_in_the_observed_at_window(factory, field, value, normalized):
    model = accepted(factory(**{field: value}))
    assert getattr(model.events[0], field) == normalized
    assert json.loads(canonical_event_batch(model))["events"][0][field] == normalized


@pytest.mark.parametrize("factory,field", TIME_FIELDS, ids=TIME_IDS)
@pytest.mark.parametrize("value", [
    "1969-12-31T23:59:59.999999Z", "0001-01-01T00:00:00Z", "9999-01-01T00:00:00Z", "9998-12-31T24:00:00Z",
    "9999-12-31T23:59:59.999999Z",
    # A zero FILETIME read as a time.
    "1601-01-01T00:00:00Z",
])
def test_process_times_outside_1970_to_9999_are_refused_with_their_own_code(factory, field, value):
    refused(factory(**{field: value}), reason=f"{field}_out_of_range")


@pytest.mark.parametrize("factory,field", TIME_FIELDS, ids=TIME_IDS)
@pytest.mark.parametrize("value", [
    "2026-11-26T10:00:00", "2026-11-26T10:00:00+00:00", "2026-11-26T13:00:00+03:00", "2026-11-26T10:00:00.1234567Z",
    "2026-11-26T10:00:00.Z", "2026-11-26t10:00:00Z", "2026-11-26T10:00:00z", "2026-11-26 10:00:00Z",
    "2026-02-30T10:00:00Z", "2026-11-26T24:00:00.000001Z", "2026-11-26T10:00:60Z", 1764150000, 1764150000.5, "",
])
def test_process_times_refuse_other_forms(factory, field, value):
    refused(factory(**{field: value}))


@pytest.mark.parametrize("factory", V2_ONLY, ids=V2_ONLY_KINDS)
def test_observed_at_keeps_the_v1_rule_in_every_new_kind(factory):
    assert accepted(factory(observed_at="2026-11-26T10:00:00Z")).events[0].observed_at == "2026-11-26T10:00:00.000000Z"
    refused(factory(observed_at="9999-01-01T00:00:00Z"), reason="observed_at_out_of_range")
    refused(factory(observed_at="1969-12-31T23:59:59Z"), reason="observed_at_out_of_range")
    refused(factory(observed_at="2026-11-26T10:00:00+00:00"))


# --- closed values of each new kind

@pytest.mark.parametrize("factory,field,values", [
    (scan, "trigger", SCAN_TRIGGERS), (behavior, "rule", BEHAVIOR_RULES),
    (behavior, "command_line_source", COMMAND_LINE_SOURCES), (persistence, "location", PERSISTENCE_LOCATIONS),
    (persistence, "scope", PERSISTENCE_SCOPES), (persistence, "change", PERSISTENCE_CHANGES),
    (gap, "source", COVERAGE_SOURCES), (gap, "reason", COVERAGE_REASONS),
], ids=["trigger", "behavior-rule", "command-line-source", "location", "scope", "change", "gap-source",
        "gap-reason"])
def test_closed_fields_accept_exactly_their_set(factory, field, values):
    for value in values:
        assert getattr(accepted(factory(**{field: value})).events[0], field) == value
    for value in (values[0].upper(), values[0] + " ", " " + values[0], values[0].replace("_", "-") + "x", "unknown",
                  "", None, 1, True, [values[0]]):
        refused(factory(**{field: value}))


def hit_list(count, severity="low"):
    return [{"rule": f"Sample_Rule_{index}", "severity": severity} for index in range(count)]


def test_scan_hits_hold_one_to_eight_distinct_rules():
    assert MAX_SCAN_HITS == 8
    for count in (1, MAX_SCAN_HITS):
        assert [hit.rule for hit in accepted(scan(hits=hit_list(count))).events[0].hits] == [
            f"Sample_Rule_{index}" for index in range(count)]
    for count in (0, MAX_SCAN_HITS + 1):
        refused(scan(hits=hit_list(count)))
    refused(scan(hits=hit_list(1) * 2), reason="duplicate_hit_rule")
    refused(scan(hits=[{"rule": "Sample_Rule", "severity": "low"}, {"rule": "Sample_Rule", "severity": "high"}]),
            reason="duplicate_hit_rule")
    for value in ({"rule": "Sample_Rule", "severity": "low"}, None, "Sample_Rule", [None], [["Sample_Rule", "low"]]):
        refused(scan(hits=value))


@pytest.mark.parametrize("severity", SCAN_HIT_SEVERITIES)
def test_each_hit_severity_is_accepted(severity):
    assert accepted(scan(hits=hit_list(1, severity))).events[0].hits[0].severity == severity


@pytest.mark.parametrize("severity", ["critical", "info", "Medium", "unknown", "", None, 1])
def test_other_hit_severities_are_refused(severity):
    refused(scan(hits=hit_list(1, severity)))


@pytest.mark.parametrize("rule", ["A", "a" * 64, "Sample_Rule.v-2", "0_leading_digit", "R1"])
def test_hit_rule_names_accept_the_pattern(rule):
    assert accepted(scan(hits=[{"rule": rule, "severity": "low"}])).events[0].hits[0].rule == rule


@pytest.mark.parametrize("rule", ["", "_rule", ".rule", "-rule", "a" * 65, "rule name", "rule\n", "kural_ç",
                                  "rule/1", "rule:1", "rule\u200b", "\uff21", 7, None])
def test_hit_rule_names_refuse_other_text(rule):
    refused(scan(hits=[{"rule": rule, "severity": "low"}]))


@pytest.mark.parametrize("extra", [{"description": "sample text"}, {"strings": ["$a"]}, {"meta": {}}, {"tags": []},
                                   {"namespace": "default"}, {"matched_bytes": "4d5a"}])
def test_a_hit_carries_only_its_rule_and_severity(extra):
    assert set(ScanHit.model_fields) == {"rule", "severity"}
    refused(scan(hits=[{"rule": "Sample_Rule", "severity": "low", **extra}]))


def test_scan_process_identity_and_action_are_optional():
    model = accepted(scan(4, pid=None, create_time=None), scan(5, create_time=None), scan(6))
    assert [(event.pid, event.create_time) for event in model.events] == [(None, None), (4321, None),
                                                                         (4321, CREATED)]
    # A process creation time names nothing without its pid.
    refused(scan(pid=None), reason="create_time_requires_pid")


def test_scan_action_id_is_canonical_uuid_text_for_any_trigger():
    identity = str(uuid4())
    for trigger in SCAN_TRIGGERS:
        assert accepted(scan(trigger=trigger, action_id=identity)).events[0].action_id == identity
        assert accepted(scan(trigger=trigger, action_id=None)).events[0].action_id is None
    for value in (identity.upper(), uuid4().hex, "{" + identity[:34] + "}", "not-a-uuid-but-thirty-six-characters",
                  "", 7, True):
        refused(scan(action_id=value))


@pytest.mark.parametrize("factory", [behavior, persistence], ids=["behavior_match", "persistence_change"])
def test_found_at_start_is_a_strict_boolean(factory):
    for value in (True, False):
        assert accepted(factory(found_at_start=value)).events[0].found_at_start is value
    for value in (1, 0, "true", "false", None, [True]):
        refused(factory(found_at_start=value))


def test_behavior_match_optional_parent_image_and_its_required_process_identity():
    assert accepted(behavior(parent_image=None)).events[0].parent_image is None
    for field in ("pid", "create_time", "image"):
        refused(behavior(**{field: None}))


def test_persistence_target_image_is_optional():
    for change in PERSISTENCE_CHANGES:
        assert accepted(persistence(change=change, target_image=None)).events[0].target_image is None


@pytest.mark.parametrize("subject", list(AGENT_STATE_SUBJECTS))
@pytest.mark.parametrize("state", AGENT_STATES)
def test_agent_state_accepts_exactly_the_allowed_subject_state_pairs(subject, state):
    event = agent(subject=subject, state=state, code=None)
    if state in AGENT_STATE_SUBJECTS[subject]:
        assert (accepted(event).events[0].subject, accepted(event).events[0].state) == (subject, state)
    else:
        refused(event, reason="state_not_allowed_for_subject")


@pytest.mark.parametrize("code", AGENT_STATE_CODES)
def test_a_code_is_allowed_only_for_service_started(code):
    assert accepted(agent(code=code)).events[0].code == code
    for subject, states in AGENT_STATE_SUBJECTS.items():
        for state in states:
            if (subject, state) != ("service", "started"):
                refused(agent(subject=subject, state=state, code=code), reason="code_requires_service_started")
    # Without a code, service/started is valid as well.
    assert accepted(agent(code=None)).events[0].code is None


@pytest.mark.parametrize("changes", [
    {"code": "crash"}, {"code": "clean"}, {"code": "First_Start"}, {"code": ""}, {"code": 1}, {"code": True},
    {"subject": "Service"}, {"subject": "sensor"}, {"subject": "engine"}, {"subject": ""}, {"subject": None},
    {"state": "unknown"}, {"state": "protected"}, {"state": "Started"}, {"state": ""}, {"state": None},
])
def test_agent_state_values_are_closed(changes):
    refused(agent(**changes))


def test_a_rule_set_id_is_allowed_only_for_the_rule_set_subject():
    for state in AGENT_STATE_SUBJECTS["rule_set"]:
        assert accepted(agent(subject="rule_set", state=state, code=None, rule_set_id=RULE_SET)).events[
            0].rule_set_id == RULE_SET
        assert accepted(agent(subject="rule_set", state=state, code=None)).events[0].rule_set_id is None
    for subject, states in AGENT_STATE_SUBJECTS.items():
        if subject != "rule_set":
            for state in states:
                refused(agent(subject=subject, state=state, code=None, rule_set_id=RULE_SET),
                        reason="rule_set_id_requires_rule_set")


@pytest.mark.parametrize("signal", TAMPER_SIGNALS)
def test_tamper_detail_is_required_exactly_for_event_log_cleared(signal):
    if signal == "event_log_cleared":
        for detail in TAMPER_DETAILS:
            assert accepted(tamper(signal=signal, detail=detail)).events[0].detail == detail
        refused(tamper(signal=signal, detail=None), reason="detail_required_for_event_log_cleared")
        refused({key: value for key, value in tamper(signal=signal).items() if key != "detail"},
                reason="detail_required_for_event_log_cleared")
    else:
        assert accepted(tamper(signal=signal, detail=None)).events[0].detail is None
        assert accepted({key: value for key, value in tamper(signal=signal).items() if key != "detail"}).events[
            0].detail is None
        for detail in TAMPER_DETAILS:
            refused(tamper(signal=signal, detail=detail), reason="detail_only_for_event_log_cleared")


@pytest.mark.parametrize("changes", [
    {"detail": "application"}, {"detail": "Security"}, {"detail": ""}, {"detail": 1},
    {"signal": "tampered"}, {"signal": "Event_Log_Cleared"}, {"signal": ""}, {"signal": None},
])
def test_tamper_values_are_closed(changes):
    refused(tamper(**changes))


# --- privacy (ADR 1.4) and identity

PRIVATE_VALUES = {"command_line": "setup.exe /quiet", "user": "ahmet", "username": "ahmet", "sid": "S-1-5-21-1",
                  "content": "sample-content"}
IDENTITY_VALUES = {"tenant_id": str(uuid4()), "device_id": str(uuid4()), "source": "self_reported",
                   "producer_verification": "verified"}


@pytest.mark.parametrize("key", list(PRIVATE_VALUES) + list(IDENTITY_VALUES))
@pytest.mark.parametrize("factory", FACTORIES, ids=EVENT_KINDS)
def test_private_and_identity_keys_are_refused_in_every_v2_kind(factory, key):
    # Refused whatever the value, null included.
    for value in ({**PRIVATE_VALUES, **IDENTITY_VALUES}[key], None):
        refused(factory(**{key: value}))


@pytest.mark.parametrize("key", list(PRIVATE_VALUES))
@pytest.mark.parametrize("factory", V1_FACTORIES, ids=EVENT_KINDS_V1)
def test_private_keys_are_refused_in_every_v1_kind(factory, key):
    for value in (PRIVATE_VALUES[key], None):
        body = v1_batch(factory(**{key: value}))
        with pytest.raises(ValidationError):
            EventBatch.model_validate(body)
        with pytest.raises(ValidationError):
            parse_event_batch(body)


@pytest.mark.parametrize("key,value", [("sha256", DIGEST), ("size", 68)])
@pytest.mark.parametrize("factory", [factory for factory in FACTORIES if factory is not scan],
                         ids=[kind for kind in EVENT_KINDS if kind != "scan_detected"])
def test_sha256_and_size_are_accepted_only_in_scan_detected(factory, key, value):
    refused(factory(**{key: value}))


@pytest.mark.parametrize("key,value", [("sha256", DIGEST), ("size", 68)])
@pytest.mark.parametrize("factory", V1_FACTORIES, ids=EVENT_KINDS_V1)
def test_sha256_and_size_stay_refused_in_v1(factory, key, value):
    with pytest.raises(ValidationError):
        parse_event_batch(v1_batch(factory(**{key: value})))


def test_no_model_has_a_private_trust_or_identity_field():
    forbidden = {*PRIVATE_VALUES, *IDENTITY_VALUES}
    for model in (*EVENT_MODELS.values(), *EVENT_MODELS_V2.values(), ScanHit, EventBatch, EventBatchV2):
        names = set(model.model_fields) - ({"source"} if model is CoverageGap else set())
        assert not forbidden & names, model.__name__
    # coverage_gap.source (ADR 1.2) names the part of the agent that lost records, from a closed set: it is not
    # a trust label and can never say self_reported or verified.
    assert literal_values(CoverageGap.model_fields["source"].annotation) == COVERAGE_SOURCES
    assert not {"self_reported", "not_verified", "verified"} & set(COVERAGE_SOURCES)
    assert [kind for kind, model in EVENT_MODELS_V2.items() if {"sha256", "size"} & set(model.model_fields)] == [
        "scan_detected"]


CLAIM = re.compile(r"protect|rules_loaded|realtime_protection|blocked|prevented|verified", re.IGNORECASE)


def test_no_field_name_or_closed_value_claims_protection():
    names = {name for model in (*EVENT_MODELS_V2.values(), ScanHit, EventBatchV2) for name in model.model_fields}
    assert [name for name in names if CLAIM.search(name)] == []
    values = [*SCAN_TRIGGERS, *SCAN_HIT_SEVERITIES, *BEHAVIOR_RULES, *COMMAND_LINE_SOURCES, *PERSISTENCE_LOCATIONS,
              *PERSISTENCE_SCOPES, *PERSISTENCE_CHANGES, *AGENT_STATE_SUBJECTS, *AGENT_STATES, *AGENT_STATE_CODES,
              *TAMPER_SIGNALS, *TAMPER_DETAILS, *COVERAGE_SOURCES, *COVERAGE_REASONS, *EVENT_KINDS]
    assert [value for value in values if CLAIM.search(value)] == []


# --- the v2 batch envelope

@pytest.mark.parametrize("changes", [
    {"schema_version": True}, {"schema_version": False}, {"schema_version": 1}, {"schema_version": 3},
    {"schema_version": "2"}, {"schema_version": 2.0}, {"schema_version": None}, {"batch_id": str(uuid4()).upper()},
    {"batch_id": uuid4().hex}, {"batch_id": "{" + str(uuid4())[:34] + "}"},
    {"batch_id": "not-a-uuid-but-thirty-six-characters"}, {"batch_id": None}, {"batch_sequence": 0},
    {"batch_sequence": -1}, {"batch_sequence": MAX_SEQUENCE + 1}, {"batch_sequence": True},
    {"batch_sequence": "1"}, {"batch_sequence": 1.0}, {"batch_sequence": None}, {"events": {"0": sensor()}},
    {"events": None},
])
def test_v2_envelope_types_are_strict(changes):
    refused(**changes)


@pytest.mark.parametrize("extra", [
    {"tenant_id": str(uuid4())}, {"device_id": str(uuid4())}, {"source": "self_reported"},
    {"producer_verification": "verified"}, {"schema": "altay-edr-event/v2"}, {"received_at": "2026-11-26T10:00:00Z"},
])
def test_unknown_v2_batch_keys_are_rejected(extra):
    refused(**extra)


def test_v2_batch_identity_and_sequence_ranges():
    assert accepted(batch_sequence=MAX_SEQUENCE).batch_sequence == MAX_SEQUENCE
    identity = str(uuid4())
    assert accepted(batch_id=identity).batch_id == identity


def test_v2_batch_holds_one_to_two_hundred_events():
    events = [gap(seq) for seq in range(1, MAX_BATCH_EVENTS + 2)]
    assert len(accepted(*events[:MAX_BATCH_EVENTS]).events) == 200
    refused(*events)
    with pytest.raises(ValidationError):
        EventBatchV2.model_validate({**batch(), "events": []})


def test_v2_event_seq_strictly_increases_with_gaps_up_to_2_53_minus_1():
    assert [event.event_seq for event in accepted(scan(1), gap(5), agent(MAX_EVENT_SEQ)).events] == [
        1, 5, MAX_EVENT_SEQ]
    refused(scan(4), gap(4), reason="event_seq_not_increasing")
    refused(scan(5), gap(4), reason="event_seq_not_increasing")
    for value in (0, -1, 2**53, True, 1.0, "1"):
        refused(gap(value))


# --- homogeneity: a batch is v1 or v2 as a whole

@pytest.mark.parametrize("factory", V2_ONLY, ids=V2_ONLY_KINDS)
def test_a_v1_batch_carries_no_v2_kind(factory):
    body = v1_batch(v1_started(1), factory(2))
    with pytest.raises(ValidationError):
        EventBatch.model_validate(body)
    with pytest.raises(ValidationError):
        parse_event_batch(body)


@pytest.mark.parametrize("event", [started(), started(parent_create_time=None), stopped(),
                                   stopped(create_time=None), v1_started(parent_create_time=None)],
                         ids=["started", "started-no-parent-time", "stopped", "stopped-null-create-time",
                              "v1-started-with-parent-time-key"])
def test_a_v1_batch_carries_no_v2_shape(event):
    with pytest.raises(ValidationError):
        parse_event_batch(v1_batch(event))


def test_a_v2_batch_refuses_the_v1_process_started_shape():
    # create_time is required in v2: records without it go in a v1 batch.
    refused(v1_started(), reason="create_time")
    # The other v1 shapes are also valid v2 shapes; the v2 canonical form gives create_time explicitly.
    model = accepted(v1_stopped(1), sensor(2))
    assert json.loads(canonical_event_batch(model))["events"][0]["create_time"] is None


def test_the_version_is_part_of_the_content_identity():
    body = v1_batch(v1_stopped(1, image=None), sensor(2))
    one, two = parse_event_batch(body), parse_event_batch({**body, "schema_version": 2})
    assert (type(one), type(two)) == (EventBatch, EventBatchV2)
    assert event_batch_digest(one) != event_batch_digest(two)
    assert json.loads(canonical_event_batch(two)) == {**json.loads(canonical_event_batch(one)), "schema_version": 2,
        "events": [{**json.loads(canonical_event_batch(one))["events"][0], "create_time": None},
                   json.loads(canonical_event_batch(one))["events"][1]]}


# --- the schema_version dispatch

def test_dispatch_chooses_the_batch_class_by_schema_version():
    assert type(parse_event_batch(v1_batch())) is EventBatch
    assert type(parse_event_batch(batch())) is EventBatchV2
    assert parse_event_batch(batch(sensor(1), batch_id="00000000-0000-4000-8000-000000000009")) == (
        EventBatchV2.model_validate(batch(sensor(1), batch_id="00000000-0000-4000-8000-000000000009")))


@pytest.mark.parametrize("version", [True, False, 0, -1, 3, 1.0, 2.0, "1", "2", None, [2], {"version": 2}])
def test_dispatch_refuses_every_other_version_as_invalid_schema_version(version):
    assert errors(parse_event_batch, batch(schema_version=version)) == [
        ("invalid_schema_version", (), "invalid_schema_version")]


@pytest.mark.parametrize("value", [{key: value for key, value in batch().items() if key != "schema_version"}, {},
                                   [], "batch", None, 2, b"{}"])
def test_dispatch_refuses_a_body_without_a_version(value):
    assert errors(parse_event_batch, value) == [("invalid_schema_version", (), "invalid_schema_version")]


@pytest.mark.parametrize("body", [
    v1_batch(batch_sequence=0), v1_batch(batch_id="not-a-uuid"), v1_batch(v1_started(1, pid=-1)),
    v1_batch(v1_started(1, image=r"\Users\x\a.exe")), v1_batch(v1_started(2), sensor(1)),
    v1_batch(sensor(1, state="started", error_code="unknown")), v1_batch(v1_started(1, command_line="x")),
    v1_batch(v1_started(1, observed_at="9999-01-01T00:00:00Z")), v1_batch(scan(1)), {**v1_batch(), "events": []},
    {**v1_batch(), "device_id": str(uuid4())},
], ids=["sequence", "batch-id", "pid", "unmasked", "order", "error-code", "command-line", "observed-at",
        "v2-kind", "empty", "identity"])
def test_a_v1_body_fails_through_the_dispatch_exactly_as_through_event_batch(body):
    # Same types, messages (the error codes) and locations; the dispatch prefixes the location with the class tag.
    direct = errors(EventBatch.model_validate, body)
    assert errors(parse_event_batch, body) == [(kind, ("EventBatch", *location), message)
                                               for kind, location, message in direct]


# --- canonical form and digests

def test_v1_bytes_and_digest_are_unchanged_through_the_dispatch():
    # The body and bytes of tests/unit/test_event_contracts.py::test_canonical_bytes_and_digest_are_pinned.
    model = parse_event_batch({"schema_version": 1, "batch_id": "00000000-0000-4000-8000-000000000001",
        "batch_sequence": 7, "events": [
            {"kind": "process_started", "event_seq": 10, "observed_at": "2026-11-22T10:00:00Z", "pid": 4321,
             "parent_pid": 1234, "session_id": 1, "image": r"\Device\HarddiskVolume3\Users\*\Masaüstü\araç.exe"},
            {"kind": "process_stopped", "event_seq": 11, "observed_at": "2026-11-22T10:00:01.000000Z", "pid": 4321,
             "exit_code": None, "image": None},
            {"kind": "sensor_state", "event_seq": 12, "observed_at": "2026-11-22T10:00:02.000000Z", "state": "failed",
             "error_code": "access_denied"}]})
    expected = ('{"batch_id":"00000000-0000-4000-8000-000000000001","batch_sequence":7,"events":['
        '{"event_seq":10,"image":"\\\\Device\\\\HarddiskVolume3\\\\Users\\\\*\\\\Masaüstü\\\\araç.exe",'
        '"kind":"process_started","observed_at":"2026-11-22T10:00:00.000000Z","parent_pid":1234,"pid":4321,'
        '"session_id":1},'
        '{"event_seq":11,"exit_code":null,"image":null,"kind":"process_stopped",'
        '"observed_at":"2026-11-22T10:00:01.000000Z","pid":4321},'
        '{"error_code":"access_denied","event_seq":12,"kind":"sensor_state",'
        '"observed_at":"2026-11-22T10:00:02.000000Z","state":"failed"}],"schema_version":1}').encode("utf-8")
    assert type(model) is EventBatch
    assert canonical_event_batch(model) == expected
    assert event_batch_digest(model) == hashlib.sha256(expected).hexdigest() == (
        "6c8263228c82609cc348e8f1c61a6d1109b1bd22366bed08206273743d00d775")


PROFILE_PATH = r"\Device\HarddiskVolume3\Users\*\Masaüstü\araç.exe"


def reference_v2_body():
    return {"schema_version": 2, "batch_id": "00000000-0000-4000-8000-000000000002", "batch_sequence": 8, "events": [
        started(20, observed_at="2026-11-26T10:00:00Z", image=PROFILE_PATH, create_time="2026-11-26T09:59:59.5Z"),
        stopped(21, exit_code=None, image="araç.exe", create_time="2026-11-26T09:59:59.5Z"),
        sensor(22, state="failed", error_code="access_denied"),
        scan(23, trigger="startup_scan", path=PROFILE_PATH, sha256="0" * 63 + "1",
             hits=[{"rule": "Sample_Rule", "severity": "medium"}], create_time="2026-11-26T09:59:59.5Z"),
        behavior(24, rule_version=1, image=PROFILE_PATH, parent_image=None, found_at_start=True,
                 command_line_source="process_query", create_time="2026-11-26T09:59:59.5Z"),
        persistence(25, target_image=PROFILE_PATH),
        agent(26, subject="rule_set", state="compiled", code=None, rule_set_id=RULE_SET),
        tamper(27, signal="event_log_cleared", detail="security"),
        gap(28, source="agent_records", reason="queue_overflow", lost=3)]}


def test_reference_v2_batch_has_pinned_canonical_bytes_and_digest():
    model = parse_event_batch(reference_v2_body())
    expected = ('{"batch_id":"00000000-0000-4000-8000-000000000002","batch_sequence":8,"events":['
        '{"create_time":"2026-11-26T09:59:59.500000Z","event_seq":20,'
        '"image":"\\\\Device\\\\HarddiskVolume3\\\\Users\\\\*\\\\Masaüstü\\\\araç.exe","kind":"process_started",'
        '"observed_at":"2026-11-26T10:00:00.000000Z","parent_create_time":"2026-11-26T08:00:00.000000Z",'
        '"parent_pid":1234,"pid":4321,"session_id":1},'
        '{"create_time":"2026-11-26T09:59:59.500000Z","event_seq":21,"exit_code":null,"image":"araç.exe",'
        '"kind":"process_stopped","observed_at":"2026-11-26T10:00:01.000000Z","pid":4321},'
        '{"error_code":"access_denied","event_seq":22,"kind":"sensor_state",'
        '"observed_at":"2026-11-26T10:00:02.000000Z","state":"failed"},'
        '{"action_id":null,"create_time":"2026-11-26T09:59:59.500000Z","event_seq":23,'
        '"hits":[{"rule":"Sample_Rule","severity":"medium"}],"kind":"scan_detected",'
        '"observed_at":"2026-11-26T10:00:03.000000Z","omitted_hits":0,'
        '"path":"\\\\Device\\\\HarddiskVolume3\\\\Users\\\\*\\\\Masaüstü\\\\araç.exe","pid":4321,'
        '"rule_set_id":"' + "a" * 64 + '","sha256":"' + "0" * 63 + '1","size":68,"trigger":"startup_scan"},'
        '{"command_line_source":"process_query","create_time":"2026-11-26T09:59:59.500000Z","event_seq":24,'
        '"found_at_start":true,"image":"\\\\Device\\\\HarddiskVolume3\\\\Users\\\\*\\\\Masaüstü\\\\araç.exe",'
        '"kind":"behavior_match","observed_at":"2026-11-26T10:00:04.000000Z","parent_image":null,"pid":4321,'
        '"rule":"encoded_powershell","rule_version":1},'
        '{"change":"added","entry_id":"' + "b" * 64 + '","event_seq":25,"found_at_start":false,'
        '"kind":"persistence_change","location":"run_key","observed_at":"2026-11-26T10:00:05.000000Z",'
        '"scope":"user","target_image":"\\\\Device\\\\HarddiskVolume3\\\\Users\\\\*\\\\Masaüstü\\\\araç.exe"},'
        '{"code":null,"event_seq":26,"kind":"agent_state","observed_at":"2026-11-26T10:00:06.000000Z",'
        '"rule_set_id":"' + "a" * 64 + '","state":"compiled","subject":"rule_set"},'
        '{"detail":"security","event_seq":27,"kind":"tamper_signal","observed_at":"2026-11-26T10:00:07.000000Z",'
        '"signal":"event_log_cleared"},'
        '{"event_seq":28,"kind":"coverage_gap","lost":3,"observed_at":"2026-11-26T10:00:08.000000Z",'
        '"reason":"queue_overflow","source":"agent_records"}],"schema_version":2}').encode("utf-8")
    assert type(model) is EventBatchV2
    assert canonical_event_batch(model) == expected
    assert "Masaüstü".encode("utf-8") in expected and b"\\u00fc" not in expected
    assert event_batch_digest(model) == hashlib.sha256(expected).hexdigest() == (
        "fac727ee80712a99e5d109647ce16ce989372e845ef4c6b73e85e8d218d8bf32")


def test_v2_digest_is_stable_over_key_order_time_form_and_omitted_nulls():
    payload = reference_v2_body()
    reference = event_batch_digest(parse_event_batch(payload))
    reordered = json.loads(json.dumps({key: payload[key] for key in reversed(list(payload))}))
    reordered["events"] = [dict(reversed(list(item.items()))) for item in reordered["events"]]
    assert event_batch_digest(parse_event_batch(reordered)) == reference
    other_form = json.loads(json.dumps(payload))
    other_form["events"][0]["create_time"] = "2026-11-26T09:59:59.500000Z"
    other_form["events"][8]["observed_at"] = "2026-11-26T10:00:08.000Z"
    assert event_batch_digest(parse_event_batch(other_form)) == reference
    omitted = json.loads(json.dumps(payload))
    del omitted["events"][1]["exit_code"], omitted["events"][3]["action_id"], omitted["events"][4]["parent_image"]
    del omitted["events"][6]["code"]
    assert event_batch_digest(parse_event_batch(omitted)) == reference
    model = parse_event_batch(payload)
    assert event_batch_digest(parse_event_batch(model.model_dump(mode="json"))) == reference


@pytest.mark.parametrize("change", [
    lambda body: body["events"][0].update(create_time="2026-11-26T09:59:59.500001Z"),
    lambda body: body["events"][0].update(parent_create_time=None),
    lambda body: body["events"][3]["hits"][0].update(severity="high"),
    lambda body: body["events"][3].update(omitted_hits=1),
    lambda body: body["events"][4].update(found_at_start=False),
    lambda body: body["events"][5].update(change="modified"),
    lambda body: body["events"][6].update(state="invalid"),
    lambda body: body["events"][7].update(detail="system"),
    lambda body: body["events"][8].update(lost=None),
    lambda body: body.update(batch_sequence=9),
], ids=["create-time", "parent-time", "severity", "omitted-hits", "found-at-start", "change", "state", "detail",
        "lost", "batch-sequence"])
def test_any_semantic_change_changes_the_v2_digest(change):
    payload = reference_v2_body()
    before = event_batch_digest(parse_event_batch(payload))
    change(payload)
    assert event_batch_digest(parse_event_batch(payload)) != before


def canonical_size(payload):
    # Independent restatement of the canonical form, usable above the cap.
    model = EventBatchV2.model_validate(payload)
    return len(json.dumps(model.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode("utf-8"))


def v2_batch_of_canonical_size(target):
    identity = str(uuid4())
    filler = []
    while canonical_size(batch(*filler, started(len(filler) + 2, image="\\" + "a" * 700),
                               scan(len(filler) + 3, path="\\"), batch_id=identity)) <= target:
        filler.append(started(len(filler) + 1, image="\\" + "a" * 700))
    payload = batch(*filler, scan(len(filler) + 1, path="\\"), batch_id=identity)
    missing = target - canonical_size(payload)
    assert 0 <= missing <= 1023, "fixture sizing no longer reaches the target"
    payload["events"][-1]["path"] = "\\" + "a" * missing
    assert canonical_size(payload) == target
    return EventBatchV2.model_validate(payload)


def test_v2_canonical_form_is_capped_at_16_kib():
    exact = v2_batch_of_canonical_size(MAX_EVENT_BATCH_BYTES)
    encoded = canonical_event_batch(exact)
    assert len(encoded) == MAX_EVENT_BATCH_BYTES == 16384
    assert event_batch_digest(exact) == hashlib.sha256(encoded).hexdigest()
    over = v2_batch_of_canonical_size(MAX_EVENT_BATCH_BYTES + 1)
    for function in (canonical_event_batch, event_batch_digest):
        # The distinct type makes the service answer 413 rather than 422, as for v1.
        with pytest.raises(EventBatchTooLarge, match="event_batch_too_large"):
            function(over)


def scan_of_stored_size(target):
    base = stored_event_bytes(ScanDetected.model_validate(scan(path="\\")))
    wide, narrow = divmod(target - base, len(WIDE.encode("utf-8")))
    return scan(path="\\" + WIDE * wide + "a" * narrow)


def test_each_v2_event_fits_the_4_kib_stored_payload_bound():
    exact = ScanDetected.model_validate(scan_of_stored_size(MAX_STORED_EVENT_BYTES))
    assert stored_event_bytes(exact) == MAX_STORED_EVENT_BYTES == 4096
    refused(scan_of_stored_size(MAX_STORED_EVENT_BYTES + 1), reason="event_too_large")
    # Two paths of 1024 three-byte characters each are within their character limit, but not within 4 KiB.
    wide_path = "\\" + "\u4e2d" * 1023
    refused(behavior(image=wide_path, parent_image=wide_path), reason="event_too_large")
    assert accepted(behavior(image=wide_path, parent_image=None)).events[0].image == wide_path
