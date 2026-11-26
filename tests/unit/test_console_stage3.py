"""Stage 3 (ADR 0004, P1): the operator console mirrors events v2, Snapshot V3 and the ten alert rules.

The console refuses a whole page or device detail on any unknown key or value, so its closed lists must equal the
Platform's. As in test_console_edr_agent.py, no TypeScript runs here: the sources are read as text, and the
expressions that carry a rule are pinned exactly. The Python names CORE and RULES add in P1 are looked up by name,
so a test fails with the missing name while one does not exist yet.
"""
from datetime import datetime, timedelta, timezone
import importlib
import json
import re
from types import SimpleNamespace
from typing import get_args
from uuid import UUID

import pytest

from test_console_edr_agent import FORBIDDEN, block, catalog, flat, names, source
from test_console_preview_server import _budgets, _fits


# Wording no new console string may use, beyond test_console_edr_agent.FORBIDDEN: a protection, blocking, prevention
# or verification claim. "engellemez" ("does not block") is the V3 card's pinned note and the one allowed form.
CLAIMS = re.compile(r"protect|korum|engelle|blocked|prevented|verified|doğrulandı", re.IGNORECASE)
NEW_RULES = ("scan_detection", "behavior_match", "persistence_added", "capability_down", "tamper_signal", "agent_silent")
V2_KINDS = ("scan_detected", "behavior_match", "persistence_change", "agent_state", "tamper_signal", "coverage_gap")
V3_COUNTERS = ("scans_completed", "scans_detected", "scans_no_verdict", "scan_jobs_dropped", "scan_cache_hits",
               "etw_events_lost", "file_change_gaps", "cmdline_unavailable")
LANGUAGES = [("events", "export const eventsTr = {", "\n};", "products", "export const productsTr = {", "\n};"),
             ("events", "export const eventsEn = {", "\n} satisfies", "products", "export const productsEn = {",
              "\n} satisfies")]


def pinned(module, name):
    """A Python name the P1 brief pins; while CORE or RULES has not added it, the test fails naming it."""
    loaded = importlib.import_module(f"security_platform.{module}")
    if not hasattr(loaded, name):
        pytest.fail(f"pinned Python name not found: security_platform.{module}.{name}")
    return getattr(loaded, name)


def ts_list(relative, name):
    return tuple(names(block(source(relative), f"export const {name} = [", "] as const;")))


def ts_table(text):
    """The `key: ["a", "b"]` rows of a TypeScript object literal, in source order."""
    return {key: tuple(names(items)) for key, items in re.findall(r"(\w+): \[([^\]]*)\]", text)}


def ts_pattern(name):
    return re.search(rf"const {name} = /(.+)/;", source("data/normalize.ts"))[1].replace("\\/", "/")


def ts_event_view_fields():
    """contracts.ts EVENT_VIEW_FIELDS: the EVENT_FIELDS rows spread first, then its own rows replacing those kinds."""
    contracts_ts = source("data/contracts.ts")
    view = block(contracts_ts, "export const EVENT_VIEW_FIELDS = {", "} as const satisfies")
    assert flat(view).strip().startswith("...EVENT_FIELDS,")
    return {**ts_table(block(contracts_ts, "export const EVENT_FIELDS = {", "} as const satisfies")), **ts_table(view)}


def strings(start, end, relative):
    return catalog(f"i18n/catalogs/{relative}.ts", start, end)


def accepted(model, value):
    from pydantic import ValidationError

    try:
        return model.model_validate(value)
    except ValidationError:
        return None


# --- Closed sets: the console's mirrors equal the Python names.

def test_event_kinds_mirror_event_contracts():
    kinds = ts_list("data/contracts.ts", "EVENT_KINDS")
    assert kinds == tuple(pinned("event_contracts", "EVENT_KINDS"))
    assert kinds[:3] == tuple(pinned("event_contracts", "EVENT_KINDS_V1")) and kinds[3:] == V2_KINDS


def test_event_fields_mirror_event_contracts_in_order():
    table = ts_table(block(source("data/contracts.ts"), "export const EVENT_FIELDS = {", "} as const satisfies"))
    platform = pinned("event_contracts", "EVENT_FIELDS")
    assert table == {kind: tuple(fields) for kind, fields in platform.items()}
    assert tuple(table) == ts_list("data/contracts.ts", "EVENT_KINDS")
    # Privacy (ADR 1.4): a file SHA-256 and size exist only in scan_detected; no kind carries text or a user.
    assert [kind for kind, fields in table.items() if "sha256" in fields or "size" in fields] == ["scan_detected"]
    assert not {"command_line", "user", "username", "sid", "content"} & {field for fields in table.values() for field in fields}


def test_event_view_fields_mirror_event_contracts_in_order():
    # P1 brief, section 5 addendum: a timeline item names coverage_gap's own source gap_source, because `source` is
    # the item's trust label. The console derives the names from EVENT_FIELDS with that one rename, as Python does.
    view = flat(block(source("data/contracts.ts"), "export const EVENT_VIEW_FIELDS = {", "} as const satisfies"))
    assert view.strip() == '...EVENT_FIELDS, coverage_gap: ["gap_source", "reason", "lost"],'
    table = ts_event_view_fields()
    assert table == {kind: tuple(fields) for kind, fields in pinned("event_contracts", "EVENT_VIEW_FIELDS").items()}
    assert tuple(table) == ts_list("data/contracts.ts", "EVENT_KINDS")


@pytest.mark.parametrize("name", ["SCAN_TRIGGERS", "SCAN_HIT_SEVERITIES", "BEHAVIOR_RULES", "COMMAND_LINE_SOURCES",
                                  "PERSISTENCE_LOCATIONS", "PERSISTENCE_SCOPES", "PERSISTENCE_CHANGES",
                                  "AGENT_STATE_CODES", "TAMPER_SIGNALS", "TAMPER_DETAILS", "COVERAGE_SOURCES",
                                  "COVERAGE_REASONS"])
def test_v2_closed_sets_mirror_event_contracts(name):
    assert ts_list("data/contracts.ts", name) == tuple(pinned("event_contracts", name))


def test_agent_state_subjects_mirror_event_contracts_in_order():
    table = ts_table(block(source("data/contracts.ts"), "export const AGENT_STATE_SUBJECTS = {", "} as const;"))
    platform = pinned("event_contracts", "AGENT_STATE_SUBJECTS")
    assert table == {subject: tuple(states) for subject, states in platform.items()}
    assert tuple(table) == tuple(platform)


