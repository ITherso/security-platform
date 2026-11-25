"""Snapshot V2: allow the Altay EDR agent's own status as product 'edr_agent'.

Only widens product_states.ck_product_id; nothing else in the database changes. A
downgrade first deletes the 'edr_agent' rows, because the narrower CHECK would refuse
them; the agent's status is the latest self-reported state and is not kept elsewhere.
"""
from alembic import op

revision = "0004_edr_agent_product"
down_revision = "0003_alerts"
branch_labels = None
depends_on = None

DDL_STATEMENTS = (
    """
ALTER TABLE product_states DROP CONSTRAINT ck_product_id
    """,
    """
ALTER TABLE product_states ADD CONSTRAINT ck_product_id CHECK (product_id IN ('hostbasedfirewall','termivar','antivirus','edr_agent'))
    """,
)
DOWNGRADE_STATEMENTS = (
    """
DELETE FROM product_states WHERE product_id = 'edr_agent'
    """,
    """
ALTER TABLE product_states DROP CONSTRAINT ck_product_id
    """,
    """
ALTER TABLE product_states ADD CONSTRAINT ck_product_id CHECK (product_id IN ('hostbasedfirewall','termivar','antivirus'))
    """,
)


def upgrade():
    for statement in DDL_STATEMENTS:
        op.execute(statement)


def downgrade():
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
