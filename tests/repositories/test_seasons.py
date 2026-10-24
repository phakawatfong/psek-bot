import sqlite3

from fantasy_bot.models import PoolRules
from fantasy_bot.repositories.pool import weekly_buy_in
from fantasy_bot.repositories.seasons import ensure_season, payout_split, season_rules


def test_ensure_season_creates_once_and_never_changes_money_rules(
    conn: sqlite3.Connection,
) -> None:
    ensure_season(conn, "2027-28", 99, PoolRules(10000, (6000, 4000)))
    ensure_season(conn, "2027-28", 99, PoolRules(20000, (5000, 3000, 2000)))
    assert (payout_split(conn, "2027-28"), weekly_buy_in(conn, "2027-28")) == ([6000, 4000], 10000)


def test_season_rules_read_back_as_stored(conn: sqlite3.Connection) -> None:
    ensure_season(conn, "2027-28", 99, PoolRules(5050, (6000, 2500, 1500)))
    assert season_rules(conn, "2027-28") == PoolRules(5050, (6000, 2500, 1500))