@pytest.mark.parametrize("name", ["RULE_SET_STATES", "CAPABILITY_STATES", "RESPONSE_CHANNEL_STATES", "RESPONSE_ACTIONS",
                                  "ISOLATION_STATES", "SERVICE_CONFIG_STATES", "PREVIOUS_RUN_ENDS",
                                  "EDR_V3_COUNTER_KEYS"])
def test_v3_closed_sets_mirror_contracts(name):
    assert ts_list("data/contracts.ts", name) == tuple(pinned("contracts", name))


def test_v3_counter_keys_are_the_v2_counters_then_the_stage3_ones():
    v2 = ts_list("data/contracts.ts", "EDR_COUNTER_KEYS")
    assert ts_list("data/contracts.ts", "EDR_V3_COUNTER_KEYS") == v2 + V3_COUNTERS


def test_v3_state_keys_equal_the_platform_model():
    normalize = source("data/normalize.ts")
    contracts_ts = source("data/contracts.ts")
    claims = names(block(normalize, "const CLAIM_KEYS = [", "];"))
    common = names(block(normalize, "const PRODUCT_KEYS = [", "];")) + claims
    own = block(normalize, "const EDR_V3_STATE_KEYS: readonly string[] = [", "];")
    keys = names(own)
    assert "...EDR_V3_COUNTER_KEYS" in own and "...EDR_CAPABILITY_KEYS" in own
    keys += list(ts_list("data/contracts.ts", "EDR_V3_COUNTER_KEYS")) + list(ts_list("data/contracts.ts", "EDR_CAPABILITY_KEYS"))
    model = pinned("contracts", "EdrAgentStatusV3")
    assert sorted(common + keys) == sorted(model.model_fields) and len(set(common + keys)) == len(common + keys)
    # Every V2 field but rule_file_present; the console tells them apart by exactly these two keys.
    v2 = pinned("contracts", "EdrAgentStatus")
    assert set(v2.model_fields) - set(model.model_fields) == {"rule_file_present"}
    assert "rule_set_state" in model.model_fields and "rule_set_state" not in v2.model_fields
    # ADR 1.3: no field name claims protection or loaded rules, in the model or in the console.
    for name in [*model.model_fields, *keys]:
        assert not re.search(r"protect|rules_loaded|realtime_protection", name, re.IGNORECASE), name
    # The four capability fields take exactly CAPABILITY_STATES, as the console's EDR_CAPABILITY_KEYS claim.
    states = pinned("contracts", "CAPABILITY_STATES")
    for key in ts_list("data/contracts.ts", "EDR_CAPABILITY_KEYS"):
        for state in states:
            assert accepted(model, {"product_id": "edr_agent", key: state}) is not None, (key, state)
        assert accepted(model, {"product_id": "edr_agent", key: "blocking"}) is None, key
    assert "export type EdrAgentStateV3 = ReportedProduct" in contracts_ts


# --- Snapshot V3 detection and normalizer rules.

def test_v3_is_told_from_v2_by_its_key_set_and_v2_keeps_its_card():
    normalize = source("data/normalize.ts")
    detector = flat(block(normalize, "export function isEdrAgentStateV3(state: object): state is EdrAgentStateV3 {", "\n}"))
    assert detector.strip() == ('return Object.prototype.hasOwnProperty.call(state, "rule_set_state") '
                                '&& !Object.prototype.hasOwnProperty.call(state, "rule_file_present");')
    product = flat(block(normalize, "function productState(", "\nexport function normalizeDeviceDetail("))
    assert 'const v3 = id === "edr_agent" && isEdrAgentStateV3(input);' in product
    assert "const value = shape(input, [...PRODUCT_KEYS, ...(v3 ? EDR_V3_STATE_KEYS : PRODUCT_STATE_KEYS[id])]);" in product
    assert product.index("if (v3) return edrAgentStateV3(value, common);") < product.index(
        'if (id === "edr_agent") return edrAgentState(value, common);')
    views = source("components/ProductViews.tsx")
    grid = flat(block(views, "function ProductGrid(", "\n}"))
    assert "const agentV3 = edr !== undefined && isV3Record(edr) ? edr : undefined;" in grid
    assert "const agent = edr !== undefined && !isV3Record(edr) ? edr : undefined;" in grid
    assert ('{agentV3 ? <EdrAgentV3Card record={agentV3}/> : agent ? <EdrAgentCard record={agent}/> '
            ': <MissingProduct id="edr_agent" selected={detail !== null}/>}') in grid
    assert "return isEdrAgentStateV3(record.state);" in block(views, "function isV3Record(", "\n}")


def test_v3_normalizer_keeps_v2_rules_and_bounds_the_stage3_fields():
    v3 = flat(block(source("data/normalize.ts"), "function edrAgentStateV3(", "\n/** The agent's own status"))
    for statement in ["requireValue(common.catalog_available === null);",
                      'requireValue(code === null || sensor === "lost" || sensor === "failed");',
                      "requireValue(engineId === null || ENGINE_PATTERN.test(engineId));",
                      "[key, value[key] === null ? null : integer(value[key])]",
                      "rule_set_id: value.rule_set_id === null ? null : hex64(value.rule_set_id),",
                      "response_actions_enabled: ascending(array(value.response_actions_enabled, RESPONSE_ACTIONS.length,"
                      " (action) => choice(action, RESPONSE_ACTIONS))),",
                      "response_key_ids: ascending(array(value.response_key_ids, 4, hex64)),",
                      "isolation_until: windowTime(value.isolation_until, true),"
                      " isolation_checked_at: windowTime(value.isolation_checked_at, true),",
                      "integer(value.heartbeat_interval_seconds, 30, 3600)",
                      "agent_started_at: timestamp(value.agent_started_at, true)"]:
        assert statement in v3, statement
    assert "rule_file_present" not in v3


def test_v3_pattern_verdicts_equal_the_platform():
    model = pinned("contracts", "EdrAgentStatusV3")
    console = re.compile(ts_pattern("BEHAVIOR_RULES_VERSION_PATTERN"))
    assert console.pattern == r"^altay-behavior/v[1-9][0-9]{0,5}$"
    for sample in ["altay-behavior/v1", "altay-behavior/v999999", "altay-behavior/v1000000", "altay-behavior/v0",
                   "altay-behavior/v01", "Altay-behavior/v1", "altay-behavior/v1 ", "altay-behavior/v1\n", "",
                   "altay-behavior/v", "altay-behavior/v12a", "altay-behavior/v١"]:
        platform_ok = accepted(model, {"product_id": "edr_agent", "behavior_rules_version": sample}) is not None
        assert platform_ok == (console.fullmatch(sample) is not None), sample
    hex64 = re.compile(ts_pattern("HEX64_PATTERN"))
    for sample in ["a" * 64, "0" * 64, "A" * 64, "a" * 63, "a" * 65, "g" * 64, " " + "a" * 63]:
        platform_ok = accepted(model, {"product_id": "edr_agent", "rule_set_id": sample}) is not None
        assert platform_ok == (hex64.fullmatch(sample) is not None), sample


