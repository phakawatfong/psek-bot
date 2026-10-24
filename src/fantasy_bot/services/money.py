import sqlite3

from fantasy_bot.calculations.payout import settle
from fantasy_bot.models import MoneyLine
from fantasy_bot.repositories import seasons, standings


def get_money_summary(conn: sqlite3.Connection, season_id: str) -> list[MoneyLine]:
    users = standings.discord_user_ids(conn, season_id)
    settlements = settle(
        standings.season_standings(conn, season_id), seasons.payout_split(conn, season_id)
    )
    return [MoneyLine(users[s.participant_id], s) for s in settlements]
