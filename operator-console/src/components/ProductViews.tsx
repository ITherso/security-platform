import { Fragment } from "react";
import type { ReactNode } from "react";
import { EDR_CAPABILITY_KEYS, EDR_COUNTER_KEYS, EDR_V3_COUNTER_KEYS } from "../data/contracts";
import type { AuditPage, CapabilityState, DeviceDetail as DeviceDetailDto, EdrAgentState, EdrAgentStateV3, EdrCapabilityKey,
  EdrCounterKey, EdrV3CounterKey, IsolationState, PreviousRunEnd, ProductRecord, ResponseChannelState, RuleSetState,
  ServiceConfigState, TermivarSummary } from "../data/contracts";
import { isEdrAgentStateV3 } from "../data/normalize";
import { booleanLabel, displayText, formatAge, formatCount, formatDate, shortIdentifier } from "./display";
import { useLocale } from "../i18n/LocaleProvider";
import type { ProductTextKey } from "../i18n/catalogs/products";

type Tone = "success" | "warning" | "danger" | "neutral" | "purple";
type ProductId = ProductRecord["product_id"];
type FirewallRecord = Extract<ProductRecord, { product_id: "hostbasedfirewall" }>;
type TermivarRecord = Extract<ProductRecord, { product_id: "termivar" }>;
type AntivirusRecord = Extract<ProductRecord, { product_id: "antivirus" }>;
type EdrAgentAnyRecord = Extract<ProductRecord, { product_id: "edr_agent" }>;
type EdrAgentRecord = Omit<EdrAgentAnyRecord, "state"> & { readonly state: EdrAgentState };
type EdrAgentV3Record = Omit<EdrAgentAnyRecord, "state"> & { readonly state: EdrAgentStateV3 };
type DisplayPair = readonly [label: string, value: ReactNode];

