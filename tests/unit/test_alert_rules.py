"""The built-in alert rules, the silence sweep's pure parts and the alert cursor as pure functions; no database.

The same rules run on PostgreSQL inside ingestion in
tests/integration/test_alerts.py (stored parents, deduplication, the cap);
the Stage 3 rules, the exact-parent lookup and `security-platform sweep` in
tests/integration/test_stage3_alerts.py.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace
from uuid import UUID, uuid4

from pydantic import ValidationError
import pytest

from security_platform.event_contracts import (AGENT_STATE_SUBJECTS, BEHAVIOR_RULES, EVENT_FIELDS, EVENT_MODELS_V2,
                                               TAMPER_SIGNALS, EventBatch, EventBatchV2, masked_image_path,
                                               stored_event_bytes)
from security_platform.services import alerts, sweep
from security_platform.services.common import ServiceError


VOLUME = r"\Device\HarddiskVolume3"
WIDE = "\U0001F600"  # four UTF-8 bytes
WORD = VOLUME + r"\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"
CMD = VOLUME + r"\Windows\System32\cmd.exe"


def path(*parts):
    return "\\".join((VOLUME, *parts))


def launch(seq, image, pid, parent=4):
    return {"kind": "process_started", "event_seq": seq, "observed_at": "2030-01-02T03:00:00Z", "pid": pid,
            "parent_pid": parent, "session_id": 1, "image": image}


def stop(seq, pid):
    return {"kind": "process_stopped", "event_seq": seq, "observed_at": "2030-01-02T03:00:01Z", "pid": pid,
            "exit_code": 0, "image": None}


def state(seq, value, code=None):
    return {"kind": "sensor_state", "event_seq": seq, "observed_at": "2030-01-02T03:00:02Z", "state": value,
            "error_code": code}


def matches(*items, previous=None):
    """(rule, key text, first_seq, last_seq, occurrences, evidence) of one contract-valid batch.

    The batches here start at event_seq 1 or find every parent in the batch,
    so the stored-event lookup never needs a database.
    """
    batch = EventBatch.model_validate({"schema_version": 1, "batch_id": str(uuid4()), "batch_sequence": 1,
                                       "events": list(items)})
    return [(match.rule, match.key, match.first_seq, match.last_seq, match.occurrences, match.evidence)
            for match in alerts.batch_matches(None, None, batch.events, previous)]


def stored_bytes(value):
    # Independent restatement of PostgreSQL's jsonb text: ", " and ": " separators, UTF-8.
    return len(json.dumps(value, ensure_ascii=False, separators=(", ", ": ")).encode("utf-8"))


USER_WRITABLE = [
    path("Users", "*", "AppData", "Local", "Temp", "a.exe"),
    path("Users", "*", "AppData", "Roaming", "b.exe"),
    path("users", "*", "appdata", "c.exe"),
    path("USERS", "*", "APPDATA", "d.exe"),
    path("Users", "*", "aPpDaTa", "e.exe"),
    path("Users", "*", "Downloads", "setup.exe"),
    path("Users", "*", "DOWNLOADS", "setup.exe"),
    # The profile folder's own stream: its part before the first ':' is the mask.
    path("Users", "*:stream", "AppData", "f.exe"),
    path("Users", "*", "Downloads:zone", "g.exe"),
    path("Windows", "Temp", "h.exe"),
    path("Windows", "TEMP", "i.exe"),
    path("data", "temp:ads", "j.exe"),
    "C:/Users/*/Downloads/k.exe",
    "D:/Temp/l.exe",
    # `Users:x` needs no mask under the contract, but the rule compares its part before ':'.
    path("Users:x", "Public", "m.exe"),
]

NOT_USER_WRITABLE = [
    path("Windows", "Temporary", "a.exe"),
    path("Windows", "MyTemp", "a.exe"),
    path("Windows", "Temp.old", "a.exe"),
    path("Tools", "temp.exe"),
    path("Users", "*", "Documents", "a.exe"),
    path("Users", "*", "Desktop", "AppData", "a.exe"),
    path("Users", "*", "Download", "a.exe"),
    path("Users", "*", "AppDataLocal", "a.exe"),
    path("Users", "*", "Public", "a.exe"),
    path("ProgramData", "AppData", "a.exe"),
    path("Users", "*"),
    path("Program Files", "Downloads", "a.exe"),
    "Registry",
]


@pytest.mark.parametrize("image", USER_WRITABLE)
def test_user_writable_places_match_case_insensitively_before_the_first_colon(image):
    assert masked_image_path(image) == image
    assert alerts.user_writable(image) is True


@pytest.mark.parametrize("image", NOT_USER_WRITABLE)
def test_near_misses_are_not_user_writable(image):
    assert masked_image_path(image) == image
    assert alerts.user_writable(image) is False


def test_the_public_profile_branch_is_reached_only_by_unusual_users_components():
    # The agent masks every profile folder, Public included (`Users\Public` is
    # sent as `Users\*`), and the contract refuses the unmasked form.
    image = r"\Users\Public\Downloads\a.exe"
    assert alerts.user_writable(image) is True
    with pytest.raises(ValueError, match="unmasked_user_folder"):
        masked_image_path(image)


def test_file_names_are_the_last_component_casefolded_before_the_first_colon():
    assert alerts.file_name(WORD) == "winword.exe"
    assert alerts.file_name(VOLUME + r"\x\cmd.exe:stream") == "cmd.exe"
    assert alerts.file_name("C:/Windows/System32/PowerShell.EXE") == "powershell.exe"
    assert alerts.file_name("Registry") == "registry"


def test_rule_tables_are_the_fixed_lists():
    # ADR 0004 section 7: the four Stage 2 rules, then the six Stage 3 rules, in this order; low or medium only.
    assert alerts.SEVERITY == {"user_writable_launch": "low", "office_browser_spawned_tool": "medium",
                               "sensor_unstable": "medium", "event_loss": "medium", "scan_detection": "medium",
                               "behavior_match": "medium", "persistence_added": "low", "capability_down": "medium",
                               "tamper_signal": "medium", "agent_silent": "medium"}
    assert alerts.RULES == ("user_writable_launch", "office_browser_spawned_tool", "sensor_unstable", "event_loss",
                            "scan_detection", "behavior_match", "persistence_added", "capability_down",
                            "tamper_signal", "agent_silent") == tuple(alerts.SEVERITY)
    assert set(alerts.SEVERITY.values()) == {"low", "medium"}
    # Every closed behavior rule id, in the contract's order, has the server's severity.
    assert alerts.BEHAVIOR_SEVERITY == dict.fromkeys(BEHAVIOR_RULES, "medium") and len(BEHAVIOR_RULES) == 10
    assert tuple(alerts.BEHAVIOR_SEVERITY) == BEHAVIOR_RULES
    assert alerts.TOOLS == {"mshta.exe", "regsvr32.exe", "rundll32.exe", "wscript.exe", "cscript.exe",
                            "powershell.exe", "pwsh.exe", "cmd.exe", "certutil.exe", "bitsadmin.exe", "msbuild.exe",
                            "installutil.exe", "wmic.exe", "schtasks.exe"}
    assert alerts.OFFICE_AND_BROWSERS == {"winword.exe", "excel.exe", "powerpnt.exe", "outlook.exe", "msaccess.exe",
                                          "mspub.exe", "onenote.exe", "visio.exe", "chrome.exe", "msedge.exe",
                                          "firefox.exe", "brave.exe", "opera.exe", "iexplore.exe"}
    assert alerts.PARENT_LOOKBACK == 2000


def test_dedup_key_is_the_lowercase_hex_sha256_of_the_key_text():
    assert alerts.dedup_key("winword.exe>cmd.exe") == hashlib.sha256(b"winword.exe>cmd.exe").hexdigest()
    assert alerts.dedup_key("çalış") == hashlib.sha256("çalış".encode("utf-8")).hexdigest()
    assert all(len(alerts.dedup_key(text)) == 64 and alerts.dedup_key(text) == alerts.dedup_key(text).lower()
               for text in ("lost", "event_loss", path("Windows", "Temp", "a.exe").casefold()))


def test_one_batch_groups_every_rule_match_per_key():
    setup = path("Users", "*", "Downloads", "Setup.exe")
    found = matches(
        launch(1, WORD, pid=10), launch(2, setup, pid=11), launch(3, CMD, pid=12, parent=10),
        state(4, "lost", "session_in_use"), launch(5, path("USERS", "*", "downloads", "SETUP.EXE"), pid=13),
        launch(6, VOLUME + r"\Windows\System32\CMD.EXE", pid=14, parent=10), state(7, "lost"),
        state(8, "failed", "access_denied"), state(9, "started"), state(10, "stopped"))
    assert found == [
        # Same image text casefolded: one key, the latest evidence.
        ("user_writable_launch", setup.casefold(), 2, 5, 2,
         {"image": path("USERS", "*", "downloads", "SETUP.EXE"), "pid": 13}),
        ("office_browser_spawned_tool", "winword.exe>cmd.exe", 3, 6, 2,
         {"image": VOLUME + r"\Windows\System32\CMD.EXE", "pid": 14, "parent_image": WORD, "parent_pid": 10}),
        ("sensor_unstable", "lost", 4, 7, 2, {"state": "lost", "error_code": None}),
        ("sensor_unstable", "failed", 8, 8, 1, {"state": "failed", "error_code": "access_denied"}),
    ]


def office(found):
    return [(key, first, evidence["parent_image"]) for rule, key, first, _, _, evidence in found
            if rule == "office_browser_spawned_tool"]


def test_a_parent_in_the_batch_is_the_latest_start_of_its_pid_without_a_stop_between():
    browser = VOLUME + r"\Program Files\Google\Chrome\Application\chrome.exe"
    notepad = VOLUME + r"\Windows\notepad.exe"
    # Started, then stopped: the pid's process ended before the child.
    assert office(matches(launch(1, WORD, pid=10), stop(2, 10), launch(3, CMD, pid=11, parent=10))) == []
    # pid reuse: the newer start decides, in both directions.
    assert office(matches(launch(1, WORD, pid=10), stop(2, 10), launch(3, notepad, pid=10),
                          launch(4, CMD, pid=11, parent=10))) == []
    assert office(matches(launch(1, notepad, pid=10), stop(2, 10), launch(3, browser, pid=10),
                          launch(4, path("Windows", "System32", "mshta.exe"), pid=11, parent=10))) == [
        ("chrome.exe>mshta.exe", 4, browser)]
    # A reused pid without a stop in between: still the latest start.
    assert office(matches(launch(1, WORD, pid=10), launch(2, notepad, pid=10), launch(3, CMD, pid=11, parent=10))) == []
    # Neither a non-tool child of an office parent nor a tool under any other parent.
    assert office(matches(launch(1, WORD, pid=10), launch(2, notepad, pid=11, parent=10),
                          launch(3, CMD, pid=12, parent=11))) == []
    # A stream suffix on either image is not part of the file name.
    assert office(matches(launch(1, WORD + ":x", pid=10), launch(2, CMD + ":y", pid=11, parent=10))) == [
        ("winword.exe>cmd.exe", 2, WORD + ":x")]


@pytest.mark.parametrize("child,found", [(2001, True), (2002, False)])
def test_the_parent_lookback_is_the_previous_2000_event_seq_values(child, found):
    # The device's first batch: a gap is no event loss, and the window counts event_seq values.
    result = matches(launch(1, WORD, pid=10), launch(child, CMD, pid=11, parent=10))
    assert office(result) == ([("winword.exe>cmd.exe", child, WORD)] if found else [])
    assert [rule for rule, *_ in result] == (["office_browser_spawned_tool"] if found else [])


def loss(found):
    return [(first, last, occurrences, evidence) for rule, _, first, last, occurrences, evidence in found
            if rule == "event_loss"]


def test_event_loss_counts_gaps_inside_and_before_the_batch_but_never_on_a_first_batch():
    sensors = [state(seq, "started") for seq in (5, 6, 9, 20)]
    assert loss(matches(*sensors)) == []
    assert loss(matches(*sensors[:3], previous=4)) == [(9, 9, 1, {"missing_events": 2})]
    # 2..4 before the batch, 7..8 and 10..19 inside it: three gaps, 15 missing events.
    assert loss(matches(*sensors, previous=1)) == [(5, 20, 3, {"missing_events": 15})]
    assert loss(matches(*[state(seq, "started") for seq in (5, 6, 7)], previous=4)) == []
    assert matches(state(5, "started"), previous=4) == []


def test_bounded_evidence_shortens_both_paths_from_their_start_and_keeps_the_masks():
    parent = path("Users", "*", "AppData", WIDE * 950, "parent.exe")
    child = path("Users", "*", "Downloads", WIDE * 950, "child.exe")
    for image in (parent, child):
        assert masked_image_path(image) == image and len(image) <= 1024
    evidence = {"image": child, "pid": 11, "parent_image": parent, "parent_pid": 10}
    assert stored_bytes(evidence) > 4096
    bounded = alerts.bounded_evidence(evidence)
    assert set(bounded) == set(evidence) and (bounded["pid"], bounded["parent_pid"]) == (11, 10)
    assert 4096 - 8 <= stored_bytes(bounded) <= 4096
    for key, name in (("image", "\\child.exe"), ("parent_image", "\\parent.exe")):
        assert bounded[key].startswith("…") and bounded[key].endswith(name)
        assert evidence[key].endswith(bounded[key][1:])
        # A leading ellipsis never forms a bare `Users` component.
        assert masked_image_path(bounded[key]) == bounded[key]
    # A short path keeps all of itself; the long one takes the rest of the budget.
    short = {**evidence, "parent_image": WORD}
    kept = alerts.bounded_evidence(short)
    assert kept["parent_image"] == WORD and kept["image"].endswith("\\child.exe") and stored_bytes(kept) <= 4096
    # JSON escapes count twice: quotes and backslashes.
    escaped = {**evidence, "image": "\\" + '"\\' * 1000, "parent_image": "\\" + '"\\' * 1000}
    assert stored_bytes(escaped) > 4096 and stored_bytes(alerts.bounded_evidence(escaped)) <= 4096
    small = {"image": WORD, "pid": 1, "parent_image": WORD, "parent_pid": 2}
    assert alerts.bounded_evidence(small) == small


def test_keyset_cursor_is_both_or_neither_with_six_fraction_digits():
    identity = uuid4()
    assert alerts.parse_keyset(None, None) is None
    assert alerts.parse_keyset("2030-01-02T03:04:05.000001Z", identity) == (
        datetime(2030, 1, 2, 3, 4, 5, 1, tzinfo=timezone.utc), identity)
    for seen_at, before_id in (("2030-01-02T03:04:05.000001Z", None), (None, identity),
                               ("2030-01-02T03:04:05Z", identity), ("2030-01-02T03:04:05.123Z", identity),
                               ("2030-01-02T03:04:05.000000+00:00", identity), ("2030-02-30T03:04:05.000000Z", identity),
                               ("2030-01-02 03:04:05.000000Z", identity), ("２０３０-01-02T03:04:05.000000Z", identity),
                               ("2030-01-02T03:04:05.000000Z", str(identity)), (datetime(2030, 1, 2), identity)):
        with pytest.raises(ServiceError, match="^Invalid pagination$"):
            alerts.parse_keyset(seen_at, before_id)
    assert alerts.keyset_time(datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)) == "2030-01-02T03:04:05.000000Z"
    istanbul = timezone(timedelta(hours=3))
    assert alerts.keyset_time(datetime(2030, 1, 2, 6, 4, 5, 7, tzinfo=istanbul)) == "2030-01-02T03:04:05.000007Z"
    assert isinstance(alerts.parse_keyset(alerts.keyset_time(datetime.now(timezone.utc)), identity)[1], UUID)


# --- Stage 3 (ADR 0004 section 7, P1 brief section 8): events v2 and the five event rules -------------------

CREATED = "2030-01-02T02:59:00.000001Z"
DIGEST = "0123456789abcdef" * 4
MASKED = path("Users", "*", "Downloads", "setup.exe")
NOTEPAD = VOLUME + r"\Windows\notepad.exe"
CHROME = VOLUME + r"\Program Files\Google\Chrome\Application\chrome.exe"
MSHTA = VOLUME + r"\Windows\System32\mshta.exe"
POWERSHELL = path("Windows", "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
DEVICE = SimpleNamespace(tenant_id=UUID(int=1), id=UUID(int=2))
# The event kind behind each Stage 3 event rule.
RULE_KINDS = {"scan_detection": "scan_detected", "behavior_match": "behavior_match",
              "persistence_added": "persistence_change", "capability_down": "agent_state",
              "tamper_signal": "tamper_signal"}
CLAIMS = re.compile(r"protect|rules_loaded|realtime_protection|blocked|prevented|verified", re.IGNORECASE)
CONSOLE = Path(__file__).resolve().parents[2] / "operator-console" / "src"


def when(index):
    """A distinct canonical create time for each index below 10**6."""
    return f"2030-01-02T02:00:00.{index:06d}Z"


def v2_launch(seq, image, pid, parent=4, *, created=None, parent_created=None):
    event = {**launch(seq, image, pid, parent), "create_time": created or when(pid)}
    if parent_created is not None:
        event["parent_create_time"] = parent_created
    return event


def v2_stop(seq, pid, created=None):
    return {**stop(seq, pid), "create_time": created or when(pid)}


def scan(seq, **changes):
    return {"kind": "scan_detected", "event_seq": seq, "observed_at": "2030-01-02T03:00:03Z", "trigger": "file_change",
            "path": MASKED, "size": 68, "sha256": DIGEST, "rule_set_id": "a" * 64,
            "hits": [{"rule": "Sample_Rule", "severity": "high"}], "omitted_hits": 0, "pid": 4321,
            "create_time": CREATED, "action_id": None, **changes}


def behavior(seq, **changes):
    return {"kind": "behavior_match", "event_seq": seq, "observed_at": "2030-01-02T03:00:04Z",
            "rule": "encoded_powershell", "rule_version": 1, "pid": 4321, "create_time": CREATED, "image": POWERSHELL,
            "parent_image": WORD, "found_at_start": False, "command_line_source": "kernel_logger", **changes}


def persistence(seq, **changes):
    return {"kind": "persistence_change", "event_seq": seq, "observed_at": "2030-01-02T03:00:05Z",
            "location": "run_key", "scope": "user", "change": "added", "entry_id": "b" * 64, "target_image": MASKED,
            "found_at_start": False, **changes}


def agent(seq, subject="realtime_scan", value="stopped", **changes):
    return {"kind": "agent_state", "event_seq": seq, "observed_at": "2030-01-02T03:00:06Z", "subject": subject,
            "state": value, "code": None, "rule_set_id": None, **changes}


def tamper(seq, signal="service_config_changed", detail=None):
    return {"kind": "tamper_signal", "event_seq": seq, "observed_at": "2030-01-02T03:00:07Z", "signal": signal,
            "detail": detail}


def gap(seq, **changes):
    return {"kind": "coverage_gap", "event_seq": seq, "observed_at": "2030-01-02T03:00:08Z",
            "source": "process_sensor", "reason": "etw_events_lost", "lost": 12, **changes}


class StoredParents:
    """A stand-in session for the one stored exact-parent lookup: it records each call and answers from `images`.

    Any other statement, such as the 2000-event window's stored lookup, fails the test.
    """

    def __init__(self, images=None):
        self.images, self.calls = dict(images or {}), []

    def execute(self, statement, parameters):
        assert statement is alerts._EXACT_PARENTS, statement
        self.calls.append(parameters)
        rows = [(pid, created, self.images[(int(pid), created)])
                for pid, created in zip(parameters["pids"], parameters["create_times"])
                if (int(pid), created) in self.images]
        return SimpleNamespace(all=lambda: rows)


def v2_batch(*items):
    return EventBatchV2.model_validate({"schema_version": 2, "batch_id": str(uuid4()), "batch_sequence": 1,
                                        "events": list(items)})


def v2_matches(*items, previous=None, session=None):
    """(rule, key text, first_seq, last_seq, occurrences, evidence, severity) of one contract-valid v2 batch."""
    found = alerts.batch_matches(session or StoredParents(), DEVICE, v2_batch(*items).events, previous)
    return [(match.rule, match.key, match.first_seq, match.last_seq, match.occurrences, match.evidence,
             match.severity) for match in found]


def reported(event, rule):
    """What a Stage 3 event rule keeps: the validated event's own fields of its kind, as stored."""
    payload = EVENT_MODELS_V2[event["kind"]].model_validate(event).model_dump(mode="json")
    return {name: payload[name] for name in EVENT_FIELDS[RULE_KINDS[rule]]}


