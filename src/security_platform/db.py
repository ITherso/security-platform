"""Explicit transaction ownership for every request and local administration."""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url, **engine_options):
        options = {"pool_pre_ping": True, "hide_parameters": True, "pool_timeout": 5, "pool_size": 5,
                   "max_overflow": 5, "connect_args": {"connect_timeout": 5,
                   "options": "-c statement_timeout=5000 -c lock_timeout=3000"}}
        options.update(engine_options)
        self.engine = create_engine(url, **options)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def session(self):
        with self.session_factory() as session:
            with session.begin():
                yield session

    def close(self):
        self.engine.dispose()
