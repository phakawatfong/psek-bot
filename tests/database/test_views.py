from sqlalchemy import select
from sqlalchemy.orm import Session

from fantasy_bot.database import tables as t


def test_gameweek_view_sums_days(seeded: Session) -> None:
    view = t.entry_gameweek.c
    rows = seeded.execute(
        select(view.entry_id, view.gameweek, view.points, view.days_played).order_by(view.entry_id)
    )
    assert [tuple(r) for r in rows] == [
        (101, 1, 700, 2), (102, 1, 900, 2), (103, 1, 500, 2), (105, 1, 18000, 2)
    ]  # fmt: skip