def test_v3_bounds_equal_the_platform():
    model = pinned("contracts", "EdrAgentStatusV3")
    for seconds in (29, 30, 3600, 3601, 0, -30):
        platform_ok = accepted(model, {"product_id": "edr_agent", "heartbeat_interval_seconds": seconds}) is not None
        assert platform_ok == (30 <= seconds <= 3600), seconds
    window = re.compile(r"(\d{4})-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z")
    for text in ["1969-12-31T23:59:59.999999Z", "1970-01-01T00:00:00.000000Z", "9998-12-31T23:59:59.999999Z",
                 "9999-01-01T00:00:00.000000Z"]:
        state = accepted(model, {"product_id": "edr_agent", "isolation_until": text})
        if state is not None:
            dumped = state.model_dump(mode="json")["isolation_until"]
            match = window.fullmatch(dumped)
            # Whatever the Platform stores, the console's windowTime accepts.
            assert match and 1970 <= int(match[1]) <= 9998, dumped
        assert (state is not None) == ("1970" <= text[:4] <= "9998"), text


def test_v3_lists_the_platform_stores_are_the_lists_the_console_accepts():
    """The console wants each list strictly ascending (Python sorted() order, unique); whatever the Platform stores."""
    model = pinned("contracts", "EdrAgentStatusV3")
    actions = tuple(pinned("contracts", "RESPONSE_ACTIONS"))
    keys = ["1" * 64, "a" * 64, "f" * 64, "0" * 64]

    def console_ok(values, maximum):
        return len(values) <= maximum and all(left < right for left, right in zip(values, values[1:]))

    for field, maximum, samples in [
            ("response_actions_enabled", len(actions), [[], list(actions), sorted(actions), ["scan_path", "isolate_host"],
                                                        ["isolate_host", "scan_path"], ["scan_path", "scan_path"]]),
            ("response_key_ids", 4, [[], sorted(keys), keys, [keys[0], keys[0]], sorted(keys) + ["b" * 64]])]:
        for sample in samples:
            state = accepted(model, {"product_id": "edr_agent", field: sample})
            if state is not None:
                assert console_ok(state.model_dump(mode="json")[field], maximum), (field, sample)
            if console_ok(sample, maximum):
                assert state is not None and state.model_dump(mode="json")[field] == sample, (field, sample)


def test_scan_hit_rule_verdicts_equal_the_platform():
    scan = pinned("event_contracts", "ScanDetected")
    console = re.compile(ts_pattern("SCAN_RULE_PATTERN"))
    fields = {"kind": "scan_detected", "event_seq": 1, "observed_at": "2030-01-02T03:04:05.000006Z",
              "trigger": "process_start", "path": "\\Device\\HarddiskVolume3\\Users\\*\\Downloads\\demo.exe", "size": 1,
              "sha256": "a" * 64, "rule_set_id": "b" * 64, "omitted_hits": 0}
    assert accepted(scan, {**fields, "hits": [{"rule": "Demo_Rule", "severity": "low"}]}) is not None
    for sample in ["Demo_Rule", "a", "A" * 64, "A" * 65, "_x", ".x", "-x", "x-y.z_w", "x y", "x/y", "ç", ""]:
        platform_ok = accepted(scan, {**fields, "hits": [{"rule": sample, "severity": "low"}]}) is not None
        assert platform_ok == (console.fullmatch(sample) is not None), sample
    # 1-8 hits of exactly {rule, severity}, as the console's scanFields() and scanHit() accept.
    hits = [{"rule": f"Demo_Rule_{index}", "severity": "medium"} for index in range(9)]
    assert accepted(scan, {**fields, "hits": []}) is None and accepted(scan, {**fields, "hits": hits[:8]}) is not None
    assert accepted(scan, {**fields, "hits": hits}) is None
    assert accepted(scan, {**fields, "hits": [{**hits[0], "description": "x"}]}) is None
    normalize = flat(source("data/normalize.ts"))
    assert "const hits = array(value.hits, 8, scanHit); requireValue(hits.length >= 1);" in normalize
    assert 'const value = shape(input, ["rule", "severity"]);' in normalize
    assert "omitted_hits: integer(value.omitted_hits, 0, 4096)" in normalize


# --- Timeline: the Platform's event view, all nine kinds, sha256 only in scan_detected.

def test_timeline_item_keys_equal_the_platform_event_view():
    event_view = pinned("services.events", "_event_view")
    fields = pinned("event_contracts", "EVENT_FIELDS")
    views = pinned("event_contracts", "EVENT_VIEW_FIELDS")
    normalize = source("data/normalize.ts")
    assert names(block(normalize, "const EVENT_VIEW_KEYS = [", "];")) == ["event_seq", "kind", "observed_at", "received_at"]
    assert ("return [...EVENT_VIEW_KEYS, ...EVENT_VIEW_FIELDS[kind], ...CLAIM_KEYS];"
            in flat(block(normalize, "function eventViewKeys(kind: EventKind): string[] {", "\n}")))
    when = datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    for kind in pinned("event_contracts", "EVENT_KINDS"):
        # Each stored field holds its own name, so the item shows under which name each stored value arrives.
        row = SimpleNamespace(event_seq=1, kind=kind, observed_at=when, received_at=when,
                              payload={name: f"stored {name}" for name in fields[kind]})
        view = event_view(row)
        console = ["event_seq", "kind", "observed_at", "received_at", *views[kind], "source", "producer_verification"]
        assert len(set(console)) == len(console) and sorted(view) == sorted(console), kind
        assert [view[name] for name in views[kind]] == [f"stored {name}" for name in fields[kind]], kind
        assert view["source"] == "self_reported" and view["producer_verification"] == "not_verified", kind
    # The gap's own source reaches the console as gap_source, a closed value; `source` stays the claim.
    assert "gap_source: choice(value.gap_source, COVERAGE_SOURCES)" in flat(normalize)


