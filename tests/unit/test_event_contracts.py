"""Closed altay-edr-event/v1 contract: kinds, privacy masking, limits and canonical identity."""
import hashlib
import json
import sys
import unicodedata
from uuid import uuid4

from pydantic import ValidationError
import pytest

from security_platform.contracts import MAX_SEQUENCE
from security_platform.event_contracts import (EVENT_FIELDS, MAX_BATCH_EVENTS, MAX_EVENT_BATCH_BYTES,
    MAX_STORED_EVENT_BYTES, REFUSED_TEXT_RANGES, REFUSED_TEXT_UNICODE_VERSION, EventBatch, EventBatchTooLarge,
    ProcessStarted, ProcessStopped, SensorState, canonical_event_batch, event_batch_digest, stored_event_bytes)


MASKED = r"\Device\HarddiskVolume3\Users\*\Downloads\setup.exe"
WIDE = "\U0001F600"  # four UTF-8 bytes, an ordinary symbol (category So)


def started(seq=1, **changes):
    return {"kind": "process_started", "event_seq": seq, "observed_at": "2026-11-22T10:00:00.000001Z",
            "pid": 4321, "parent_pid": 1234, "session_id": 1, "image": MASKED, **changes}


def stopped(seq=2, **changes):
    return {"kind": "process_stopped", "event_seq": seq, "observed_at": "2026-11-22T10:00:01.000000Z",
            "pid": 4321, "exit_code": 0, "image": "setup.exe", **changes}


def sensor(seq=3, **changes):
    return {"kind": "sensor_state", "event_seq": seq, "observed_at": "2026-11-22T10:00:02.000000Z",
            "state": "lost", "error_code": "session_in_use", **changes}


def batch(*events, **changes):
    return {"schema_version": 1, "batch_id": str(uuid4()), "batch_sequence": 1,
            "events": list(events) or [started(), stopped(), sensor()], **changes}


def canonical_size(payload):
    # Independent restatement of the canonical form, usable above the cap.
    model = EventBatch.model_validate(payload)
    return len(json.dumps(model.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8"))


def test_every_kind_validates_with_exactly_its_closed_fields():
    model = EventBatch.model_validate(batch())
    assert [type(event) for event in model.events] == [ProcessStarted, ProcessStopped, SensorState]
    assert EVENT_FIELDS == {"process_started": ("pid", "parent_pid", "session_id", "image"),
                            "process_stopped": ("pid", "exit_code", "image"),
                            "sensor_state": ("state", "error_code")}
    for event in json.loads(canonical_event_batch(model))["events"]:
        assert set(event) == {"kind", "event_seq", "observed_at", *EVENT_FIELDS[event["kind"]]}
    assert set(EventBatch.model_fields) == {"schema_version", "batch_id", "batch_sequence", "events"}


def test_no_trust_or_identity_claim_can_be_carried():
    for model in (EventBatch, ProcessStarted, ProcessStopped, SensorState):
        assert not {"source", "producer_verification", "tenant_id", "device_id"} & set(model.model_fields)


@pytest.mark.parametrize("field", ["pid", "parent_pid", "session_id"])
@pytest.mark.parametrize("value", [-1, 2**32, True, 1.0, "1", None])
def test_process_started_numbers_are_strict_unsigned_32_bit(field, value):
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch(started(**{field: value})))


@pytest.mark.parametrize("value", [0, 2**32 - 1])
def test_process_numbers_accept_the_full_unsigned_range(value):
    model = EventBatch.model_validate(batch(started(1, pid=value, parent_pid=value, session_id=value),
                                            stopped(2, pid=value, exit_code=value)))
    assert model.events[0].session_id == value and model.events[1].exit_code == value


@pytest.mark.parametrize("value", [None, "", 7, "a" * 1025, "\\" + "a" * 1024])
def test_process_started_image_is_bounded(value):
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch(started(image=value)))


