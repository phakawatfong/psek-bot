import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from fantasy_bot.clients.nbafantasy import NotFound
from fantasy_bot.database import tables as t
from fantasy_bot.models.nbafantasy import SyncResult
from fantasy_bot.repositories.season import ensure_season
from fantasy_bot.services.sync import sync_season

SEASON = "2026-27"
AFTER_DAY_4 = datetime(2026, 10, 24, tzinfo=UTC)  # day 4 deadline: 2026-10-23T19:30Z
BEFORE_DAY_4 = datetime(2026, 10, 23, tzinfo=UTC)
FIXTURES = Path(__file__).parents[1] / "fixtures" / "nbafantasy"
# Real nbafantasy responses for day 4, trimmed to one entry's ten players.
RESPONSES = {
    "bootstrap-static/": "bootstrap.json",
    "leagues-classic/14/standings/?page_standings=1": "league_14.json",
    "fixtures/?event=4": "fixtures_4.json",
    "event/4/live/": "live_4.json",
    "entry/34409/": "entry_34409.json",
    "entry/34409/event/4/picks/": "picks_34409_4.json",
}


class FakeApi:
    def __init__(self, fail_on: str | None = None) -> None:
        self.calls: list[str] = []
        self.fail_on = fail_on

    async def fetch(self, path: str) -> Any:
        self.calls.append(path)
        if path == self.fail_on:
            raise ConnectionError("nbafantasy is down")
        if path not in RESPONSES:
            raise NotFound(path)
        return json.loads((FIXTURES / RESPONSES[path]).read_text())


def track(session: Session, *entry_ids: int) -> None:
    ensure_season(session, SEASON, 14, 10000)
    session.flush()  # the season first: participants point at it
    session.add_all(
        t.Participant(season_id=SEASON, entry_id=entry_id, joined_gameweek=1)
        for entry_id in entry_ids
    )
    session.commit()


def one(session: Session, sql: str) -> tuple[Any, ...]:
    return tuple(session.execute(text(sql)).one())


def sync(session: Session, api: FakeApi, now: datetime = AFTER_DAY_4) -> SyncResult:
    return asyncio.run(sync_season(session, api.fetch, SEASON, now))


def test_sync_stores_day_and_rebuilt_points_match_official(session: Session) -> None:
    track(session, 34409)
    assert sync(session, FakeApi()) == SyncResult(days_synced=[4], entries=1, mismatches=[])
    assert one(
        session, "SELECT count(*), entry_id, day_id, official, computed FROM v_entry_day_reconcile"
    ) == (1, 34409, 4, 130, 130)
    assert one(session, "SELECT count(*), sum(multiplier) FROM fact_pick") == (10, 5)
    assert one(
        session,
        "SELECT home_team_id, away_team_id, home_score, away_score FROM fixture"
        " WHERE nba_game_id = '0022600099'",
    ) == (17, 5, 125, 132)
    assert one(session, "SELECT entry_name FROM entry WHERE entry_id = 34409") == ("Test Team",)


def test_final_day_is_not_fetched_again(session: Session) -> None:
    track(session, 34409)
    sync(session, FakeApi())
    second = FakeApi()
    assert sync(session, second).days_synced == []
    assert second.calls == [
        "bootstrap-static/",
        "leagues-classic/14/standings/?page_standings=1",
        "entry/34409/",
    ]


def test_days_before_their_deadline_are_skipped(session: Session) -> None:
    track(session, 34409)
    assert sync(session, FakeApi(), now=BEFORE_DAY_4).days_synced == []


def test_unknown_entry_is_skipped(session: Session) -> None:
    track(session, 34409, 999)
    result = sync(session, FakeApi())
    assert (result.entries, one(session, "SELECT count(*) FROM fact_entry_day")) == (1, (1,))


def test_failed_fetch_records_error_and_writes_no_partial_day(session: Session) -> None:
    track(session, 34409)
    with pytest.raises(ConnectionError):
        sync(session, FakeApi(fail_on="entry/34409/event/4/picks/"))
    counts = one(
        session,
        "SELECT (SELECT count(*) FROM fact_player_stat), (SELECT count(*) FROM fact_entry_day),"
        " (SELECT error FROM sync_run)",
    )
    assert counts == (0, 0, "ConnectionError('nbafantasy is down')")


def test_friend_registered_after_day_is_final_gets_backfilled(session: Session) -> None:
    track(session)
    sync(session, FakeApi())  # day 4 becomes final with nobody tracked
    session.add(t.Participant(season_id=SEASON, entry_id=34409, joined_gameweek=1))
    session.commit()
    late = FakeApi()
    assert sync(session, late) == SyncResult(days_synced=[4], entries=1, mismatches=[])
    assert late.calls == [
        "bootstrap-static/",
        "leagues-classic/14/standings/?page_standings=1",
        "entry/34409/",
        "entry/34409/event/4/picks/",
    ]
    assert one(session, "SELECT official, computed FROM v_entry_day_reconcile") == (130, 130)


def test_every_team_in_the_league_is_stored(session: Session) -> None:
    track(session)  # nobody registered yet
    sync(session, FakeApi())
    rows = session.execute(
        text("SELECT entry_id, entry_name, manager_name FROM entry ORDER BY entry_id")
    )
    assert [tuple(r) for r in rows] == [
        (34409, "Test Team", "Test Manager"),
        (55555, "Other Team", "Other Manager"),
    ]


def test_someone_added_to_the_file_gets_points_in_the_same_sync(
    session: Session, tmp_path: Path
) -> None:
    track(session)  # nobody in the pool yet
    path = tmp_path / "participants.csv"
    path.write_text("entry_id,from_gameweek,name\n34409,1,test\n")
    result = asyncio.run(sync_season(session, FakeApi().fetch, SEASON, AFTER_DAY_4, path))
    assert (result.entries, result.days_synced) == (1, [4])
    assert one(session, "SELECT official, computed FROM v_entry_day_reconcile") == (130, 130)