const PRODUCT_LABELS: Readonly<Record<ProductId, ProductTextKey>> = {
  hostbasedfirewall: "product.name.hostbasedfirewall", termivar: "product.name.termivar", antivirus: "product.name.antivirus",
  edr_agent: "product.name.edr_agent",
};
const EDR_SENSOR_LABELS: Readonly<Record<string, ProductTextKey>> = {
  started: "product.edr.sensor.started", lost: "product.edr.sensor.lost", failed: "product.edr.sensor.failed",
  stopped: "product.edr.sensor.stopped", disabled: "product.edr.sensor.disabled", unknown: "display.unknown",
};
const EDR_COUNTER_LABELS: Readonly<Record<EdrCounterKey, ProductTextKey>> = {
  events_queue_dropped: "product.edr.counter.events_queue_dropped", events_write_failed: "product.edr.counter.events_write_failed",
  events_unmapped: "product.edr.counter.events_unmapped", events_skipped: "product.edr.counter.events_skipped",
  events_evicted: "product.edr.counter.events_evicted", events_discarded: "product.edr.counter.events_discarded",
  events_degraded: "product.edr.counter.events_degraded", outbox_backlog: "product.edr.counter.outbox_backlog",
};
/** Snapshot V3: the V2 counters, then the Stage 3 ones. */
const EDR_V3_COUNTER_LABELS: Readonly<Record<EdrV3CounterKey, ProductTextKey>> = {
  ...EDR_COUNTER_LABELS, scans_completed: "product.edr.counter.scans_completed",
  scans_detected: "product.edr.counter.scans_detected", scans_no_verdict: "product.edr.counter.scans_no_verdict",
  scan_jobs_dropped: "product.edr.counter.scan_jobs_dropped", scan_cache_hits: "product.edr.counter.scan_cache_hits",
  etw_events_lost: "product.edr.counter.etw_events_lost", file_change_gaps: "product.edr.counter.file_change_gaps",
  cmdline_unavailable: "product.edr.counter.cmdline_unavailable",
};
const EDR_CAPABILITY_LABELS: Readonly<Record<EdrCapabilityKey, ProductTextKey>> = {
  realtime_scan_state: "product.edrV3.realtimeScan", file_change_sensor_state: "product.edrV3.fileChangeSensor",
  command_line_sensor_state: "product.edrV3.commandLineSensor", persistence_watch_state: "product.edrV3.persistenceWatch",
};
const RULE_SET_LABELS: Readonly<Record<RuleSetState, ProductTextKey>> = {
  compiled: "product.edrV3.ruleSet.compiled", missing: "product.edrV3.ruleSet.missing",
  invalid: "product.edrV3.ruleSet.invalid", unreadable: "product.edrV3.ruleSet.unreadable", unknown: "display.unknown",
};
const CAPABILITY_LABELS: Readonly<Record<CapabilityState, ProductTextKey>> = {
  running: "product.edrV3.capability.running", degraded: "product.edrV3.capability.degraded",
  stopped: "product.edrV3.capability.stopped", failed: "product.edrV3.capability.failed",
  not_available: "product.edrV3.capability.not_available", unknown: "display.unknown",
};
const RESPONSE_CHANNEL_LABELS: Readonly<Record<ResponseChannelState, ProductTextKey>> = {
  ready: "product.edrV3.responseChannel.ready", not_configured: "product.edrV3.responseChannel.not_configured",
  awaiting_tenant_binding: "product.edrV3.responseChannel.awaiting_tenant_binding",
  journal_invalid: "product.edrV3.responseChannel.journal_invalid", unknown: "display.unknown",
};
const ISOLATION_LABELS: Readonly<Record<IsolationState, ProductTextKey>> = {
  inactive: "product.edrV3.isolation.inactive", active: "product.edrV3.isolation.active",
  partial: "product.edrV3.isolation.partial", unknown: "display.unknown",
};
const SERVICE_CONFIG_LABELS: Readonly<Record<ServiceConfigState, ProductTextKey>> = {
  as_installed: "product.edrV3.serviceConfig.as_installed", changed: "product.edrV3.serviceConfig.changed",
  unknown: "display.unknown",
};
const PREVIOUS_RUN_LABELS: Readonly<Record<PreviousRunEnd, ProductTextKey>> = {
  clean: "product.edrV3.previousRun.clean", unclean: "product.edrV3.previousRun.unclean",
  first_start: "product.edrV3.previousRun.first_start", unknown: "display.unknown",
};
const ERROR_LABELS: Readonly<Record<string, ProductTextKey>> = {
  config_error: "product.error.config_error", policy_error: "product.error.policy_error", temp_error: "product.error.temp_error",
  runtime_error: "product.error.runtime_error", telemetry_error: "product.error.telemetry_error", history_error: "product.error.history_error",
  network_profile_error: "product.error.network_profile_error", recovery_error: "product.error.recovery_error",
  application_rule_recovery_error: "product.error.application_rule_recovery_error", liveness_error: "product.error.liveness_error",
  application_usage_error: "product.error.application_usage_error", maintenance: "product.error.maintenance",
  health_unavailable: "product.error.health_unavailable", unknown_error: "product.error.unknown_error",
};
const AUDIT_ACTIONS: Readonly<Record<string, ProductTextKey>> = {
  tenant_created: "product.audit.action.tenant_created", membership_set: "product.audit.action.membership_set",
  membership_revoked: "product.audit.action.membership_revoked", enrollment_grant_created: "product.audit.action.enrollment_grant_created",
  enrollment_grant_revoked: "product.audit.action.enrollment_grant_revoked", device_enrolled: "product.audit.action.device_enrolled",
  device_revoked: "product.audit.action.device_revoked", device_credential_rotated: "product.audit.action.device_credential_rotated",
  tenant_event_retention_set: "product.audit.action.tenant_event_retention_set",
  alert_acknowledged: "product.audit.action.alert_acknowledged", alert_closed: "product.audit.action.alert_closed",
  tenant_alert_retention_set: "product.audit.action.tenant_alert_retention_set",
  alerts_pruned: "product.audit.action.alerts_pruned",
};
const ACTOR_LABELS: Readonly<Record<string, ProductTextKey>> = {
  operator: "product.audit.actor.operator", device: "product.audit.actor.device", local_admin: "product.audit.actor.local_admin",
};
const OBJECT_LABELS: Readonly<Record<string, ProductTextKey>> = {
  tenant: "product.audit.object.tenant", membership: "product.audit.object.membership", enrollment_grant: "product.audit.object.enrollment_grant",
  device: "product.audit.object.device", device_credential: "product.audit.object.device_credential",
  alert: "product.audit.object.alert",
};
const SEVERITIES = [
  ["critical", "product.severity.critical"], ["high", "product.severity.high"], ["medium", "product.severity.medium"],
  ["low", "product.severity.low"], ["info", "product.severity.info"], ["unassigned", "product.severity.unassigned"],
] as const;

