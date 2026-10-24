import sqlite3

from fantasy_bot.models import DaySchedule, GameweekSchedule
from fantasy_bot.repositories import schedule
from fantasy_bot.repositories.standings import day_info


def get_schedule(
    conn: sqlite3.Connection, season_id: str, day_id: int | None = None
) -> DaySchedule | None:
    """NBA games on `day_id` (default: the next day not yet finished); None if no such day."""
    day_id = day_id or schedule.upcoming_day(conn, season_id)
    info = day_info(conn, season_id, day_id) if day_id else None
    if day_id is None or info is None:
        return None
    return DaySchedule(day_id, info[0], schedule.games_for_day(conn, season_id, day_id))


def get_gameweek_schedule(
    conn: sqlite3.Connection, season_id: str, gameweek: int
) -> GameweekSchedule | None:
    """Every day of a gameweek with its games; None if the gameweek doesn't exist."""
    days = [
        get_schedule(conn, season_id, d)
        for d in schedule.days_in_gameweek(conn, season_id, gameweek)
    ]
    if not days:
        return None
    return GameweekSchedule(gameweek, [d for d in days if d is not None])


def team_codes(conn: sqlite3.Connection, season_id: str) -> list[str]:
    """Short codes of every NBA team, e.g. "ATL"."""
    return schedule.team_codes(conn, season_id)