def office_v2(found):
    return [(key, first, evidence["parent_image"]) for rule, key, first, _, _, evidence, _ in found
            if rule == "office_browser_spawned_tool"]


def test_stage3_tables_follow_the_event_contracts():
    # Each event rule keeps its kind's timeline fields (event_contracts.EVENT_FIELDS): the shape the console reads.
    assert alerts.EVIDENCE_FIELDS == {rule: EVENT_FIELDS[kind] for rule, kind in RULE_KINDS.items()}
    assert (*alerts.EVIDENCE_FIELDS, "agent_silent") == alerts.RULES[4:]
    assert alerts.CAPABILITY_DOWN == {"realtime_scan": ("stopped", "failed"),
                                      "rule_set": ("missing", "invalid", "unreadable"),
                                      "file_change_sensor": ("failed",), "command_line_sensor": ("failed",),
                                      "persistence_watch": ("failed",), "response_channel": ("journal_invalid",)}
    assert all(set(states) <= set(AGENT_STATE_SUBJECTS[subject]) for subject, states in alerts.CAPABILITY_DOWN.items())
    assert alerts.PERSISTENCE_ADDED_CHANGES == ("added", "modified")
    assert (sweep.RULE, sweep.EVIDENCE_FIELDS, sweep.HEARTBEAT_FACTOR, sweep.SWEEP_CHUNK_DEVICES) == (
        "agent_silent", ("last_received_at", "threshold_seconds"), 3, 200)
    assert sweep.RESULT_KEYS == ("tenants", "failed_tenants", "devices_checked", "alerts_opened", "already_alerted",
                                 "suppressed", "devices_busy")


