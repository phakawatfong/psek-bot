import sqlite3
from collections.abc import Sequence

from fantasy_bot.domain.payout import ParticipantId, Standing


class SqliteRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def ensure_season(self, season_id: str, league_id: int, split_bp: Sequence[int]) -> None:
        """Create the season with its payout split once; later calls leave it untouched."""
        with self._conn:
            created = self._conn.execute(
                "INSERT OR IGNORE INTO season VALUES (?, ?, NULL)", (season_id, league_id)
            ).rowcount
            if created:
                self._conn.executemany(
                    "INSERT INTO payout_rank VALUES (?, ?, ?)",
                    [(season_id, rank, bp) for rank, bp in enumerate(split_bp, start=1)],
                )

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

    def discord_user_ids(self, season_id: str) -> dict[ParticipantId, int]:
        rows = self._conn.execute(
            "SELECT participant_id, discord_user_id FROM participant WHERE season_id = ?",
            (season_id,),
        )
        return {ParticipantId(pid): user_id for pid, user_id in rows}
