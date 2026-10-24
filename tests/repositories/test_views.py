import sqlite3


def test_gameweek_view_sums_days(seeded: sqlite3.Connection) -> None:
    rows = seeded.execute(
        "SELECT entry_id, gameweek, points, days_played FROM v_entry_gameweek ORDER BY entry_id"
    )
    assert [tuple(r) for r in rows] == [
        (101, 1, 700, 2), (102, 1, 900, 2), (103, 1, 500, 2), (105, 1, 18000, 2)
    ]  # fmt: skip