def test_no_rule_evidence_or_sweep_count_name_claims_protection():
    names = [*alerts.RULES, *(name for fields in alerts.EVIDENCE_FIELDS.values() for name in fields),
             *sweep.EVIDENCE_FIELDS, *sweep.RESULT_KEYS]
    assert [name for name in names if CLAIMS.search(name)] == []


def console_text(relative, start, end):
    text = (CONSOLE / relative).read_text(encoding="utf-8")
    head = text.index(start) + len(start)
    return text[head:text.index(end, head)]


def test_capability_down_and_the_silence_evidence_equal_the_consoles():
    table = console_text("data/contracts.ts", "export const CAPABILITY_DOWN_STATES = {", "} as const;")
    console = {subject: tuple(re.findall(r'"(\w+)"', states))
               for subject, states in re.findall(r"(\w+): \[([^\]]*)\]", table)}
    assert console == alerts.CAPABILITY_DOWN and list(console) == list(alerts.CAPABILITY_DOWN)
    normalize = (CONSOLE / "data/normalize.ts").read_text(encoding="utf-8")
    assert 'shape(value.evidence, ["last_received_at", "threshold_seconds"])' in normalize


def test_scan_detection_raises_on_every_scan_keyed_by_its_sha256():
    other = "fedcba9876543210" * 4
    second = scan(2, path=path("Windows", "Temp", "x.dll"), trigger="startup_scan", pid=None, create_time=None)
    third = scan(3, sha256=other, hits=[{"rule": "Other.Rule-1", "severity": "low"}, {"rule": "R2", "severity": "medium"}],
                 omitted_hits=4096, action_id="00000000-0000-4000-8000-000000000001")
    assert v2_matches(scan(1), second, third) == [
        # The same content: one key, the latest evidence.
        ("scan_detection", DIGEST, 1, 2, 2, reported(second, "scan_detection"), "medium"),
        ("scan_detection", other, 3, 3, 1, reported(third, "scan_detection"), "medium")]
    assert tuple(reported(third, "scan_detection")) == EVENT_FIELDS["scan_detected"]