function mapped<T>(values: Readonly<Record<string, T>>, key: string, fallback: T): T {
  return Object.hasOwn(values, key) ? values[key] ?? fallback : fallback;
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  return <span className="badge" data-tone={tone}>{children}</span>;
}

function KeyValues({ values }: { values: readonly DisplayPair[] }) {
  return <dl className="key-values">{values.map(([label, value]) =>
    <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
  )}</dl>;
}

function Heading({ title, subtitle, eyebrow }: { title: string; subtitle?: string; eyebrow?: string }) {
  return <div className="view-heading">
    {eyebrow && <p className="eyebrow">{eyebrow}</p>}
    <h2>{title}</h2>
    {subtitle && <p className="muted">{subtitle}</p>}
  </div>;
}

function EmptyState({ title, description, role }: {
  title: string; description?: string; role?: "status" | "alert";
}) {
  return <div className="empty-state" role={role}>
    <h3>{title}</h3>{description && <p className="muted">{description}</p>}
  </div>;
}

function ProductHeading({ id, label, tone }: { id: ProductId; label: string; tone: Tone }) {
  const { t } = useLocale();
  return <div className="panel-heading"><h3>{t(PRODUCT_LABELS[id])}</h3><Badge tone={tone}>{label}</Badge></div>;
}

function MissingProduct({ id, selected }: { id: ProductId; selected: boolean }) {
  const { t } = useLocale();
  const catalog: Record<ProductId, { label: ProductTextKey; tone: Tone; description: ProductTextKey }> = {
    hostbasedfirewall: { label: "product.catalog.localFirewall", tone: "neutral", description: "product.catalog.firewallDescription" },
    termivar: { label: "product.catalog.experimental", tone: "purple", description: "product.catalog.termivarDescription" },
    antivirus: { label: "product.catalog.planned", tone: "neutral", description: "product.catalog.antivirusDescription" },
    edr_agent: { label: "product.catalog.prototype", tone: "purple", description: "product.catalog.edrDescription" },
  };
  const item = catalog[id];
  return <article className="product-card">
    <ProductHeading id={id} label={t(selected ? "product.missing.badge" : item.label)} tone={selected ? "neutral" : item.tone}/>
    <p className="product-description">{t(item.description)}</p>
    <p className="muted">{t(selected ? "product.missing.explanation" : "product.missing.selectDevice")}</p>
  </article>;
}

