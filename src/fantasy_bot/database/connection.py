"""Opening the database, migrating it, and backing it up, all through SQLAlchemy's engine.

Queries use SQLAlchemy sessions (see tables.py). Migrations and backups are plain SQL scripts and
SQLite's backup feature, so they run on the SQLite connection the engine manages.
"""

import sqlite3
from contextlib import closing
from datetime import date
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

MIGRATIONS = files(__package__) / "migrations"
BACKUPS_KEPT = 14


def create(path: str) -> Engine:
    """An engine for the SQLite file at `path`, or ":memory:" for a throwaway database."""
    if path == ":memory:":
        # One shared connection; otherwise each connection would see its own empty database.
        engine = create_engine("sqlite://", poolclass=StaticPool)
    else:
        engine = create_engine(f"sqlite:///{path}")
    event.listen(engine, "connect", _enforce_foreign_keys)
    return engine


def sessions(engine: Engine) -> sessionmaker[Session]:
    """A session factory; open one session per command or sync, `with sessions() as session`."""
    return sessionmaker(engine)


def _enforce_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    dbapi_connection.execute("PRAGMA foreign_keys = ON")  # SQLite leaves them off by default


def migrate(engine: Engine, migrations: Traversable = MIGRATIONS) -> int:
    """Apply each `NNN_name.sql` newer than PRAGMA user_version, one transaction per file."""
    with closing(engine.raw_connection()) as raw:
        conn: sqlite3.Connection = raw.driver_connection  # type: ignore[assignment]
        current: int = conn.execute("PRAGMA user_version").fetchone()[0]
        pending = sorted(
            (int(f.name.split("_", 1)[0]), f)
            for f in migrations.iterdir()
            if f.name.endswith(".sql")
        )
        for version, script in pending:
            if version <= current:
                continue
            try:
                conn.executescript(
                    f"BEGIN;\n{script.read_text()}\nPRAGMA user_version = {version};\nCOMMIT;"
                )
            except sqlite3.Error:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
            current = version
    return current


def backup(engine: Engine, directory: Path, today: date) -> Path:
    """Copy the database to `directory/bot-YYYY-MM-DD.db`, keeping the newest BACKUPS_KEPT.

    SQLite's backup API takes a consistent copy even while the bot is writing; copying the
    file directly could catch it half-written.
    """
    with closing(engine.raw_connection()) as raw:
        conn: sqlite3.Connection = raw.driver_connection  # type: ignore[assignment]
        if conn.in_transaction:
            # SQLite's backup waits forever on a lock this same connection holds.
            raise RuntimeError("commit or roll back before backing up")
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"bot-{today.isoformat()}.db"
        with closing(sqlite3.connect(target)) as copy:
            conn.backup(copy)
    for old in sorted(directory.glob("bot-*.db"))[:-BACKUPS_KEPT]:
        old.unlink()
    return target
