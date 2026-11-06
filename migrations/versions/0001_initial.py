"""Initial tenant/device boundary and bounded state schema."""
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

DDL_STATEMENTS = (
    """
CREATE TABLE principals (
	id UUID NOT NULL,
	issuer VARCHAR(512) NOT NULL,
	subject VARCHAR(255) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_principal_identity UNIQUE (issuer, subject)
)
    """,
    """
CREATE TABLE tenants (
	id UUID NOT NULL,
	name VARCHAR(120) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)
    """,
    """
CREATE TABLE audit_events (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	actor_type VARCHAR(20) NOT NULL,
	actor_id UUID,
	action VARCHAR(48) NOT NULL,
	object_type VARCHAR(32) NOT NULL,
	object_id UUID NOT NULL,
	outcome VARCHAR(16) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_audit_actor CHECK (actor_type IN ('operator','device','local_admin')),
	CONSTRAINT ck_audit_outcome CHECK (outcome = 'success'),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
)
    """,
    """
CREATE TABLE devices (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	label VARCHAR(80) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	last_sequence BIGINT,
	last_message_id UUID,
	last_content_digest VARCHAR(64),
	last_received_at TIMESTAMP WITH TIME ZONE,
	source_observed_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_device_tenant_identity UNIQUE (tenant_id, id),
	CONSTRAINT ck_device_sequence CHECK (last_sequence IS NULL OR last_sequence >= 1),
	CONSTRAINT ck_device_snapshot_consistency CHECK ((last_sequence IS NULL AND last_message_id IS NULL AND last_content_digest IS NULL AND last_received_at IS NULL) OR (last_sequence IS NOT NULL AND last_message_id IS NOT NULL AND last_content_digest IS NOT NULL AND last_received_at IS NOT NULL)),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
)
    """,
    """
CREATE TABLE memberships (
	tenant_id UUID NOT NULL,
	principal_id UUID NOT NULL,
	role VARCHAR(20) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (tenant_id, principal_id),
	CONSTRAINT ck_membership_role CHECK (role IN ('tenant_admin','viewer')),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(principal_id) REFERENCES principals (id)
)
    """,
    """
CREATE TABLE device_credentials (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	device_id UUID NOT NULL,
	token_digest VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT fk_credential_tenant_device FOREIGN KEY(tenant_id, device_id) REFERENCES devices (tenant_id, id),
	CONSTRAINT ck_credential_expiry CHECK (expires_at > created_at),
	CONSTRAINT ck_credential_digest CHECK (length(token_digest) = 64),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	UNIQUE (token_digest)
)
    """,
    """
CREATE TABLE enrollment_grants (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	token_digest VARCHAR(64) NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	consumed_at TIMESTAMP WITH TIME ZONE,
	revoked_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_grant_tenant_identity UNIQUE (tenant_id, id),
	CONSTRAINT fk_grant_creator_membership FOREIGN KEY(tenant_id, created_by) REFERENCES memberships (tenant_id, principal_id),
	CONSTRAINT ck_grant_expiry CHECK (expires_at > created_at),
	CONSTRAINT ck_grant_digest CHECK (length(token_digest) = 64),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	UNIQUE (token_digest)
)
    """,
    """
CREATE TABLE product_states (
	tenant_id UUID NOT NULL,
	device_id UUID NOT NULL,
	product_id VARCHAR(32) NOT NULL,
	snapshot_sequence BIGINT NOT NULL,
	received_at TIMESTAMP WITH TIME ZONE NOT NULL,
	payload JSONB NOT NULL,
	PRIMARY KEY (tenant_id, device_id, product_id),
	CONSTRAINT fk_product_tenant_device FOREIGN KEY(tenant_id, device_id) REFERENCES devices (tenant_id, id),
	CONSTRAINT ck_product_id CHECK (product_id IN ('hostbasedfirewall','termivar','antivirus')),
	CONSTRAINT ck_product_sequence CHECK (snapshot_sequence >= 1),
	CONSTRAINT ck_product_payload_bytes CHECK (octet_length(payload::text) <= 16384),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
)
    """,
    """
CREATE INDEX ix_audit_tenant_created ON audit_events (tenant_id, created_at, id)
    """,
    """
CREATE INDEX ix_device_tenant_created ON devices (tenant_id, created_at, id)
    """,
    """
CREATE INDEX ix_credential_device ON device_credentials (tenant_id, device_id)
    """,
    """
CREATE UNIQUE INDEX uq_credential_active_device ON device_credentials (tenant_id, device_id) WHERE revoked_at IS NULL
    """,
    """
CREATE INDEX ix_grant_tenant_created ON enrollment_grants (tenant_id, created_at, id)
    """,
)


def upgrade():
    for statement in DDL_STATEMENTS:
        op.execute(statement)


def downgrade():
    op.drop_table('product_states')
    op.drop_table('enrollment_grants')
    op.drop_table('device_credentials')
    op.drop_table('memberships')
    op.drop_table('devices')
    op.drop_table('audit_events')
    op.drop_table('tenants')
    op.drop_table('principals')
