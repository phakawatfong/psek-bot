import sqlite3

from discord import app_commands

from fantasy_bot.bot.commands import money

PREFIX = "psek-nba"


def register_all(tree: app_commands.CommandTree, conn: sqlite3.Connection, season_id: str) -> None:
    """Every slash command the bot exposes. Users type /psek-nba-<name>."""
    routes = [
        # (name, description shown in Discord, handler)
        (
            "money",
            "Show the pool, each payout, and each person's net",
            money.handler(conn, season_id),
        ),
    ]
    for name, description, callback in routes:
        tree.add_command(
            app_commands.Command(
                name=f"{PREFIX}-{name}", description=description, callback=callback
            )
        )