def test_behavior_match_is_keyed_by_rule_and_casefolded_image():
    latest = behavior(4, image=POWERSHELL.upper(), rule_version=2, parent_image=None, found_at_start=True,
                      command_line_source="process_query")
    certutil = behavior(3, rule="certutil_download_or_decode", image=path("Windows", "System32", "certutil.exe"))
    key = "encoded_powershell>" + POWERSHELL.casefold()
    assert alerts.behavior_key("encoded_powershell", POWERSHELL.upper()) == key
    assert v2_matches(behavior(1), behavior(2), certutil, latest) == [
        ("behavior_match", key, 1, 4, 3, reported(latest, "behavior_match"), "medium"),
        ("behavior_match", "certutil_download_or_decode>" + certutil["image"].casefold(), 3, 3, 1,
         reported(certutil, "behavior_match"), "medium")]
    # No rule id holds the separator, so two (rule, image) pairs never share a key text.
    assert all(">" not in rule for rule in BEHAVIOR_RULES)


def test_a_behavior_match_alerts_severity_comes_from_the_servers_table(monkeypatch):
    monkeypatch.setitem(alerts.BEHAVIOR_SEVERITY, "shadow_copy_deletion", "low")
    found = v2_matches(behavior(1), behavior(2, rule="shadow_copy_deletion"))
    assert [(key.partition(">")[0], severity) for _, key, *_, severity in found] == [
        ("encoded_powershell", "medium"), ("shadow_copy_deletion", "low")]
    assert alerts.SEVERITY["behavior_match"] == "medium"
    # The agent cannot send a severity: the contract refuses the key in the event.
    for value in ("low", "medium", "high"):
        with pytest.raises(ValidationError, match="severity"):
            v2_batch(behavior(1, severity=value))


