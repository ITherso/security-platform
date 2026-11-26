"""Built-in server rules on self-reported endpoint events, and the operator alert lifecycle.

A rule match is not a diagnosis. Alerts are derived from what a device says
about itself, so every alert stays self_reported/not_verified like its events.
No rule says that anything was protected, blocked or prevented.

The event rules run inside event ingestion, in the same transaction, only for
the events of a newly accepted batch: an exact retry, a conflict, a 413 or a
422 evaluates nothing. They read only contract fields: the masked image paths
as stored, pids, create times, kinds, the closed values of the v2 kinds, and
event_seq values. The four Stage 2 rules apply unchanged to v1 events and to
the v2 shapes of the three v1 kinds. The five Stage 3 event rules keep the
triggering event's own fields as evidence. agent_silent is never raised by an
event: `security-platform sweep` (services/sweep.py) opens it from the server
clock, through the same upsert and cap.

Deduplication: while an alert of a (tenant, device, rule, key) is not closed,
a new match updates it. Every distinct key of a batch is one bounded INSERT ...
ON CONFLICT on the partial unique index uq_alert_not_closed_key, so an
operator's close racing an ingestion ends either in the closed alert plus a new
open one, or in a closed alert that includes the match; never in two alerts
that are not closed. The device row lock that ingestion (or the sweep) holds
serialises every opening of one device's alerts; operators only acknowledge or
close.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, cast, func, literal, literal_column, or_, select, text, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from security_platform.event_contracts import BEHAVIOR_RULES
from security_platform.models import Alert, Device, EndpointEvent
from security_platform.services.audit import write_event
from security_platform.services.common import (DEFAULT_LIMITS, Conflict, NotFound, ServiceError, canonical_utc, iso,
    locked_tenant, require_membership, utc_now)


# Every rule's severity, low or medium only, in this order. RULES is the single source of the alert rules: the
# alerts.ck_alert_rule CHECK (migration 0005 hardcodes its copy; a parity test compares them) and the operator
# console mirror it.
SEVERITY = {"user_writable_launch": "low", "office_browser_spawned_tool": "medium", "sensor_unstable": "medium",
            "event_loss": "medium", "scan_detection": "medium", "behavior_match": "medium",
            "persistence_added": "low", "capability_down": "medium", "tamper_signal": "medium",
            "agent_silent": "medium"}
RULES = tuple(SEVERITY)
# A behavior_match alert's severity comes from this table, keyed by the closed behavior rule id: the server's,
# never the agent's (the event carries no severity, and extra="forbid" refuses one). A new behavior rule ships
# in the agent and the Platform together (ADR 0004 section 4).
BEHAVIOR_SEVERITY = {rule: "medium" for rule in BEHAVIOR_RULES}
# The evidence of the five Stage 3 event rules: these fields of the triggering event under the same names, as
# stored. Each is the timeline field list of its kind (event_contracts.EVENT_FIELDS, the shape the console
# requires), so the evidence is a subset of the event's own stored payload and fits the 4 KiB evidence CHECK
# whenever the event fits its own 4 KiB payload CHECK.
EVIDENCE_FIELDS = {
    "scan_detection": ("trigger", "path", "size", "sha256", "rule_set_id", "hits", "omitted_hits", "pid",
                       "create_time", "action_id"),
    "behavior_match": ("rule", "rule_version", "pid", "create_time", "image", "parent_image", "found_at_start",
                       "command_line_source"),
    "persistence_added": ("location", "scope", "change", "entry_id", "target_image", "found_at_start"),
    "capability_down": ("subject", "state", "code", "rule_set_id"),
    "tamper_signal": ("signal", "detail"),
}
# capability_down: the agent_state (subject, state) pairs that raise it, keyed by subject. Every other pair
# (running, degraded, not_available, stopping, a sensor's stopped, ...) raises nothing.
CAPABILITY_DOWN = {"realtime_scan": ("stopped", "failed"), "rule_set": ("missing", "invalid", "unreadable"),
                   "file_change_sensor": ("failed",), "command_line_sensor": ("failed",),
                   "persistence_watch": ("failed",), "response_channel": ("journal_invalid",)}
# persistence_added: the changes that raise it; a removal raises nothing.
PERSISTENCE_ADDED_CHANGES = ("added", "modified")
STATUSES = ("open", "acknowledged", "closed")
TOOLS = frozenset({"mshta.exe", "regsvr32.exe", "rundll32.exe", "wscript.exe", "cscript.exe", "powershell.exe",
                   "pwsh.exe", "cmd.exe", "certutil.exe", "bitsadmin.exe", "msbuild.exe", "installutil.exe",
                   "wmic.exe", "schtasks.exe"})
OFFICE_AND_BROWSERS = frozenset({"winword.exe", "excel.exe", "powerpnt.exe", "outlook.exe", "msaccess.exe",
                                 "mspub.exe", "onenote.exe", "visio.exe", "chrome.exe", "msedge.exe", "firefox.exe",
                                 "brave.exe", "opera.exe", "iexplore.exe"})
# A parent is looked for among the child's previous 2000 event_seq values of
# the same device only. A parent outside this window, or one whose event was
# already deleted (retention prune or the per-device cap), is not found, and
# the rule stays silent. A v2 child that names its parent's create time is the
# exception: its parent is that exact process, at any distance (see
# _stored_exact_parents), and only that one.
PARENT_LOOKBACK = 2000
# Equals the alerts evidence CHECK (octet_length(evidence::text) <= 4096).
MAX_EVIDENCE_BYTES = 4096
ELLIPSIS = "…"
_SEPARATORS = re.compile(r"[\\/]")
# The paging cursor's time: ISO UTC with exactly six fraction digits, ASCII digits only.
KEYSET_TIME_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$"
_KEYSET_TIME = re.compile(KEYSET_TIME_PATTERN)
# A literal, never a bound parameter, so the planner matches the partial
# index's predicate (status <> 'closed') in custom and generic plans alike.
_NOT_CLOSED = "status <> 'closed'"


def _names(image):
    """The components of an image path (split on both separators), casefolded, each cut at its first ':'."""
    return [component.partition(":")[0].casefold() for component in _SEPARATORS.split(image)]


def file_name(image):
    """The last component of an image path, casefolded, without an NTFS stream suffix."""
    return _names(image)[-1]


def user_writable(image):
    """Rule user_writable_launch: Users\\*\\AppData, Users\\*\\Downloads, Users\\Public, or any Temp component."""
    names = _names(image)
    if "temp" in names:
        return True
    for index, name in enumerate(names):
        if name == "users":
            following = names[index + 1:index + 3]
            if following[:1] == ["public"] or (len(following) == 2 and following[0] == "*"
                                               and following[1] in {"appdata", "downloads"}):
                return True
    return False


def dedup_key(key_text):
    """Lowercase hex SHA-256 of a rule's key text."""
    return hashlib.sha256(key_text.encode("utf-8")).hexdigest()


