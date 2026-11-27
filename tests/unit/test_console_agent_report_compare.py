"""GitHub issue #15: the console's status report and device comparison carry the Altay EDR agent's own state.

As in test_console_edr_agent.py, no TypeScript runs here; operator-console/tests/agent-report-compare.test.ts runs the
copies themselves and renders the comparison page and the report preview. The sources are read as text: the report's
and the comparison's agent fields must be the Platform's own field names, the label tables they share must be the
device-detail card's, and the new wording must call every value the agent reports its own unverified claim, keep the
card's notes that it is no protection or rule-loading claim and that the console sends the agent no actions, and make
no protection, loading or verification claim of its own.
"""
import re

import pytest

from security_platform.contracts import PRODUCT_IDS, EdrAgentStatus, EdrAgentStatusV3
from test_console_edr_agent import FORBIDDEN, block, catalog, flat, names, source
from test_console_stage3 import CLAIMS, ts_list


# The report shows the product's own fields as its own rows, and copies neither of V3's two lists.
PRODUCT_FIELDS = {"product_id", "catalog_available", "source", "producer_verification", "status", "version",
                  "source_observed_at"}
V3_LISTS = {"response_actions_enabled", "response_key_ids"}
# The comparison's agent fields that are not agent state fields: the product's status, version, times and claims.
COMPARE_OWN = {"status", "version", "received_at", "observed_at", "source", "verification"}
CARD_TABLES = ("EDR_SENSOR_LABELS", "RULE_SET_LABELS", "CAPABILITY_LABELS", "RESPONSE_CHANNEL_LABELS", "ISOLATION_LABELS",
               "SERVICE_CONFIG_LABELS", "PREVIOUS_RUN_LABELS")
# The only allowed forms of "verified" in the new wording: the negations.
NEGATIONS = re.compile(r"not independently verified|not verified|not_verified", re.IGNORECASE)
NEW_KEYS = {"report.product.edr_agent", "report.agentNote", "report.agentClaim", "compare.section.edr_agent",
            "compare.sectionNote.edr_agent", "compare.value.notInFormat", "compare.note.agentClaim",
            *(f"compare.field.edr.{name}" for name in sorted(COMPARE_OWN))}


def ts_items(text):
    """The items of a TypeScript array literal in order, each `...NAME` spread replaced by contracts.ts's NAME list."""
    items = []
    for token in (part.strip() for part in text.split(",")):
        if token.startswith("..."):
            items.extend(ts_list("data/contracts.ts", token[3:]))
        elif token:
            items.append(re.fullmatch(r'"(\w+)"', token)[1])
    return items


def report_agent_keys(version):
    return ts_items(block(source("features/reports/reportModel.ts"), f"export const REPORT_AGENT_{version}_KEYS = [",
                          "] as const;"))


def compare_fields():
    """(key, section, kind, the Snapshot version that alone has it, or None) of each COMPARE_FIELDS entry, in order."""
    text = flat(block(source("features/compare/compareModel.ts"), "export const COMPARE_FIELDS = [", "] as const satisfies"))
    fields = []
    for entry in re.split(r"(?=\{ key: )", text)[1:]:
        key, section, kind = re.match(r'\{ key: "([\w.]+)", section: "(\w+)", kind: "(\w+)"', entry).groups()
        version = re.search(r'format: "(v2|v3)"', entry)
        fields.append((key, section, kind, version[1] if version else None))
    return fields


def table(text, name):
    return dict(re.findall(r'(\w+): "([\w.]+)"', block(text, f"const {name}:", "};")))


