import sqlite3

from fantasy_bot.models import PoolRules


def ensure_season(
    conn: sqlite3.Connection, season_id: str, league_id: int, rules: PoolRules
) -> None:
    """Create the season with its money rules once; later calls leave it untouched.

    Money is recomputed from facts on every call, so changing the rules mid-season would
    rewrite every past week.
    """
    with conn:
        created = conn.execute(
            "INSERT OR IGNORE INTO season (season_id, league_id, weekly_buy_in_minor)"
            " VALUES (?, ?, ?)",
            (season_id, league_id, rules.weekly_buy_in_minor),
        ).rowcount
        if created:
            conn.executemany(
                "INSERT INTO payout_rank VALUES (?, ?, ?)",
                [(season_id, rank, bp) for rank, bp in enumerate(rules.split_bp, start=1)],
            )


def season_rules(conn: sqlite3.Connection, season_id: str) -> PoolRules:
    buy_in: int = conn.execute(
        "SELECT weekly_buy_in_minor FROM season WHERE season_id = ?", (season_id,)
    ).fetchone()[0]
    return PoolRules(buy_in, tuple(payout_split(conn, season_id)))


def payout_split(conn: sqlite3.Connection, season_id: str) -> list[int]:
    rows = conn.execute(
        "SELECT share_bp FROM payout_rank WHERE season_id = ? ORDER BY rank", (season_id,)
    )
    return [bp for (bp,) in rows]
