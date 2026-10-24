import sqlite3

from fantasy_bot.services.money import get_money_summary

SEASON = "2026-27"


def test_ranks_by_latest_total_and_skips_pending(seeded: sqlite3.Connection) -> None:
    result = get_money_summary(seeded, SEASON)
    # Bravo: 900, Alpha: 700, Charlie: 500, Delta never synced: 0. Pending Echo is not in the pool.
    assert [
        (line.name.team_name, s.rank, s.points, s.payout, s.net)
        for line in result
        for s in [line.settlement]
    ] == [
        ("Bravo", 1, 900, 2000, 1000),
        ("Alpha", 2, 700, 1200, 200),
        ("Charlie", 3, 500, 800, -200),
        ("Delta", 4, 0, 0, -1000),
    ]


def test_entry_not_synced_yet_is_named_by_id(seeded: sqlite3.Connection) -> None:
    seeded.execute("DELETE FROM entry WHERE entry_id = 104")
    names = [line.name.team_name for line in get_money_summary(seeded, SEASON)]
    assert names == ["Bravo", "Alpha", "Charlie", "entry 104"]


def test_season_without_participants_is_empty(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO season VALUES ('2027-28', 99, NULL)")
    conn.execute("INSERT INTO payout_rank VALUES ('2027-28', 1, 10000)")
    assert get_money_summary(conn, "2027-28") == []
