"""The built-in alert rules and the alert cursor as pure functions; no database.

The same rules run on PostgreSQL inside ingestion in
tests/integration/test_alerts.py (stored parents, deduplication, the cap).
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from uuid import UUID, uuid4

import pytest

from security_platform.event_contracts import EventBatch, masked_image_path
from security_platform.services import alerts
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
    assert alerts.SEVERITY == {"user_writable_launch": "low", "office_browser_spawned_tool": "medium",
                               "sensor_unstable": "medium", "event_loss": "medium"}
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