function FirewallCard({ record }: { record: FirewallRecord }) {
  const { locale, t } = useLocale();
  const state = record.state;
  const statuses: Readonly<Record<string, readonly [ProductTextKey, Tone]>> = {
    running: ["product.hbf.running", "success"], observing: ["product.hbf.observing", "purple"],
    degraded: ["product.hbf.degraded", "warning"], stopped: ["product.hbf.stopped", "danger"],
    unavailable: ["product.hbf.unavailable", "neutral"], unknown: ["display.unknown", "neutral"],
  };
  const [label, tone] = mapped(statuses, state.status, ["display.unknown", "neutral"] as const);
  const modes: Readonly<Record<string, ProductTextKey>> = { enforce: "product.hbf.enforce", sniff: "product.hbf.observing", unknown: "display.unknown" };
  const errors = state.error_codes;
  const errorText = errors == null ? t("product.errors.unknown") : errors.length
    ? t("product.errors.reported", errors.map(code => t(mapped(ERROR_LABELS, code, "product.error.unknown_error"))).join(" · "))
    : t("product.errors.none");
  return <article className="product-card">
    <ProductHeading id="hostbasedfirewall" label={t(label)} tone={tone}/>
    <p className="product-description">{t("product.hbf.description")}</p>
    <KeyValues values={[
      [t("product.label.version"), displayText(state.version, t("display.unknown"))],
      [t("product.label.mode"), t(mapped(modes, state.firewall_mode, "display.unknown"))],
      [t("product.label.installed"), booleanLabel(state.installed, locale)],
      [t("product.label.running"), booleanLabel(state.reported_running, locale)],
      [t("product.label.reportedStale"), booleanLabel(state.reported_stale, locale)],
      [t("product.label.received"), formatDate(record.received_at, locale)],
      [t("product.label.sourceAge"), formatAge(record.observation, locale)],
    ]}/>
    <p className="state-note">{errorText}</p>
  </article>;
}

function SeveritySummary({ report }: { report: TermivarSummary }) {
  const { locale, t } = useLocale();
  const values = report.severity_counts;
  if (!values || SEVERITIES.some(([key]) => !Number.isSafeInteger(values[key]) || values[key] < 0)) {
    return <p className="muted">{t("product.severity.unknown")}</p>;
  }
  const total = SEVERITIES.reduce((sum, [key]) => sum + values[key], 0);
  if (total === 0) return <p className="muted">{t("product.severity.empty")}</p>;
  return <div className="severity-legend" role="list" aria-label={t("product.severity.aria")}>
    {SEVERITIES.map(([key, label]) =>
      <span key={key} role="listitem" data-severity={key}>{t(label)} {formatCount(values[key], locale)}</span>
    )}
  </div>;
}

function TermivarCard({ record }: { record: TermivarRecord }) {
  const { locale, t } = useLocale();
  const state = record.state;
  const report = state.latest_report;
  const presence: Readonly<Record<string, ProductTextKey>> = { present: "product.termivar.present", none: "product.termivar.none", unknown: "display.unknown" };
  return <article className="product-card">
    <ProductHeading id="termivar" label={t(state.status === "experimental" ? "product.catalog.experimental" : "display.unknown")} tone="purple"/>
    <p className="product-description">{t("product.termivar.description")}</p>
    <KeyValues values={[
      [t("product.termivar.report"), t(mapped(presence, state.report_presence, "display.unknown"))],
      [t("product.termivar.installed"), booleanLabel(state.scanner_installed, locale)],
      [t("product.termivar.importAge"), formatAge(record.report_import_age, locale)],
      [t("product.label.sourceAge"), formatAge(record.observation, locale)],
      [t("product.label.received"), formatDate(record.received_at, locale)],
    ]}/>
    {report && state.report_presence === "present" && <>
      <h4>{t("product.termivar.recordsTitle")}</h4>
      <KeyValues values={[
        [t("product.termivar.subjects"), formatCount(report.subject_count, locale)],
        [t("product.termivar.items"), formatCount(report.item_count, locale)],
        [t("product.termivar.informational"), formatCount(report.counts.informational, locale)],
        [t("product.termivar.needsReview"), formatCount(report.counts.needs_review, locale)],
        [t("product.termivar.confirmed"), formatCount(report.counts.confirmed, locale)],
        [t("product.termivar.imported"), formatDate(report.imported_at, locale)],
      ]}/>
      <SeveritySummary report={report}/>
    </>}
    <p className="state-note">{t("product.termivar.notice")}</p>
  </article>;
}

