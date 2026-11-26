"""Stage 3 detection contracts: event v2 kinds, the ten alert rules, agent_silent's null sequences, two indexes.

- endpoint_events.ck_endpoint_event_kind widens to the nine altay-edr-event kinds (v1 and v2);
- alerts.ck_alert_rule widens to the ten rules;
- alerts.first_event_seq and last_event_seq drop NOT NULL, and ck_alert_event_seq allows null only for
  agent_silent (both null) and requires both for every other rule; nullness is checked explicitly, because a
  CHECK whose result is null passes;
- ix_endpoint_events_process_identity: the exact parent lookup of a v2 child, by the parent's
  (pid, create_time) text in the payload, over v2 process_started rows only;
- ix_alert_silence_episode: agent_silent alerts of a device by episode key, whatever their status.

The value lists are hardcoded: a migration is frozen and never imports application constants. A parity test
compares the head schema's lists with event_contracts.EVENT_KINDS and the alert rules.

The downgrade first deletes the rows the narrower CHECKs would refuse (events of the six v2-only kinds, alerts
of the six new rules, agent_silent included) and lowers each touched device's stored_events by the exact
number of its deleted events, as retention prune does; then it restores NOT NULL, the CHECKs exactly as 0002
and 0003 wrote them, and drops both indexes. v2-shaped events of the three v1 kinds stay: the v1 CHECK accepts
them, and the v1 timeline shows only the v1 fields.

Timeouts. migrations/env.py runs the whole upgrade in one transaction and gives every statement a 5 s
statement_timeout and a 3 s lock_timeout. This is the first migration whose statements read the event table
whole: the kind CHECK's validation, the process-identity index build and the downgrade's deletion take time in
proportion to the stored events, and alerts is read whole as well. On a populated database (a few GB of events)
a 5 s bound would cancel the statement and roll the whole upgrade back on every retry. So each direction lifts
statement_timeout for its own statements only: SET LOCAL ends with the transaction, and SET LOCAL ... TO DEFAULT
gives any later migration of the same run env.py's value again. lock_timeout stays as env.py sets it, so a lock
that a running server holds still fails the migration fast instead of queueing it behind live traffic. The
transaction holds ACCESS EXCLUSIVE on endpoint_events and alerts from its first ALTER until COMMIT: ingestion,
the timeline and the alert views wait (and fail at their own lock_timeout) for that long.
"""
from alembic import op

revision = "0005_stage3_detection"
down_revision = "0004_edr_agent_product"
branch_labels = None
depends_on = None

LIFT_STATEMENT_TIMEOUT = "SET LOCAL statement_timeout = 0"
RESTORE_STATEMENT_TIMEOUT = "SET LOCAL statement_timeout TO DEFAULT"

DDL_STATEMENTS = (
    """
ALTER TABLE endpoint_events DROP CONSTRAINT ck_endpoint_event_kind
    """,
    """
ALTER TABLE endpoint_events ADD CONSTRAINT ck_endpoint_event_kind CHECK (kind IN ('process_started','process_stopped','sensor_state','scan_detected','behavior_match','persistence_change','agent_state','tamper_signal','coverage_gap'))
    """,
    """
ALTER TABLE alerts DROP CONSTRAINT ck_alert_rule
    """,
    """
ALTER TABLE alerts ADD CONSTRAINT ck_alert_rule CHECK (rule IN ('user_writable_launch','office_browser_spawned_tool','sensor_unstable','event_loss','scan_detection','behavior_match','persistence_added','capability_down','tamper_signal','agent_silent'))
    """,
    """
ALTER TABLE alerts DROP CONSTRAINT ck_alert_event_seq
    """,
    """
ALTER TABLE alerts ALTER COLUMN first_event_seq DROP NOT NULL
    """,
    """
ALTER TABLE alerts ALTER COLUMN last_event_seq DROP NOT NULL
    """,
    """
ALTER TABLE alerts ADD CONSTRAINT ck_alert_event_seq CHECK ((rule = 'agent_silent' AND first_event_seq IS NULL AND last_event_seq IS NULL) OR (rule <> 'agent_silent' AND first_event_seq IS NOT NULL AND last_event_seq IS NOT NULL AND first_event_seq >= 1 AND last_event_seq >= first_event_seq))
    """,
    """
CREATE INDEX ix_endpoint_events_process_identity ON endpoint_events (tenant_id, device_id, (payload ->> 'pid'), (payload ->> 'create_time')) WHERE kind = 'process_started' AND payload ? 'create_time'
    """,
    """
CREATE INDEX ix_alert_silence_episode ON alerts (tenant_id, device_id, dedup_key) WHERE rule = 'agent_silent'
    """,
)
DOWNGRADE_STATEMENTS = (
    """
WITH removed AS (
	DELETE FROM endpoint_events WHERE kind NOT IN ('process_started','process_stopped','sensor_state')
	RETURNING tenant_id, device_id
), per_device AS (
	SELECT tenant_id, device_id, count(*) AS deleted FROM removed GROUP BY tenant_id, device_id
)
UPDATE device_event_cursors AS cursor_row SET stored_events = GREATEST(cursor_row.stored_events - per_device.deleted, 0)
FROM per_device WHERE cursor_row.tenant_id = per_device.tenant_id AND cursor_row.device_id = per_device.device_id
    """,
    """
DELETE FROM alerts WHERE rule NOT IN ('user_writable_launch','office_browser_spawned_tool','sensor_unstable','event_loss')
    """,
    """
DROP INDEX ix_alert_silence_episode
    """,
    """
DROP INDEX ix_endpoint_events_process_identity
    """,
    """
ALTER TABLE alerts DROP CONSTRAINT ck_alert_event_seq
    """,
    """
ALTER TABLE alerts ALTER COLUMN first_event_seq SET NOT NULL
    """,
    """
ALTER TABLE alerts ALTER COLUMN last_event_seq SET NOT NULL
    """,
    """
ALTER TABLE alerts ADD CONSTRAINT ck_alert_event_seq CHECK (first_event_seq >= 1 AND last_event_seq >= first_event_seq)
    """,
    """
ALTER TABLE alerts DROP CONSTRAINT ck_alert_rule
    """,
    """
ALTER TABLE alerts ADD CONSTRAINT ck_alert_rule CHECK (rule IN ('user_writable_launch','office_browser_spawned_tool','sensor_unstable','event_loss'))
    """,
    """
ALTER TABLE endpoint_events DROP CONSTRAINT ck_endpoint_event_kind
    """,
    """
ALTER TABLE endpoint_events ADD CONSTRAINT ck_endpoint_event_kind CHECK (kind IN ('process_started','process_stopped','sensor_state'))
    """,
)


def _run(statements):
    op.execute(LIFT_STATEMENT_TIMEOUT)
    for statement in statements:
        op.execute(statement)
    op.execute(RESTORE_STATEMENT_TIMEOUT)


def upgrade():
    _run(DDL_STATEMENTS)


def downgrade():
    _run(DOWNGRADE_STATEMENTS)
