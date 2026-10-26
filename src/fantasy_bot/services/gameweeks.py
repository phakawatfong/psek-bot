"""Resolve weekly commands from fantasy deadlines, never from the latest points."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from fantasy_bot.models.money import PoolWeek
from fantasy_bot.repositories import calendar, points


class GameweekError(ValueError):
    """An unavailable week or missing data, safe to show in Discord."""


def resolve_gameweek(
    session: Session, season_id: str, gameweek: int | None, now: datetime | None = None
) -> int:
    days = sorted(
        (
            (week, datetime.fromisoformat(deadline), final)
            for week, deadline, final in calendar.days(session, season_id)
        ),
        key=lambda row: row[1],
    )
    if not days:
        raise GameweekError("No fantasy calendar synced yet. Please try after the next sync.")
    if gameweek is not None:
        if gameweek not in {week for week, _, _ in days}:
            raise GameweekError(f"Gameweek {gameweek} is not in the synced fantasy calendar.")
        return gameweek
    now = now or datetime.now(UTC)
    if now >= days[-1][1] and days[-1][2]:
        raise GameweekError("The fantasy season has ended. Choose a gameweek explicitly.")
    return next((week for week, deadline, _ in reversed(days) if deadline <= now), days[0][0])


def get_week(
    session: Session, season_id: str, gameweek: int | None, now: datetime | None = None
) -> PoolWeek:
    selected = resolve_gameweek(session, season_id, gameweek, now)
    week = next((w for w in points.pool_weeks(session, season_id) if w.gameweek == selected), None)
    if week is None:
        raise GameweekError(
            f"No synced points or eligible participants for gameweek {selected} yet."
        )
    return week
