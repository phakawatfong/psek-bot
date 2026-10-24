import sqlite3

from fantasy_bot.models import DayPoints, PointsHistory, StandingRow
from fantasy_bot.repositories import schedule, standings
from fantasy_bot.services.schedule import current_gameweek


def get_standings(
    conn: sqlite3.Connection, season_id: str, gameweek: int | None = None
) -> list[StandingRow]:
    """Season standings, or one gameweek's when `gameweek` is given. Best first."""
    if gameweek is None:
        return standings.season_table(conn, season_id)
    return standings.gameweek_table(conn, season_id, gameweek)


def get_day_points(
    conn: sqlite3.Connection, season_id: str, day_id: int | None = None
) -> DayPoints | None:
    """Each team's points on `day_id` (default: the latest synced day); None if no such day."""
    day_id = day_id or standings.latest_synced_day(conn, season_id)
    info = standings.day_info(conn, season_id, day_id) if day_id else None
    if day_id is None or info is None:
        return None
    name, final = info
    return DayPoints(day_id, name, final, standings.day_table(conn, season_id, day_id))


def get_day_points_in_week(
    conn: sqlite3.Connection, season_id: str, day_number: int, gameweek: int | None = None
) -> DayPoints | None:
    """Points on day `day_number` (1 = first) of a gameweek (default: the current one).

    None if the gameweek has no such day or its points aren't synced yet.
    """
    days = _synced_days_in(conn, season_id, gameweek)
    if not 1 <= day_number <= len(days):
        return None
    return get_day_points(conn, season_id, days[day_number - 1])


def get_gameweek_points(
    conn: sqlite3.Connection, season_id: str, gameweek: int | None = None
) -> list[DayPoints]:
    """Each synced day of a gameweek (default: the current one), oldest first."""
    days = [get_day_points(conn, season_id, d) for d in _synced_days_in(conn, season_id, gameweek)]
    return [d for d in days if d is not None]


def _synced_days_in(conn: sqlite3.Connection, season_id: str, gameweek: int | None) -> list[int]:
    """The gameweek's days that already have points, in order."""
    gameweek = gameweek or current_gameweek(conn, season_id)
    latest = standings.latest_synced_day(conn, season_id)
    if gameweek is None or latest is None:
        return []
    return [d for d in schedule.days_in_gameweek(conn, season_id, gameweek) if d <= latest]


def get_points_history(conn: sqlite3.Connection, season_id: str) -> PointsHistory:
    """Every approved team's season total after each synced day, for the points chart."""
    return PointsHistory(
        standings.daily_totals(conn, season_id), standings.gameweek_of_day(conn, season_id)
    )
