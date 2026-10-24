import sqlite3
from collections.abc import Sequence


def ensure_season(
    conn: sqlite3.Connection,
    season_id: str,
    league_id: int,
    split_bp: Sequence[int],
    weekly_buy_in_minor: int,
) -> None:
    """Create the season with its payout split and weekly buy-in once.

    Later calls leave an existing season untouched: money is recomputed from facts on every
    call, so changing these mid-season would rewrite every past week.
    """
    with conn:
        created = conn.execute(
            "INSERT OR IGNORE INTO season (season_id, league_id, weekly_buy_in_minor)"
            " VALUES (?, ?, ?)",
            (season_id, league_id, weekly_buy_in_minor),
        ).rowcount
        if created:
            conn.executemany(
                "INSERT INTO payout_rank VALUES (?, ?, ?)",
                [(season_id, rank, bp) for rank, bp in enumerate(split_bp, start=1)],
            )


def payout_split(conn: sqlite3.Connection, season_id: str) -> list[int]:
    rows = conn.execute(
        "SELECT share_bp FROM payout_rank WHERE season_id = ? ORDER BY rank", (season_id,)
    )
    return [bp for (bp,) in rows]
