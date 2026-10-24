import sqlite3

from fantasy_bot.domain.payout import ParticipantId, Standing


class SqliteRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def season_standings(self, season_id: str) -> list[Standing]:
        rows = self._conn.execute(
            "SELECT participant_id, total_points, buy_in_minor"
            " FROM v_season_standings WHERE season_id = ?",
            (season_id,),
        )
        return [Standing(ParticipantId(pid), points, buy_in) for pid, points, buy_in in rows]

    def payout_split(self, season_id: str) -> list[int]:
        rows = self._conn.execute(
            "SELECT share_bp FROM payout_rank WHERE season_id = ? ORDER BY rank", (season_id,)
        )
        return [bp for (bp,) in rows]