def test_timeline_renders_every_kind_with_its_fields():
    timeline = source("features/events/DeviceTimeline.tsx")
    row = block(timeline, "function EventRow({ event }: { event: TimelineEvent }) {", "\n  return <tr>")
    fields_tsx = source("features/events/EventFields.tsx")
    kinds = ts_list("data/contracts.ts", "EVENT_KINDS")
    for kind in kinds:
        assert f"case '{kind}':" in row, kind
    labels = dict(re.findall(r"(\w+): '(events\.kind\.\w+)'",
                             block(source("features/events/eventsModel.ts"), "export const KIND_LABELS", "};")))
    assert labels == {kind: f"events.kind.{kind}" for kind in kinds}
    # Each v2 kind's renderer names every field of that kind under its view name (coverage_gap's own source is
    # gap_source; EVENT_VIEW_FIELDS).
    renderers = {"scan_detected": block(fields_tsx, "export function ScanFields(", "\nexport function BehaviorFields("),
                 "behavior_match": block(fields_tsx, "export function BehaviorFields(", "\nexport function PersistenceFields("),
                 "persistence_change": block(fields_tsx, "export function PersistenceFields(", "\n/** agent_state"),
                 "agent_state": block(fields_tsx, "export function AgentStateFieldList(", "\nexport function TamperFields("),
                 "tamper_signal": block(fields_tsx, "export function TamperFields(", "\n}\n"),
                 "coverage_gap": block(row, "case 'coverage_gap':", "break;"),
                 "process_started": block(row, "case 'process_started':", "break;"),
                 "process_stopped": block(row, "case 'process_stopped':", "break;")}
    table = ts_event_view_fields()
    columns = {"pid": "pid = ", "parent_pid": "parentPid = ", "image": "image = ", "exit_code": "exitCode = "}
    for kind, text in renderers.items():
        for field in table[kind]:
            assert f"'events.field.{field}'" in text or (field in columns and columns[field] in text), (kind, field)
    assert "case 'scan_detected':" in row and "<ScanFields fields={event} pidShown />" in row
    assert "<BehaviorFields fields={event} processShown />" in row
    assert "'events.column.details'] as const;" in timeline and '<td className="event-details-cell">{details}</td>' in timeline
    # The two v2 process times: null on a v1 row, shown as not reported.
    assert "<Moment value={event.create_time} />" in renderers["process_started"]
    assert "<Moment value={event.parent_create_time} />" in renderers["process_started"]
    assert "return value === null ? <>{t('events.notReported')}</>" in flat(fields_tsx)


def test_sha256_is_shown_only_in_scan_detected():
    fields_tsx = source("features/events/EventFields.tsx")
    scan = block(fields_tsx, "export function ScanFields(", "\nexport function BehaviorFields(")
    assert fields_tsx.count("sha256") == scan.count("sha256") == 2  # the label key and the value
    for relative in ["features/events/DeviceTimeline.tsx", "features/events/AlertsPage.tsx",
                     "features/events/eventsModel.ts", "components/ProductViews.tsx"]:
        assert "sha256" not in source(relative), relative
    contracts_ts = source("data/contracts.ts")
    assert contracts_ts.count("readonly sha256: string;") == 1
    assert "readonly sha256: string;" in block(contracts_ts, "export interface ScanDetectedFields {", "\n}")


def test_timeline_keeps_the_agent_reported_labelling():
    timeline = source("features/events/DeviceTimeline.tsx")
    assert "<p className=\"state-note\">{t('events.timeline.trust')}</p>" in timeline
    assert "<p className=\"event-note\">{t('events.timeline.matchNote')}</p>" in timeline
    for _, start, end, *_ in LANGUAGES:
        entries = strings(start, end, "events")
        assert "self_reported" in entries["events.timeline.trust"] and "not_verified" in entries["events.timeline.trust"]
        assert "SHA-256" in entries["events.timeline.matchNote"]
        assert entries["events.column.details"].endswith(("(cihaz beyanı)", "(device claim)"))


# --- Alerts: ten rules, the ADR wording, agent_silent without an event sequence.

def test_alert_rules_and_severities_mirror_services_alerts():
    rules = ts_list("data/contracts.ts", "ALERT_RULES")
    assert rules == tuple(pinned("services.alerts", "RULES"))
    severity = dict(re.findall(r'(\w+): "(\w+)"', block(
        source("data/normalize.ts"), "const ALERT_SEVERITY: Readonly<Record<AlertRule, AlertSeverity>> = {", "};")))
    assert severity == dict(pinned("services.alerts", "SEVERITY")) and tuple(severity) == rules
    assert set(severity.values()) == {"low", "medium"}
    behavior = pinned("services.alerts", "BEHAVIOR_SEVERITY")
    assert set(behavior) == set(pinned("event_contracts", "BEHAVIOR_RULES"))
    assert set(behavior.values()) == {severity["behavior_match"]} == {"medium"}
    model = source("features/events/eventsModel.ts")
    for table, prefix in [("RULE_LABELS", "alerts.rule"), ("RULE_DESCRIPTIONS", "alerts.description")]:
        labels = dict(re.findall(r"(\w+): '([\w.]+)'", block(model, f"export const {table}:", "};")))
        assert labels == {rule: f"{prefix}.{rule}" for rule in rules}, table


def test_alert_keys_equal_the_platform_alert_view_and_agent_silent_has_null_sequences():
    alert_view = pinned("services.alerts", "alert_view")
    when = datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    row = SimpleNamespace(id=UUID(int=1), device_id=UUID(int=2), rule="agent_silent", severity="medium", status="open",
                          occurrences=1, first_event_seq=None, last_event_seq=None, first_seen_at=when,
                          last_seen_at=when, evidence={"last_received_at": "2030-01-02T02:00:00.000000Z",
                                                       "threshold_seconds": 900},
                          acknowledged_at=None, closed_at=None)
    view = alert_view(row)
    normalize = source("data/normalize.ts")
    keys = names(block(normalize, "const ALERT_KEYS = [", "];")) + names(block(normalize, "const CLAIM_KEYS = [", "];"))
    assert sorted(view) == sorted(keys) and view["first_event_seq"] is None and view["last_event_seq"] is None
    alert = flat(block(normalize, "function alert(input: unknown): Alert {", "\ninterface AlertQuery"))
    silent = alert[alert.index('if (rule === "agent_silent") {'):alert.index("// Every other rule has an event_seq range")]
    assert "requireValue(value.first_event_seq === null && value.last_event_seq === null);" in silent
    assert 'const evidence = shape(value.evidence, ["last_received_at", "threshold_seconds"]);' in silent
    assert "last_received_at: timestamp(evidence.last_received_at)," in silent
    assert "threshold_seconds: integer(evidence.threshold_seconds, MIN_SILENCE_THRESHOLD, MAX_SILENCE_THRESHOLD)" in silent
    # Any other rule with null sequences is refused: integer() takes only safe integers, and 1 is the minimum.
    assert "const firstSeq = integer(value.first_event_seq, 1), lastSeq = integer(value.last_event_seq, 1);" in alert
    assert alert.index("requireValue(value.first_event_seq === null") < alert.index("const firstSeq = integer(")
    # threshold = max(SP_SILENCE_ALERT_SECONDS in 300..86400, 3 x a heartbeat of 30..3600): within 300..86400.
    assert "const MIN_SILENCE_THRESHOLD = 300, MAX_SILENCE_THRESHOLD = 86400;" in normalize
    contracts_ts = source("data/contracts.ts")
    silent_type = flat(block(contracts_ts, "export interface AgentSilentAlert extends AlertCommon {", "\n}"))
    assert "readonly first_event_seq: null; readonly last_event_seq: null;" in silent_type


