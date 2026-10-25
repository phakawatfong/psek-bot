from sqlalchemy.orm import Session

from fantasy_bot.services.chart import get_gameweek_points, get_points_history

SEASON = "2026-27"


def test_points_history_has_one_series_per_team_with_data(seeded: Session) -> None:
    history = get_points_history(seeded, SEASON)
    # Delta has no synced days and Echo isn't in the pool; order follows participant order.
    assert [(s.name.team_name, s.days, s.totals) for s in history.series] == [
        ("Alpha", [1, 2], [400, 700]),
        ("Bravo", [1, 2], [500, 900]),
        ("Charlie", [1, 2], [200, 500]),
    ]
    assert history.gameweek_of_day == {1: 1, 2: 1}


def test_gameweek_points_follow_each_pool(two_weeks: Session) -> None:
    weekly = get_gameweek_points(two_weeks, SEASON)
    # The points that rank each pool; Delta joins in gameweek 2.
    assert [(s.name.team_name, s.gameweeks, s.points) for s in weekly.series] == [
        ("Alpha", [1, 2], [700, 600]),
        ("Bravo", [1, 2], [900, 100]),
        ("Charlie", [1, 2], [500, 300]),
        ("Delta", [2], [0]),
    ]
    assert weekly.not_final == [2]
