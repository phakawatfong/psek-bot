import sqlite3

import pytest

from fantasy_bot.models import DaySchedule, Game
from fantasy_bot.services.schedule import get_schedule

SEASON = "2026-27"


@pytest.fixture
def with_games(seeded: sqlite3.Connection) -> sqlite3.Connection:
    """Days 1-2 are finished; day 3 has one game played and one still to come."""
    seeded.executemany(
        "INSERT INTO nba_team VALUES (?, ?, ?, ?)",
        [(SEASON, 1, "Atlanta Hawks", "ATL"), (SEASON, 2, "Boston Celtics", "BOS")],
    )
    seeded.execute(
        "INSERT INTO day (season_id, day_id, gameweek, name, deadline_time, finished,"
        " data_checked) VALUES (?, 3, 1, 'Gameweek 1 - Day 3', '2026-10-22T18:00:00Z', 0, 0)",
        (SEASON,),
    )
    seeded.executemany(
        "INSERT INTO fixture VALUES (?, ?, 3, ?, ?, ?, ?, ?, ?, ?)",
        [
            (SEASON, 11, "0022600011", "2026-10-23T02:00:00Z", 2, 1, None, None, 0),
            (SEASON, 10, "0022600010", "2026-10-22T23:00:00Z", 1, 2, 110, 104, 1),
        ],
    )
    return seeded


def test_default_day_is_the_next_unfinished_one(with_games: sqlite3.Connection) -> None:
    assert get_schedule(with_games, SEASON) == DaySchedule(
        3,
        "Gameweek 1 - Day 3",
        [
            Game("2026-10-22T23:00:00Z", "ATL", "BOS", 110, 104, True),
            Game("2026-10-23T02:00:00Z", "BOS", "ATL", None, None, False),
        ],
    )


def test_day_without_synced_games_is_empty(with_games: sqlite3.Connection) -> None:
    assert get_schedule(with_games, SEASON, 1) == DaySchedule(1, "Gameweek 1 - Day 1", [])


def test_unknown_day_has_no_schedule(with_games: sqlite3.Connection) -> None:
    assert get_schedule(with_games, SEASON, 99) is None