@pytest.mark.parametrize("image", ["\\" + "a" * 1023, "a" * 1024])
def test_process_started_image_accepts_1024_characters(image):
    assert len(EventBatch.model_validate(batch(started(image=image))).events[0].image) == 1024


@pytest.mark.parametrize("image", [
    MASKED,
    r"C:\Users\*\AppData\Local\Temp\tool.exe",
    r"\Device\HarddiskVolume3\USERS\*\tool.exe",
    r"\Device\HarddiskVolume3\users\*\tool.exe",
    r"\Device\HarddiskVolume3\Users\*\Users\*\tool.exe",
    r"\Device\HarddiskVolume3\Windows\System32\svchost.exe",
    r"\Device\HarddiskVolume3\Program Files\UsersGuide\tool.exe",
    r"\\server\share\Users\*\tool.exe",
    r"\??\C:\Users\*",
    r"\Device\HarddiskVolume3\Users",
    "C:/Users/*/tool.exe",
    # The name part before the first ':' is masked; the stream name stays.
    r"\Device\HarddiskVolume3\Users\*\a.exe",
    r"\Device\HarddiskVolume3\Users\*:payload.exe",
    r"\Users\*:payload.exe",
    r"\Users\*",
    r"\Users\*:",
    r"\Users\*:a:$DATA",
    # A stream on a folder named Users is not a Users component, also when
    # another component follows it (only then can the rule be tested).
    r"\Device\HarddiskVolume3\Users:stream",
    r"\Device\HarddiskVolume3\Users:stream\x.exe",
])
def test_masked_or_profile_free_paths_are_accepted(image):
    assert EventBatch.model_validate(batch(started(image=image))).events[0].image == image


@pytest.mark.parametrize("image", ["Registry", "MemCompression", "System", "setup.exe", "Users", "*"])
def test_bare_names_without_a_separator_are_accepted(image):
    assert EventBatch.model_validate(batch(started(image=image))).events[0].image == image


@pytest.mark.parametrize("image", [
    r"\Device\HarddiskVolume3\Users\ahmet\Downloads\setup.exe",
    r"\Device\HarddiskVolume3\users\ahmet\tool.exe",
    r"\Device\HarddiskVolume3\USERS\ahmet\tool.exe",
    r"\Device\HarddiskVolume3\uSeRs\Public\tool.exe",
    r"\Device\HarddiskVolume3\Users\*\Users\bob\tool.exe",
    r"\Device\HarddiskVolume3\Users\**\tool.exe",
    r"\Device\HarddiskVolume3\Users\*ahmet\tool.exe",
    r"\Device\HarddiskVolume3\Users\\tool.exe",
    "\\Device\\HarddiskVolume3\\Users\\",
    r"C:\Users/ahmet/tool.exe",
    r"\Device\HarddiskVolume3\Users/ahmet\tool.exe",
    "C:/Users/ahmet/tool.exe",
    r"\Device\HarddiskVolume3\Users\ahmet:payload.exe",
    r"\Users\ahmet:payload.exe",
    r"\Users\**",
    r"\Users\*x:y",
    r"\Users\:x",
    "\\Users\\",
    r"\Users\ahmet:",
    # A file directly under Users is masked to '*' as well.
    r"\Device\HarddiskVolume3\Users\setup.exe",
    r"\Device\HarddiskVolume3\Users\setup.exe:payload.exe",
])
def test_unmasked_profile_folder_is_refused(image):
    with pytest.raises(ValidationError, match="unmasked_user_folder"):
        EventBatch.model_validate(batch(started(image=image)))


@pytest.mark.parametrize("image,reason", [
    ("\\tool\x00.exe", "invalid_image_text"), ("\\tool\x1f.exe", "invalid_image_text"),
    ("\\tool\x7f.exe", "invalid_image_text"), ("\\tool\u0085.exe", "invalid_image_text"),
    ("\\tool\u202e.exe", "invalid_image_text"), ("\\tool\u200b.exe", "invalid_image_text"),
    ("tool\u202e.exe", "invalid_image_text"), ("\\tool\ud800.exe", "valid string"),
])
def test_image_refuses_control_or_format_text(image, reason):
    with pytest.raises(ValidationError, match=reason):
        EventBatch.model_validate(batch(started(image=image)))


