"""Self-reported endpoint events, per-device event cursor and tenant event retention."""
from alembic import op

revision = "0002_endpoint_events"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

DDL_STATEMENTS = (
    """
ALTER TABLE tenants ADD COLUMN event_retention_days SMALLINT DEFAULT 30 NOT NULL
	CONSTRAINT ck_tenant_event_retention CHECK (event_retention_days BETWEEN 1 AND 90)
    """,
    """
CREATE TABLE device_event_cursors (
	tenant_id UUID NOT NULL,
	device_id UUID NOT NULL,
	last_batch_sequence BIGINT NOT NULL,
	last_batch_id UUID NOT NULL,
	last_batch_digest VARCHAR(64) NOT NULL,
	last_event_seq BIGINT NOT NULL,
	last_received_at TIMESTAMP WITH TIME ZONE NOT NULL,
	stored_events BIGINT DEFAULT 0 NOT NULL,
	cap_deleted_events BIGINT DEFAULT 0 NOT NULL,
	PRIMARY KEY (tenant_id, device_id),
	CONSTRAINT fk_event_cursor_tenant_device FOREIGN KEY(tenant_id, device_id) REFERENCES devices (tenant_id, id),
	CONSTRAINT ck_event_cursor_batch_sequence CHECK (last_batch_sequence >= 1),
	CONSTRAINT ck_event_cursor_digest CHECK (last_batch_digest ~ '^[0-9a-f]{64}$'),
	CONSTRAINT ck_event_cursor_event_seq CHECK (last_event_seq >= 1),
	CONSTRAINT ck_event_cursor_stored_events CHECK (stored_events >= 0),
	CONSTRAINT ck_event_cursor_cap_deleted_events CHECK (cap_deleted_events >= 0)
)
    """,
    """
CREATE TABLE endpoint_events (
	tenant_id UUID NOT NULL,
	device_id UUID NOT NULL,
	event_seq BIGINT NOT NULL,
	kind VARCHAR(32) NOT NULL,
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	received_at TIMESTAMP WITH TIME ZONE NOT NULL,
	payload JSONB NOT NULL,
	PRIMARY KEY (tenant_id, device_id, event_seq),
	CONSTRAINT fk_endpoint_event_tenant_device FOREIGN KEY(tenant_id, device_id) REFERENCES devices (tenant_id, id),
	CONSTRAINT ck_endpoint_event_sequence CHECK (event_seq >= 1),
	CONSTRAINT ck_endpoint_event_kind CHECK (kind IN ('process_started','process_stopped','sensor_state')),
	CONSTRAINT ck_endpoint_event_observed_at CHECK (observed_at >= '1970-01-01 00:00:00+00' AND observed_at < '9999-01-01 00:00:00+00'),
	CONSTRAINT ck_endpoint_event_payload_bytes CHECK (octet_length(payload::text) <= 4096)
)
    """,
    """
CREATE INDEX ix_endpoint_events_tenant_received ON endpoint_events (tenant_id, received_at)
    """,
)


def upgrade():
    for statement in DDL_STATEMENTS:
        op.execute(statement)


def downgrade():
    op.drop_table('endpoint_events')
    op.drop_table('device_event_cursors')
    op.drop_column('tenants', 'event_retention_days')
