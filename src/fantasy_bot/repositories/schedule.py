import sqlite3

from fantasy_bot.models import Game


def upcoming_day(conn: sqlite3.Connection, season_id: str) -> int | None:
    """The first day whose games aren't all finished, else the last day."""
    day_id: int | None = conn.execute(
        "SELECT COALESCE("
        " (SELECT min(day_id) FROM day WHERE season_id = ?1 AND NOT finished),"
        " (SELECT max(day_id) FROM day WHERE season_id = ?1))",
        (season_id,),
    ).fetchone()[0]
    return day_id


def games_for_day(conn: sqlite3.Connection, season_id: str, day_id: int) -> list[Game]:
    rows = conn.execute(
        "SELECT f.kickoff_time, h.short_name, a.short_name, f.home_score, f.away_score, f.finished"
        " FROM fixture f"
        " JOIN nba_team h ON h.season_id = f.season_id AND h.team_id = f.home_team_id"
        " JOIN nba_team a ON a.season_id = f.season_id AND a.team_id = f.away_team_id"
        " WHERE f.season_id = ? AND f.day_id = ? ORDER BY f.kickoff_time, h.short_name",
        (season_id, day_id),
    )
    return [
        Game(kickoff, home, away, hs, aws, bool(done))
        for kickoff, home, away, hs, aws, done in rows
    ]
