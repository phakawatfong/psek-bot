import sqlite3
from datetime import date
from pathlib import Path

import pytest

from fantasy_bot.repositories.database import backup, connect, migrate


def user_version(conn: sqlite3.Connection) -> int:
    version: int = conn.execute("PRAGMA user_version").fetchone()[0]
    return version


def test_fresh_database_reaches_latest_version() -> None:
    conn = connect(":memory:")
    assert migrate(conn) == 3
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_schema WHERE type = 'table'")}
    assert {"season", "participant", "ledger", "fact_player_stat", "fact_pick"} <= tables


def test_rerunning_migrate_is_a_no_op() -> None:
    conn = connect(":memory:")
    migrate(conn)
    assert migrate(conn) == 3
    assert user_version(conn) == 3


def test_failed_migration_rolls_back_and_keeps_old_version(tmp_path: Path) -> None:
    (tmp_path / "001_ok.sql").write_text("CREATE TABLE a (x INTEGER);")
    (tmp_path / "002_broken.sql").write_text("CREATE TABLE b (x INTEGER); NOT VALID SQL;")
    conn = connect(":memory:")
    with pytest.raises(sqlite3.Error):
        migrate(conn, tmp_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_schema WHERE type = 'table'")}
    assert (user_version(conn), tables) == (1, {"a"})


def test_schema_rejects_bad_money_and_unknown_status() -> None:
    conn = connect(":memory:")
    migrate(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO season (season_id, league_id, weekly_buy_in_minor) VALUES ('x', 14, -5)"
        )
    conn.execute("INSERT INTO season (season_id, league_id) VALUES ('2026-27', 14)")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO participant (season_id, discord_user_id, entry_id, status,"
            " registered_at) VALUES ('2026-27', 1, 7912, 'winner', '2026-10-24')"
        )


def test_backup_is_a_full_copy_and_keeps_only_the_newest_fourteen(
    seeded: sqlite3.Connection, tmp_path: Path
) -> None:
    seeded.commit()
    for day in range(1, 16):  # fifteen older copies already there
        (tmp_path / f"bot-2026-09-{day:02d}.db").write_bytes(b"old")
    target = backup(seeded, tmp_path, date(2026, 10, 25))
    copy = connect(str(target))
    assert copy.execute("SELECT count(*) FROM participant").fetchone()[0] == 5
    kept = sorted(p.name for p in tmp_path.glob("bot-*.db"))
    assert (len(kept), kept[0], kept[-1]) == (14, "bot-2026-09-03.db", "bot-2026-10-25.db")


def test_backup_refuses_uncommitted_work_instead_of_hanging(
    seeded: sqlite3.Connection, tmp_path: Path
) -> None:
    with pytest.raises(RuntimeError, match="commit or roll back"):
        backup(seeded, tmp_path, date(2026, 10, 25))