def _stored_bytes(value):
    """Byte length of PostgreSQL's jsonb text (", " and ": " separators), as event_contracts measures events."""
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(", ", ": "),
                          allow_nan=False).encode("utf-8"))


def _string_bytes(value):
    return _stored_bytes(value) - 2


def _tail(value, budget):
    """The end of a path behind an ellipsis, whose JSON string text takes at most `budget` bytes."""
    if _string_bytes(value) <= budget:
        return value
    kept, used = [], _string_bytes(ELLIPSIS)
    for character in reversed(value):
        size = _string_bytes(character)
        if used + size > budget:
            break
        kept.append(character)
        used += size
    return ELLIPSIS + "".join(reversed(kept))


def bounded_evidence(evidence):
    """Evidence whose stored text fits in 4 KiB.

    Only office_browser_spawned_tool can exceed it: its two image paths come
    from two events, each of which may fill most of its own 4 KiB. The image
    paths are then shortened from their start, fairly shared, behind a leading
    ellipsis; the file names stay. Dropping a prefix never unmasks a profile
    folder.
    """
    if _stored_bytes(evidence) <= MAX_EVIDENCE_BYTES:
        return evidence
    paths = sorted((key for key in ("image", "parent_image") if isinstance(evidence.get(key), str)),
                   key=lambda key: _string_bytes(evidence[key]))
    bounded = {**evidence, **{key: "" for key in paths}}
    budget = MAX_EVIDENCE_BYTES - _stored_bytes(bounded)
    for remaining, key in zip(range(len(paths), 0, -1), paths):
        bounded[key] = _tail(evidence[key], budget // remaining)
        budget -= _string_bytes(bounded[key])
    return bounded


@dataclass
class Match:
    """All matches of one (rule, key text) in one batch; they become one upsert.

    first_seq and last_seq are None only for agent_silent, which no event raises (ck_alert_event_seq).
    """
    rule: str
    key: str
    first_seq: int | None
    last_seq: int | None
    occurrences: int
    evidence: dict
    severity: str


# The exact parent of a v2 child: the device's stored v2 process_started event of one (pid, create_time),
# through ix_endpoint_events_process_identity (migration 0005). The payload keys, the kind and the `?` operand
# are literals, never bound parameters, so that the planner matches the partial index's expressions and
# predicate in custom and generic plans alike; the identities travel as two text arrays, so every batch runs the
# same statement text. LIMIT 1 per identity bounds the statement by the batch's distinct identities (at most
# 200 rows): the contract gives one process one identity, and of out-of-contract duplicates any one is taken.
_EXACT_PARENTS = text(
    "SELECT wanted.pid, wanted.create_time, parent.image "
    "FROM unnest(CAST(:pids AS text[]), CAST(:create_times AS text[])) AS wanted (pid, create_time) "
    "CROSS JOIN LATERAL (SELECT payload ->> 'image' AS image FROM endpoint_events "
    "WHERE tenant_id = :tenant_id AND device_id = :device_id AND kind = 'process_started' "
    "AND payload ? 'create_time' AND payload ->> 'pid' = wanted.pid "
    "AND payload ->> 'create_time' = wanted.create_time AND event_seq < :first_seq LIMIT 1) AS parent")


def _stored_exact_parents(session, device, identities, first_seq):
    """The image of the stored v2 process_started event of each (pid, create_time) identity that has one.

    One index-backed statement per batch, whatever the distance: no 2000-event
    window and no stop check, because the identity is exact. Only rows before
    the batch count (event_seq < first_seq), as in the window's stored range:
    the batch's own rows, already inserted in this transaction, were looked at
    in order. A v1 row has no create_time and is never an exact parent.
    """
    wanted = sorted(identities)
    rows = session.execute(_EXACT_PARENTS, {
        "pids": [str(pid) for pid, _ in wanted], "create_times": [created for _, created in wanted],
        "tenant_id": device.tenant_id, "device_id": device.id, "first_seq": first_seq}).all()
    return {(int(pid), created): image for pid, created, image in rows}


def _stored_process_events(session, device, pending, first_seq):
    """The latest stored process event of each parent pid that `pending` children look for.

    Every child of the batch has event_seq >= first_seq, so the union of the
    children's windows over stored events lies in [first_seq - 2000, first_seq):
    one bounded range of the primary key, filtered by pid.
    """
    low = max(1, min(child.event_seq for child, _ in pending) - PARENT_LOOKBACK)
    if low >= first_seq:
        return {}
    pid = cast(EndpointEvent.payload["pid"].as_string(), BigInteger)
    rows = session.execute(select(EndpointEvent.event_seq, EndpointEvent.kind, pid,
                                  EndpointEvent.payload["image"].as_string())
        .where(EndpointEvent.tenant_id == device.tenant_id, EndpointEvent.device_id == device.id,
               EndpointEvent.event_seq >= low, EndpointEvent.event_seq < first_seq,
               EndpointEvent.kind.in_(("process_started", "process_stopped")),
               pid.in_(sorted({child.parent_pid for child, _ in pending})))
        .order_by(EndpointEvent.event_seq)).all()
    return {row_pid: (seq, kind, image) for seq, kind, row_pid, image in rows}


def behavior_key(rule, image):
    """behavior_match's key text: the closed rule id, '>', the casefolded image (a rule id never holds '>')."""
    return f"{rule}>{image.casefold()}"


def batch_matches(session, device, events, previous_event_seq):
    """Every rule match of one accepted batch, grouped per (rule, key text), in order of first event_seq.

    `previous_event_seq` is the device cursor's last_event_seq before this
    batch, or None for the device's first batch. A batch is v1 or v2; v2's
    process_started and process_stopped carry the v1 fields too.
    """
    matches = {}

    def add(rule, key, seq, evidence, count=1, severity=None):
        match = matches.get((rule, key))
        if match is None:
            matches[(rule, key)] = Match(rule, key, seq, seq, count, bounded_evidence(evidence),
                                         SEVERITY[rule] if severity is None else severity)
            return
        match.occurrences += count
        match.first_seq = min(match.first_seq, seq)
        if seq > match.last_seq:
            match.last_seq, match.evidence = seq, bounded_evidence(evidence)

    def reported(rule, key, event):
        """A Stage 3 event rule: its evidence is the event's own EVIDENCE_FIELDS, as stored."""
        payload = event.model_dump(mode="json")
        add(rule, key, event.event_seq, {name: payload[name] for name in EVIDENCE_FIELDS[rule]},
            severity=BEHAVIOR_SEVERITY[event.rule] if rule == "behavior_match" else None)

    def spawned(child, child_name, parent_image):
        parent_name = file_name(parent_image)
        if parent_name in OFFICE_AND_BROWSERS:
            add("office_browser_spawned_tool", f"{parent_name}>{child_name}", child.event_seq,
                {"image": child.image, "pid": child.pid, "parent_image": parent_image, "parent_pid": child.parent_pid})

    def tool_launch(child, child_name, earlier):
        seq, kind, image = earlier
        # The latest event of the parent pid decides: a stop means that process ended.
        if kind != "process_started" or seq < child.event_seq - PARENT_LOOKBACK:
            return
        spawned(child, child_name, image)

    latest = {}   # pid -> (event_seq, kind, image) of its latest process event so far in this batch
    pending = []  # tool launches whose parent pid has no earlier event in this batch
    started = {}  # (pid, create_time) -> image of the latest v2 process_started of that process so far in this batch
    exact = []    # v2 tool launches naming their parent's create time, whose parent is not earlier in this batch
    for event in events:
        kind = event.kind
        if kind == "process_started":
            if user_writable(event.image):
                add("user_writable_launch", event.image.casefold(), event.event_seq,
                    {"image": event.image, "pid": event.pid})
            child_name = file_name(event.image)
            if child_name in TOOLS:
                parent_created = getattr(event, "parent_create_time", None)
                if parent_created is not None:
                    # The parent is exactly the process (parent_pid, parent_create_time), or none: no window.
                    identity = (event.parent_pid, parent_created)
                    if identity in started:
                        spawned(event, child_name, started[identity])
                    else:
                        exact.append((event, child_name, identity))
                elif event.parent_pid in latest:
                    tool_launch(event, child_name, latest[event.parent_pid])
                else:
                    pending.append((event, child_name))
            latest[event.pid] = (event.event_seq, kind, event.image)
            created = getattr(event, "create_time", None)
            if created is not None:
                started[(event.pid, created)] = event.image
        elif kind == "process_stopped":
            latest[event.pid] = (event.event_seq, kind, None)
        elif kind == "sensor_state":
            if event.state in {"lost", "failed"}:
                add("sensor_unstable", event.state, event.event_seq,
                    {"state": event.state, "error_code": event.error_code})
        elif kind == "scan_detected":
            reported("scan_detection", event.sha256, event)
        elif kind == "behavior_match":
            reported("behavior_match", behavior_key(event.rule, event.image), event)
        elif kind == "persistence_change":
            if event.change in PERSISTENCE_ADDED_CHANGES:
                reported("persistence_added", event.entry_id, event)
        elif kind == "agent_state":
            if event.state in CAPABILITY_DOWN.get(event.subject, ()):
                reported("capability_down", event.subject, event)
        elif kind == "tamper_signal":
            reported("tamper_signal", event.signal, event)
        # coverage_gap raises nothing: the timeline shows the gap the agent reported.
    if pending:
        stored = _stored_process_events(session, device, pending, events[0].event_seq)
        for child, child_name in pending:
            if child.parent_pid in stored:
                tool_launch(child, child_name, stored[child.parent_pid])
    if exact:
        parents = _stored_exact_parents(session, device, {identity for _, _, identity in exact}, events[0].event_seq)
        for child, child_name, identity in exact:
            if identity in parents:
                spawned(child, child_name, parents[identity])
    # A device's first batch may start above 1 and its numbering may carry
    # over from an earlier enrollment: only a device with a cursor can lose events.
    if previous_event_seq is not None:
        missing, before = 0, previous_event_seq
        for event in events:
            if event.event_seq > before + 1:
                missing += event.event_seq - before - 1
                add("event_loss", "event_loss", event.event_seq, {"missing_events": missing})
            before = event.event_seq
    return sorted(matches.values(), key=lambda match: (match.first_seq, match.rule, match.key))


def _not_closed(table):
    return table.c.status != literal_column("'closed'")


def _open_alerts(tenant_id, device_id, cap):
    """The device's alerts that are not closed, counted up to `cap` (a bounded index scan)."""
    table = Alert.__table__.alias("device_open")
    return select(func.count()).select_from(select(table.c.id).where(
        table.c.tenant_id == tenant_id, table.c.device_id == device_id, _not_closed(table)).limit(cap).subquery())


def _upsert(device, match, proposed_id, received_at, *, cap=None):
    """One bounded INSERT ... ON CONFLICT for one key; RETURNING the id of the alert it opened or updated.

    Without `cap` it may open an alert. With `cap` (the device had reached it),
    the proposed row exists only if an alert of this key is not closed, so the
    statement updates it, or if the device's alerts that are not closed are,
    in this statement's snapshot, fewer than the cap: an operator's close may
    have freed a slot. Otherwise nothing is inserted or returned: suppressed.

    The conflict arbiter is the partial unique index. If an operator closes
    the conflicting alert while this statement waits for its row lock,
    PostgreSQL retries the insertion, which then opens a new alert.

    agent_silent's null sequence columns pass through unchanged: greatest()
    of two nulls is null, which ck_alert_event_seq requires for that rule.
    """
    table = Alert.__table__
    values = {"id": proposed_id, "tenant_id": device.tenant_id, "device_id": device.id, "rule": match.rule,
              "severity": match.severity, "dedup_key": dedup_key(match.key), "status": "open",
              "occurrences": match.occurrences, "first_event_seq": match.first_seq, "last_event_seq": match.last_seq,
              "first_seen_at": received_at, "last_seen_at": received_at, "evidence": match.evidence,
              "created_at": received_at, "updated_at": received_at}
    proposed = select(*(literal(value, table.c[name].type).label(name) for name, value in values.items()))
    if cap is not None:
        same_key = table.alias("same_key")
        proposed = proposed.where(or_(
            select(same_key.c.id).where(same_key.c.tenant_id == device.tenant_id, same_key.c.device_id == device.id,
                                        same_key.c.rule == match.rule, same_key.c.dedup_key == values["dedup_key"],
                                        _not_closed(same_key)).exists(),
            _open_alerts(device.tenant_id, device.id, cap).scalar_subquery() < cap))
    statement = pg_insert(Alert).from_select(list(values), proposed)
    excluded = statement.excluded
    evidence = excluded.evidence
    if match.rule == "event_loss":
        # The cumulative count of missing events; every other rule keeps the latest evidence.
        evidence = func.jsonb_build_object(literal_column("'missing_events'"),
            cast(Alert.evidence["missing_events"].as_string(), BigInteger)
            + cast(excluded.evidence["missing_events"].as_string(), BigInteger))
    return statement.on_conflict_do_update(
        index_elements=[Alert.tenant_id, Alert.device_id, Alert.rule, Alert.dedup_key],
        index_where=text(_NOT_CLOSED),
        set_={"occurrences": Alert.occurrences + excluded.occurrences,
              "last_event_seq": func.greatest(Alert.last_event_seq, excluded.last_event_seq),
              "last_seen_at": excluded.last_seen_at, "evidence": evidence, "updated_at": excluded.updated_at},
    ).returning(Alert.id)


def open_matches(session, device, matches, *, received_at, limits=DEFAULT_LIMITS):
    """Open or update one alert per match, in order; return each match's outcome: opened, updated or suppressed.

    The caller holds the device row lock (event ingestion, or the sweep for
    agent_silent), so no other transaction opens an alert of this device
    meanwhile; operators can only close alerts, which lowers the count. The
    count taken here is therefore never too low, and at the cap each statement
    recounts in its own snapshot.
    """
    cap = limits.max_open_alerts_per_device
    open_alerts = session.scalar(_open_alerts(device.tenant_id, device.id, cap))
    outcomes = []
    for match in matches:
        proposed_id = uuid4()
        alert_id = session.scalar(_upsert(device, match, proposed_id, received_at,
                                          cap=cap if open_alerts >= cap else None))
        if alert_id is None:
            outcomes.append("suppressed")
        elif alert_id == proposed_id:
            open_alerts += 1
            outcomes.append("opened")
        else:
            outcomes.append("updated")
    return outcomes


def raise_alerts(session, device, events, *, received_at, previous_event_seq, limits=DEFAULT_LIMITS):
    """Open or update the alerts of one newly accepted batch; return how many openings the cap suppressed."""
    matches = batch_matches(session, device, events, previous_event_seq)
    if not matches:
        return 0
    return open_matches(session, device, matches, received_at=received_at, limits=limits).count("suppressed")


def keyset_time(value):
    """A paging cursor time: ISO UTC with exactly six fraction digits."""
    return canonical_utc(value)


def parse_keyset(before_seen_at, before_id):
    """The cursor (last_seen_at, id) of a previous page's next_before, or None without one.

    Both values or neither; before_seen_at is ISO UTC with exactly six
    fraction digits and names a real instant. Anything else is invalid
    pagination.
    """
    if before_seen_at is None and before_id is None:
        return None
    if (not isinstance(before_seen_at, str) or _KEYSET_TIME.fullmatch(before_seen_at) is None
            or not isinstance(before_id, UUID)):
        raise ServiceError("Invalid pagination")
    try:
        return datetime.fromisoformat(before_seen_at[:-1] + "+00:00"), before_id
    except ValueError:
        raise ServiceError("Invalid pagination") from None


def alert_view(row):
    return {"id": str(row.id), "device_id": str(row.device_id), "rule": row.rule, "severity": row.severity,
            "status": row.status, "occurrences": row.occurrences, "first_event_seq": row.first_event_seq,
            "last_event_seq": row.last_event_seq, "first_seen_at": iso(row.first_seen_at),
            "last_seen_at": iso(row.last_seen_at), "evidence": row.evidence,
            "acknowledged_at": iso(row.acknowledged_at), "closed_at": iso(row.closed_at),
            "source": "self_reported", "producer_verification": "not_verified"}


def list_alerts(session, operator, tenant_id, *, status=None, device_id=None, before_seen_at=None, before_id=None,
                limit=50, limits=DEFAULT_LIMITS):
    """Newest activity first, by (last_seen_at DESC, id DESC), with a keyset cursor; any tenant member reads.

    `before_seen_at` and `before_id` come together, from the previous page's
    next_before. An alert that gains a match between two page reads moves to
    the front, so a later page does not show it again.
    """
    require_membership(session, operator, tenant_id)
    if type(limit) is not int or not 1 <= limit <= limits.max_page_size:
        raise ServiceError("Invalid pagination")
    keyset = parse_keyset(before_seen_at, before_id)
    if (status is not None and status not in STATUSES) or (device_id is not None and not isinstance(device_id, UUID)):
        raise ServiceError("Invalid alert filter")
    if device_id is not None and session.scalar(select(Device.id).where(Device.tenant_id == tenant_id,
                                                                         Device.id == device_id)) is None:
        raise NotFound("Resource not found")
    query = select(Alert).where(Alert.tenant_id == tenant_id)
    if device_id is not None:
        query = query.where(Alert.device_id == device_id)
    if status is not None:
        query = query.where(Alert.status == status)
    if keyset is not None:
        query = query.where(tuple_(Alert.last_seen_at, Alert.id) < tuple_(*keyset))
    rows = session.scalars(query.order_by(Alert.last_seen_at.desc(), Alert.id.desc()).limit(limit + 1)).all()
    last = rows[limit - 1] if len(rows) > limit else None
    return {"items": [alert_view(row) for row in rows[:limit]],
            "next_before": None if last is None else {"seen_at": keyset_time(last.last_seen_at), "id": str(last.id)}}


def _locked_alert(session, operator, tenant_id, alert_id):
    """The tenant_admin's principal and the alert row, locked for the transition, as revoke_device does it.

    The tenant row lock comes first (write_event needs it); an unknown alert,
    or one of another tenant, is 404 after the role check.
    """
    locked_tenant(session, tenant_id)
    principal, _ = require_membership(session, operator, tenant_id, admin=True, lock=True)
    alert = session.scalar(select(Alert).where(Alert.tenant_id == tenant_id, Alert.id == alert_id)
                           .with_for_update().execution_options(populate_existing=True))
    if alert is None:
        raise NotFound("Resource not found")
    return principal, alert


def acknowledge_alert(session, operator, tenant_id, alert_id, *, limits=DEFAULT_LIMITS, now=None):
    """open -> acknowledged (tenant_admin). A repeat changes nothing and writes no audit row; closed is 409."""
    now = utc_now(now)
    principal, alert = _locked_alert(session, operator, tenant_id, alert_id)
    if alert.status == "closed":
        raise Conflict("Alert is closed")
    if alert.status == "open":
        alert.status, alert.acknowledged_at, alert.acknowledged_by, alert.updated_at = (
            "acknowledged", now, principal.id, now)
        session.flush()
        # The audit row names the alert (object_type alert, object_id its id),
        # never its evidence. audit_events has no details column: the alert's
        # device and rule stay on the alert row, which is never deleted.
        write_event(session, tenant_id=tenant_id, actor_type="operator", actor_id=principal.id,
            action="alert_acknowledged", object_type="alert", object_id=alert.id, now=now, limits=limits)
    return alert_view(alert)


def close_alert(session, operator, tenant_id, alert_id, *, limits=DEFAULT_LIMITS, now=None):
    """open or acknowledged -> closed (tenant_admin). A repeat changes nothing and writes no audit row.

    The next match of the same key opens a new alert.
    """
    now = utc_now(now)
    principal, alert = _locked_alert(session, operator, tenant_id, alert_id)
    if alert.status != "closed":
        alert.status, alert.closed_at, alert.closed_by, alert.updated_at = "closed", now, principal.id, now
        session.flush()
        write_event(session, tenant_id=tenant_id, actor_type="operator", actor_id=principal.id,
            action="alert_closed", object_type="alert", object_id=alert.id, now=now, limits=limits)
    return alert_view(alert)
