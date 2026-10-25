from sqlalchemy.orm import Session

from fantasy_bot.models.standings import StandingRow
from fantasy_bot.repositories import points


def get_standings(session: Session, season_id: str) -> list[StandingRow]:
    """Every team in the pool, 1st to last, by season points."""
    return points.season_table(session, season_id)