function AntivirusCard({ record }: { record: AntivirusRecord }) {
  const { locale, t } = useLocale();
  const state = record.state;
  return <article className="product-card">
    <ProductHeading id="antivirus" label={t(state.status === "planned" ? "product.catalog.planned" : "display.unknown")} tone="neutral"/>
    <p className="product-description">{t("product.catalog.antivirusDescription")}</p>
    <KeyValues values={[
      [t("product.antivirus.availability"), t(state.availability === "unavailable" ? "product.antivirus.unavailable" : "display.unknown")],
      [t("product.label.received"), formatDate(record.received_at, locale)],
      [t("product.label.sourceAge"), formatAge(record.observation, locale)],
    ]}/>
    <p className="state-note">{t("product.antivirus.notice")}</p>
  </article>;
}

/** The agent's own state (Snapshot V3), told from V2 by its key set. Every value is the agent's claim: "compiled" is
 * only that it compiled its rule file, its scans run after the fact (after a process start, its own start, a file
 * change, a remote scan request or on a persistence target) and block nothing, an isolation state is its report about
 * its own filters, and the console sends it no action. */
function EdrAgentV3Card({ record }: { record: EdrAgentV3Record }) {
  const { locale, t } = useLocale();
  const state = record.state;
  const running = state.status === "running";
  const unstable = state.sensor_state === "lost" || state.sensor_state === "failed";
  const errorCode = state.sensor_error_code !== null ? <code>{state.sensor_error_code}</code>
    : t(unstable ? "product.edr.sensorError.notReported" : "product.edr.sensorError.notApplicable");
  const count = (value: number | null): string => value === null ? t("display.unknown") : formatCount(value, locale);
  const hex = (value: string): ReactNode => <code title={value}>{value.slice(0, 16)}…</code>;
  const heartbeat = state.heartbeat_interval_seconds;
  const keys = state.response_key_ids;
  return <article className="product-card">
    <ProductHeading id="edr_agent" label={t(running ? "product.edr.running" : "display.unknown")} tone={running ? "purple" : "neutral"}/>
    <p className="product-description">{t("product.edrV3.description")}</p>
    <KeyValues values={[
      [t("product.edr.version"), displayText(state.version, t("display.unknown"))],
      [t("product.edr.startedAt"), formatDate(state.agent_started_at, locale)],
      [t("product.edr.engine"), displayText(state.engine_id, t("display.unknown"))],
      [t("product.edrV3.ruleSet"), t(mapped(RULE_SET_LABELS, state.rule_set_state, "display.unknown"))],
      [t("product.edrV3.ruleSetId"), state.rule_set_id === null ? t("display.unknown") : hex(state.rule_set_id)],
      [t("product.edrV3.behaviorRules"), displayText(state.behavior_rules_version, t("display.unknown"))],
      [t("product.edr.sensorState"), t(mapped(EDR_SENSOR_LABELS, state.sensor_state, "display.unknown"))],
      [t("product.edr.sensorError"), errorCode],
      [t("product.edrV3.serviceConfig"), t(mapped(SERVICE_CONFIG_LABELS, state.service_config_state, "display.unknown"))],
      [t("product.edrV3.previousRun"), t(mapped(PREVIOUS_RUN_LABELS, state.previous_run_end, "display.unknown"))],
      [t("product.edrV3.heartbeat"), heartbeat === null ? t("display.unknown")
        : t("product.edrV3.seconds", formatCount(heartbeat, locale), heartbeat)],
      [t("product.label.received"), formatDate(record.received_at, locale)],
      [t("product.label.sourceAge"), formatAge(record.observation, locale)],
      [t("product.edr.claims"), `${t("app.claim.device")} (${state.source}) · ${t("app.claim.notVerified")} (${state.producer_verification})`],
    ]}/>
    <h4>{t("product.edrV3.capabilitiesTitle")}</h4>
    <KeyValues values={EDR_CAPABILITY_KEYS.map((key): DisplayPair =>
      [t(EDR_CAPABILITY_LABELS[key]), t(mapped(CAPABILITY_LABELS, state[key], "display.unknown"))])}/>
    <p className="state-note">{t("product.edrV3.scanNote")}</p>
    <h4>{t("product.edrV3.responseTitle")}</h4>
    <KeyValues values={[
      [t("product.edrV3.responseChannel"), t(mapped(RESPONSE_CHANNEL_LABELS, state.response_channel_state, "display.unknown"))],
      [t("product.edrV3.responseActions"), state.response_actions_enabled.length ? state.response_actions_enabled.join(", ")
        : t("product.edrV3.none")],
      [t("product.edrV3.responseKeys"), keys.length
        ? keys.map((id, index) => <Fragment key={id}>{index ? " " : null}{hex(id)}</Fragment>) : t("product.edrV3.none")],
      [t("product.edrV3.lastAction"), count(state.last_action_seq)],
      [t("product.edrV3.isolation"), t(mapped(ISOLATION_LABELS, state.isolation_state, "display.unknown"))],
      [t("product.edrV3.isolationUntil"), formatDate(state.isolation_until, locale)],
      [t("product.edrV3.isolationChecked"), formatDate(state.isolation_checked_at, locale)],
      [t("product.edrV3.quarantine"), count(state.quarantine_items)],
    ]}/>
    <p className="muted">{t("product.edrV3.responseScope")}</p>
    <h4>{t("product.edr.countersTitle")}</h4>
    <KeyValues values={EDR_V3_COUNTER_KEYS.map((key): DisplayPair => [t(EDR_V3_COUNTER_LABELS[key]), count(state[key])])}/>
    <p className="muted">{t("product.edrV3.countersScope")}</p>
    <p className="state-note">{t("product.edrV3.notice")}</p>
  </article>;
}

