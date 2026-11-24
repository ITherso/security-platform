"""Built-in server rules on self-reported endpoint events, and the operator alert lifecycle.

A rule match is not a diagnosis. Alerts are derived from what a device says
about itself, so every alert stays self_reported/not_verified like its events.

The rules run inside event ingestion, in the same transaction, only for the
events of a newly accepted batch: an exact retry, a conflict, a 413 or a 422
evaluates nothing. They read only contract fields: the masked image paths as
stored, pids, kinds, states, codes and event_seq values.

Deduplication: while an alert of a (tenant, device, rule, key) is not closed,
a new match updates it. Every distinct key of a batch is one bounded INSERT ...
ON CONFLICT on the partial unique index uq_alert_not_closed_key, so an
operator's close racing an ingestion ends either in the closed alert plus a new
open one, or in a closed alert that includes the match; never in two alerts
that are not closed. The device row lock that ingestion holds serialises every
opening of one device's alerts; operators only acknowledge or close.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, cast, func, literal, literal_column, or_, select, text, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from security_platform.models import Alert, Device, EndpointEvent
from security_platform.services.audit import write_event
from security_platform.services.common import (DEFAULT_LIMITS, Conflict, NotFound, ServiceError, iso, locked_tenant,
    require_membership, utc_now)


SEVERITY = {"user_writable_launch": "low", "office_browser_spawned_tool": "medium", "sensor_unstable": "medium",
            "event_loss": "medium"}
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
# the rule stays silent.
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
    """All matches of one (rule, key text) in one batch; they become one upsert."""
    rule: str
    key: str
    first_seq: int
    last_seq: int
    occurrences: int
    evidence: dict


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


def batch_matches(session, device, events, previous_event_seq):
    """Every rule match of one accepted batch, grouped per (rule, key text), in order of first event_seq.

    `previous_event_seq` is the device cursor's last_event_seq before this
    batch, or None for the device's first batch.
    """
    matches = {}

    def add(rule, key, seq, evidence, count=1):
        match = matches.get((rule, key))
        if match is None:
            matches[(rule, key)] = Match(rule, key, seq, seq, count, bounded_evidence(evidence))
            return
        match.occurrences += count
        match.first_seq = min(match.first_seq, seq)
        if seq > match.last_seq:
            match.last_seq, match.evidence = seq, bounded_evidence(evidence)

    def tool_launch(child, child_name, earlier):
        seq, kind, image = earlier
        # The latest event of the parent pid decides: a stop means that process ended.
        if kind != "process_started" or seq < child.event_seq - PARENT_LOOKBACK:
            return
        parent_name = file_name(image)
        if parent_name in OFFICE_AND_BROWSERS:
            add("office_browser_spawned_tool", f"{parent_name}>{child_name}", child.event_seq,
                {"image": child.image, "pid": child.pid, "parent_image": image, "parent_pid": child.parent_pid})

    latest = {}   # pid -> (event_seq, kind, image) of its latest process event so far in this batch
    pending = []  # tool launches whose parent pid has no earlier event in this batch
    for event in events:
        if event.kind == "process_started":
            if user_writable(event.image):
                add("user_writable_launch", event.image.casefold(), event.event_seq,
                    {"image": event.image, "pid": event.pid})
            child_name = file_name(event.image)
            if child_name in TOOLS:
                if event.parent_pid in latest:
                    tool_launch(event, child_name, latest[event.parent_pid])
                else:
                    pending.append((event, child_name))
            latest[event.pid] = (event.event_seq, event.kind, event.image)
        elif event.kind == "process_stopped":
            latest[event.pid] = (event.event_seq, event.kind, None)
        elif event.state in {"lost", "failed"}:
            add("sensor_unstable", event.state, event.event_seq, {"state": event.state, "error_code": event.error_code})
    if pending:
        stored = _stored_process_events(session, device, pending, events[0].event_seq)
        for child, child_name in pending:
            if child.parent_pid in stored:
                tool_launch(child, child_name, stored[child.parent_pid])
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
    """
    table = Alert.__table__
    values = {"id": proposed_id, "tenant_id": device.tenant_id, "device_id": device.id, "rule": match.rule,
              "severity": SEVERITY[match.rule], "dedup_key": dedup_key(match.key), "status": "open",
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


def raise_alerts(session, device, events, *, received_at, previous_event_seq, limits=DEFAULT_LIMITS):
    """Open or update the alerts of one newly accepted batch; return how many openings the cap suppressed.

    The caller holds the device row lock, so no other transaction opens an
    alert of this device meanwhile; operators can only close alerts, which
    lowers the count. The count taken here is therefore never too low, and at
    the cap each statement recounts in its own snapshot.
    """
    matches = batch_matches(session, device, events, previous_event_seq)
    if not matches:
        return 0
    cap = limits.max_open_alerts_per_device
    open_alerts = session.scalar(_open_alerts(device.tenant_id, device.id, cap))
    suppressed = 0
    for match in matches:
        proposed_id = uuid4()
        alert_id = session.scalar(_upsert(device, match, proposed_id, received_at,
                                          cap=cap if open_alerts >= cap else None))
        if alert_id is None:
            suppressed += 1
        elif alert_id == proposed_id:
            open_alerts += 1
    return suppressed


def keyset_time(value):
    """A paging cursor time: ISO UTC with exactly six fraction digits."""
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


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
