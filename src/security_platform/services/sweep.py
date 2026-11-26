"""`security-platform sweep`: one agent_silent alert per silence episode of a device's Altay EDR agent.

agent_silent is the one rule that no event raises: this sweep opens it from
the server clock. Nothing schedules it; an operator runs it, for example from
Task Scheduler. Without it, silence shows only as a stale device.

Candidates are the devices that are not revoked, have a snapshot heartbeat
(devices.last_received_at) and whose latest accepted snapshot carried the
edr_agent product. That last check relies on snapshot ingestion
(services/snapshots.py): every accepted snapshot, of any version, is a whole
state. Under the device row lock and in one transaction it deletes every
product_states row of the device, inserts its own products with
snapshot_sequence set to its sequence, and sets devices.last_sequence to the
same value. An edr_agent row whose snapshot_sequence equals
devices.last_sequence therefore exists exactly when the latest snapshot
carried edr_agent. HBF's one-shot sender never sends edr_agent, so it is never
a candidate. Events are no heartbeat and never move last_received_at, and an
exact snapshot retry does not move it either.

A candidate is silent when now - last_received_at is more than its threshold,
on the server clock only. The threshold is max(SP_SILENCE_ALERT_SECONDS,
3 x heartbeat_interval_seconds) when the stored edr_agent payload is V3 with a
valid interval, and the setting alone otherwise (a V2 payload has no
interval). Silence is not a diagnosis: network loss, sleep, shutdown, an
isolation that lost contact and an administrator stop all look the same. The
alert never implies that anything was protected before.

One alert per silence episode. The episode is named by last_received_at, and
its canonical UTC text is the alert's key text. While any agent_silent alert of
that key exists for the device, in any status (closed included), the sweep
changes nothing: no new alert, no occurrence and no last_seen_at change. A new
contact moves last_received_at, so the next silence is a new episode.

Work goes per tenant, in chunks of at most SWEEP_CHUNK_DEVICES candidates by
device id, each in its own short transaction. The device rows of a chunk's
silent candidates are locked FOR UPDATE SKIP LOCKED, the lock that ingestion
takes. A row another transaction holds belongs to a device that is reporting
(or being revoked or read) right now: it is skipped and counted in
devices_busy. Under the lock each device is checked again. Then the alert
opens through the ingestion upsert (services/alerts.open_matches), the
per-device open-alert cap included, with first_seen_at = last_seen_at = the
sweep time and both event sequences null. A failing chunk rolls back only
itself: the tenant is skipped for this run and counted in failed_tenants, as
`events prune` does, and the next run retries it.
"""
from collections import Counter
from datetime import timedelta

from sqlalchemy import and_, literal_column, select
from sqlalchemy.exc import SQLAlchemyError

from security_platform.contracts import MAX_HEARTBEAT_INTERVAL_SECONDS, MIN_HEARTBEAT_INTERVAL_SECONDS
from security_platform.models import Alert, Device, ProductState, Tenant
from security_platform.services.alerts import SEVERITY, Match, bounded_evidence, dedup_key, open_matches
from security_platform.services.common import DEFAULT_LIMITS, canonical_utc, utc_now
from security_platform.settings import SILENCE_ALERT_SECONDS_RANGE


SWEEP_CHUNK_DEVICES = 200
RULE = "agent_silent"
# The evidence: the server's own record of the last contact (the key text) and the threshold this run applied.
EVIDENCE_FIELDS = ("last_received_at", "threshold_seconds")
# A reported heartbeat interval counts three times: one or two late heartbeats are not yet silence.
HEARTBEAT_FACTOR = 3
RESULT_KEYS = ("tenants", "failed_tenants", "devices_checked", "alerts_opened", "already_alerted", "suppressed",
               "devices_busy")
# A literal, never a bound parameter, so that the planner matches ix_alert_silence_episode's predicate.
_SILENT_RULE = literal_column("'agent_silent'")


def heartbeat_interval(payload):
    """The heartbeat_interval_seconds of a stored V3 edr_agent payload, or None.

    V3 is told from V2 by its key set, as the console does it: V3 has
    rule_set_state and no rule_file_present. A V2 payload, a null interval or
    anything but an integer in the agent's own 30..3600 range gives None.
    """
    if not isinstance(payload, dict) or "rule_set_state" not in payload or "rule_file_present" in payload:
        return None
    value = payload.get("heartbeat_interval_seconds")
    if type(value) is not int or not MIN_HEARTBEAT_INTERVAL_SECONDS <= value <= MAX_HEARTBEAT_INTERVAL_SECONDS:
        return None
    return value


def silence_threshold(silence_alert_seconds, payload):
    """Seconds without a snapshot after which a candidate is silent: max(setting, 3 x a valid V3 interval)."""
    interval = heartbeat_interval(payload)
    return silence_alert_seconds if interval is None else max(silence_alert_seconds, HEARTBEAT_FACTOR * interval)


def is_silent(now, last_received_at, threshold):
    """Strictly more than `threshold` seconds of server time since the last accepted snapshot."""
    return now - last_received_at > timedelta(seconds=threshold)


def _tenants(session):
    return session.scalars(select(Tenant.id).order_by(Tenant.id)).all()