def test_alert_evidence_of_the_event_rules_is_the_event_fields():
    alert = flat(block(source("data/normalize.ts"), "function alert(input: unknown): Alert {", "\ninterface AlertQuery"))
    for statement in ["evidence: scanFields(shape(value.evidence, EVENT_FIELDS.scan_detected))",
                      "evidence: behaviorFields(shape(value.evidence, EVENT_FIELDS.behavior_match))",
                      'evidence: persistenceFields(shape(value.evidence, EVENT_FIELDS.persistence_change), ["added", "modified"])',
                      "evidence: capabilityDownEvidence(shape(value.evidence, EVENT_FIELDS.agent_state))",
                      "evidence: tamperFields(shape(value.evidence, EVENT_FIELDS.tamper_signal))"]:
        assert statement in alert, statement
    # capability_down's pairs (brief section 8), each an allowed agent_state pair.
    down = ts_table(block(source("data/contracts.ts"), "export const CAPABILITY_DOWN_STATES = {", "} as const;"))
    assert down == {"realtime_scan": ("stopped", "failed"), "rule_set": ("missing", "invalid", "unreadable"),
                    "file_change_sensor": ("failed",), "command_line_sensor": ("failed",),
                    "persistence_watch": ("failed",), "response_channel": ("journal_invalid",)}
    subjects = pinned("event_contracts", "AGENT_STATE_SUBJECTS")
    assert all(set(states) <= set(subjects[subject]) for subject, states in down.items())


def test_alert_rule_mirrors_equal_their_python_sources():
    # The tests above pin the brief's values; these copies must also follow the Python names they mirror, so that a
    # change on the Platform side that the console did not take fails here rather than in the browser.
    capability_down = pinned("services.alerts", "CAPABILITY_DOWN")
    added_changes = tuple(pinned("services.alerts", "PERSISTENCE_ADDED_CHANGES"))
    silent_fields = tuple(pinned("services.sweep", "EVIDENCE_FIELDS"))
    heartbeat_interval = pinned("services.sweep", "heartbeat_interval")
    silence_threshold = pinned("services.sweep", "silence_threshold")
    setting_range = pinned("settings", "SILENCE_ALERT_SECONDS_RANGE")
    shortest = pinned("contracts", "MIN_HEARTBEAT_INTERVAL_SECONDS")
    longest = pinned("contracts", "MAX_HEARTBEAT_INTERVAL_SECONDS")
    contracts_ts, normalize = source("data/contracts.ts"), source("data/normalize.ts")
    alert = flat(block(normalize, "function alert(input: unknown): Alert {", "\ninterface AlertQuery"))
    # capability_down: services.alerts.CAPABILITY_DOWN, subjects and states in order.
    down = ts_table(block(contracts_ts, "export const CAPABILITY_DOWN_STATES = {", "} as const;"))
    assert down == capability_down and tuple(down) == tuple(capability_down)
    # persistence_added: services.alerts.PERSISTENCE_ADDED_CHANGES, in the normalizer and in the alert type.
    [changes] = re.findall(
        r"persistenceFields\(shape\(value\.evidence, EVENT_FIELDS\.persistence_change\), \[([^\]]*)\]\)", alert)
    assert tuple(names(changes)) == added_changes
    added_type = flat(block(contracts_ts, "export interface PersistenceAddedAlert extends AlertBase {", "\n}"))
    [union] = re.findall(r"readonly evidence: PersistenceChangeFields<([^>]*)>;", added_type)
    assert tuple(names(union)) == added_changes
    # agent_silent: services.sweep.EVIDENCE_FIELDS, in order, in the shape check, the built value and the alert type.
    silent = alert[alert.index('if (rule === "agent_silent") {'):alert.index("// Every other rule has an event_seq range")]
    [required] = re.findall(r"const evidence = shape\(value\.evidence, \[([^\]]*)\]\);", silent)
    assert tuple(names(required)) == silent_fields
    assert tuple(re.findall(r"(\w+): \w+\(evidence\.\1[,)]", silent)) == silent_fields
    silent_type = flat(block(contracts_ts, "export interface AgentSilentAlert extends AlertCommon {", "\n}"))
    [typed] = re.findall(r"readonly evidence: \{([^}]*)\};", silent_type)
    assert tuple(re.findall(r"readonly (\w+):", typed)) == silent_fields
    # threshold_seconds: every threshold the sweep can apply, max(SP_SILENCE_ALERT_SECONDS, 3 x a valid V3 heartbeat
    # interval) or the setting alone, lies in the console's bounds, and both bounds are reached. silence_threshold is
    # monotonic in both arguments, so the corners give its extremes.
    payloads = [None, {"rule_file_present": True}]
    for seconds in (shortest, longest):
        payload = {"rule_set_state": "unknown", "heartbeat_interval_seconds": seconds}
        assert heartbeat_interval(payload) == seconds
        payloads.append(payload)
    thresholds = {silence_threshold(setting, payload) for setting in setting_range for payload in payloads}
    [(minimum, maximum)] = re.findall(r"const MIN_SILENCE_THRESHOLD = (\d+), MAX_SILENCE_THRESHOLD = (\d+);", normalize)
    assert (int(minimum), int(maximum)) == (min(thresholds), max(thresholds))
    assert "threshold_seconds: integer(evidence.threshold_seconds, MIN_SILENCE_THRESHOLD, MAX_SILENCE_THRESHOLD)" in silent