def test_report_covers_every_platform_product():
    model = source("features/reports/reportModel.ts")
    assert tuple(names(block(model, "export const REPORT_PRODUCT_IDS = [", "] as const"))) == PRODUCT_IDS
    capture = source("features/reports/capture.ts")
    assert "input.products.length === REPORT_PRODUCT_IDS.length" in capture and "products.length === 3" not in capture
    assert "products: REPORT_PRODUCT_IDS.map((id) => productFromDetail(id," in flat(capture)
    # A missing agent has no metric: which Snapshot version it would have reported is not known.
    assert 'metrics: id === "edr_agent" ? [] : KEYS[id].map((key) => metric(key, null))' in flat(capture)


@pytest.mark.parametrize("version,model,left_out", [("V2", EdrAgentStatus, PRODUCT_FIELDS),
                                                    ("V3", EdrAgentStatusV3, PRODUCT_FIELDS | V3_LISTS)])
def test_report_agent_metrics_are_the_platform_fields(version, model, left_out):
    keys = report_agent_keys(version)
    assert len(set(keys)) == len(keys)
    assert set(keys) == set(model.model_fields) - left_out
    capture = flat(source("features/reports/capture.ts"))
    # V3 is told from V2 by its key set, as on the device-detail card, and each list is copied as the state has it.
    assert "if (isEdrAgentStateV3(agent)) return { ...common," in capture
    assert f"metrics: REPORT_AGENT_{version}_KEYS.map((key) => metric(key, {'agent' if version == 'V3' else 'v2'}[key]))" in capture


def test_report_and_comparison_copies_keep_the_platform_bounds():
    normalize = source("data/normalize.ts")
    capture = flat(source("features/reports/capture.ts"))
    compare = flat(source("features/compare/compareModel.ts"))
    for name in ("ENGINE_PATTERN", "BEHAVIOR_RULES_VERSION_PATTERN", "HEX64_PATTERN"):
        pattern = re.search(rf"const {name} = (/.+/);", normalize)[1]
        assert pattern in capture and pattern in compare, name
    schema = EdrAgentStatusV3.model_json_schema()["properties"]["heartbeat_interval_seconds"]
    [bounds] = [item for item in schema["anyOf"] if item.get("type") == "integer"]
    assert (bounds["minimum"], bounds["maximum"]) == (30, 3600)
    assert "value >= 30 && value <= 3600" in capture
    assert 'kind: "number", minimum: 30, maximum: 3600, format: "v3"' in compare
    # Counters, the action sequence and quarantine items up to 2^53 - 1; a sensor code only with a lost or failed sensor.
    assert "const safeCount: MetricCheck = (value) => typeof value === \"number\" && Number.isSafeInteger(value) && value >= 0;" in capture
    assert "const SAFE = Number.MAX_SAFE_INTEGER;" in compare
    assert 'reportRequire(code === null || sensor === "lost" || sensor === "failed");' in capture
    assert '(fields["edr.sensor_error_code"] === null || fields["edr.sensor_state"] === "lost" || fields["edr.sensor_state"] === "failed")' in compare


def test_report_and_comparison_copies_keep_isolation_times_in_the_normalizer_window():
    """isolation_until and isolation_checked_at are device times: the normalizer's windowTime, not the generic check."""
    normalize = source("data/normalize.ts")
    window = flat(block(normalize, "function windowTime(value: unknown, nullable = false): string | null {", "\n}"))
    first, last = re.search(r"requireValue\(year >= (\d+) && year <= (\d+)\);", window).groups()
    assert (first, last) == ("1970", "9998")
    assert ("isolation_until: windowTime(value.isolation_until, true), isolation_checked_at:"
            " windowTime(value.isolation_checked_at, true),") in flat(normalize)
    bounds = f"return year >= {first} && year <= {last};"
    capture = flat(source("features/reports/capture.ts"))
    assert ("const deviceTime: MetricCheck = (value) => { try { const year = Number(reportTimestamp(value).slice(0, 4));"
            f" {bounds} }} catch {{ return false; }} }};") in capture
    assert "isolation_until: optional(deviceTime), isolation_checked_at: optional(deviceTime)," in capture
    compare = flat(source("features/compare/compareModel.ts"))
    assert ('case "timestamp": try { const time = compareTimestamp(value); return spec.deviceTime !== true'
            ' || inDeviceTimeWindow(time); } catch { return false; }') in compare
    assert f"const year = Number(value.slice(0, 4)); {bounds}" in flat(block(compare, "function inDeviceTimeWindow(", "}"))
    entries = re.split(r"(?=\{ key: )", flat(block(source("features/compare/compareModel.ts"), "export const COMPARE_FIELDS = [",
                                                     "] as const satisfies")))[1:]
    assert {re.match(r'\{ key: "([\w.]+)"', entry)[1] for entry in entries if "deviceTime: true" in entry} == {
        "edr.isolation_until", "edr.isolation_checked_at"}


