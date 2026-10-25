"""One gameweek's pool: who put in what, and who wins what."""

from sqlalchemy.orm import Session

from fantasy_bot.models.pool import Pool, PoolLine
from fantasy_bot.repositories import participants, points
from fantasy_bot.services.prizes import settle


def get_pool(session: Session, season_id: str, gameweek: int | None = None) -> Pool | None:
    """That gameweek's pool, or the latest one with points; None if it has no points yet."""
    weeks = points.pool_weeks(session, season_id)
    if gameweek is not None:
        weeks = [w for w in weeks if w.gameweek == gameweek]
    if not weeks:
        return None
    week = weeks[-1]
    names = participants.names(session, season_id)
    lines = [PoolLine(names[s.participant_id], s) for s in settle(week.standings)]
    return Pool(week.gameweek, week.final, lines)