def test_alerts_page_uses_the_adr_wording_in_both_languages():
    events = source("i18n/catalogs/events.ts")
    tr = strings("export const eventsTr = {", "\n};", "events")
    en = strings("export const eventsEn = {", "\n} satisfies", "events")
    assert tr["alerts.rule.capability_down"] == "Ajan bir yeteneğinin çalışmadığını bildirdi"
    assert en["alerts.rule.capability_down"] == "The agent reported that one of its capabilities is not working"
    assert tr["alerts.rule.tamper_signal"] == "Kurcalama belirtisi (ajanın beyanı)"
    assert en["alerts.rule.tamper_signal"] == "Tamper sign (reported by the agent)"
    assert '"alerts.rule.agent_silent.since": (time: string) => `Ajandan ${time}\'den beri durum gelmedi`,' in events
    assert '"alerts.rule.agent_silent.since": (time: string) => `No status from the agent since ${time}`,' in events
    page = flat(source("features/events/AlertsPage.tsx"))
    assert ("t('alerts.rule.agent_silent.since', formatPreciseDate(alert.evidence.last_received_at, locale))" in page)
    assert "<td className=\"alert-rule-cell\"><RuleLabel alert={alert} />" in page
    # Factual match labels; never a diagnosis.
    assert "eşleşti" in tr["alerts.rule.scan_detection"] and "matched" in en["alerts.rule.scan_detection"]
    assert "eşleşti" in tr["alerts.rule.behavior_match"] and "matched" in en["alerts.rule.behavior_match"]
    assert "eklendi veya değişti" in tr["alerts.rule.persistence_added"]
    assert "added or changed" in en["alerts.rule.persistence_added"]
    # agent_silent: network loss, sleep, shutdown, an isolation that lost contact and an administrator stop look alike.
    for phrase in ["Ağ kaybı", "uyku", "kapanma", "temasını kaybetmiş bir izolasyon", "yönetici durdurması", "aynı görünür"]:
        assert phrase in tr["alerts.description.agent_silent"], phrase
    for phrase in ["Network loss", "sleep", "shutdown", "an isolation that lost contact", "an administrator stop",
                   "look the same"]:
        assert phrase in en["alerts.description.agent_silent"], phrase
    rules = ts_list("data/contracts.ts", "ALERT_RULES")
    for entries in (tr, en):
        for rule in rules:
            assert entries[f"alerts.rule.{rule}"] and entries[f"alerts.description.{rule}"], rule
    assert "{ALERT_RULES.map((rule) =>" in page and "{t(RULE_DESCRIPTIONS[rule])}" in page


def test_agent_silent_row_shows_no_event_sequence():
    page = source("features/events/AlertsPage.tsx")
    seen = flat(block(page, "function SeenAt({ at, sequence }: { at: string; sequence: number | null }) {", "\n}"))
    assert ("<span className=\"cell-sub\">{sequence === null ? t('alerts.sweep') : t('alerts.sequence', String(sequence))}"
            "</span>") in seen
    assert page.count("t('alerts.sequence'") == 1 and page.count("first_event_seq") == 1 and page.count("last_event_seq") == 1
    assert "<SeenAt at={alert.first_seen_at} sequence={alert.first_event_seq} />" in page
    assert "<SeenAt at={alert.last_seen_at} sequence={alert.last_event_seq} />" in page
    assert strings("export const eventsTr = {", "\n};", "events")["alerts.sweep"] == "Olaydan değil: sunucu taraması"
    assert strings("export const eventsEn = {", "\n} satisfies", "events")["alerts.sweep"] == "Not from an event: server sweep"


# --- The V3 card.

def test_v3_card_carries_the_scan_note_and_every_state_and_counter():
    views = source("components/ProductViews.tsx")
    card = flat(block(views, "function EdrAgentV3Card(", "\nfunction isV3Record("))
    assert '<p className="state-note">{t("product.edrV3.scanNote")}</p>' in card
    assert card.count("<ProductHeading") == 1 and 'label={t(running ? "product.edr.running" : "display.unknown")}' in card
    assert ("<KeyValues values={EDR_V3_COUNTER_KEYS.map((key): DisplayPair => [t(EDR_V3_COUNTER_LABELS[key]),"
            " count(state[key])])}/>") in card
    assert "EDR_CAPABILITY_KEYS.map((key): DisplayPair =>" in card
    assert 'const count = (value: number | null): string => value === null ? t("display.unknown") : formatCount(value, locale);' in card
    assert ('[t("product.edr.claims"), `${t("app.claim.device")} (${state.source}) · ${t("app.claim.notVerified")}'
            ' (${state.producer_verification})`],') in card
    for key in ["rule_set_state", "rule_set_id", "behavior_rules_version", "sensor_state", "sensor_error_code",
                "service_config_state", "previous_run_end", "heartbeat_interval_seconds", "response_channel_state",
                "response_actions_enabled", "response_key_ids", "last_action_seq", "isolation_state", "isolation_until",
                "isolation_checked_at", "quarantine_items", "agent_started_at", "engine_id", "version"]:
        assert f"state.{key}" in card, key
    counters = dict(re.findall(r"(\w+): \"(product\.edr\.counter\.\w+)\"",
                               block(views, "const EDR_V3_COUNTER_LABELS", "};")))
    assert "...EDR_COUNTER_LABELS" in block(views, "const EDR_V3_COUNTER_LABELS", "};")
    assert counters == {key: f"product.edr.counter.{key}" for key in V3_COUNTERS}
    for table, values in [("RULE_SET_LABELS", "RULE_SET_STATES"), ("CAPABILITY_LABELS", "CAPABILITY_STATES"),
                          ("RESPONSE_CHANNEL_LABELS", "RESPONSE_CHANNEL_STATES"), ("ISOLATION_LABELS", "ISOLATION_STATES"),
                          ("SERVICE_CONFIG_LABELS", "SERVICE_CONFIG_STATES"), ("PREVIOUS_RUN_LABELS", "PREVIOUS_RUN_ENDS")]:
        labels = dict(re.findall(r'(\w+): "([\w.]+)"', block(views, f"const {table}:", "};")))
        assert tuple(labels) == ts_list("data/contracts.ts", values), table
        assert labels.pop("unknown") == "display.unknown", table
        for _, _, _, _, start, end in LANGUAGES:
            entries = strings(start, end, "products")
            words = [entries[key] for key in labels.values()]
            assert len(set(words)) == len(words), (table, words)


