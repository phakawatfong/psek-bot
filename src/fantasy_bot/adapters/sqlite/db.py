import sqlite3
from importlib.resources import files
from importlib.resources.abc import Traversable

MIGRATIONS = files(__package__) / "migrations"


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
