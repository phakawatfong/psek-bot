import sqlite3

from fantasy_bot.models import ParticipantId, Standing


def season_standings(conn: sqlite3.Connection, season_id: str) -> list[Standing]:
    rows = conn.execute(
        "SELECT participant_id, total_points, buy_in_minor"
        " FROM v_season_standings WHERE season_id = ?",
        (season_id,),
    )
    return [Standing(ParticipantId(pid), points, buy_in) for pid, points, buy_in in rows]


def discord_user_ids(conn: sqlite3.Connection, season_id: str) -> dict[ParticipantId, int]:
    rows = conn.execute(
        "SELECT participant_id, discord_user_id FROM participant WHERE season_id = ?",
        (season_id,),
    )
    return {ParticipantId(pid): user_id for pid, user_id in rows}