def interpreter_ranges(categories):
    """Inclusive code point ranges of the running interpreter's general categories."""
    ranges, first = [], None
    for code in range(sys.maxunicode + 1):
        if unicodedata.category(chr(code)) in categories:
            first = code if first is None else first
        elif first is not None:
            ranges.append((first, code - 1))
            first = None
    if first is not None:
        ranges.append((first, sys.maxunicode))
    return tuple(ranges)


def test_refused_text_table_is_the_frozen_unicode_16_control_and_format_set():
    # The table is frozen, so the contract never follows the running
    # interpreter. Only a Python with the same Unicode database can confirm
    # that the table is that database's Cc+Cf set; on any other version
    # (the project also supports 3.12 and 3.13) the comparison is skipped, and
    # the two tests below still pin the behaviour. Changing the table is an
    # explicit contract change for the Platform and the agent together.
    assert REFUSED_TEXT_UNICODE_VERSION == "16.0.0"
    if unicodedata.unidata_version != REFUSED_TEXT_UNICODE_VERSION:
        pytest.skip(f"interpreter Unicode {unicodedata.unidata_version}; the table is frozen at "
                    f"{REFUSED_TEXT_UNICODE_VERSION}")
    assert REFUSED_TEXT_RANGES == interpreter_ranges({"Cc", "Cf"})


def test_image_text_refuses_exactly_the_frozen_table():
    refused = {code for first, last in REFUSED_TEXT_RANGES for code in range(first, last + 1)}
    neighbours = {code for first, last in REFUSED_TEXT_RANGES for code in (first - 1, last + 1)
                  if code >= 0 and not 0xD800 <= code <= 0xDFFF} - refused
    assert neighbours
    for code in sorted(refused):
        for factory in (started, stopped):
            with pytest.raises(ValidationError, match="invalid_image_text"):
                EventBatch.model_validate(batch(factory(image="tool" + chr(code) + ".exe")))
    for code in sorted(neighbours):
        model = EventBatch.model_validate(batch(started(image="tool" + chr(code) + ".exe"),
                                                stopped(image="tool" + chr(code) + ".exe")))
        assert [event.image for event in model.events] == ["tool" + chr(code) + ".exe"] * 2


def test_refused_text_does_not_depend_on_the_running_unicode_database(monkeypatch):
    # Only the frozen table decides: another database cannot refuse or admit text.
    monkeypatch.setattr(unicodedata, "category", lambda character: "Cf")
    EventBatch.model_validate(batch(started(image=r"C:\Users\*\tool.exe"), stopped(image="tool.exe")))
    monkeypatch.setattr(unicodedata, "category", lambda character: "Lo")
    with pytest.raises(ValidationError, match="invalid_image_text"):
        EventBatch.model_validate(batch(started(image="\\tool\u202e.exe")))


@pytest.mark.parametrize("changes", [
    {"exit_code": None}, {"image": None}, {"exit_code": 2**32 - 1}, {"image": "a" * 260}, {"image": "ü.exe"},
    {"image": "\ufffd=45:A.exe"}, {"image": "\ufffd"},
])
def test_process_stopped_accepts_null_exit_code_and_short_names(changes):
    EventBatch.model_validate(batch(stopped(**changes)))


def agent_short_name(kernel_name):
    """The agent transform the contract documents for the kernel short name."""
    return kernel_name.replace("\\", "\ufffd").replace("/", "\ufffd") or None


# Kernel short names (the low byte of each UTF-16 unit, decoded by the agent)
# of Яндекс.exe, دانلود.exe, 支付宝.exe, 作業ツール.exe, 桜.exe and 一键清理.exe.
KERNEL_SHORT_NAMES = ["/=45:A.exe", "/'FDH/.exe", "/\u061d.exe", "\\mÄüë.exe", "\\.exe", ""]