def test_comparison_agent_section_has_the_report_agent_fields():
    fields = compare_fields()
    assert list(dict.fromkeys(section for _, section, _, _ in fields)) == ["device", "hbf", "termivar", "edr_agent",
                                                                           "antivirus"]
    agent = [(key, kind, version) for key, section, kind, version in fields if section == "edr_agent"]
    assert all(key.startswith("edr.") for key, _, _ in agent)
    assert all(section == "edr_agent" for key, section, _, _ in fields if key.startswith("edr."))
    v2, v3 = set(report_agent_keys("V2")), set(report_agent_keys("V3"))
    assert sorted(key[4:] for key, _, _ in agent) == sorted(v2 | v3 | COMPARE_OWN)
    # A field of one Snapshot version only is marked with it, and no other field is.
    assert {key[4:] for key, _, version in agent if version == "v2"} == v2 - v3 == {"rule_file_present"}
    assert {key[4:] for key, _, version in agent if version == "v3"} == v3 - v2
    assert all(version is None for _, section, _, version in fields if section != "edr_agent")
    # Each agent counter, and the action sequence and quarantine item count whose scope is not defined, is a count:
    # never compared across devices (scope_not_established).
    counters = set(ts_list("data/contracts.ts", "EDR_V3_COUNTER_KEYS"))
    assert {key[4:] for key, kind, _ in agent if kind == "count"} == counters | {"last_action_seq", "quarantine_items"}
    model = flat(source("features/compare/compareModel.ts"))
    assert 'for (const product of ["hbf", "termivar", "edr", "av"] as const) {' in model
    # Termivar's summary rule covers its own counts only, not the agent's counters.
    assert 'const countKeys = COMPARE_FIELDS.filter((field) => field.section === "termivar" && field.kind === "count");' in model


def test_comparison_shows_a_version_only_field_when_a_selected_agent_has_that_version():
    rows = flat(block(source("features/compare/compareFields.ts"), "export function compareFields(", "\n}"))
    assert "const formats = state.slots.map((slot) => slot === null ? null : agentFormat(slot.fields));" in rows
    assert "return format === null || formats.includes(format);" in rows
    model = flat(source("features/compare/compareModel.ts"))
    assert ('return fields["edr.status"] === null ? null : fields["edr.rule_set_state"] === null ? "v2" : "v3";'
            in model)


