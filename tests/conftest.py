import sqlite3

import pytest

from fantasy_bot.repositories.database import connect, migrate

SEASON = "2026-27"


@pytest.fixture
def conn() -> sqlite3.Connection:
    conn = connect(":memory:")
    migrate(conn)
    return conn


@pytest.fixture
def seeded(conn: sqlite3.Connection) -> sqlite3.Connection:
    """Five entries over two final days of gameweek 1; entry 104 has no data, 105 is pending.

    The season uses the default weekly buy-in of 100.00 and a 50/30/20 split.
    """
    conn.execute("INSERT INTO season (season_id, league_id) VALUES (?, 14)", (SEASON,))
    conn.executemany(
        "INSERT INTO payout_rank VALUES (?, ?, ?)",
        [(SEASON, 1, 5000), (SEASON, 2, 3000), (SEASON, 3, 2000)],
    )
    conn.executemany(
        "INSERT INTO day (season_id, day_id, gameweek, name, deadline_time, finished,"
        " data_checked) VALUES (?, ?, 1, ?, '2026-10-20T18:30:00Z', 1, 1)",
        [(SEASON, 1, "Gameweek 1 - Day 1"), (SEASON, 2, "Gameweek 1 - Day 2")],
    )
    entries = [(101, "Alpha"), (102, "Bravo"), (103, "Charlie"), (104, "Delta"), (105, "Echo")]
    conn.executemany(
        "INSERT INTO entry (season_id, entry_id, entry_name, manager_name)"
        " VALUES (?, ?, ?, 'manager')",
        [(SEASON, e, n) for e, n in entries],
    )
    participants = [  # (discord user, entry, status)
        (11, 101, "approved"),
        (12, 102, "approved"),
        (13, 103, "approved"),
        (14, 104, "approved"),
        (15, 105, "pending"),
    ]
    conn.executemany(
        "INSERT INTO participant (season_id, discord_user_id, entry_id, status, registered_at)"
        " VALUES (?, ?, ?, ?, '2026-10-24T00:00:00Z')",
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