function isV3Record(record: EdrAgentRecord | EdrAgentV3Record): record is EdrAgentV3Record {
  return isEdrAgentStateV3(record.state);
}

/** The agent's own state (Snapshot V2). Presence of the rule file only; nothing here is a protection claim. */
function EdrAgentCard({ record }: { record: EdrAgentRecord }) {
  const { locale, t } = useLocale();
  const state = record.state;
  const running = state.status === "running";
  const ruleFile: ProductTextKey = state.rule_file_present === true ? "product.edr.ruleFile.present"
    : state.rule_file_present === false ? "product.edr.ruleFile.absent" : "display.unknown";
  const unstable = state.sensor_state === "lost" || state.sensor_state === "failed";
  const errorCode = state.sensor_error_code !== null ? <code>{state.sensor_error_code}</code>
    : t(unstable ? "product.edr.sensorError.notReported" : "product.edr.sensorError.notApplicable");
  const count = (value: number | null): string => value === null ? t("display.unknown") : formatCount(value, locale);
  return <article className="product-card">
    <ProductHeading id="edr_agent" label={t(running ? "product.edr.running" : "display.unknown")} tone={running ? "purple" : "neutral"}/>
    <p className="product-description">{t("product.edr.description")}</p>
    <KeyValues values={[
      [t("product.edr.version"), displayText(state.version, t("display.unknown"))],
      [t("product.edr.startedAt"), formatDate(state.agent_started_at, locale)],
      [t("product.edr.engine"), displayText(state.engine_id, t("display.unknown"))],
      [t("product.edr.ruleFile"), t(ruleFile)],
      [t("product.edr.sensorState"), t(mapped(EDR_SENSOR_LABELS, state.sensor_state, "display.unknown"))],
      [t("product.edr.sensorError"), errorCode],
      [t("product.label.received"), formatDate(record.received_at, locale)],
      [t("product.label.sourceAge"), formatAge(record.observation, locale)],
      [t("product.edr.claims"), `${t("app.claim.device")} (${state.source}) · ${t("app.claim.notVerified")} (${state.producer_verification})`],
    ]}/>
    <h4>{t("product.edr.countersTitle")}</h4>
    <KeyValues values={EDR_COUNTER_KEYS.map((key): DisplayPair => [t(EDR_COUNTER_LABELS[key]), count(state[key])])}/>
    <p className="muted">{t("product.edr.countersScope")}</p>
    <p className="state-note">{t("product.edr.notice")}</p>
  </article>;
}