def test_report_and_comparison_use_the_card_labels():
    views = source("components/ProductViews.tsx")
    shared = source("features/agentLabels.ts")
    for name in CARD_TABLES:
        assert table(shared, name) == table(views, name), name
    wiring = dict(re.findall(r"(\w+): (\w+_LABELS)", block(shared, "const AGENT_STATE_LABELS = {", "} as const")))
    capabilities = ts_list("data/contracts.ts", "EDR_CAPABILITY_KEYS")
    assert wiring == {"sensor_state": "EDR_SENSOR_LABELS", "rule_set_state": "RULE_SET_LABELS",
                      **{key: "CAPABILITY_LABELS" for key in capabilities}, "response_channel_state": "RESPONSE_CHANNEL_LABELS",
                      "isolation_state": "ISOLATION_LABELS", "service_config_state": "SERVICE_CONFIG_LABELS",
                      "previous_run_end": "PREVIOUS_RUN_LABELS"}
    cards = flat(block(views, "function EdrAgentV3Card(", "\nfunction ProductGrid("))
    for field, name in wiring.items():
        assert f"mapped({name}, state.{field}," in cards or (field in capabilities and f"mapped({name}, state[key]," in cards)
    # Each field's label is the card's capability or counter label, or the label of the card row that shows it.
    labels = table(shared, "AGENT_FIELD_LABELS")
    assert set(labels) == set(report_agent_keys("V2")) | set(report_agent_keys("V3"))
    card_labels = {name: label for table_name in ("EDR_CAPABILITY_LABELS", "EDR_COUNTER_LABELS", "EDR_V3_COUNTER_LABELS")
                   for name, label in table(views, table_name).items()}
    assert set(card_labels) == set(capabilities) | set(ts_list("data/contracts.ts", "EDR_V3_COUNTER_KEYS"))
    for field, label in labels.items():
        if field in card_labels:
            assert label == card_labels[field], field
        else:
            assert f'[t("{label}"),' in cards, field
    # The card's own expressions for the running status, the rule file and an absent sensor code.
    helpers = flat(shared)
    assert 'return status === "running" ? "product.edr.running" : "display.unknown";' in helpers
    assert ('return present === true ? "product.edr.ruleFile.present" : present === false ? "product.edr.ruleFile.absent"'
            ' : "display.unknown";') in helpers
    assert ('return sensorState === "lost" || sensorState === "failed" ? "product.edr.sensorError.notReported"'
            ' : "product.edr.sensorError.notApplicable";') in helpers


def test_report_preview_marks_every_agent_value_as_the_agents_claim():
    preview = flat(source("features/reports/ReportPreview.tsx"))
    assert ('const claim = (value: ReactNode): ReactNode => agent && present'
            ' ? <>{value}<span className="report-claim">{translate(locale, "report.agentClaim")}</span></> : value;') in preview
    for row in ('[translate(locale, "report.reportStatus"), claim(productStatus(product, locale))]',
                '[translate(locale, "report.version"), claim(product.version ?? translate(locale, "report.notSupplied"))]',
                '[translate(locale, "report.sourceObservedAt"), claim(formatDate(product.sourceObservedAt, locale))]',
                '[translate(locale, AGENT_FIELD_LABELS[item.key]), claim(agentValue(product, item.key, item.value, locale))]'):
        assert row in preview, row
    # The source and verification rows stay. The agent's note covers the values it marks, so only a reported agent has
    # it; a V3 agent also keeps the card's scan note and its response note (the console sends the agent no actions),
    # beside its response channel, action sequence, isolation and quarantine values.
    assert '[translate(locale, "report.verification"), translate(locale, "report.notVerified")]' in preview
    assert '{agent && present && <p className="report-trust-note">{translate(locale, "report.agentNote")}</p>}' in preview
    assert '{agentV3 && <p className="report-trust-note">{translate(locale, "product.edrV3.scanNote")}</p>}' in preview
    assert '{agentV3 && <p className="report-trust-note">{translate(locale, "product.edrV3.responseScope")}</p>}' in preview
    assert [preview.count(f'"{key}"') for key in ("report.agentNote", "product.edrV3.scanNote",
                                                  "product.edrV3.responseScope")] == [1, 1, 1]
    # null is "not supplied", never 0.
    assert 'if (value === null) return translate(locale, "report.notSupplied");' in preview
    css = source("features/reports/print.css")
    assert ".report-claim{" in css and "#print-root .report-claim{" in css


