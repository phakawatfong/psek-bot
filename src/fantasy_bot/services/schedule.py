import sqlite3

from fantasy_bot.models import DaySchedule
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
