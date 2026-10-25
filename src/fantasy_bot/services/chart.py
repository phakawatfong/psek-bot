from collections import defaultdict

from sqlalchemy.orm import Session

from fantasy_bot.models.chart import GameweekPoints, GameweekSeries, PointsHistory
from fantasy_bot.models.participant import ParticipantId
from fantasy_bot.repositories import participants, points


def get_points_history(session: Session, season_id: str) -> PointsHistory:
    """Every team's season total after each synced day, for the chart by day."""
    return PointsHistory(
        points.daily_totals(session, season_id), points.gameweek_of_day(session, season_id)
    )


def get_gameweek_points(session: Session, season_id: str) -> GameweekPoints:
    """Every team's points in each gameweek, after transfer costs: what decides each pool."""
    weeks = points.pool_weeks(session, season_id)
    names = participants.names(session, season_id)
    by_team: dict[ParticipantId, list[tuple[int, int]]] = defaultdict(list)
    for week in weeks:
        for standing in week.standings:
            by_team[standing.participant_id].append((week.gameweek, standing.points))
    return GameweekPoints(
        series=[
            GameweekSeries(pid, names[pid], [gw for gw, _ in rows], [pts for _, pts in rows])
            for pid, rows in sorted(by_team.items())
        ],
        not_final=[w.gameweek for w in weeks if not w.final],
    )
