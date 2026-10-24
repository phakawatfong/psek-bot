import sqlite3

from fantasy_bot.models import DayPointsRow, ParticipantName, StandingRow
from fantasy_bot.services.participants import list_participants
from fantasy_bot.services.standings import get_day_points, get_points_history, get_standings

SEASON = "2026-27"


def named(team: str) -> ParticipantName:
    return ParticipantName(team, "manager")


def test_season_standings_rank_approved_teams_by_latest_total(seeded: sqlite3.Connection) -> None:
    assert get_standings(seeded, SEASON) == [
        StandingRow(1, named("Bravo"), 900),
        StandingRow(2, named("Alpha"), 700),
        StandingRow(3, named("Charlie"), 500),
        StandingRow(4, named("Delta"), 0),
    ]


def test_gameweek_standings_net_out_transfer_costs(seeded: sqlite3.Connection) -> None:
    seeded.execute("UPDATE fact_entry_day SET transfers_cost = 450 WHERE entry_id = 102")
    assert [(r.rank, r.name.team_name, r.points) for r in get_standings(seeded, SEASON, 1)] == [
        (1, "Alpha", 700),
        (2, "Charlie", 500),
        (3, "Bravo", 0),
        (3, "Delta", 0),
    ]


def test_day_points_default_to_latest_day_and_share_ranks_on_ties(
    seeded: sqlite3.Connection,
) -> None:
    report = get_day_points(seeded, SEASON)
    assert report is not None
    assert (report.day_id, report.day_name, report.final) == (2, "Gameweek 1 - Day 2", True)
    assert report.rows == [
        DayPointsRow(1, named("Bravo"), 400, 900),
        DayPointsRow(2, named("Alpha"), 300, 700),
        DayPointsRow(2, named("Charlie"), 300, 500),
        DayPointsRow(4, named("Delta"), 0, 0),
    ]


def test_unknown_day_has_no_points(seeded: sqlite3.Connection) -> None:
    assert get_day_points(seeded, SEASON, 99) is None


def test_participants_list_approved_then_pending(seeded: sqlite3.Connection) -> None:
    rows = list_participants(seeded, SEASON)
    assert [(r.name.team_name, r.entry_id, r.status) for r in rows] == [
        ("Alpha", 101, "approved"),
        ("Bravo", 102, "approved"),
        ("Charlie", 103, "approved"),
        ("Delta", 104, "approved"),
        ("Echo", 105, "pending"),
    ]


def test_points_history_has_one_series_per_approved_team_with_data(
    seeded: sqlite3.Connection,
) -> None:
    history = get_points_history(seeded, SEASON)
    # Delta has no synced days and pending Echo is not shown; order follows registration.
    assert [(s.name.team_name, s.days, s.totals) for s in history.series] == [
        ("Alpha", [1, 2], [400, 700]),
        ("Bravo", [1, 2], [500, 900]),
        ("Charlie", [1, 2], [200, 500]),
    ]
    assert history.gameweek_of_day == {1: 1, 2: 1}
