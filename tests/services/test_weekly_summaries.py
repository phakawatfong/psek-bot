from datetime import UTC, datetime

import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session

from fantasy_bot.database import tables as t
from fantasy_bot.models.prizes import PrizeRule
from fantasy_bot.services.gameweeks import GameweekError, get_week, resolve_gameweek
from fantasy_bot.services.money import get_season_money
from fantasy_bot.services.pool import get_pool
from fantasy_bot.services.prize_rules import PrizeError
from fantasy_bot.services.standings import get_standings

SEASON = "test"
RULES = [PrizeRule(2, (120, 70, 50, 30, 20, 10))]


@pytest.fixture
def six_people(session: Session) -> Session:
    session.add(t.Season(season_id=SEASON, league_id=1, weekly_buy_in_minor=5000))
    session.flush()
    session.add_all(
        t.Day(
            season_id=SEASON,
            day_id=week,
            gameweek=week,
            name=f"Week {week}",
            deadline_time=stamp,
            finished=week < 3,
            data_checked=week < 3,
            facts_final=False,
        )
        for week, stamp in [
            (1, "2026-10-20T22:30:00Z"),
            (2, "2026-10-27T22:30:00Z"),
            (3, "2026-11-03T22:30:00Z"),
        ]
    )
    session.add_all(
        t.Entry(
            season_id=SEASON, entry_id=i, entry_name=f"Team {i}", manager_name="", started_day=1
        )
        for i in range(1, 7)
    )
    session.flush()
    session.add_all(
        t.Participant(season_id=SEASON, entry_id=i, joined_gameweek=2) for i in range(1, 7)
    )
    session.add_all(
        t.FactEntryDay(
            season_id=SEASON,
            entry_id=i,
            day_id=week,
            points=(7 - i) * 100 if week < 3 else i * 100,
            total_points=10000 - i,
            transfers_cost=0,
            points_on_bench=0,
        )
        for week in range(1, 4)
        for i in range(1, 7)
    )
    session.commit()
    return session


def test_gw1_excluded_and_gw2_pays_agreed_amounts(six_people: Session) -> None:
    with pytest.raises(GameweekError, match="eligible participants for gameweek 1"):
        get_pool(six_people, SEASON, RULES, 1)
    pool = get_pool(six_people, SEASON, RULES, 2)
    assert pool.final
    assert [line.settlement.payout for line in pool.lines] == [12000, 7000, 5000, 3000, 2000, 1000]
    season = get_season_money(six_people, SEASON, RULES)
    assert season.gameweeks == [2] and season.not_final == [3]
    assert sum(row.total.paid for row in season.rows) == 30000


def test_weekly_standings_use_that_weeks_points_not_season_totals(six_people: Session) -> None:
    result = get_standings(six_people, SEASON, 3)
    assert not result.final and result.gameweek == 3
    assert [r.name.team_name for r in result.rows] == [f"Team {i}" for i in range(6, 0, -1)]
    # Transfer costs change weekly ranking and ties.
    six_people.execute(
        update(t.FactEntryDay)
        .where(t.FactEntryDay.day_id == 3, t.FactEntryDay.entry_id == 6)
        .values(transfers_cost=100)
    )
    result = get_standings(six_people, SEASON, 3)
    assert [r.rank for r in result.rows] == [1, 1, 3, 4, 5, 6]
    assert result.rows[0].points == 500


def test_only_final_weeks_accumulate(six_people: Session) -> None:
    before = get_season_money(six_people, SEASON, RULES)
    assert all(row.total.weeks == 1 for row in before.rows)
    six_people.execute(update(t.Day).where(t.Day.day_id == 3).values(data_checked=True))
    after = get_season_money(six_people, SEASON, RULES)
    assert after.gameweeks == [2, 3] and after.not_final == []
    assert all(row.total.weeks == 2 and row.total.paid == 10000 for row in after.rows)
    assert sum(row.total.net for row in after.rows) == 0
    assert {r.name.team_name: r.total.net for r in after.rows} == {
        "Team 1": 3000,
        "Team 2": -1000,
        "Team 3": -2000,
        "Team 4": -2000,
        "Team 5": -1000,
        "Team 6": 3000,
    }


def test_new_effective_rule_changes_only_its_weeks(six_people: Session) -> None:
    first = get_pool(six_people, SEASON, RULES, 2)
    changed = [*RULES, PrizeRule(3, (1, 1, 1, 1, 1, 1))]
    assert get_pool(six_people, SEASON, changed, 2) == first
    assert [line.settlement.payout for line in get_pool(six_people, SEASON, changed, 3).lines] == [
        5000
    ] * 6


def test_seventh_participant_requires_rule_starting_that_week(six_people: Session) -> None:
    six_people.add(
        t.Entry(season_id=SEASON, entry_id=7, entry_name="Team 7", manager_name="", started_day=3)
    )
    six_people.flush()
    six_people.add(t.Participant(season_id=SEASON, entry_id=7, joined_gameweek=3))
    six_people.flush()
    with pytest.raises(PrizeError, match="7 eligible participants"):
        get_pool(six_people, SEASON, RULES, 3)
    changed = [*RULES, PrizeRule(3, (7, 6, 5, 4, 3, 2, 1))]
    assert len(get_pool(six_people, SEASON, changed, 2).lines) == 6
    next_pool = get_pool(six_people, SEASON, changed, 3)
    assert len(next_pool.lines) == 7
    assert sum(line.settlement.payout for line in next_pool.lines) == 35000
    assert all(line.settlement.payout > 0 for line in next_pool.lines)


@pytest.mark.parametrize(
    ("stamp", "week"),
    [
        ("2026-10-19T00:00:00Z", 1),
        ("2026-10-27T22:29:59Z", 1),
        ("2026-10-27T22:30:00Z", 2),
        ("2026-10-28T05:30:00+07:00", 2),
        ("2026-11-03T22:30:00Z", 3),
    ],
)
def test_current_week_uses_fantasy_deadline(six_people: Session, stamp: str, week: int) -> None:
    assert resolve_gameweek(six_people, SEASON, None, datetime.fromisoformat(stamp)) == week


def test_missing_current_week_points_never_falls_back(six_people: Session) -> None:
    six_people.add(
        t.Day(
            season_id=SEASON,
            day_id=4,
            gameweek=4,
            name="Week 4",
            deadline_time="2026-11-10T22:30:00Z",
            finished=False,
            data_checked=False,
            facts_final=False,
        )
    )
    six_people.flush()
    with pytest.raises(GameweekError, match="gameweek 4"):
        get_week(six_people, SEASON, None, datetime(2026, 11, 11, tzinfo=UTC))


def test_end_of_season_requires_explicit_week(six_people: Session) -> None:
    six_people.execute(update(t.Day).values(finished=True))
    with pytest.raises(GameweekError, match="season has ended"):
        resolve_gameweek(six_people, SEASON, None, datetime(2026, 12, 1, tzinfo=UTC))
    assert get_week(six_people, SEASON, 2).gameweek == 2
