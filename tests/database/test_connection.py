import sqlite3
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fantasy_bot.database import tables as t
from fantasy_bot.database.connection import backup, create, migrate


def user_version(engine: Engine) -> int:
    with engine.connect() as conn:
        version: int = conn.execute(text("PRAGMA user_version")).scalar_one()
    return version


def table_names(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT name FROM sqlite_schema WHERE type = 'table'"))
        return {name for (name,) in rows}


def test_fresh_database_reaches_latest_version() -> None:
    engine = create(":memory:")
    assert migrate(engine) == 6
    assert {"season", "participant", "fact_player_stat", "fact_pick"} <= table_names(engine)
    assert "ledger" not in table_names(engine)  # dropped in 004: real payments aren't tracked


def test_rerunning_migrate_is_a_no_op(engine: Engine) -> None:
    assert (migrate(engine), user_version(engine)) == (6, 6)


def test_failed_migration_rolls_back_and_keeps_old_version(tmp_path: Path) -> None:
    (tmp_path / "001_ok.sql").write_text("CREATE TABLE a (x INTEGER);")
    (tmp_path / "002_broken.sql").write_text("CREATE TABLE b (x INTEGER); NOT VALID SQL;")
    engine = create(":memory:")
    with pytest.raises(sqlite3.Error):
        migrate(engine, tmp_path)
    assert (user_version(engine), table_names(engine)) == (1, {"a"})


def test_schema_rejects_bad_money_bad_start_week_and_duplicate_teams(session: Session) -> None:
    session.add(t.Season(season_id="x", league_id=14, weekly_buy_in_minor=-5))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.add(t.Season(season_id="2026-27", league_id=14, weekly_buy_in_minor=10000))
    session.commit()
    for gameweek in (0, 1, 2):  # 0 is invalid; the second team 1 is a duplicate
        session.add(t.Participant(season_id="2026-27", entry_id=1, joined_gameweek=gameweek))
        if gameweek == 1:
            session.commit()
            continue
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_foreign_keys_are_enforced(session: Session) -> None:
    session.add(t.Participant(season_id="no-such-season", entry_id=1, joined_gameweek=1))
    with pytest.raises(IntegrityError):
        session.commit()


def test_backup_is_a_full_copy_and_keeps_only_the_newest_fourteen(
    seeded: Session, engine: Engine, tmp_path: Path
) -> None:
    for day in range(1, 16):  # fifteen older copies already there
        (tmp_path / f"bot-2026-09-{day:02d}.db").write_bytes(b"old")
    target = backup(engine, tmp_path, date(2026, 10, 25))
    with Session(create(str(target))) as copy:
        assert copy.scalar(select(func.count()).select_from(t.Participant)) == 4
    kept = sorted(p.name for p in tmp_path.glob("bot-*.db"))
    assert (len(kept), kept[0], kept[-1]) == (14, "bot-2026-09-03.db", "bot-2026-10-25.db")


def test_backup_refuses_uncommitted_work_instead_of_hanging(
    seeded: Session, engine: Engine, tmp_path: Path
) -> None:
    seeded.add(t.Participant(season_id="2026-27", entry_id=105, joined_gameweek=1))
    seeded.flush()  # written but not committed
    with pytest.raises(RuntimeError, match="commit or roll back"):
        backup(engine, tmp_path, date(2026, 10, 25))