def test_persistence_added_raises_on_added_or_modified_entries_and_never_on_a_removal():
    modified = persistence(2, change="modified", target_image=None, found_at_start=True)
    service = persistence(5, entry_id="d" * 64, location="service", scope="machine")
    assert v2_matches(persistence(1), modified, persistence(3, change="removed"),
                      persistence(4, change="removed", entry_id="c" * 64), service) == [
        ("persistence_added", "b" * 64, 1, 2, 2, reported(modified, "persistence_added"), "low"),
        ("persistence_added", "d" * 64, 5, 5, 1, reported(service, "persistence_added"), "low")]
    assert v2_matches(persistence(1, change="removed")) == []


AGENT_PAIRS = [(subject, value) for subject, states in AGENT_STATE_SUBJECTS.items() for value in states]


@pytest.mark.parametrize("subject,value", AGENT_PAIRS)
def test_capability_down_raises_exactly_on_the_listed_agent_states(subject, value):
    event = agent(1, subject, value, rule_set_id="c" * 64 if subject == "rule_set" else None,
                  code="unclean_stop" if (subject, value) == ("service", "started") else None)
    expected = [("capability_down", subject, 1, 1, 1, reported(event, "capability_down"), "medium")]
    assert v2_matches(event) == (expected if value in alerts.CAPABILITY_DOWN.get(subject, ()) else [])


