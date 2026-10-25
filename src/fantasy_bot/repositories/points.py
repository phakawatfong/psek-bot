"""Points as the friends see them: the season table, totals per day, and each gameweek's pool."""

from itertools import groupby

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from fantasy_bot.database import tables as t
from fantasy_bot.database.queries import ENTRY_OF_PARTICIPANT, MANAGER_NAME, TEAM_NAME
from fantasy_bot.models.chart import PointsSeries
from fantasy_bot.models.money import PoolWeek, Standing
from fantasy_bot.models.participant import ParticipantId, ParticipantName
from fantasy_bot.models.standings import StandingRow


def season_table(session: Session, season_id: str) -> list[StandingRow]:
    standings = t.season_standings
    points = standings.c.total_points
    rows = session.execute(
        select(func.rank().over(order_by=points.desc()), TEAM_NAME, MANAGER_NAME, points)
        .select_from(t.Participant)
        .outerjoin(t.Entry, ENTRY_OF_PARTICIPANT)
        .join(standings, standings.c.participant_id == t.Participant.participant_id)
        .where(standings.c.season_id == season_id)
        .order_by(points.desc(), TEAM_NAME)
    )
    return [
        StandingRow(rank, ParticipantName(team, manager), pts) for rank, team, manager, pts in rows
    ]


def daily_totals(session: Session, season_id: str) -> list[PointsSeries]:
    """Each team's season total after every synced day, in participant order."""
    day = t.FactEntryDay
    rows = session.execute(
        select(t.Participant.participant_id, TEAM_NAME, MANAGER_NAME, day.day_id, day.total_points)
        .select_from(t.Participant)
        .outerjoin(t.Entry, ENTRY_OF_PARTICIPANT)
        .join(
            day,
            and_(day.season_id == t.Participant.season_id, day.entry_id == t.Participant.entry_id),
        )
        .where(t.Participant.season_id == season_id)
        .order_by(t.Participant.participant_id, day.day_id)
    ).all()
    return [
        PointsSeries(
            ParticipantId(pid),
            ParticipantName(group[0][1], group[0][2]),
            [day_id for *_, day_id, _ in group],
            [total for *_, total in group],
        )
        for pid, rows_of_pid in groupby(rows, key=lambda r: r[0])
        for group in [list(rows_of_pid)]
    ]


def gameweek_of_day(session: Session, season_id: str) -> dict[int, int]:
    rows = session.execute(select(t.Day.day_id, t.Day.gameweek).where(t.Day.season_id == season_id))
    return {day_id: gameweek for day_id, gameweek in rows}


def pool_weeks(session: Session, season_id: str) -> list[PoolWeek]:
    """Every gameweek with synced points, oldest first, with its pool's standings."""
    pool = t.gameweek_pool.c
    rows = session.execute(
        select(pool.gameweek, pool.final, pool.participant_id, pool.points, pool.buy_in_minor)
        .where(pool.season_id == season_id)
        .order_by(pool.gameweek, pool.participant_id)
    ).all()
    return [
        PoolWeek(
            gameweek,
            bool(week[0][1]),
            [Standing(ParticipantId(pid), points, buy_in) for _, _, pid, points, buy_in in week],
        )
        for gameweek, group in groupby(rows, key=lambda r: r[0])
        for week in [list(group)]
    ]