function ProductGrid({ detail }: { detail: DeviceDetailDto | null }) {
  const firewall = detail?.products.find((product): product is FirewallRecord => product.product_id === "hostbasedfirewall");
  const termivar = detail?.products.find((product): product is TermivarRecord => product.product_id === "termivar");
  const antivirus = detail?.products.find((product): product is AntivirusRecord => product.product_id === "antivirus");
  const edr = detail?.products.find((product): product is EdrAgentRecord | EdrAgentV3Record => product.product_id === "edr_agent");
  // V3 is told from V2 by its key set (normalize.ts isEdrAgentStateV3); a V2 device keeps the V2 card.
  const agentV3 = edr !== undefined && isV3Record(edr) ? edr : undefined;
  const agent = edr !== undefined && !isV3Record(edr) ? edr : undefined;
  return <div className="product-grid">
    {firewall ? <FirewallCard record={firewall}/> : <MissingProduct id="hostbasedfirewall" selected={detail !== null}/>}
    {termivar ? <TermivarCard record={termivar}/> : <MissingProduct id="termivar" selected={detail !== null}/>}
    {antivirus ? <AntivirusCard record={antivirus}/> : <MissingProduct id="antivirus" selected={detail !== null}/>}
    {agentV3 ? <EdrAgentV3Card record={agentV3}/>
      : agent ? <EdrAgentCard record={agent}/> : <MissingProduct id="edr_agent" selected={detail !== null}/>}
  </div>;
}

export interface ProductCardsProps { detail?: DeviceDetailDto | null }

export function ProductCards({ detail = null }: ProductCardsProps) {
  const { t } = useLocale();
  return <section className="panel">
    <Heading title={t("product.products.title")} eyebrow={t("product.products.eyebrow")} subtitle={detail
      ? t("product.products.forDevice", displayText(detail.label, t("product.device.unnamed")))
      : t("product.products.noSelection")}/>
    <ProductGrid detail={detail}/>
    {detail && <p className="muted">{t("product.products.sourceNotice")}</p>}
  </section>;
}

export interface DeviceDetailProps { detail: DeviceDetailDto | null; onClose?: () => void; actions?: ReactNode }

export function DeviceDetail({ detail, onClose, actions }: DeviceDetailProps) {
  const { locale, t } = useLocale();
  if (!detail) return <EmptyState title={t("product.device.notSelected")} description={t("product.device.selectHelp")}/>;
  const connection: Readonly<Record<string, readonly [ProductTextKey, Tone]>> = {
    recent: ["product.device.recent", "success"], stale: ["product.device.stale", "warning"],
    never_seen: ["product.device.neverSeen", "neutral"],
  };
  const [connectionLabel, connectionTone] = mapped(connection, detail.connection_status, ["product.device.unknownConnection", "neutral"] as const);
  return <section className="panel">
    <div className="panel-heading">
      <Heading title={displayText(detail.label, t("product.device.unnamed"))} subtitle={detail.id} eyebrow={t("product.device.eyebrow")}/>
      {onClose && <button type="button" className="btn btn-ghost" onClick={onClose} aria-label={t("product.device.closeAria")}>{t("product.device.close")}</button>}
    </div>
    <div className="detail-actions">
      <Badge tone={detail.identity_status === "revoked" ? "danger" : "neutral"}>{t(detail.identity_status === "revoked"
        ? "product.device.revoked" : detail.identity_status === "active" ? "product.device.active" : "product.device.unknownRegistration")}</Badge>
      <Badge tone={connectionTone}>{t(connectionLabel)}</Badge>
    </div>
    {actions}
    <KeyValues values={[
      [t("product.device.created"), formatDate(detail.created_at, locale)],
      [t("product.device.lastReceived"), formatDate(detail.last_received_at, locale)],
      [t("product.device.sourceObserved"), formatDate(detail.source_observed_at, locale)],
      [t("product.label.sourceAge"), formatAge(detail.source_observation, locale)],
      [t("product.device.sequence"), detail.last_sequence === null ? t("display.unknown") : String(detail.last_sequence)],
      [t("product.device.revokedAt"), detail.revoked_at ? formatDate(detail.revoked_at, locale) : t("product.device.noRevocation")],
    ]}/>
    <p className="state-note">{t("product.device.trustNotice")}</p>
    <h3 className="detail-section">{t("product.device.productsTitle")}</h3>
    <ProductGrid detail={detail}/>
    <p className="muted">{t("product.device.sourceNotice")}</p>
  </section>;
}

