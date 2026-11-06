"""Migrations use an explicit owner DSN, separate from the runtime account."""
import os

from alembic import context
from sqlalchemy import create_engine, pool

from security_platform.db import Base
import security_platform.models  # noqa: F401


config = context.config
target_metadata = Base.metadata
url = os.environ.get("SP_MIGRATION_DATABASE_URL") or config.get_main_option("sqlalchemy.url")
if not url:
    raise RuntimeError("Set SP_MIGRATION_DATABASE_URL for schema migrations")


if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(url, poolclass=pool.NullPool, hide_parameters=True,
            connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000 -c lock_timeout=3000"}).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
