from datetime import datetime

from sqlalchemy.orm import Session

from fantasy_bot.models.standings import GameweekStandings, StandingRow
from fantasy_bot.repositories import participants
from fantasy_bot.services.gameweeks import get_week


def get_standings(
    session: Session, season_id: str, gameweek: int | None = None, *, now: datetime | None = None
) -> GameweekStandings:
    """Eligible participants ranked by this gameweek's points, after transfer costs."""
    week = get_week(session, season_id, gameweek, now)
    names = participants.names(session, season_id)
    ordered = sorted(week.standings, key=lambda s: (-s.points, s.participant_id))
    rows = []
    rank = 1
    for position, standing in enumerate(ordered, start=1):
        if position == 1 or standing.points != ordered[position - 2].points:
            rank = position
        rows.append(StandingRow(rank, names[standing.participant_id], standing.points))
    return GameweekStandings(week.gameweek, week.final, rows)