def test_capability_down_is_keyed_by_subject_and_keeps_the_latest_state():
    assert sum(value in alerts.CAPABILITY_DOWN.get(subject, ()) for subject, value in AGENT_PAIRS) == 9
    failed, invalid = agent(3, "realtime_scan", "failed"), agent(4, "rule_set", "invalid")
    found = v2_matches(agent(1, "realtime_scan", "stopped"), agent(2, "realtime_scan", "running"), failed, invalid,
                       agent(5, "rule_set", "compiled", rule_set_id="c" * 64))
    assert found == [("capability_down", "realtime_scan", 1, 3, 2, reported(failed, "capability_down"), "medium"),
                     ("capability_down", "rule_set", 4, 4, 1, reported(invalid, "capability_down"), "medium")]
    # The console requires a null code here: only (service, started) carries one, and it raises nothing.
    assert [evidence["code"] for *_, evidence, _ in found] == [None, None]


def test_tamper_signal_raises_on_every_signal_keyed_by_the_signal():
    signals = [tamper(seq, signal, "security" if signal == "event_log_cleared" else None)
               for seq, signal in enumerate(TAMPER_SIGNALS, start=1)]
    found = v2_matches(*signals, tamper(len(signals) + 1, "event_log_cleared", "system"))
    assert [(rule, key, occurrences, severity) for rule, key, _, _, occurrences, _, severity in found] == [
        ("tamper_signal", signal, 2 if signal == "event_log_cleared" else 1, "medium") for signal in TAMPER_SIGNALS]
    assert {key: evidence for _, key, _, _, _, evidence, _ in found}["event_log_cleared"] == {
        "signal": "event_log_cleared", "detail": "system"}


def test_coverage_gaps_and_other_states_raise_nothing_and_v2_sensor_states_keep_sensor_unstable():
    assert v2_matches(gap(1), gap(2, source="agent_records", reason="queue_overflow", lost=None),
                      agent(3, "realtime_scan", "degraded"), agent(4, "file_change_sensor", "not_available"),
                      agent(5, "service", "stopping"), agent(6, "persistence_watch", "stopped"),
                      persistence(7, change="removed")) == []
    assert v2_matches(state(1, "lost", "session_in_use"), state(2, "failed"), state(3, "stopped"), state(4, "lost")) == [
        ("sensor_unstable", "lost", 1, 4, 2, {"state": "lost", "error_code": None}, "medium"),
        ("sensor_unstable", "failed", 2, 2, 1, {"state": "failed", "error_code": None}, "medium")]


def test_events_raise_every_rule_but_agent_silent():
    found = v2_matches(v2_launch(3, WORD, pid=10), v2_launch(4, path("Users", "*", "AppData", "x.exe"), pid=11),
                       v2_launch(5, CMD, pid=12, parent=10), state(6, "lost"), scan(7), behavior(8), persistence(9),
                       agent(10), tamper(11), gap(12), previous=1)
    assert sorted({rule for rule, *_ in found}) == sorted(set(alerts.RULES) - {"agent_silent"})


