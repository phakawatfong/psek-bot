import asyncio
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from fantasy_bot.clients.nbafantasy import NotFound
from fantasy_bot.models import SyncResult
from fantasy_bot.repositories.seasons import ensure_season
from fantasy_bot.services.sync import sync_season

SEASON = "2026-27"
AFTER_DAY_4 = datetime(2026, 10, 24, tzinfo=UTC)  # day 4 deadline: 2026-10-23T19:30Z
BEFORE_DAY_4 = datetime(2026, 10, 23, tzinfo=UTC)
FIXTURES = Path(__file__).parents[1] / "fixtures" / "nbafantasy"
# Real nbafantasy responses for day 4, trimmed to one entry's ten players.
RESPONSES = {
    "bootstrap-static/": "bootstrap.json",
    "fixtures/": "fixtures_4.json",  # the whole season; day 4 is all the trimmed data has
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


def track(conn: sqlite3.Connection, *entry_ids: int) -> None:
    ensure_season(conn, SEASON, 14, [5000, 3000, 2000], 10000)
    conn.executemany(
        "INSERT INTO participant (season_id, discord_user_id, entry_id, registered_at)"
        " VALUES (?, ?, ?, '2026-10-20T00:00:00Z')",
        [(SEASON, i, entry_id) for i, entry_id in enumerate(entry_ids)],
    )


def one(conn: sqlite3.Connection, sql: str) -> tuple[Any, ...]:
    return tuple(conn.execute(sql).fetchone())


def sync(conn: sqlite3.Connection, api: FakeApi, now: datetime = AFTER_DAY_4) -> SyncResult:
    return asyncio.run(sync_season(conn, api.fetch, SEASON, now))


def test_sync_stores_day_and_rebuilt_points_match_official(conn: sqlite3.Connection) -> None:
    track(conn, 34409)
    assert sync(conn, FakeApi()) == SyncResult(days_synced=[4], entries=1, mismatches=[])
    assert one(
        conn, "SELECT count(*), entry_id, day_id, official, computed FROM v_entry_day_reconcile"
    ) == (1, 34409, 4, 130, 130)
    assert one(conn, "SELECT count(*), sum(multiplier) FROM fact_pick") == (10, 5)
    assert one(
        conn,
        "SELECT home_team_id, away_team_id, home_score, away_score FROM fixture"
        " WHERE nba_game_id = '0022600099'",
    ) == (17, 5, 125, 132)
    assert one(conn, "SELECT entry_name FROM entry") == ("Test Team",)


def test_final_day_is_not_fetched_again(conn: sqlite3.Connection) -> None:
    track(conn, 34409)
    sync(conn, FakeApi())
    second = FakeApi()
    assert sync(conn, second).days_synced == []
    assert second.calls == ["bootstrap-static/", "entry/34409/"]


def test_days_before_their_deadline_are_skipped(conn: sqlite3.Connection) -> None:
    track(conn, 34409)
    assert sync(conn, FakeApi(), now=BEFORE_DAY_4).days_synced == []


def test_unknown_entry_is_skipped(conn: sqlite3.Connection) -> None:
    track(conn, 34409, 999)
    result = sync(conn, FakeApi())
    assert (result.entries, one(conn, "SELECT count(*) FROM fact_entry_day")) == (1, (1,))


def test_failed_fetch_records_error_and_writes_no_partial_day(conn: sqlite3.Connection) -> None:
    track(conn, 34409)
    with pytest.raises(ConnectionError):
        sync(conn, FakeApi(fail_on="entry/34409/event/4/picks/"))
    counts = one(
        conn,
        "SELECT (SELECT count(*) FROM fact_player_stat), (SELECT count(*) FROM fact_entry_day),"
        " (SELECT error FROM sync_run)",
    )
    assert counts == (0, 0, "ConnectionError('nbafantasy is down')")


def test_friend_registered_after_day_is_final_gets_backfilled(conn: sqlite3.Connection) -> None:
    track(conn)
    sync(conn, FakeApi())  # day 4 becomes final with nobody tracked
    conn.execute(
        "INSERT INTO participant (season_id, discord_user_id, entry_id, registered_at)"
        " VALUES (?, 1, 34409, '2026-10-24T00:00:00Z')",
        (SEASON,),
    )
    late = FakeApi()
    assert sync(conn, late) == SyncResult(days_synced=[4], entries=1, mismatches=[])
    assert late.calls == ["bootstrap-static/", "entry/34409/", "entry/34409/event/4/picks/"]
    assert one(conn, "SELECT official, computed FROM v_entry_day_reconcile") == (130, 130)


def test_upcoming_day_gets_its_schedule_but_no_points(conn: sqlite3.Connection) -> None:
    track(conn, 34409)
    api = FakeApi()
    assert sync(conn, api, now=BEFORE_DAY_4).days_synced == []
    assert api.calls == ["bootstrap-static/", "entry/34409/", "fixtures/"]
    assert one(conn, "SELECT count(*), (SELECT count(*) FROM fact_entry_day) FROM fixture") == (
        12,
        0,
    )


def test_season_schedule_is_refreshed_every_six_hours_only(conn: sqlite3.Connection) -> None:
    track(conn, 34409)
    sync(conn, FakeApi())
    soon, later = FakeApi(), FakeApi()
    sync(conn, soon, now=AFTER_DAY_4 + timedelta(hours=5))
    sync(conn, later, now=AFTER_DAY_4 + timedelta(hours=6))
    assert ("fixtures/" in soon.calls, "fixtures/" in later.calls) == (False, True)