@pytest.mark.parametrize("kernel_name", KERNEL_SHORT_NAMES)
def test_kernel_short_names_are_accepted_after_the_agent_transform(kernel_name):
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch(stopped(image=kernel_name)))
    sent = agent_short_name(kernel_name)
    assert sent is None or ("\\" not in sent and "/" not in sent)
    assert EventBatch.model_validate(batch(stopped(image=sent))).events[0].image == sent


@pytest.mark.parametrize("changes", [
    {"exit_code": -1}, {"exit_code": 2**32}, {"exit_code": True}, {"exit_code": "0"}, {"pid": None},
    {"image": ""}, {"image": "a" * 261}, {"image": r"C:\Windows\tool.exe"}, {"image": "dir/tool.exe"},
    {"image": "tool\x00.exe"}, {"image": "tool\u202e.exe"}, {"image": 5},
])
def test_process_stopped_rejects_out_of_range_or_path_like_values(changes):
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch(stopped(**changes)))


@pytest.mark.parametrize("state", ["started", "lost", "failed", "stopped"])
def test_every_sensor_state_accepts_a_null_error_code(state):
    assert EventBatch.model_validate(batch(sensor(state=state, error_code=None))).events[0].error_code is None


@pytest.mark.parametrize("state", ["lost", "failed"])
@pytest.mark.parametrize("code", ["session_name_invalid", "session_in_use", "access_denied", "session_start_failed",
                                  "session_stop_failed", "unknown"])
def test_lost_and_failed_carry_a_known_error_code(state, code):
    assert EventBatch.model_validate(batch(sensor(state=state, error_code=code))).events[0].error_code == code


@pytest.mark.parametrize("state", ["started", "stopped"])
def test_started_and_stopped_cannot_carry_an_error_code(state):
    with pytest.raises(ValidationError, match="unexpected_error_code"):
        EventBatch.model_validate(batch(sensor(state=state, error_code="unknown")))


@pytest.mark.parametrize("changes", [
    {"state": "running"}, {"state": None}, {"state": "LOST"}, {"error_code": "raw driver message"},
    {"error_code": 5}, {"error_code": ""},
])
def test_sensor_state_values_are_closed(changes):
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch(sensor(**changes)))


def test_event_seq_must_strictly_increase_but_may_have_gaps():
    model = EventBatch.model_validate(batch(started(1), stopped(5), sensor(MAX_SEQUENCE)))
    assert [event.event_seq for event in model.events] == [1, 5, MAX_SEQUENCE]
    for events in ([started(1), stopped(1)], [started(2), stopped(1)], [started(1), stopped(3), sensor(2)]):
        with pytest.raises(ValidationError, match="event_seq_not_increasing"):
            EventBatch.model_validate(batch(*events))


@pytest.mark.parametrize("value", [0, -1, MAX_SEQUENCE + 1, True, 1.0, "1", None])
def test_event_seq_is_a_strict_positive_63_bit_integer(value):
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch(sensor(seq=value)))


def test_batch_holds_one_to_two_hundred_events():
    events = [sensor(seq, state="started", error_code=None) for seq in range(1, MAX_BATCH_EVENTS + 2)]
    assert len(EventBatch.model_validate(batch(*events[:MAX_BATCH_EVENTS])).events) == 200
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch(*events))
    with pytest.raises(ValidationError):
        EventBatch.model_validate({**batch(), "events": []})


def batch_of_canonical_size(target):
    payload = batch(*[started(seq, image="\\" + "a" * 1000) for seq in range(1, 15)], started(15, image="\\"))
    missing = target - canonical_size(payload)
    assert 0 <= missing <= 1023, "fixture sizing no longer reaches the target"
    payload["events"][-1]["image"] = "\\" + "a" * missing
    assert canonical_size(payload) == target
    return EventBatch.model_validate(payload)