def test_v1_events_and_the_v2_shapes_of_the_v1_kinds_raise_the_stage2_matches():
    setup = path("Users", "*", "Downloads", "Setup.exe")
    v1 = [launch(1, WORD, pid=10), launch(2, setup, pid=11), launch(3, CMD, pid=12, parent=10), stop(4, 10),
          launch(5, CMD, pid=13, parent=10), state(6, "lost", "session_in_use"), launch(7, CHROME, pid=14),
          launch(2007, MSHTA, pid=15, parent=14), launch(2008, CMD, pid=16, parent=14),
          state(2009, "failed", "access_denied")]
    # v1 is unchanged: the window (a parent 2000 event_seq values back at most), its stop check, event_loss.
    assert matches(*v1, previous=0) == [
        ("user_writable_launch", setup.casefold(), 2, 2, 1, {"image": setup, "pid": 11}),
        ("office_browser_spawned_tool", "winword.exe>cmd.exe", 3, 3, 1,
         {"image": CMD, "pid": 12, "parent_image": WORD, "parent_pid": 10}),
        ("sensor_unstable", "lost", 6, 6, 1, {"state": "lost", "error_code": "session_in_use"}),
        ("event_loss", "event_loss", 2007, 2007, 1, {"missing_events": 1999}),
        ("office_browser_spawned_tool", "chrome.exe>mshta.exe", 2007, 2007, 1,
         {"image": MSHTA, "pid": 15, "parent_image": CHROME, "parent_pid": 14}),
        ("sensor_unstable", "failed", 2009, 2009, 1, {"state": "failed", "error_code": "access_denied"})]
    # The same events in their v2 shapes, without parent_create_time, raise exactly the same.
    v2 = [event if event["kind"] == "sensor_state" else {**event, "create_time": when(event["pid"])} for event in v1]
    for previous in (None, 0):
        found = v2_matches(*v2, previous=previous)
        assert [match[:6] for match in found] == matches(*v1, previous=previous)
        assert [match[6] for match in found] == [alerts.SEVERITY[match[0]] for match in found]


def test_an_exact_parent_in_the_batch_is_that_process_at_any_distance_and_after_its_stop():
    session = StoredParents()
    found = v2_matches(
        v2_launch(1, WORD, pid=10), v2_stop(2, 10), v2_launch(3, NOTEPAD, pid=10, created=when(99)),
        # WORD exactly: 4,000 event_seq values back, stopped and its pid reused since.
        v2_launch(4001, CMD, pid=11, parent=10, parent_created=when(10)),
        # Notepad exactly: not an office or browser parent.
        v2_launch(4002, MSHTA, pid=12, parent=10, parent_created=when(99)),
        # No parent create time: the window, whose latest pid 10 event is out of reach.
        v2_launch(4003, path("Windows", "System32", "wscript.exe"), pid=13, parent=10),
        session=session)
    assert office_v2(found) == [("winword.exe>cmd.exe", 4001, WORD)]
    assert [rule for rule, *_ in found] == ["office_browser_spawned_tool"] and session.calls == []


def test_children_naming_a_parent_outside_the_batch_take_one_stored_lookup_and_never_the_window():
    session = StoredParents({(20, when(20)): CHROME, (30, when(30)): NOTEPAD})
    found = v2_matches(
        v2_launch(5, WORD, pid=10),
        # (10, when(77)) is not the WORD process above and nothing stored has it: no match, although the window
        # would have taken WORD.
        v2_launch(6, CMD, pid=11, parent=10, parent_created=when(77)),
        v2_launch(7, MSHTA, pid=12, parent=20, parent_created=when(20)),
        v2_launch(8, path("Windows", "System32", "rundll32.exe"), pid=13, parent=20, parent_created=when(20)),
        v2_launch(9, CMD, pid=14, parent=30, parent_created=when(30)),
        # Not a tool: no parent is looked for.
        v2_launch(10, NOTEPAD, pid=15, parent=40, parent_created=when(40)),
        session=session)
    assert office_v2(found) == [("chrome.exe>mshta.exe", 7, CHROME), ("chrome.exe>rundll32.exe", 8, CHROME)]
    # One statement for the batch: its distinct identities, sorted, and only rows before the batch.
    assert session.calls == [{"pids": ["10", "20", "30"], "create_times": [when(77), when(20), when(30)],
                              "tenant_id": DEVICE.tenant_id, "device_id": DEVICE.id, "first_seq": 5}]
    # A parent must come before its child, in the batch or stored: one later in the batch is not taken.
    later = StoredParents()
    assert office_v2(v2_matches(v2_launch(1, CMD, pid=11, parent=10, parent_created=when(10)),
                                v2_launch(2, WORD, pid=10), session=later)) == []
    assert [call["first_seq"] for call in later.calls] == [1]


def longest(event, *keys, prefix, suffix):
    """`event` with its `keys` paths as long as the stored-event bound allows: 1,024 code points, four-byte ones first."""
    model, room, best = EVENT_MODELS_V2[event["kind"]], 1024 - len(prefix) - len(suffix), None
    for wide in range(room + 1):
        candidate = {**event, **dict.fromkeys(keys, prefix + WIDE * wide + "x" * (room - wide) + suffix)}
        try:
            model.model_validate(candidate)
        except ValidationError:
            break
        best = candidate
    return best


DOWNLOADS = path("Users", "*", "Downloads") + "\\"
MAXIMAL = {
    "scan_detection": lambda: longest(scan(2**53 - 1, size=2**53 - 1, pid=2**32 - 1, omitted_hits=4096,
                                           action_id="00000000-0000-4000-8000-000000000001",
                                           hits=[{"rule": f"R{index}" + "x" * 62, "severity": "high"}
                                                 for index in range(8)]),
                                      "path", prefix=DOWNLOADS, suffix=".exe"),
    "behavior_match": lambda: longest(behavior(2**53 - 1, pid=2**32 - 1, rule="certutil_download_or_decode",
                                               rule_version=65535, command_line_source="process_query"),
                                      "image", "parent_image", prefix=DOWNLOADS, suffix=".exe"),
    "persistence_added": lambda: longest(persistence(2**53 - 1, location="scheduled_task", scope="machine",
                                                     change="modified"),
                                         "target_image", prefix=DOWNLOADS, suffix=".exe"),
}


