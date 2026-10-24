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


def days_in_gameweek(conn: sqlite3.Connection, season_id: str, gameweek: int) -> list[int]:
    rows = conn.execute(
        "SELECT day_id FROM day WHERE season_id = ? AND gameweek = ? ORDER BY day_id",
        (season_id, gameweek),
    )
    return [day_id for (day_id,) in rows]


def team_codes(conn: sqlite3.Connection, season_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT short_name FROM nba_team WHERE season_id = ? ORDER BY short_name", (season_id,)
    )
    return [code for (code,) in rows]


def gameweek_of(conn: sqlite3.Connection, season_id: str, day_id: int) -> int | None:
    row = conn.execute(
        "SELECT gameweek FROM day WHERE season_id = ? AND day_id = ?", (season_id, day_id)
    ).fetchone()
    return row[0] if row else None


def gameweek_starts_at(conn: sqlite3.Connection, season_id: str, gameweek: int) -> str | None:
    """Deadline of the gameweek's first day: once it passes, the week is under way."""
    starts_at: str | None = conn.execute(
        "SELECT min(deadline_time) FROM day WHERE season_id = ? AND gameweek = ?",
        (season_id, gameweek),
    ).fetchone()[0]
    return starts_at