def test_canonical_form_is_capped_at_16_kib():
    exact = batch_of_canonical_size(MAX_EVENT_BATCH_BYTES)
    encoded = canonical_event_batch(exact)
    assert len(encoded) == MAX_EVENT_BATCH_BYTES == 16384
    assert event_batch_digest(exact) == hashlib.sha256(encoded).hexdigest()
    over = batch_of_canonical_size(MAX_EVENT_BATCH_BYTES + 1)
    for function in (canonical_event_batch, event_batch_digest):
        # A distinct type, so that the service answers 413 rather than 422.
        with pytest.raises(EventBatchTooLarge, match="event_batch_too_large"):
            function(over)


def started_of_stored_size(target):
    base = stored_event_bytes(ProcessStarted.model_validate(started(image="\\")))
    wide, narrow = divmod(target - base, len(WIDE.encode("utf-8")))
    return started(image="\\" + WIDE * wide + "a" * narrow)


def test_each_event_fits_the_4_kib_stored_payload_bound():
    exact = ProcessStarted.model_validate(started_of_stored_size(MAX_STORED_EVENT_BYTES))
    assert stored_event_bytes(exact) == MAX_STORED_EVENT_BYTES == 4096
    with pytest.raises(ValidationError, match="event_too_large"):
        ProcessStarted.model_validate(started_of_stored_size(MAX_STORED_EVENT_BYTES + 1))
    # The character limit alone would admit 1024 four-byte characters.
    with pytest.raises(ValidationError, match="event_too_large"):
        EventBatch.model_validate(batch(started(image="\\" + WIDE * 1023)))
    EventBatch.model_validate(batch(started(image="\\" + "\u4e2d" * 1023)))


def test_stored_size_counts_jsonb_separators_and_escapes():
    event = ProcessStarted.model_validate(started(image=r'\a"b'))
    compact = json.dumps(event.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
    # Seven fields: one space after each colon and after each of six commas.
    assert stored_event_bytes(event) == len(compact.encode("utf-8")) + 7 + 6
    assert r'"image": "\\a\"b"' in json.dumps(event.model_dump(mode="json"), separators=(", ", ": "))


@pytest.mark.parametrize("value,normalized", [
    ("2026-11-22T10:00:00Z", "2026-11-22T10:00:00.000000Z"),
    ("2026-11-22T10:00:00.1Z", "2026-11-22T10:00:00.100000Z"),
    ("2026-11-22T10:00:00.123456Z", "2026-11-22T10:00:00.123456Z"),
    ("2024-02-29T23:59:59.999999Z", "2024-02-29T23:59:59.999999Z"),
    # ISO 8601 end of day, normalized by utc_text exactly as for snapshots.
    ("2026-12-31T24:00:00Z", "2027-01-01T00:00:00.000000Z"),
])
def test_observed_at_is_utc_text_stored_with_microseconds(value, normalized):
    model = EventBatch.model_validate(batch(sensor(observed_at=value)))
    assert model.events[0].observed_at == normalized
    assert json.loads(canonical_event_batch(model))["events"][0]["observed_at"] == normalized


@pytest.mark.parametrize("value", [
    "2026-11-22T10:00:00", "2026-11-22T10:00:00+00:00", "2026-11-22T13:00:00+03:00",
    "2026-11-22T10:00:00.1234567Z", "2026-11-22T10:00:00.Z", "2026-11-22t10:00:00Z", "2026-11-22T10:00:00z",
    "2026-11-22 10:00:00Z", "2026-02-30T10:00:00Z", "2026-11-22T24:00:00.000001Z", "2026-11-22T10:00:60Z",
    1764000000, None, "",
])
def test_observed_at_rejects_other_time_forms(value):
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch(sensor(observed_at=value)))