def _latest_agent_state(tenant_id, device_id, last_sequence):
    """The edr_agent product_states row of the device's latest accepted snapshot (columns or values)."""
    return and_(ProductState.tenant_id == tenant_id, ProductState.device_id == device_id,
                ProductState.product_id == "edr_agent", ProductState.snapshot_sequence == last_sequence)


def _candidates(session, tenant_id, after, limit):
    """The tenant's next candidates by device id: (id, last_received_at, the stored edr_agent payload)."""
    query = (select(Device.id, Device.last_received_at, ProductState.payload)
             .join(ProductState, _latest_agent_state(Device.tenant_id, Device.id, Device.last_sequence))
             .where(Device.tenant_id == tenant_id, Device.revoked_at.is_(None), Device.last_received_at.is_not(None)))
    if after is not None:
        query = query.where(Device.id > after)
    return session.execute(query.order_by(Device.id).limit(limit)).all()


def _open_episode(session, device, now, silence_alert_seconds, limits):
    """Check a locked candidate again and open its silence episode's alert; return the count it adds to, if any."""
    if device.revoked_at is not None or device.last_received_at is None:
        return None
    payload = session.scalar(select(ProductState.payload).where(
        _latest_agent_state(device.tenant_id, device.id, device.last_sequence)))
    if payload is None:
        return None
    threshold = silence_threshold(silence_alert_seconds, payload)
    if not is_silent(now, device.last_received_at, threshold):
        return None
    key = canonical_utc(device.last_received_at)
    # Any status, closed included: one alert per episode, whatever the operator did with it.
    episode = session.scalar(select(Alert.id).where(Alert.tenant_id == device.tenant_id, Alert.device_id == device.id,
                                                    Alert.rule == _SILENT_RULE, Alert.dedup_key == dedup_key(key))
                             .limit(1))
    if episode is not None:
        return "already_alerted"
    evidence = bounded_evidence({"last_received_at": key, "threshold_seconds": threshold})
    [outcome] = open_matches(session, device, [Match(RULE, key, None, None, 1, evidence, SEVERITY[RULE])],
                             received_at=now, limits=limits)
    # Only this sweep opens agent_silent, under this lock and after the check above, so the upsert never finds an
    # alert of the key to update; "updated" would mean one existed.
    return {"opened": "alerts_opened", "suppressed": "suppressed"}.get(outcome, "already_alerted")


def _sweep_chunk(session, tenant_id, after, now, silence_alert_seconds, chunk_size, limits):
    """One chunk of one tenant's candidates; return (candidates read, the last device id read, its counts)."""
    rows = _candidates(session, tenant_id, after, chunk_size)
    counts = Counter(devices_checked=len(rows))
    silent = [device_id for device_id, last_received_at, payload in rows
              if is_silent(now, last_received_at, silence_threshold(silence_alert_seconds, payload))]
    if silent:
        locked = session.scalars(select(Device).where(Device.tenant_id == tenant_id, Device.id.in_(silent))
                                 .order_by(Device.id).with_for_update(skip_locked=True)
                                 .execution_options(populate_existing=True)).all()
        counts["devices_busy"] += len(silent) - len(locked)
        for device in locked:
            outcome = _open_episode(session, device, now, silence_alert_seconds, limits)
            if outcome is not None:
                counts[outcome] += 1
    return len(rows), rows[-1][0] if rows else after, counts


def sweep_silent_agents(database, *, silence_alert_seconds, now=None, chunk_size=SWEEP_CHUNK_DEVICES,
                        limits=DEFAULT_LIMITS):
    """Open one agent_silent alert per silence episode in every tenant; return the counts of this run.

    `silence_alert_seconds` is the validated SP_SILENCE_ALERT_SECONDS and
    `limits.max_open_alerts_per_device` the open-alert cap. Counts include
    only committed chunks. tenants and failed_tenants are as in `events
    prune`; devices_checked counts candidates, alerts_opened the new alerts,
    already_alerted the silent devices whose episode already has an alert,
    suppressed the openings the cap kept back (the next run tries again) and
    devices_busy the silent devices whose row another transaction held.
    """
    minimum, maximum = SILENCE_ALERT_SECONDS_RANGE
    if type(silence_alert_seconds) is not int or not minimum <= silence_alert_seconds <= maximum:
        raise ValueError("Invalid bounded platform setting")
    if type(chunk_size) is not int or not 1 <= chunk_size <= SWEEP_CHUNK_DEVICES:
        raise ValueError("Invalid sweep chunk size")
    now = utc_now(now)
    with database.session() as session:
        tenants = _tenants(session)
    totals, failed = Counter(), 0
    for tenant_id in tenants:
        after = None
        try:
            while True:
                with database.session() as session:
                    read, after, counts = _sweep_chunk(session, tenant_id, after, now, silence_alert_seconds,
                                                       chunk_size, limits)
                # Added only once the chunk has committed.
                totals.update(counts)
                if read < chunk_size:
                    break
        except SQLAlchemyError:
            failed += 1
    return {"tenants": len(tenants), "failed_tenants": failed, **{key: totals[key] for key in RESULT_KEYS[2:]}}
