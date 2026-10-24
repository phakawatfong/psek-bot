import sqlite3

from discord import app_commands

from fantasy_bot.bot.commands import money


def register_all(tree: app_commands.CommandTree, conn: sqlite3.Connection, season_id: str) -> None:
    money.register(tree, conn, season_id)
