"""The season's money rules, so commands and logs can state them instead of hiding them."""

import sqlite3

from fantasy_bot.models import PoolRules
from fantasy_bot.repositories.seasons import season_rules


def get_rules(conn: sqlite3.Connection, season_id: str) -> PoolRules:
    return season_rules(conn, season_id)


def config_drift(stored: PoolRules, configured: PoolRules) -> list[str]:
    """Plain-words differences between .env and the season's rules, which stay in force."""
    differences = []
    if configured.weekly_buy_in_minor != stored.weekly_buy_in_minor:
        differences.append(
            f"WEEKLY_BUY_IN is {configured.weekly_buy_in_minor / 100:g} in .env, but this"
            f" season uses {stored.weekly_buy_in_minor / 100:g}"
        )
    if configured.split_bp != stored.split_bp:
        differences.append(
            f"PAYOUT_SPLIT is {percentages(configured.split_bp)} in .env, but this season uses"
            f" {percentages(stored.split_bp)}"
        )
    return differences


def percentages(split_bp: tuple[int, ...]) -> str:
    """(5000, 3000, 2000) -> "50/30/20"."""
    return "/".join(f"{bp / 100:g}" for bp in split_bp)