@pytest.mark.parametrize("rule", sorted(MAXIMAL))
def test_evidence_of_a_maximal_event_fits_the_4_kib_check_unshortened(rule):
    event = MAXIMAL[rule]()
    size = stored_event_bytes(EVENT_MODELS_V2[event["kind"]].model_validate(event))
    assert 4096 - 8 < size <= 4096
    [(found, _, _, _, _, evidence, _)] = v2_matches(event)
    # A subset of the event's own stored fields: smaller than the event itself, and never shortened.
    assert found == rule and evidence == reported(event, rule) and stored_bytes(evidence) < size


def test_office_evidence_of_two_maximal_v2_processes_is_bounded():
    parent = longest(v2_launch(1, WORD, pid=10), "image", prefix=path("Program Files", "Office") + "\\",
                     suffix="\\WINWORD.EXE")["image"]
    child = longest(v2_launch(2, CMD, pid=11, parent=10, parent_created=when(10)), "image",
                    prefix=path("Program Files", "Tools") + "\\", suffix="\\cmd.exe")
    [(rule, key, _, _, _, evidence, _)] = v2_matches(child, session=StoredParents({(10, when(10)): parent}))
    assert (rule, key) == ("office_browser_spawned_tool", "winword.exe>cmd.exe")
    assert stored_bytes({"image": child["image"], "parent_image": parent}) > 4096
    assert 4096 - 8 <= stored_bytes(evidence) <= 4096
    assert evidence["image"].startswith("…") and evidence["image"].endswith("\\cmd.exe")
    assert evidence["parent_image"].startswith("…") and evidence["parent_image"].endswith("\\WINWORD.EXE")


# --- `security-platform sweep` (P1 brief section 9): its pure parts ------------------------------------------

def v3_state(interval):
    return {"product_id": "edr_agent", "rule_set_state": "compiled", "heartbeat_interval_seconds": interval}


def test_the_heartbeat_interval_is_read_only_from_a_valid_v3_payload():
    for interval in (30, 60, 3600):
        assert sweep.heartbeat_interval(v3_state(interval)) == interval
    for payload in (v3_state(None), v3_state(29), v3_state(3601), v3_state(True), v3_state(60.0), v3_state("60"),
                    {"product_id": "edr_agent", "rule_set_state": "compiled"},
                    # V2 has rule_file_present and no interval; a payload with both keys is no V3.
                    {"product_id": "edr_agent", "rule_file_present": True, "heartbeat_interval_seconds": 60},
                    {**v3_state(60), "rule_file_present": True}, {}, None, [], "edr_agent"):
        assert sweep.heartbeat_interval(payload) is None, payload


def test_the_silence_threshold_is_the_larger_of_the_setting_and_three_heartbeats():
    assert sweep.silence_threshold(900, v3_state(60)) == 900
    assert sweep.silence_threshold(900, v3_state(300)) == 900
    assert sweep.silence_threshold(900, v3_state(301)) == 903
    assert sweep.silence_threshold(300, v3_state(3600)) == 10800
    assert sweep.silence_threshold(86400, v3_state(3600)) == 86400
    # V2 reports no interval: the setting alone.
    assert sweep.silence_threshold(900, {"product_id": "edr_agent", "rule_file_present": True}) == 900
    assert sweep.silence_threshold(300, v3_state(None)) == 300
    # Always inside the 300..86400 the console accepts as threshold_seconds.
    assert {sweep.silence_threshold(setting, v3_state(interval))
            for setting in (300, 86400) for interval in (30, 3600)} <= set(range(300, 86401))


def test_silence_is_strictly_more_than_the_threshold_on_the_server_clock():
    last = datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert sweep.is_silent(last + timedelta(seconds=900, microseconds=1), last, 900)
    assert not sweep.is_silent(last + timedelta(seconds=900), last, 900)
    # A last contact ahead of the server clock is no silence.
    assert not sweep.is_silent(last - timedelta(days=2), last, 300)


class NoDatabase:
    def session(self):
        raise AssertionError("the sweep opened the database")


@pytest.mark.parametrize("value", [299, 86401, 0, -1, True, "900", 900.0, None])
def test_the_sweep_refuses_an_out_of_range_setting_before_any_database_access(value):
    with pytest.raises(ValueError, match="^Invalid bounded platform setting$"):
        sweep.sweep_silent_agents(NoDatabase(), silence_alert_seconds=value)


@pytest.mark.parametrize("size", [0, 201, -1, True, 2.0, None])
def test_the_sweep_chunk_size_is_bounded(size):
    with pytest.raises(ValueError, match="^Invalid sweep chunk size$"):
        sweep.sweep_silent_agents(NoDatabase(), silence_alert_seconds=900, chunk_size=size)


def test_the_sweep_needs_an_aware_server_time():
    with pytest.raises(ValueError, match="timezone-aware"):
        sweep.sweep_silent_agents(NoDatabase(), silence_alert_seconds=900, now=datetime(2030, 1, 2))
