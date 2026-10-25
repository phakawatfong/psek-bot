from sqlalchemy.orm import Session

from fantasy_bot.database import tables as t
from fantasy_bot.models.pool import Pool
from fantasy_bot.services.pool import get_pool

SEASON = "2026-27"


def lines(pool: Pool | None) -> list[tuple[str, int, int, int, int, int]]:
    assert pool is not None
    return [
        (line.name.team_name, s.rank, s.points, s.buy_in, s.payout, s.net)
        for line in pool.lines
        for s in [line.settlement]
    ]


def test_pool_shows_what_each_person_put_in_and_wins(seeded: Session) -> None:
    pool = get_pool(seeded, SEASON, 1)
    assert pool is not None and (pool.gameweek, pool.final) == (1, True)
    assert lines(pool) == [
        ("Bravo", 1, 900, 10000, 20000, 10000),
        ("Alpha", 2, 700, 10000, 12000, 2000),
        ("Charlie", 3, 500, 10000, 6000, -4000),
        ("Delta", 4, 0, 10000, 2000, -8000),
    ]


def test_default_is_the_latest_gameweek_even_if_not_final(two_weeks: Session) -> None:
    pool = get_pool(two_weeks, SEASON)
    assert pool is not None and (pool.gameweek, pool.final) == (2, False)
    assert [name for name, *_ in lines(pool)] == ["Alpha", "Charlie", "Bravo", "Delta"]


def test_someone_joining_later_is_only_in_later_pools(two_weeks: Session) -> None:
    assert [name for name, *_ in lines(get_pool(two_weeks, SEASON, 1))] == [
        "Bravo",
        "Alpha",
        "Charlie",
    ]


def test_gameweek_without_points_has_no_pool(seeded: Session, session: Session) -> None:
    assert get_pool(seeded, SEASON, 5) is None
    session.add(t.Season(season_id="2027-28", league_id=99, weekly_buy_in_minor=10000))
    session.commit()
    assert get_pool(session, "2027-28") is None
