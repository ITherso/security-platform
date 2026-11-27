"""Alert retention: tenants.alert_retention_days, audit_events.details and the closed-alert index.

- tenants.alert_retention_days: INTEGER NOT NULL DEFAULT 60, ck_tenant_alert_retention BETWEEN 30 AND 3650. Every
  existing tenant gets 60, the owner's choice of 2026-11-26;
- audit_events.details: nullable JSONB, ck_audit_details (null, or an object of at most 1024 bytes). Only the
  `alerts prune` record writes it, with that run's counts for the tenant; every earlier row stays null. The
  audit API does not return it;
- ix_alert_tenant_closed: alerts (tenant_id, closed_at) WHERE status = 'closed', the range that `alerts prune`
  reads, locks and deletes.

The runtime role's DELETE on alerts is a grant (scripts/managed_postgres.py), not part of this migration: run
`grant` after it, as after every migration.

The downgrade deletes the audit rows of the two actions this revision's code writes (alerts_pruned and
tenant_alert_retention_set): the code of 0005 does not know them, and the operator console rejects an audit
page that holds an unknown action. Then it drops the index and both columns, with their CHECKs. Deleted alerts
do not come back; only a backup restores them.

Locks and timeouts. migrations/env.py runs the whole upgrade in one transaction with a 5 s statement_timeout and
a 3 s lock_timeout. The index build reads alerts whole and takes time in proportion to it, and the CHECK of
each new column reads its table whole, so each direction lifts statement_timeout for its own statements only,
as 0005 does: SET LOCAL ends with the transaction, and SET LOCAL ... TO DEFAULT gives any later migration of
the same run env.py's value again. lock_timeout stays at 3 s. Each direction first takes all three table locks,
one LOCK TABLE each, in a fixed order: tenants, alerts, audit_events. That is the order in which an operator's
acknowledge or close takes them (tenant row, alert row, audit insert); ingestion and the sweep reach alerts
without tenants and never touch audit_events. No work runs before the last lock is held, so a lock that is
not free within 3 s fails the migration before it has read a table, and the earlier locks are held for the
wait only. The upgrade holds ACCESS EXCLUSIVE on tenants and audit_events and SHARE on alerts (alert reads go
on, alert writes wait) until COMMIT; the downgrade holds ACCESS EXCLUSIVE on all three.
"""
from alembic import op

revision = "0006_alert_retention"
down_revision = "0005_stage3_detection"
branch_labels = None
depends_on = None

LIFT_STATEMENT_TIMEOUT = "SET LOCAL statement_timeout = 0"
RESTORE_STATEMENT_TIMEOUT = "SET LOCAL statement_timeout TO DEFAULT"

DDL_STATEMENTS = (
    """
LOCK TABLE tenants IN ACCESS EXCLUSIVE MODE
    """,
    """
LOCK TABLE alerts IN SHARE MODE
    """,
    """
LOCK TABLE audit_events IN ACCESS EXCLUSIVE MODE
    """,
    """
ALTER TABLE tenants ADD COLUMN alert_retention_days INTEGER DEFAULT 60 NOT NULL
	CONSTRAINT ck_tenant_alert_retention CHECK (alert_retention_days BETWEEN 30 AND 3650)
    """,
    """
CREATE INDEX ix_alert_tenant_closed ON alerts (tenant_id, closed_at) WHERE status = 'closed'
    """,
    """
ALTER TABLE audit_events ADD COLUMN details JSONB
	CONSTRAINT ck_audit_details CHECK (details IS NULL OR (jsonb_typeof(details) = 'object' AND octet_length(details::text) <= 1024))
    """,
)
DOWNGRADE_STATEMENTS = (
    """
LOCK TABLE tenants IN ACCESS EXCLUSIVE MODE
    """,
    """
LOCK TABLE alerts IN ACCESS EXCLUSIVE MODE
    """,
    """
LOCK TABLE audit_events IN ACCESS EXCLUSIVE MODE
    """,
    """
DELETE FROM audit_events WHERE action IN ('alerts_pruned','tenant_alert_retention_set')
    """,
    """
DROP INDEX ix_alert_tenant_closed
    """,
    """
ALTER TABLE audit_events DROP COLUMN details
    """,
    """
ALTER TABLE tenants DROP COLUMN alert_retention_days
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
