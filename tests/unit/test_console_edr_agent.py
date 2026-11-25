"""The operator console's edr_agent DTO and normalizer mirror the Platform's Snapshot V2 contract.

The console rejects a whole device detail on any unknown key, value or integer outside JavaScript's safe range, so
its closed lists must equal contracts.py. This checkout runs no TypeScript in pytest; the sources are read as text,
and the agent card's and normalizer's expressions are pinned exactly.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from types import SimpleNamespace
from typing import get_args
from uuid import UUID

import pytest

from security_platform import contracts
from security_platform.contracts import (MAX_SNAPSHOT_SEQUENCE, PRODUCT_IDS, AntivirusStatus, EdrAgentStatus,
    HostBasedFirewallStatus, SnapshotEnvelope, TermivarStatus)
from security_platform.services.common import DEFAULT_LIMITS
from security_platform.services.inventory import _device_view, _product_view
from test_console_preview_server import _budgets, _fits


ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "operator-console/src"
PRODUCT_MODELS = {"hostbasedfirewall": HostBasedFirewallStatus, "termivar": TermivarStatus,
                  "antivirus": AntivirusStatus, "edr_agent": EdrAgentStatus}
NOTE_TR = "Ajan kendi durumunu bildirir; koruma veya kural yükleme iddiası değildir"
NOTE_EN = "The agent reports its own state; this is no claim of protection or rule loading"
# Wording the agent's status must never use: a loaded-rules, active-protection or real-time-protection claim.
FORBIDDEN = re.compile(r"yüklü|yüklendi|loaded|koruma aktif|aktif koruma|protection active|active protection|"
                       r"gerçek zamanlı koruma|real-time protection|korunuyor|protected", re.IGNORECASE)


def source(relative):
    return (CONSOLE / relative).read_text(encoding="utf-8")


def block(text, start, end):
    head = text.index(start) + len(start)
    return text[head:text.index(end, head)]


def names(text):
    return re.findall(r'"(\w+)"', text)


def catalog(relative, start, end, quote='"'):
    """String entries of one TR or EN catalog object whose keys and values use `quote`."""
    entry = re.compile(rf"{quote}([\w.]+){quote}: {quote}((?:[^{quote}\\\n]|\\.)*){quote}")
    return dict(entry.findall(block(source(relative), start, end)))


def counter_keys():
    return names(block(source("data/contracts.ts"), "export const EDR_COUNTER_KEYS = [", "] as const;"))


def flat(text):
    """Every run of whitespace as one space: a pinned statement may wrap differently, but not change."""
    return re.sub(r"\s+", " ", text)


def agent_card():
    return block(source("components/ProductViews.tsx"), "function EdrAgentCard(", "\nfunction ProductGrid(")


def test_console_product_ids_are_the_platform_products():
    assert tuple(names(block(source("data/contracts.ts"), "export const PRODUCT_IDS = [", "] as const;"))) == PRODUCT_IDS


def test_console_state_keys_equal_every_platform_dto():
    normalize = source("data/normalize.ts")
    claims = names(block(normalize, "const CLAIM_KEYS = [", "];"))
    common = block(normalize, "const PRODUCT_KEYS = [", "];")
    assert "...CLAIM_KEYS" in common
    common_keys = names(common) + claims
    table = block(normalize, "const PRODUCT_STATE_KEYS: Readonly<Record<ProductId, readonly string[]>> = {", "\n};")
    entries = dict(re.findall(r"(\w+): \[([^\]]*)\]", table))
    assert tuple(entries) == PRODUCT_IDS
    for product_id, model in PRODUCT_MODELS.items():
        keys = names(entries[product_id]) + (counter_keys() if "...EDR_COUNTER_KEYS" in entries[product_id] else [])
        assert sorted(common_keys + keys) == sorted(model.model_fields), product_id
        assert len(set(common_keys + keys)) == len(common_keys + keys), product_id


def test_console_enums_equal_the_platform_literals():
    contracts_ts = source("data/contracts.ts")
    assert tuple(names(block(contracts_ts, "export const EDR_SENSOR_STATES = [", "] as const;"))) == get_args(
        contracts.EdrSensorState)
    assert tuple(names(block(contracts_ts, "export const SENSOR_ERROR_CODES = [", "] as const;"))) == get_args(
        contracts.EdrSensorErrorCode)
    assert tuple(counter_keys()) == tuple(name for name in EdrAgentStatus.model_fields
                                          if name.startswith("events_") or name == "outbox_backlog")
    normalize = block(source("data/normalize.ts"), "function edrAgentState(", "\nfunction productState(")
    assert 'status: choice(value.status, ["running", "unknown"])' in normalize
    assert get_args(EdrAgentStatus.model_fields["status"].annotation) == ("running", "unknown")


def test_console_patterns_equal_the_platform_patterns():
    normalize = source("data/normalize.ts")
    engine = re.search(r"const ENGINE_PATTERN = /(.+)/;", normalize)[1].replace("\\/", "/")
    version = re.search(r"const VERSION_PATTERN = /(.+)/;", normalize)[1]
    schema = EdrAgentStatus.model_json_schema()["properties"]
    [platform_engine] = [item["pattern"] for item in schema["engine_id"]["anyOf"] if "pattern" in item]
    [platform_version] = [item["pattern"] for item in schema["version"]["anyOf"] if "pattern" in item]
    assert engine == platform_engine == r"^[A-Za-z0-9][A-Za-z0-9._+/ -]*$"
    assert version == platform_version
    assert "const engine = value.engine_id === null ? null : text(value.engine_id, 128);" in normalize
    # The same verdicts: ASCII only, a letter or digit first, at most 128 characters.
    console = re.compile(engine)
    for sample in ["edr-agent/0.3.0", "edr-agent/0.3.0 scanner/1.2", "A" * 128, "A" * 129, "", " x", "-x", "/x",
                   "x;y", "x:y", "x\\y", "çekirdek", "x​", "０", "x+y_z.w"]:
        try:
            EdrAgentStatus.model_validate({"product_id": "edr_agent", "engine_id": sample})
            platform_ok = True
        except ValueError:
            platform_ok = False
        assert platform_ok == (1 <= len(sample) <= 128 and console.fullmatch(sample) is not None), sample


def test_console_normalizer_enforces_the_agent_rules():
    normalize = source("data/normalize.ts")
    agent = block(normalize, "function edrAgentState(", "\nfunction productState(")
    # No catalog claim, a code only with lost or failed, counters as safe non-negative integers or null.
    assert "requireValue(common.catalog_available === null);" in agent
    assert 'requireValue(code === null || sensor === "lost" || sensor === "failed");' in agent
    assert "[key, value[key] === null ? null : integer(value[key])]" in agent
    assert "function integer(value: unknown, minimum = 0, maximum = Number.MAX_SAFE_INTEGER): number {" in normalize
    assert "Number.isSafeInteger(value)" in block(normalize, "function integer(", "\n}")
    assert "agent_started_at: timestamp(value.agent_started_at, true)" in agent
    assert "rule_file_present: nullableBoolean(value.rule_file_present)" in agent
    # The engine ID must match ENGINE_PATTERN (the Platform's EngineText), and the checked value is the one kept.
    assert "requireValue(engine === null || ENGINE_PATTERN.test(engine));" in agent
    assert "engine_id: engine, rule_file_present:" in agent
    assert agent.count("ENGINE_PATTERN") == 1 and normalize.count("ENGINE_PATTERN =") == 1
    assert 'if (id === "edr_agent") return edrAgentState(value, common);' in normalize
    detail = block(normalize, "export function normalizeDeviceDetail(", "\n}")
    assert "array<ProductRecord>(value.products, PRODUCT_IDS.length," in detail
    assert "array(value.missing_products, PRODUCT_IDS.length," in detail
    assert "PRODUCT_IDS.every((id) => present.includes(id) !== missing.includes(id))" in detail


@pytest.mark.parametrize("start,end,note,rule_file", [
    ("export const productsTr = {", "\n};", NOTE_TR, ("Var", "Yok")),
    ("export const productsEn = {", "\n} satisfies", NOTE_EN, ("Present", "Absent")),
])
def test_agent_card_wording_in_both_languages(start, end, note, rule_file):
    entries = catalog("i18n/catalogs/products.ts", start, end)
    agent = {key: value for key, value in entries.items() if ".edr" in key or key.endswith("edr_agent")}
    assert agent["product.edr.notice"] == note + "."
    assert (agent["product.edr.ruleFile.present"], agent["product.edr.ruleFile.absent"]) == rule_file
    assert entries["display.unknown"] in ("Bilinmiyor", "Unknown")
    assert {f"product.edr.counter.{key}" for key in counter_keys()} <= set(agent)
    assert {f"product.edr.sensor.{state}" for state in get_args(contracts.EdrSensorState) if state != "unknown"} <= set(agent)
    for key, value in agent.items():
        assert not FORBIDDEN.search(value), key


@pytest.mark.parametrize("start,end,pending", [
    ("export const productHubTr = {", "\n};", "sanal makinede kabulü henüz yapılmadı"),
    ("export const productHubEn = {", "\n} satisfies", "acceptance in a VM is still pending"),
])
def test_hub_card_states_the_prototype_and_pending_vm_acceptance(start, end, pending):
    entries = catalog("i18n/catalogs/productHub.ts", start, end, quote="'")
    hub = {key: value for key, value in entries.items() if key.startswith("productHub.edr.")}
    assert hub["productHub.edr.name"] == "Altay EDR"
    assert pending in hub["productHub.edr.limit"] and "self_reported / not_verified" in hub["productHub.edr.limit"]
    assert "VM" in entries["productHub.availability.prototype"]
    for key, value in hub.items():
        assert not FORBIDDEN.search(value), key
    entry = block(source("features/productHub/productCatalog.ts"), "{ kind: 'product', id: 'edr_agent',", "},")
    assert "availability: 'prototype_pending_acceptance'" in entry and "verification: 'not_verified'" in entry


# The agent card's expressions are pinned exactly. No TSX is rendered here, and a one-line edit of any of them would
# make the card misstate the agent's own report: a rule file or a running loop nobody reported, a hidden error code,
# an unreported counter shown as 0, a failed sensor labelled as started.

def test_card_shows_the_rule_file_presence_only():
    """true -> present, false -> absent, anything else (null) -> display.unknown; never a loaded-rules claim."""
    card = flat(agent_card())
    assert flat('const ruleFile: ProductTextKey = state.rule_file_present === true ? "product.edr.ruleFile.present"'
                ' : state.rule_file_present === false ? "product.edr.ruleFile.absent" : "display.unknown";') in card
    assert '[t("product.edr.ruleFile"), t(ruleFile)],' in card


def test_card_says_running_only_for_a_running_service_loop():
    card = flat(agent_card())
    assert 'const running = state.status === "running";' in card
    assert ('<ProductHeading id="edr_agent" label={t(running ? "product.edr.running" : "display.unknown")}'
            ' tone={running ? "purple" : "neutral"}/>') in card
    assert card.count("<ProductHeading") == 1 and card.count("product.edr.running") == 1


def test_card_shows_a_reported_error_code_and_unreported_counters_as_unknown():
    card = flat(agent_card())
    assert 'const unstable = state.sensor_state === "lost" || state.sensor_state === "failed";' in card
    assert ('const errorCode = state.sensor_error_code !== null ? <code>{state.sensor_error_code}</code>'
            ' : t(unstable ? "product.edr.sensorError.notReported" : "product.edr.sensorError.notApplicable");') in card
    assert '[t("product.edr.sensorError"), errorCode],' in card
    # null means the agent did not report the counter: display.unknown, never 0.
    assert ('const count = (value: number | null): string => value === null ? t("display.unknown")'
            ' : formatCount(value, locale);') in card
    assert ('<KeyValues values={EDR_COUNTER_KEYS.map((key): DisplayPair => [t(EDR_COUNTER_LABELS[key]),'
            ' count(state[key])])}/>') in card
    assert card.count("formatCount(") == 1


def test_card_labels_each_sensor_state_with_its_own_label():
    views = source("components/ProductViews.tsx")
    table = block(views, "const EDR_SENSOR_LABELS: Readonly<Record<string, ProductTextKey>> = {", "};")
    entry = r'(\w+): "([\w.]+)",'
    pairs = re.findall(entry, table)
    assert re.sub(entry, "", table).strip() == "", table
    labels = dict(pairs)
    assert len(labels) == len(pairs)
    assert labels == {state: "display.unknown" if state == "unknown" else f"product.edr.sensor.{state}"
                      for state in get_args(contracts.EdrSensorState)}
    # The card shows the table's label, and display.unknown for any other value.
    assert ('[t("product.edr.sensorState"), t(mapped(EDR_SENSOR_LABELS, state.sensor_state, "display.unknown"))],'
            in flat(agent_card()))
    mapped = block(views, "function mapped<T>(", "\n}")
    assert "return Object.hasOwn(values, key) ? values[key] ?? fallback : fallback;" in mapped
    # Each state reads as a different word in both languages.
    for start, end in (("export const productsTr = {", "\n};"), ("export const productsEn = {", "\n} satisfies")):
        entries = catalog("i18n/catalogs/products.ts", start, end)
        words = [entries[labels[state]] for state in get_args(contracts.EdrSensorState)]
        assert len(set(words)) == len(words), words


def test_card_shows_claims_counters_and_the_note():
    views = source("components/ProductViews.tsx")
    card = flat(agent_card())
    assert '<p className="state-note">{t("product.edr.notice")}</p>' in card
    assert '<p className="muted">{t("product.edr.countersScope")}</p>' in card
    assert ('[t("product.edr.claims"), `${t("app.claim.device")} (${state.source}) · ${t("app.claim.notVerified")}'
            ' (${state.producer_verification})`],') in card
    assert '[t("product.edr.startedAt"), formatDate(state.agent_started_at, locale)],' in card
    labels = dict(re.findall(r"(\w+): \"(product\.edr\.counter\.\w+)\"", block(views, "const EDR_COUNTER_LABELS", "};")))
    assert labels == {key: f"product.edr.counter.{key}" for key in counter_keys()}
    grid = block(views, "function ProductGrid(", "\n}")
    assert '<MissingProduct id="edr_agent"' in grid and "<EdrAgentCard record={agent}/>" in grid


def test_sample_mode_has_agent_statuses_and_missing_agents():
    demo = source("fixtures/demo-data.ts")
    specs = block(demo, "const specs: DeviceSpec[] = [", "\n  ];")
    assert specs.count("edrAgent(") >= 5
    assert {state for state in re.findall(r'edrAgent\(-?\d+, "(\w+)"', specs)} >= {"started", "failed", "disabled", "unknown"}
    assert 'code: "access_denied"' in specs
    # At least one device without the agent, so the missing card shows in sample mode.
    assert any("edrAgent(" not in line for line in re.findall(r"states: \[[^\n]*\] \}", specs))
    assert "missing_products: PRODUCT_IDS.filter(" in demo


def test_largest_four_product_detail_fits_the_default_strict_json_profile():
    """A device detail rendered by the Platform's own view functions, every value at its contract maximum."""
    when = datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    errors = list(get_args(contracts.ErrorCode))[:16]
    message = SnapshotEnvelope.model_validate({
        "schema_version": 2, "message_id": "00000000-0000-4000-8000-000000000009", "sequence": MAX_SNAPSHOT_SEQUENCE,
        "source_observed_at": "2030-01-02T03:04:05.123456Z", "products": [
            {"product_id": "hostbasedfirewall", "status": "unavailable", "error_codes": errors, "version": "V" * 64,
             "catalog_available": False, "source_observed_at": "2030-01-02T03:04:05.123456Z"},
            {"product_id": "termivar", "status": "experimental", "report_presence": "present", "version": "T" * 64,
             "source_observed_at": "2030-01-02T03:04:05.123456Z", "latest_report": {
                 "digest": "f" * 64, "report_schema": "venom-rendered-assessment/v1",
                 "imported_at": "2030-01-02T03:04:05.123456Z", "subject_count": 1024, "item_count": 4096,
                 "counts": {"informational": 4096, "needs_review": 0, "confirmed": 0},
                 "severity_counts": {"unassigned": 4096, "info": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}}},
            {"product_id": "antivirus", "status": "unknown", "availability": "unknown", "catalog_available": False},
            {"product_id": "edr_agent", "status": "running", "version": "E" * 64, "engine_id": "G" * 128,
             "agent_started_at": "2030-01-02T03:04:05.123456Z", "source_observed_at": "2030-01-02T03:04:05.123456Z",
             "rule_file_present": True, "sensor_state": "failed", "sensor_error_code": "session_start_failed",
             **{key: MAX_SNAPSHOT_SEQUENCE for key in counter_keys()}}]})
    row = SimpleNamespace(id=UUID(int=1), tenant_id=UUID(int=2), label="L" * 80, created_at=when, revoked_at=when,
                          last_sequence=message.sequence, last_received_at=when, source_observed_at=when)
    products = [SimpleNamespace(product_id=product.product_id, snapshot_sequence=message.sequence, received_at=when,
                                payload=product.model_dump(mode="json")) for product in message.products]
    detail = {**_device_view(row, when + timedelta(seconds=1), DEFAULT_LIMITS),
              "products": [_product_view(product, when + timedelta(seconds=1)) for product in products],
              "missing_products": []}
    text = json.dumps(detail, ensure_ascii=False, separators=(",", ":"))
    fits, usage = _fits(text, _budgets()[1]["default"])
    assert fits, usage
    integers = re.findall(r"(?<![\w.\"])-?\d+(?![\w.\"])", text)
    assert max(int(value) for value in integers) == MAX_SNAPSHOT_SEQUENCE == 2**53 - 1
