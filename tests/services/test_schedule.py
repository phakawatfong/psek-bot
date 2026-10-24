import sqlite3

import pytest

from fantasy_bot.models import DaySchedule, Game
from fantasy_bot.services.schedule import (
    current_gameweek,
    get_day_schedule,
    get_gameweek_schedule,
    get_upcoming_day_schedule,
)

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


def test_day_number_counts_within_the_gameweek(with_games: sqlite3.Connection) -> None:
    assert get_day_schedule(with_games, SEASON, 3, gameweek=1) == DaySchedule(
        3,
        "Gameweek 1 - Day 3",
        [
            Game("2026-10-22T23:00:00Z", "ATL", "BOS", 110, 104, True),
            Game("2026-10-23T02:00:00Z", "BOS", "ATL", None, None, False),
        ],
    )


def test_day_without_synced_games_is_empty(with_games: sqlite3.Connection) -> None:
    assert get_day_schedule(with_games, SEASON, 1) == DaySchedule(1, "Gameweek 1 - Day 1", [])


def test_day_or_gameweek_that_does_not_exist_has_no_schedule(
    with_games: sqlite3.Connection,
) -> None:
    assert get_day_schedule(with_games, SEASON, 4) is None
    assert get_day_schedule(with_games, SEASON, 1, gameweek=9) is None


def test_current_gameweek_holds_the_next_unfinished_day(with_games: sqlite3.Connection) -> None:
    # Days 1-2 are finished, day 3 is not: all three are gameweek 1.
    assert current_gameweek(with_games, SEASON) == 1


def test_gameweek_schedule_lists_every_day_in_order(with_games: sqlite3.Connection) -> None:
    week = get_gameweek_schedule(with_games, SEASON)  # default: the current gameweek
    assert week is not None and week.gameweek == 1
    assert [(d.day_id, len(d.games)) for d in week.days] == [(1, 0), (2, 0), (3, 2)]
    assert get_gameweek_schedule(with_games, SEASON, 9) is None


def test_upcoming_day_is_the_first_one_not_finished(with_games: sqlite3.Connection) -> None:
    # Day 3 has one game played and one to come: still upcoming, not yesterday's news.
    upcoming = get_upcoming_day_schedule(with_games, SEASON)
    assert upcoming is not None and (upcoming.day_id, len(upcoming.games)) == (3, 2)


def test_no_days_means_no_upcoming_day(conn: sqlite3.Connection) -> None:
    assert get_upcoming_day_schedule(conn, SEASON) is None
