import sqlite3

from fantasy_bot.adapters.sqlite.db import connect, migrate
from fantasy_bot.adapters.sqlite.repository import SqliteRepository
from fantasy_bot.application.services import money_summary

SEASON = "2026-27"


def seeded() -> sqlite3.Connection:
    conn = connect(":memory:")
    migrate(conn)
    conn.execute("INSERT INTO season VALUES (?, 14, NULL)", (SEASON,))
    conn.executemany(
        "INSERT INTO payout_rank VALUES (?, ?, ?)",
        [(SEASON, 1, 5000), (SEASON, 2, 3000), (SEASON, 3, 2000)],
    )
    conn.executemany(
        "INSERT INTO day VALUES (?, ?, 1, ?, '2026-10-20T18:30:00Z', 1, 1)",
        [(SEASON, 1, "Gameweek 1 - Day 1"), (SEASON, 2, "Gameweek 1 - Day 2")],
    )
    entries = [(101, "Alpha"), (102, "Bravo"), (103, "Charlie"), (104, "Delta"), (105, "Echo")]
    conn.executemany(
        "INSERT INTO entry VALUES (?, ?, ?, 'manager')", [(SEASON, e, n) for e, n in entries]
    )
    participants = [  # (discord user, entry, buy-in, status)
        (11, 101, 1000, "approved"),
        (12, 102, 1000, "approved"),
        (13, 103, 1000, "approved"),
        (14, 104, 1000, "approved"),
        (15, 105, 1000, "pending"),
    ]
    conn.executemany(
        "INSERT INTO participant (season_id, discord_user_id, entry_id, buy_in_minor, status,"
        " registered_at) VALUES (?, ?, ?, ?, ?, '2026-10-24T00:00:00Z')",
        [(SEASON, *p) for p in participants],
    )
    day_totals = [  # (entry, day, day points, running total)
        (101, 1, 400, 400), (101, 2, 300, 700),
        (102, 1, 500, 500), (102, 2, 400, 900),
        (103, 1, 200, 200), (103, 2, 300, 500),
        (105, 1, 9000, 9000), (105, 2, 9000, 18000),
    ]  # fmt: skip
    conn.executemany(
        "INSERT INTO fact_entry_day VALUES (?, ?, ?, ?, ?, 0, 0, NULL)",
        [(SEASON, *d) for d in day_totals],
    )
    return conn


def test_money_summary_ranks_by_latest_total_and_skips_pending() -> None:
    result = money_summary(SqliteRepository(seeded()), SEASON)
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


def test_ensure_season_creates_once_and_keeps_existing_split() -> None:
    conn = connect(":memory:")
    migrate(conn)
    repo = SqliteRepository(conn)
    repo.ensure_season("2027-28", 99, [6000, 4000])
    repo.ensure_season("2027-28", 99, [5000, 3000, 2000])
    assert repo.payout_split("2027-28") == [6000, 4000]
    assert money_summary(repo, "2027-28") == []


def test_gameweek_view_sums_days() -> None:
    rows = seeded().execute(
        "SELECT entry_id, gameweek, points, days_played FROM v_entry_gameweek ORDER BY entry_id"
    )
    assert [tuple(r) for r in rows] == [
        (101, 1, 700, 2), (102, 1, 900, 2), (103, 1, 500, 2), (105, 1, 18000, 2)
    ]  # fmt: skip
