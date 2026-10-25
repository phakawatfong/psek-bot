"""Writes for the nbafantasy sync. Every write converges, so re-running a sync is safe.

Functions here don't commit; the sync commits each step as one transaction.
"""

import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from typing import Any

from sqlalchemy import delete, inspect, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from fantasy_bot.database import tables as t
from fantasy_bot.models.nbafantasy import (
    Day,
    Entry,
    EntryDay,
    Fixture,
    LeagueTeam,
    Mismatch,
    Pick,
    Player,
    PlayerStat,
    Team,
)


def _upsert(session: Session, table: type[t.Base], season_id: str, rows: Sequence[Any]) -> None:
    """Insert rows (dataclasses named like the columns), updating ones that already exist.

    The conflict target is the table's primary key, read from its mapping.
    """
    if not rows:
        return
    keys = [column.name for column in inspect(table).primary_key]
    values = [{"season_id": season_id, **asdict(row)} for row in rows]
    statement = insert(table)
    statement = statement.on_conflict_do_update(
        index_elements=keys,
        set_={column: statement.excluded[column] for column in values[0] if column not in keys},
    )
    session.execute(statement, values)


def upsert_teams(session: Session, season_id: str, rows: Sequence[Team]) -> None:
    _upsert(session, t.NbaTeam, season_id, rows)


def upsert_players(session: Session, season_id: str, rows: Sequence[Player]) -> None:
    _upsert(session, t.Player, season_id, rows)


def upsert_days(session: Session, season_id: str, rows: Sequence[Day]) -> None:
    _upsert(session, t.Day, season_id, rows)


def upsert_fixtures(session: Session, season_id: str, rows: Sequence[Fixture]) -> None:
    _upsert(session, t.Fixture, season_id, rows)


def upsert_entries(session: Session, season_id: str, rows: Sequence[Entry]) -> None:
    _upsert(session, t.Entry, season_id, rows)


def upsert_league_teams(session: Session, season_id: str, rows: Sequence[LeagueTeam]) -> None:
    """Names of every team in the league; leaves started_day to the per-entry fetch."""
    if not rows:
        return
    statement = insert(t.Entry)
    session.execute(
        statement.on_conflict_do_update(
            index_elements=["season_id", "entry_id"],
            set_={
                "entry_name": statement.excluded.entry_name,
                "manager_name": statement.excluded.manager_name,
            },
        ),
        [{"season_id": season_id, **asdict(team)} for team in rows],
    )


def upsert_entry_day(session: Session, season_id: str, row: EntryDay) -> None:
    _upsert(session, t.FactEntryDay, season_id, [row])


def replace_day_stats(
    session: Session, season_id: str, day_id: int, rows: Sequence[PlayerStat]
) -> None:
    """Replace a day's stats wholesale, so a stat nbafantasy later removes doesn't linger."""
    day_fixtures = select(t.Fixture.fixture_id).where(
        t.Fixture.season_id == season_id, t.Fixture.day_id == day_id
    )
    session.execute(
        delete(t.FactPlayerStat).where(
            t.FactPlayerStat.season_id == season_id, t.FactPlayerStat.fixture_id.in_(day_fixtures)
        )
    )
    _upsert(session, t.FactPlayerStat, season_id, rows)


def replace_picks(
    session: Session, season_id: str, entry_id: int, day_id: int, rows: Sequence[Pick]
) -> None:
    session.execute(
        delete(t.FactPick).where(
            t.FactPick.season_id == season_id,
            t.FactPick.entry_id == entry_id,
            t.FactPick.day_id == day_id,
        )
    )
    _upsert(session, t.FactPick, season_id, rows)


def save_raw(
    session: Session, season_id: str, request_key: str, body: Any, fetched_at: str
) -> None:
    statement = insert(t.RawApiResponse).values(
        season_id=season_id,
        source="nbafantasy",
        request_key=request_key,
        fetched_at=fetched_at,
        body=json.dumps(body),
    )
    session.execute(
        statement.on_conflict_do_update(
            index_elements=["season_id", "source", "request_key"],
            set_={"fetched_at": statement.excluded.fetched_at, "body": statement.excluded.body},
        )
    )


def final_day_ids(session: Session, season_id: str) -> set[int]:
    return set(
        session.scalars(
            select(t.Day.day_id).where(t.Day.season_id == season_id, t.Day.facts_final.is_(True))
        )
    )


def synced_entry_days(session: Session, season_id: str) -> set[tuple[int, int]]:
    rows = session.execute(
        select(t.FactEntryDay.entry_id, t.FactEntryDay.day_id).where(
            t.FactEntryDay.season_id == season_id
        )
    )
    return {(entry_id, day_id) for entry_id, day_id in rows}


def mark_day_final(session: Session, season_id: str, day_id: int) -> None:
    session.execute(
        update(t.Day)
        .where(t.Day.season_id == season_id, t.Day.day_id == day_id)
        .values(facts_final=True)
    )


def reconcile_mismatches(
    session: Session, season_id: str, day_ids: Iterable[int]
) -> list[Mismatch]:
    view = t.entry_day_reconcile.c
    rows = session.execute(
        select(view.entry_id, view.day_id, view.official, view.computed)
        .where(
            view.season_id == season_id,
            view.official != view.computed,
            view.day_id.in_(list(day_ids)),
        )
        .order_by(view.day_id, view.entry_id)
    )
    return [Mismatch(*row) for row in rows]


def start_sync_run(session: Session, season_id: str, started_at: str) -> int:
    run = t.SyncRun(season_id=season_id, started_at=started_at)
    session.add(run)
    session.commit()
    return run.sync_run_id


def finish_sync_run(
    session: Session,
    run_id: int,
    finished_at: str,
    days_synced: int | None,
    error: str | None = None,
) -> None:
    session.execute(
        update(t.SyncRun)
        .where(t.SyncRun.sync_run_id == run_id)
        .values(finished_at=finished_at, days_synced=days_synced, error=error)
    )
    session.commit()