@pytest.mark.parametrize("value,normalized", [
    ("1970-01-01T00:00:00Z", "1970-01-01T00:00:00.000000Z"),
    ("1970-01-01T00:00:00.000001Z", "1970-01-01T00:00:00.000001Z"),
    # The bound applies to the normalized instant.
    ("1969-12-31T24:00:00Z", "1970-01-01T00:00:00.000000Z"),
    ("9998-12-31T23:59:59Z", "9998-12-31T23:59:59.000000Z"),
    ("9998-12-31T23:59:59.999999Z", "9998-12-31T23:59:59.999999Z"),
])
def test_observed_at_accepts_both_ends_of_its_window(value, normalized):
    assert EventBatch.model_validate(batch(sensor(observed_at=value))).events[0].observed_at == normalized


@pytest.mark.parametrize("value", [
    "1969-12-31T23:59:59.999999Z", "0001-01-01T00:00:00Z", "1601-01-01T00:00:00Z",
    "9999-01-01T00:00:00Z", "9998-12-31T24:00:00Z", "9999-12-31T23:59:59.999999Z",
])
def test_observed_at_outside_1970_to_9999_is_refused(value):
    # 9998-12-31T24:00:00Z normalizes to 9999-01-01T00:00:00Z, the first refused instant.
    with pytest.raises(ValidationError, match="observed_at_out_of_range"):
        EventBatch.model_validate(batch(started(observed_at=value)))


@pytest.mark.parametrize("extra", [
    {"tenant_id": str(uuid4())}, {"device_id": str(uuid4())}, {"source": "self_reported"},
    {"producer_verification": "verified"}, {"schema": "altay-edr-event/v1"}, {"received_at": "2026-11-22T10:00:00Z"},
])
def test_unknown_batch_keys_are_rejected(extra):
    with pytest.raises(ValidationError):
        EventBatch.model_validate({**batch(), **extra})


@pytest.mark.parametrize("extra", [
    {"command_line": "setup.exe /quiet"}, {"user": "ahmet"}, {"sid": "S-1-5-21-1"}, {"sha256": "a" * 64},
    {"source": "self_reported"}, {"producer_verification": "verified"}, {"received_at": "2026-11-22T10:00:00Z"},
])
@pytest.mark.parametrize("factory", [started, stopped, sensor])
def test_unknown_event_keys_are_rejected(factory, extra):
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch(factory(**extra)))


@pytest.mark.parametrize("event", [
    {**sensor(), "kind": "network_connection"}, {**sensor(), "kind": None},
    {key: value for key, value in sensor().items() if key != "kind"}, [], "sensor_state",
])
def test_unknown_or_missing_kind_is_rejected(event):
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch(event))


def test_omitted_nullable_fields_are_stored_as_null():
    model = EventBatch.model_validate(batch(
        {key: value for key, value in stopped().items() if key not in {"exit_code", "image"}},
        {key: value for key, value in sensor(state="failed").items() if key != "error_code"}))
    stopped_event, sensor_event = json.loads(canonical_event_batch(model))["events"]
    assert stopped_event["exit_code"] is None and stopped_event["image"] is None
    assert sensor_event["error_code"] is None


@pytest.mark.parametrize("factory,field", [
    (started, "pid"), (started, "parent_pid"), (started, "session_id"), (started, "image"), (started, "observed_at"),
    (started, "event_seq"), (stopped, "pid"), (sensor, "state"),
])
def test_required_fields_cannot_be_null_or_missing(factory, field):
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch(factory(**{field: None})))
    with pytest.raises(ValidationError):
        EventBatch.model_validate(batch({key: value for key, value in factory().items() if key != field}))


@pytest.mark.parametrize("changes", [
    {"schema_version": True}, {"schema_version": 2}, {"schema_version": "1"}, {"schema_version": 1.0},
    {"schema_version": None}, {"batch_id": str(uuid4()).upper()}, {"batch_id": uuid4().hex},
    {"batch_id": "{" + str(uuid4())[:34] + "}"}, {"batch_id": "not-a-uuid-but-thirty-six-characters"},
    {"batch_id": None}, {"batch_sequence": 0}, {"batch_sequence": -1}, {"batch_sequence": MAX_SEQUENCE + 1},
    {"batch_sequence": True}, {"batch_sequence": "1"}, {"batch_sequence": 1.0}, {"batch_sequence": None},
    {"events": {"0": sensor()}}, {"events": None},
])
def test_envelope_types_are_strict(changes):
    with pytest.raises(ValidationError):
        EventBatch.model_validate({**batch(), **changes})