@pytest.mark.parametrize("start,end,note", [("export const productsTr = {", "\n};", "başlangıç sonrası tarama; engellemez"),
                                            ("export const productsEn = {", "\n} satisfies",
                                             "scans after start; does not block")])
def test_v3_card_wording_claims_no_protection(start, end, note):
    entries = strings(start, end, "products")
    assert note in entries["product.edrV3.scanNote"]
    new = {key: value for key, value in entries.items()
           if key.startswith("product.edrV3.") or key in {f"product.edr.counter.{name}" for name in V3_COUNTERS}}
    assert {f"product.edr.counter.{name}" for name in V3_COUNTERS} <= set(new) and len(new) > 50
    for key, value in new.items():
        assert not FORBIDDEN.search(value), key
        assert not CLAIMS.search(value.replace("engellemez", "") if key == "product.edrV3.scanNote" else value), key


# ADR 0004 sections 1.2 and 3: a scan follows one of five triggers, and only the first is a process starting from the
# file. A file dropped on disk is scanned on file_change without ever running, so no scan wording may tie scanning to
# a process start. For each language: the V3 card note's phrase for every trigger, in SCAN_TRIGGERS order.
SCAN_NOTE_TRIGGERS = [
    ("export const productsTr = {", "\n};", "export const eventsTr = {", "\n};",
     ("bir süreç başladıktan sonra imajını", "ajan başlarken çalışan süreçlerin imajlarını",
      "yeni veya değişmiş çalıştırılabilirleri", "uzaktan istenen bir taramanın dosyalarını",
      "kalıcılık kayıtlarının hedeflerini")),
    ("export const productsEn = {", "\n} satisfies", "export const eventsEn = {", "\n} satisfies",
     ("a process's image after the process starts", "the images of running processes when the agent starts",
      "new or changed executables", "the files of a remote scan request", "the targets of persistence entries")),
]
NARROW_SCAN = re.compile(r"only after|after a process started|after its process|ancak süreci|süreç başladıktan sonra "
                         r"taradığı", re.IGNORECASE)


@pytest.mark.parametrize("products_start,products_end,events_start,events_end,phrases", SCAN_NOTE_TRIGGERS,
                         ids=["tr", "en"])
def test_scan_wording_covers_every_scan_trigger(products_start, products_end, events_start, events_end, phrases):
    triggers = tuple(pinned("event_contracts", "SCAN_TRIGGERS"))
    note = strings(products_start, products_end, "products")["product.edrV3.scanNote"]
    entries = strings(events_start, events_end, "events")
    description = entries["alerts.description.scan_detection"]
    assert len(phrases) == len(triggers) == 5
    for phrase in phrases:
        assert phrase in note, phrase
    # The rule panel names the evidence's trigger field by its label, and every trigger value it can show.
    assert entries["events.field.trigger"].casefold() in description.casefold()
    assert re.findall(r"\((\w+)\)", description) == list(triggers)
    for text in (note, description):
        assert not NARROW_SCAN.search(text), text


# --- Strict JSON: a V3 device detail needs its own route profile; v2 pages fit the event profile.

def _largest_v3_detail():
    contracts = importlib.import_module("security_platform.contracts")
    from security_platform.services.common import DEFAULT_LIMITS
    from security_platform.services.inventory import _device_view, _product_view

    model = pinned("contracts", "EdrAgentStatusV3")
    maximum = contracts.MAX_SNAPSHOT_SEQUENCE
    when = datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    observed = "2030-01-02T03:04:05.123456Z"
    actions = list(pinned("contracts", "RESPONSE_ACTIONS"))
    agent = {"product_id": "edr_agent", "status": "running", "version": "E" * 64, "engine_id": "G" * 128,
             "agent_started_at": observed, "source_observed_at": observed, "sensor_state": "failed",
             "sensor_error_code": "session_start_failed",
             **{key: maximum for key in pinned("contracts", "EDR_V3_COUNTER_KEYS")},
             "rule_set_state": "compiled", "rule_set_id": "f" * 64, "realtime_scan_state": "degraded",
             "file_change_sensor_state": "not_available", "command_line_sensor_state": "failed",
             "persistence_watch_state": "stopped", "response_channel_state": "awaiting_tenant_binding",
             "response_key_ids": sorted(character * 64 for character in "0abf"), "last_action_seq": maximum,
             "isolation_state": "partial", "isolation_until": observed, "isolation_checked_at": observed,
             "quarantine_items": maximum, "service_config_state": "changed", "previous_run_end": "first_start",
             "heartbeat_interval_seconds": 3600, "behavior_rules_version": "altay-behavior/v999999"}
    state = accepted(model, {**agent, "response_actions_enabled": sorted(actions)}) or model.model_validate(
        {**agent, "response_actions_enabled": actions})
    firewall = contracts.HostBasedFirewallStatus.model_validate({
        "product_id": "hostbasedfirewall", "status": "unavailable", "error_codes": list(get_args(contracts.ErrorCode))[:16],
        "version": "V" * 64, "catalog_available": False, "source_observed_at": observed})
    antivirus = contracts.AntivirusStatus.model_validate(
        {"product_id": "antivirus", "status": "unknown", "availability": "unknown", "catalog_available": False})
    products = [firewall.model_dump(mode="json"), antivirus.model_dump(mode="json"), state.model_dump(mode="json")]
    row = SimpleNamespace(id=UUID(int=1), tenant_id=UUID(int=2), label="L" * 80, created_at=when, revoked_at=when,
                          last_sequence=maximum, last_received_at=when, source_observed_at=when)
    records = [SimpleNamespace(product_id=payload["product_id"], snapshot_sequence=maximum, received_at=when,
                               payload=payload) for payload in products]
    later = when + timedelta(seconds=1)
    detail = {**_device_view(row, later, DEFAULT_LIMITS), "products": [_product_view(record, later) for record in records],
              "missing_products": ["termivar"]}
    return detail, len(model.model_fields)


def test_largest_v3_detail_needs_and_fits_the_detail_profile():
    source_ts, budgets = _budgets()
    profile = budgets["sp-device-detail-v1"]
    assert profile == {**budgets["default"], "objectKeys": 45}
    adapter = source("adapters/platformReadOnly.ts")
    assert 'if (operation.type === "detail") return "sp-device-detail-v1";' in adapter
    assert adapter.index('if (operation.type === "detail")') < adapter.index('return operation.type === "events"')
    detail, fields = _largest_v3_detail()
    text = json.dumps(detail, ensure_ascii=False, separators=(",", ":"))
    assert fields == 45 == profile["objectKeys"]
    assert not _fits(text, budgets["default"])[0]
    fits, usage = _fits(text, profile)
    assert fits and usage["objectKeys"] == 45, usage
    assert len(text.encode("utf-8")) <= 512 * 1024


