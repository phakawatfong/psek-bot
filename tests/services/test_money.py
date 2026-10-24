import sqlite3

import pytest

from fantasy_bot.models import DEFAULT_RULES, PoolRules, SeasonMoney, WeekMoney
from fantasy_bot.services.money import get_season_money, get_week_money

SEASON = "2026-27"


@pytest.fixture
def two_weeks(seeded: sqlite3.Connection) -> sqlite3.Connection:
    """Adds gameweek 2: one day, not final yet. Delta joins from gameweek 2 on."""
    seeded.execute(
        "INSERT INTO day (season_id, day_id, gameweek, name, deadline_time, finished,"
        " data_checked) VALUES (?, 3, 2, 'Gameweek 2 - Day 1', '2026-10-27T18:00:00Z', 0, 0)",
        (SEASON,),
    )
    seeded.executemany(
        "INSERT INTO fact_entry_day VALUES (?, ?, 3, ?, ?, 0, 0, NULL)",
        [(SEASON, 101, 600, 1300), (SEASON, 102, 100, 1000), (SEASON, 103, 300, 800)],
    )
    seeded.execute("UPDATE participant SET joined_gameweek = 2 WHERE entry_id = 104")
    return seeded


def week_table(week: WeekMoney | None) -> list[tuple[str, int, int, int]]:
    assert week is not None
    return [
        (line.name.team_name, line.settlement.points, line.settlement.payout, line.settlement.net)
        for line in week.lines
    ]


def test_final_week_splits_its_own_pool(seeded: sqlite3.Connection) -> None:
    # Four approved teams x 100.00 = 400.00. Pending Echo is not in the pool.
    week = get_week_money(seeded, SEASON, 1)
    assert week is not None and week.final
    assert week_table(week) == [
        ("Bravo", 900, 20000, 10000),
        ("Alpha", 700, 12000, 2000),
        ("Charlie", 500, 8000, -2000),
        ("Delta", 0, 0, -10000),
    ]


def test_team_joining_later_only_pays_from_its_gameweek(two_weeks: sqlite3.Connection) -> None:
    week_1 = [team for team, *_ in week_table(get_week_money(two_weeks, SEASON, 1))]
    week_2 = [team for team, *_ in week_table(get_week_money(two_weeks, SEASON, 2))]
    assert (week_1, len(week_2)) == (["Bravo", "Alpha", "Charlie"], 4)


def test_season_counts_final_weeks_and_shows_current_week_separately(
    two_weeks: sqlite3.Connection,
) -> None:
    season = get_season_money(two_weeks, SEASON)
    # Week 1 only: Bravo, Alpha, Charlie each paid 100.00 into a 300.00 pool.
    assert (season.rules, season.settled_weeks) == (DEFAULT_RULES, [1])
    assert [(r.name.team_name, r.total.paid, r.total.won, r.total.net) for r in season.rows] == [
        ("Bravo", 10000, 15000, 5000),
        ("Alpha", 10000, 9000, -1000),
        ("Charlie", 10000, 6000, -4000),
    ]
    assert season.in_progress is not None and not season.in_progress.final
    assert week_table(season.in_progress) == [
        ("Alpha", 600, 20000, 10000),
        ("Charlie", 300, 12000, 2000),
        ("Bravo", 100, 8000, -2000),
        ("Delta", 0, 0, -10000),
    ]


def test_week_without_points_has_no_money(seeded: sqlite3.Connection) -> None:
    assert get_week_money(seeded, SEASON, 5) is None


def test_empty_season(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO season (season_id, league_id) VALUES ('2027-28', 99)")
    conn.execute("INSERT INTO payout_rank VALUES ('2027-28', 1, 10000)")
    assert get_season_money(conn, "2027-28") == SeasonMoney(
        PoolRules(10000, (10000,)), [], [], None
    )
