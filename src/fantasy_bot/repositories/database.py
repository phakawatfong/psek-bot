import sqlite3
from contextlib import closing
from datetime import date
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

MIGRATIONS = files(__package__) / "migrations"
BACKUPS_KEPT = 14


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection, migrations: Traversable = MIGRATIONS) -> int:
    """Apply each `NNN_name.sql` newer than PRAGMA user_version, one transaction per file."""
    current: int = conn.execute("PRAGMA user_version").fetchone()[0]
    pending = sorted(
        (int(f.name.split("_", 1)[0]), f) for f in migrations.iterdir() if f.name.endswith(".sql")
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


def backup(conn: sqlite3.Connection, directory: Path, today: date) -> Path:
    """Copy the database to `directory/bot-YYYY-MM-DD.db`, keeping the newest BACKUPS_KEPT.

    SQLite's backup API takes a consistent copy even while the bot is writing; copying the
    file directly could catch it half-written.
    """
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
