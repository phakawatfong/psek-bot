import sqlite3

from fantasy_bot.models import DaySchedule, GameweekSchedule
from fantasy_bot.repositories import schedule
from fantasy_bot.repositories.standings import day_info


def current_gameweek(conn: sqlite3.Connection, season_id: str) -> int | None:
    """The gameweek of the next day not yet finished, else the last gameweek."""
    day_id = schedule.upcoming_day(conn, season_id)
    return schedule.gameweek_of(conn, season_id, day_id) if day_id else None


def get_upcoming_day_schedule(conn: sqlite3.Connection, season_id: str) -> DaySchedule | None:
    """The first day whose games aren't all finished, so a day in progress counts as upcoming."""
    day_id = schedule.upcoming_day(conn, season_id)
    return _day(conn, season_id, day_id) if day_id else None


def get_gameweek_schedule(
    conn: sqlite3.Connection, season_id: str, gameweek: int | None = None
) -> GameweekSchedule | None:
    """Every day of a gameweek (default: the current one) with its games; None if unknown."""
    gameweek = gameweek or current_gameweek(conn, season_id)
    if gameweek is None:
        return None
    days = [_day(conn, season_id, d) for d in schedule.days_in_gameweek(conn, season_id, gameweek)]
    found = [d for d in days if d is not None]
    return GameweekSchedule(gameweek, found) if found else None


def get_day_schedule(
    conn: sqlite3.Connection, season_id: str, day_number: int, gameweek: int | None = None
) -> DaySchedule | None:
    """Day `day_number` (1 = first) of a gameweek (default: the current one); None if unknown."""
    gameweek = gameweek or current_gameweek(conn, season_id)
    days = schedule.days_in_gameweek(conn, season_id, gameweek) if gameweek else []
    return _day(conn, season_id, days[day_number - 1]) if 1 <= day_number <= len(days) else None


def team_codes(conn: sqlite3.Connection, season_id: str) -> list[str]:
    """Short codes of every NBA team, e.g. "ATL"."""
    return schedule.team_codes(conn, season_id)


def _day(conn: sqlite3.Connection, season_id: str, day_id: int) -> DaySchedule | None:
    info = day_info(conn, season_id, day_id)
    if info is None:
        return None
    return DaySchedule(day_id, info[0], schedule.games_for_day(conn, season_id, day_id))
