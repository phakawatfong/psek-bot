from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, update
from sqlalchemy.orm import Session

from fantasy_bot.database import tables as t
from fantasy_bot.database.connection import create, migrate

SEASON = "2026-27"


@pytest.fixture
def engine() -> Engine:
    engine = create(":memory:")
    migrate(engine)
    return engine


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def seeded(session: Session) -> Session:
    """Five league entries over two final days of gameweek 1. Four are participants: 104 has
    no data yet, and 105 (Echo) is in the league but not in the pool.

    The season uses the default weekly buy-in of 100.00. Rows are flushed
    in foreign-key order: the mappings have no relationship()s, so SQLAlchemy doesn't order
    inserts across tables by itself.
    """
    session.add(t.Season(season_id=SEASON, league_id=14, weekly_buy_in_minor=10000))
    session.flush()  # the season first: everything else points at it
    session.add_all(
        t.Day(
            season_id=SEASON,
            day_id=day,
            gameweek=1,
            name=f"Gameweek 1 - Day {day}",
            deadline_time="2026-10-20T18:30:00Z",
            finished=True,
            data_checked=True,
            facts_final=False,
        )
        for day in (1, 2)
    )
    session.add_all(
        t.Entry(
            season_id=SEASON, entry_id=entry, entry_name=name, manager_name="manager", started_day=1
        )
        for entry, name in [
            (101, "Alpha"),
            (102, "Bravo"),
            (103, "Charlie"),
            (104, "Delta"),
            (105, "Echo"),
        ]
    )
    session.flush()  # days and entries, before the facts that point at them
    session.add_all(  # Echo (105) is in the league but not in the pool
        t.Participant(season_id=SEASON, entry_id=entry, joined_gameweek=1)
        for entry in (101, 102, 103, 104)
    )
    day_totals = [  # (entry, day, day points, running total)
        (101, 1, 400, 400), (101, 2, 300, 700),
        (102, 1, 500, 500), (102, 2, 400, 900),
        (103, 1, 200, 200), (103, 2, 300, 500),
        (105, 1, 9000, 9000), (105, 2, 9000, 18000),
    ]  # fmt: skip
    session.add_all(
        t.FactEntryDay(
            season_id=SEASON,
            entry_id=entry,
            day_id=day,
            points=points,
            total_points=total,
            transfers_cost=0,
            points_on_bench=0,
        )
        for entry, day, points, total in day_totals
    )
    session.commit()
    return session


@pytest.fixture
def league(seeded: Session) -> Session:
    """The seeded league plus Foxtrot (106), a league team that isn't in the pool."""
    seeded.add(
        t.Entry(
            season_id=SEASON, entry_id=106, entry_name="Foxtrot", manager_name="fox", started_day=1
        )
    )
    seeded.commit()
    return seeded


@pytest.fixture
def two_weeks(seeded: Session) -> Session:
    """Adds gameweek 2: one day, not final yet. Delta joins from gameweek 2 on."""
    seeded.add(
        t.Day(
            season_id=SEASON,
            day_id=3,
            gameweek=2,
            name="Gameweek 2 - Day 1",
            deadline_time="2026-10-27T18:00:00Z",
            finished=False,
            data_checked=False,
            facts_final=False,
        )
    )
    seeded.flush()
    seeded.add_all(
        t.FactEntryDay(
            season_id=SEASON,
            entry_id=entry,
            day_id=3,
            points=points,
            total_points=total,
            transfers_cost=0,
            points_on_bench=0,
        )
        for entry, points, total in [(101, 600, 1300), (102, 100, 1000), (103, 300, 800)]
    )
    seeded.execute(
        update(t.Participant).where(t.Participant.entry_id == 104).values(joined_gameweek=2)
    )
    seeded.commit()
    return seeded