def test_largest_batch_sequence_is_accepted():
    assert EventBatch.model_validate(batch(batch_sequence=MAX_SEQUENCE)).batch_sequence == MAX_SEQUENCE


def test_digest_is_stable_over_key_order_time_form_and_omitted_nulls():
    payload = batch(started(), stopped(), sensor())
    reference = event_batch_digest(EventBatch.model_validate(payload))
    reordered = json.loads(json.dumps({key: payload[key] for key in reversed(list(payload))}))
    reordered["events"] = [dict(reversed(list(event.items()))) for event in reordered["events"]]
    assert event_batch_digest(EventBatch.model_validate(reordered)) == reference
    other_form = json.loads(json.dumps(payload))
    other_form["events"][1]["observed_at"] = "2026-11-22T10:00:01Z"
    assert event_batch_digest(EventBatch.model_validate(other_form)) == reference
    nullable = batch(started(), stopped(exit_code=None, image=None), sensor(state="failed", error_code=None))
    omitted = json.loads(json.dumps(nullable))
    del omitted["events"][1]["exit_code"], omitted["events"][1]["image"], omitted["events"][2]["error_code"]
    assert event_batch_digest(EventBatch.model_validate(omitted)) == event_batch_digest(EventBatch.model_validate(nullable))
    model = EventBatch.model_validate(payload)
    assert event_batch_digest(EventBatch.model_validate(model.model_dump(mode="json"))) == reference


@pytest.mark.parametrize("change", [
    lambda payload: payload["events"][0].update(pid=4322), lambda payload: payload.update(batch_sequence=2),
    lambda payload: payload.update(batch_id=str(uuid4())), lambda payload: payload["events"][1].update(exit_code=1),
    lambda payload: payload["events"][2].update(observed_at="2026-11-22T10:00:02.000001Z"),
])
def test_any_semantic_change_changes_the_digest(change):
    payload = batch()
    before = event_batch_digest(EventBatch.model_validate(payload))
    change(payload)
    assert event_batch_digest(EventBatch.model_validate(payload)) != before


def test_canonical_bytes_and_digest_are_pinned():
    model = EventBatch.model_validate({"schema_version": 1, "batch_id": "00000000-0000-4000-8000-000000000001",
        "batch_sequence": 7, "events": [
            started(10, image=r"\Device\HarddiskVolume3\Users\*\Masaüstü\araç.exe", observed_at="2026-11-22T10:00:00Z"),
            stopped(11, exit_code=None, image=None),
            sensor(12, state="failed", error_code="access_denied")]})
    expected = ('{"batch_id":"00000000-0000-4000-8000-000000000001","batch_sequence":7,"events":['
        '{"event_seq":10,"image":"\\\\Device\\\\HarddiskVolume3\\\\Users\\\\*\\\\Masaüstü\\\\araç.exe",'
        '"kind":"process_started","observed_at":"2026-11-22T10:00:00.000000Z","parent_pid":1234,"pid":4321,'
        '"session_id":1},'
        '{"event_seq":11,"exit_code":null,"image":null,"kind":"process_stopped",'
        '"observed_at":"2026-11-22T10:00:01.000000Z","pid":4321},'
        '{"error_code":"access_denied","event_seq":12,"kind":"sensor_state",'
        '"observed_at":"2026-11-22T10:00:02.000000Z","state":"failed"}],"schema_version":1}').encode("utf-8")
    assert canonical_event_batch(model) == expected
    assert "Masaüstü".encode("utf-8") in expected and b"\\u00fc" not in expected
    assert event_batch_digest(model) == hashlib.sha256(expected).hexdigest()