def test_comparison_page_has_the_agent_section_and_its_note():
    page = flat(source("features/compare/ComparePage.tsx"))
    assert "['termivar', 'compare.section.termivar'], ['edr_agent', 'compare.section.edr_agent'], ['antivirus'," in page
    assert "edr_agent: 'compare.sectionNote.edr_agent'" in page
    assert "return isAgentCompareKey(key) ? AGENT_FIELD_LABELS[key.slice(4) as ReportAgentMetricKey] : FIELD_LABELS[key];" in page
    # A row with no note of its own carries the agent's claim, as the report marks it: every agent row but the
    # server's receipt time and the source and verification labels (the verification row keeps its own note).
    assert ("function isAgentClaim(field: ComparedField): boolean { return field.section === 'edr_agent'"
            " && !['edr.received_at', 'edr.source', 'edr.verification'].includes(field.key); }") in page
    assert ("field.key.endsWith('.verification') ? t('compare.note.verification')"
            " : isAgentClaim(field) ? t('compare.note.agentClaim') : undefined} />") in page


@pytest.mark.parametrize("language", ["tr", "en"])
def test_new_report_and_comparison_wording_claims_nothing(language):
    tr = language == "tr"
    reports = catalog("i18n/catalogs/reports.ts", f"export const reports{'Tr' if tr else 'En'} = {{",
                      "\n} as const;" if tr else "\n} satisfies")
    compare = catalog("i18n/catalogs/compare.ts", f"export const compare{'Tr' if tr else 'En'} = {{",
                      "\n};" if tr else "\n} satisfies", quote="'")
    products = catalog("i18n/catalogs/products.ts", f"export const products{'Tr' if tr else 'En'} = {{",
                       "\n};" if tr else "\n} satisfies")
    # The device card's own sentences: the V2 note's denial of a protection or rule-loading claim, and the V3 response
    # note's statement that the console sends the agent no actions.
    no_protection = products["product.edr.notice"].split("; ", 1)[1].removesuffix(".")
    no_action = products["product.edrV3.responseScope"].split(". ", 1)[1]
    assert no_protection == ("koruma veya kural yükleme iddiası değildir" if tr
                             else "this is no claim of protection or rule loading")
    assert no_action == ("Konsol bu aşamada ajana aksiyon göndermez ve bir aksiyonun yapıldığını göstermez." if tr
                         else "The console sends the agent no actions in this stage and does not show that an action"
                              " was carried out.")
    new = {key: value for key, value in {**reports, **compare}.items() if key in NEW_KEYS}
    assert set(new) == NEW_KEYS
    for key, value in new.items():
        assert not FORBIDDEN.search(value), key
        # The card's denial is the one allowed form of a protection word.
        assert not CLAIMS.search(NEGATIONS.sub("", value.replace(no_protection, ""))), key
    # The agent is a prototype waiting for its VM acceptance; its values are its own unverified claims and, as the card
    # says beside the same values, no protection or rule-loading claim.
    pending = "sanal makinede kabulü henüz yapılmadı" if tr else "acceptance in a VM is still pending"
    for key in ("report.agentNote", "compare.sectionNote.edr_agent"):
        assert pending in new[key] and "(self_reported)" in new[key] and "(not_verified)" in new[key], key
        assert no_protection in new[key], key
    # The comparison shows the V3 response values with no card note beside them, so its note says it too; the report
    # shows the card's response note itself (test_report_preview_marks_every_agent_value_as_the_agents_claim).
    assert no_action in new["compare.sectionNote.edr_agent"]
    # The report's note covers the values it marks with the claim, not every row of its section: the server's receipt
    # time, the clock state and the source and verification labels are not the agent's claims.
    marker = new["report.agentClaim"].split(" · ")[0]
    assert f"“{marker}”" in new["report.agentNote"]
    assert ("Bu bölümdeki her değer" if tr else "Every value in this section") not in new["report.agentNote"]
    assert ("bağımsız doğrulanmadı" if tr else "not independently verified") in new["report.agentClaim"]
    # Each agent row of the comparison carries the report's claim, word for word.
    assert new["compare.note.agentClaim"] == new["report.agentClaim"]
