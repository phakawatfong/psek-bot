"""The synced fantasy calendar, including days whose points have not arrived yet."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from fantasy_bot.database import tables as t


def days(session: Session, season_id: str) -> list[tuple[int, str, bool]]:
    rows = session.execute(
        select(t.Day.gameweek, t.Day.deadline_time, t.Day.finished)
        .where(t.Day.season_id == season_id)
        .order_by(t.Day.day_id)
    )
    return [(week, deadline, finished) for week, deadline, finished in rows]
