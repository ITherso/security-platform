"""Rule alerts on self-reported endpoint events and the per-device suppressed-alert counter."""
from alembic import op

revision = "0003_alerts"
down_revision = "0002_endpoint_events"
branch_labels = None
depends_on = None

DDL_STATEMENTS = (
    """
ALTER TABLE device_event_cursors ADD COLUMN suppressed_alerts BIGINT DEFAULT 0 NOT NULL
	CONSTRAINT ck_event_cursor_suppressed_alerts CHECK (suppressed_alerts >= 0)
    """,
    """
CREATE TABLE alerts (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	device_id UUID NOT NULL,
	rule TEXT NOT NULL,
	severity TEXT NOT NULL,
	dedup_key CHAR(64) NOT NULL,
	status TEXT NOT NULL,
	occurrences BIGINT NOT NULL,
	first_event_seq BIGINT NOT NULL,
	last_event_seq BIGINT NOT NULL,
	first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL,
	last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL,
	evidence JSONB NOT NULL,
	acknowledged_at TIMESTAMP WITH TIME ZONE,
	acknowledged_by UUID,
	closed_at TIMESTAMP WITH TIME ZONE,
	closed_by UUID,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_alert_tenant_device FOREIGN KEY(tenant_id, device_id) REFERENCES devices (tenant_id, id),
	CONSTRAINT fk_alert_acknowledger_membership FOREIGN KEY(tenant_id, acknowledged_by) REFERENCES memberships (tenant_id, principal_id),
	CONSTRAINT fk_alert_closer_membership FOREIGN KEY(tenant_id, closed_by) REFERENCES memberships (tenant_id, principal_id),
	CONSTRAINT ck_alert_rule CHECK (rule IN ('user_writable_launch','office_browser_spawned_tool','sensor_unstable','event_loss')),
	CONSTRAINT ck_alert_severity CHECK (severity IN ('low','medium')),
	CONSTRAINT ck_alert_dedup_key CHECK (dedup_key ~ '^[0-9a-f]{64}$'),
	CONSTRAINT ck_alert_status CHECK (status IN ('open','acknowledged','closed')),
	CONSTRAINT ck_alert_occurrences CHECK (occurrences >= 1),
	CONSTRAINT ck_alert_event_seq CHECK (first_event_seq >= 1 AND last_event_seq >= first_event_seq),
	CONSTRAINT ck_alert_evidence_object CHECK (jsonb_typeof(evidence) = 'object'),
	CONSTRAINT ck_alert_evidence_bytes CHECK (octet_length(evidence::text) <= 4096),
	CONSTRAINT ck_alert_acknowledgement CHECK ((acknowledged_at IS NULL) = (acknowledged_by IS NULL)),
	CONSTRAINT ck_alert_closure CHECK ((closed_at IS NULL) = (closed_by IS NULL)),
	CONSTRAINT ck_alert_lifecycle CHECK ((status = 'open' AND acknowledged_at IS NULL AND closed_at IS NULL) OR (status = 'acknowledged' AND acknowledged_at IS NOT NULL AND closed_at IS NULL) OR (status = 'closed' AND closed_at IS NOT NULL))
)
    """,
    """
CREATE UNIQUE INDEX uq_alert_not_closed_key ON alerts (tenant_id, device_id, rule, dedup_key) WHERE status <> 'closed'
    """,
    """
CREATE INDEX ix_alert_tenant_seen ON alerts (tenant_id, last_seen_at DESC, id DESC)
    """,
    """
CREATE INDEX ix_alert_device_seen ON alerts (tenant_id, device_id, last_seen_at DESC, id DESC)
    """,
)


def upgrade():
    for statement in DDL_STATEMENTS:
        op.execute(statement)


def downgrade():
    op.drop_table('alerts')
    op.drop_column('device_event_cursors', 'suppressed_alerts')
