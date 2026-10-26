from sqlalchemy import update
from sqlalchemy.orm import Session

from fantasy_bot.database import tables as t
from fantasy_bot.models.money import SeasonMoney
from fantasy_bot.models.prizes import PrizeRule
from fantasy_bot.services.money import get_season_money

SEASON = "2026-27"


def table(money: SeasonMoney) -> list[tuple[str, dict[int, int], int, int, int]]:
    return [
        (r.name.team_name, r.net_by_gameweek, r.total.paid, r.total.won, r.total.net)
        for r in money.rows
    ]


def test_final_week_is_split_50_30_15_5(seeded: Session) -> None:
    # Four teams x 100.00 = 400.00. Echo is in the league but not the pool.
    money = get_season_money(seeded, SEASON, [PrizeRule(1, (50, 30, 15, 5))])
    assert (money.weekly_buy_in, money.gameweeks, money.not_final) == (10000, [1], [])
    assert table(money) == [
        ("Bravo", {1: 10000}, 10000, 20000, 10000),
        ("Alpha", {1: 2000}, 10000, 12000, 2000),
        ("Charlie", {1: -4000}, 10000, 6000, -4000),
        ("Delta", {1: -8000}, 10000, 2000, -8000),
    ]


def test_week_still_being_played_is_named_but_not_counted(two_weeks: Session) -> None:
    money = get_season_money(
        two_weeks, SEASON, [PrizeRule(1, (50, 30, 15)), PrizeRule(2, (50, 30, 15, 5))]
    )
    assert (money.gameweeks, money.not_final) == ([1], [2])
    # Week 1 had three teams (Delta joins in week 2), pool 300.00: 50/30/15 scaled up.
    assert table(money) == [
        ("Bravo", {1: 5789}, 10000, 15789, 5789),
        ("Alpha", {1: -526}, 10000, 9474, -526),
        ("Charlie", {1: -5263}, 10000, 4737, -5263),
    ]


def test_each_gameweek_and_the_total(two_weeks: Session) -> None:
    two_weeks.execute(update(t.Day).where(t.Day.day_id == 3).values(data_checked=True))
    two_weeks.commit()
    money = get_season_money(
        two_weeks, SEASON, [PrizeRule(1, (50, 30, 15)), PrizeRule(2, (50, 30, 15, 5))]
    )
    # Week 2, pool 400.00: Alpha +100, Charlie +20, Bravo -40, Delta -80.
    assert (money.gameweeks, money.not_final) == ([1, 2], [])
    assert table(money) == [
        ("Alpha", {1: -526, 2: 10000}, 20000, 29474, 9474),
        ("Bravo", {1: 5789, 2: -4000}, 20000, 21789, 1789),
        ("Charlie", {1: -5263, 2: 2000}, 20000, 16737, -3263),
        ("Delta", {2: -8000}, 10000, 2000, -8000),
    ]


def test_empty_season(session: Session) -> None:
    session.add(t.Season(season_id="2027-28", league_id=99, weekly_buy_in_minor=10000))
    session.commit()
    assert get_season_money(
        session, "2027-28", [PrizeRule(2, (120, 70, 50, 30, 20, 10))]
    ) == SeasonMoney(10000, [], [], [])
