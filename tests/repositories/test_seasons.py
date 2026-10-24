import sqlite3

from fantasy_bot.repositories.pool import weekly_buy_in
from fantasy_bot.repositories.seasons import ensure_season, payout_split


def test_ensure_season_creates_once_and_never_changes_money_rules(
    conn: sqlite3.Connection,
) -> None:
    ensure_season(conn, "2027-28", 99, [6000, 4000], 10000)
    ensure_season(conn, "2027-28", 99, [5000, 3000, 2000], 20000)
    assert (payout_split(conn, "2027-28"), weekly_buy_in(conn, "2027-28")) == ([6000, 4000], 10000)
