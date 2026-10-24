import sqlite3
from itertools import groupby

from fantasy_bot.models import ParticipantId, PoolWeek, Standing


def pool_weeks(conn: sqlite3.Connection, season_id: str) -> list[PoolWeek]:
    """Every gameweek with synced points, oldest first, with its pool's standings."""
    rows = conn.execute(
        "SELECT gameweek, final, participant_id, points, buy_in_minor FROM v_gameweek_pool"
        " WHERE season_id = ? ORDER BY gameweek, participant_id",
        (season_id,),
    ).fetchall()
    return [
        PoolWeek(
            gameweek,
            bool(week[0][1]),
            [Standing(ParticipantId(pid), points, buy_in) for _, _, pid, points, buy_in in week],
        )
        for gameweek, group in groupby(rows, key=lambda r: r[0])
        for week in [list(group)]
    ]


def weekly_buy_in(conn: sqlite3.Connection, season_id: str) -> int:
    amount: int = conn.execute(
        "SELECT weekly_buy_in_minor FROM season WHERE season_id = ?", (season_id,)
    ).fetchone()[0]
    return amount