function AuditReference({ label, value }: { label: string; value: string | null }) {
  const { locale } = useLocale();
  return <div className="audit-reference"><span>{label}</span><small className="muted" title={value ?? undefined}>{shortIdentifier(value, locale)}</small></div>;
}

export interface AuditViewProps {
  page: AuditPage | null;
  tenantName?: string;
  status?: "ready" | "loading" | "error" | "idle";
  errorMessage?: string;
  onNext?: (offset: number) => void;
  onPrev?: () => void;
}

export function AuditView({ page, tenantName = "", status = "ready", errorMessage = "", onNext, onPrev }: AuditViewProps) {
  const { locale, t } = useLocale();
  const nextOffset = page?.next_offset ?? null;
  const hasNext = nextOffset !== null && Number.isSafeInteger(nextOffset) && nextOffset >= 0 && nextOffset <= 10000;
  const columns = ["product.audit.action", "product.audit.object", "product.audit.actor", "product.audit.time", "product.audit.outcome"] as const;
  return <section className="panel" aria-busy={status === "loading"}>
    <Heading title={t("product.audit.title")} eyebrow={t("product.audit.eyebrow")} subtitle={tenantName
      ? t("product.audit.tenantSubtitle", tenantName) : t("product.audit.defaultSubtitle")}/>
    {status === "loading" ? <EmptyState title={t("product.audit.loading")} role="status"/>
      : status === "error" ? <EmptyState title={t("product.audit.error")} role="alert" description={displayText(errorMessage, t("product.audit.errorHelp"))}/>
      : status !== "ready" || !page ? <EmptyState title={t("product.audit.notLoaded")} description={t("product.audit.selectHelp")}/>
      : <>
        {!page.items.length ? <EmptyState title={t("product.audit.empty")} description={t("product.audit.emptyHelp")}/>
          : <div className="table-scroll"><table className="data-table">
            <caption className="muted">{t("product.audit.caption", displayText(tenantName, t("product.audit.selectedTenant")))}</caption>
            <thead><tr>{columns.map(key => <th key={key} scope="col">{t(key)}</th>)}</tr></thead>
            <tbody>{page.items.map(entry => <tr key={entry.id}>
              <td>{t(mapped(AUDIT_ACTIONS, entry.action, "product.audit.unknownAction"))}</td>
              <td><AuditReference label={t(mapped(OBJECT_LABELS, entry.object_type, "product.audit.object"))} value={entry.object_id}/></td>
              <td><AuditReference label={t(mapped(ACTOR_LABELS, entry.actor_type, "display.unknown"))} value={entry.actor_id}/></td>
              <td>{formatDate(entry.created_at, locale)}</td>
              <td><Badge tone={entry.outcome === "success" ? "success" : "neutral"}>{t(entry.outcome === "success" ? "product.audit.success" : "product.audit.unknownOutcome")}</Badge></td>
            </tr>)}</tbody>
          </table></div>}
        <div className="audit-pagination">
          <span className="muted">{t("product.audit.loadedCount", formatCount(page.items.length, locale), page.items.length)}</span>
          <div className="detail-actions">
            <button type="button" className="btn btn-ghost" disabled={!onPrev} onClick={onPrev}>{t("product.audit.previous")}</button>
            <button type="button" className="btn btn-ghost" disabled={!hasNext || !onNext} onClick={() => {
              if (hasNext && onNext && nextOffset !== null) onNext(nextOffset);
            }}>{t("product.audit.next")}</button>
          </div>
        </div>
        <p className="muted">{t("product.audit.scopeNotice")}</p>
      </>}
  </section>;
}
