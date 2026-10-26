"""One gameweek's pool: who put in what, and who wins what."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import Session

from fantasy_bot.models.pool import Pool, PoolLine
from fantasy_bot.models.prizes import PrizeRule
from fantasy_bot.repositories import participants
from fantasy_bot.services.gameweeks import get_week
from fantasy_bot.services.prize_rules import weights_for
from fantasy_bot.services.prizes import settle


def get_pool(
    session: Session,
    season_id: str,
    rules: Sequence[PrizeRule],
    gameweek: int | None = None,
    *,
    now: datetime | None = None,
) -> Pool:
    """The selected week's pool, defaulting to the current fantasy gameweek."""
    week = get_week(session, season_id, gameweek, now)
    weights = weights_for(rules, week.gameweek, len(week.standings))
    names = participants.names(session, season_id)
    lines = [PoolLine(names[s.participant_id], s) for s in settle(week.standings, weights)]
    return Pool(week.gameweek, week.final, lines)