def test_full_v2_event_and_alert_pages_fit_the_event_profile():
    from pydantic import ValidationError

    event_view = pinned("services.events", "_event_view")
    alert_view = pinned("services.alerts", "alert_view")
    scan = pinned("event_contracts", "ScanDetected")
    max_event_seq = pinned("event_contracts", "MAX_EVENT_SEQ")
    _, budgets = _budgets()
    profile = budgets["sp-events-alerts-v1"]
    fields = {"kind": "scan_detected", "observed_at": "2030-01-02T03:04:05.000006Z", "trigger": "file_change",
              "size": 2**53 - 1, "sha256": "a" * 64, "rule_set_id": "b" * 64, "omitted_hits": 4096, "pid": 2**32 - 1,
              "create_time": "2030-01-02T03:04:05.000006Z", "action_id": "00000000-0000-4000-8000-000000000001",
              "hits": [{"rule": f"R{index}" + "x" * 62, "severity": "high"} for index in range(8)]}
    prefix, suffix = "\\Device\\HarddiskVolume3\\Users\\*\\Downloads\\", ".exe"
    # The longest contract-valid path: 1,024 code points, as many non-BMP as the stored-event bound allows.
    path = None
    for astral in range(1024 - len(prefix) - len(suffix) + 1):
        candidate = prefix + "\U0001F512" * astral + "x" * (1024 - len(prefix) - len(suffix) - astral) + suffix
        try:
            scan.model_validate({**fields, "event_seq": max_event_seq, "path": candidate})
        except ValidationError:
            break
        path = candidate
    assert path is not None
    when = datetime(2030, 1, 2, 3, 4, 6, tzinfo=timezone.utc)
    rows = [SimpleNamespace(event_seq=max_event_seq - index, kind="scan_detected", observed_at=when, received_at=when,
                            payload=scan.model_validate({**fields, "event_seq": max_event_seq - index, "path": path})
                            .model_dump(mode="json")) for index in range(100)]
    events = {"items": [event_view(row) for row in rows], "next_before_seq": rows[-1].event_seq, "cap_deleted_events": 0,
              "suppressed_alerts": 0}
    evidence = {key: rows[0].payload[key] for key in pinned("event_contracts", "EVENT_FIELDS")["scan_detected"]}
    alerts = {"items": [alert_view(SimpleNamespace(
        id=UUID(int=1000 - index), device_id=UUID(int=7), rule="scan_detection", severity="medium", status="open",
        occurrences=2**31, first_event_seq=max_event_seq - 100, last_event_seq=max_event_seq - index, first_seen_at=when,
        last_seen_at=when, evidence=evidence, acknowledged_at=None, closed_at=None)) for index in range(100)],
        "next_before": {"seen_at": "2030-01-02T03:04:06.000000Z", "id": str(UUID(int=901))}}
    for page in (events, alerts):
        text = json.dumps(page, ensure_ascii=False, separators=(",", ":"))
        assert len(text.encode("utf-8")) <= 512 * 1024
        fits, usage = _fits(text, profile)
        assert fits, usage


# --- Catalogs and sample data.

def test_new_catalog_strings_exist_in_both_languages_and_claim_nothing():
    tr = strings("export const eventsTr = {", "\n};", "events")
    en = strings("export const eventsEn = {", "\n} satisfies", "events")
    assert set(tr) == set(en)
    events = source("i18n/catalogs/events.ts")
    tr_block = block(events, "export const eventsTr = {", "\n};")
    en_block = block(events, "export const eventsEn = {", "\n} satisfies")
    for key in ["events.field.bytes", "alerts.evidence.seconds", "alerts.rule.agent_silent.since"]:
        assert f'"{key}": (' in tr_block and f'"{key}": (' in en_block, key
    new_prefixes = ("events.field.", "alerts.description.")
    new_keys = {"alerts.rules.title", "alerts.sweep", "alerts.evidence.lastReceived", "alerts.evidence.threshold",
                "events.timeline.matchNote", "events.column.details",
                *(f"alerts.rule.{rule}" for rule in NEW_RULES), *(f"events.kind.{kind}" for kind in V2_KINDS)}
    for entries in (tr, en):
        chosen = {key: value for key, value in entries.items() if key in new_keys or key.startswith(new_prefixes)}
        assert new_keys <= set(chosen) and len(chosen) > 45
        for key, value in chosen.items():
            assert not FORBIDDEN.search(value) and not CLAIMS.search(value), key
    for start, end in [("export const productHubTr = {", "\n};"), ("export const productHubEn = {", "\n} satisfies")]:
        hub = catalog("i18n/catalogs/productHub.ts", start, end, quote="'")
        assert "V3" in hub["productHub.edr.source"] and "V3" in hub["productHub.edr.feature"]


def test_sample_data_has_one_labelled_v3_device_with_v2_events_and_a_sweep_alert():
    demo = source("fixtures/demo-data.ts")
    specs = block(demo, "const specs: DeviceSpec[] = [", "\n  ];")
    assert 'label: "DEMO · Bursa V3 ajan örneği"' in specs and specs.count("edrAgentV3(") == 1
    builder = block(demo, "const edrAgentV3 = (observed: number): EdrAgentStateV3 => {", "\n  };")
    assert 'rule_set_id: "0123456789abcdef".repeat(4)' in builder and "rule_file_present" not in builder
    for call in ["d10.scan(", "d10.behavior(", "d10.persistence(", "d10.agent(", "d10.tamper(", "d10.gap("]:
        assert call in demo, call
    assert 'sha256: "deadbeef".repeat(8)' in demo
    silent = flat(block(demo, "// The sample sweep: no event, so no event sequences", "\n  ];"))
    assert "first_event_seq: null, last_event_seq: null" in silent and 'rule: "agent_silent"' in silent
    assert "evidence: { last_received_at: at6(1800), threshold_seconds: 900 }" in silent
    # v1 sample events stay v1 rows: their v2 creation times are null.
    recorder = flat(block(demo, "const recorder = (clockAhead: number) => {", "\n  };"))
    assert "create_time: created === null ? null : at6(created - clockAhead)," in recorder
