import sqlite3

from fantasy_bot.services.money import get_money_summary

SEASON = "2026-27"


def test_ranks_by_latest_total_and_skips_pending(seeded: sqlite3.Connection) -> None:
    result = get_money_summary(seeded, SEASON)
    # 102: 900, 101: 700, 103: 500, 104 never synced: 0. Pending 105 is excluded from the pool.
    assert [
        (line.discord_user_id, s.rank, s.points, s.payout, s.net)
        for line in result
        for s in [line.settlement]
    ] == [
        (12, 1, 900, 2000, 1000),
        (11, 2, 700, 1200, 200),
        (13, 3, 500, 800, -200),
        (14, 4, 0, 0, -1000),
    ]


def test_season_without_participants_is_empty(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO season VALUES ('2027-28', 99, NULL)")
    conn.execute("INSERT INTO payout_rank VALUES ('2027-28', 1, 10000)")
    assert get_money_summary(conn, "2027-28") == []
