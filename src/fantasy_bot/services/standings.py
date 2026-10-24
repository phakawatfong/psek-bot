import sqlite3

from fantasy_bot.models import DayPoints, StandingRow
from fantasy_bot.repositories import standings


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
