import sqlite3

import discord
from discord import app_commands

from fantasy_bot.bot.commands import register_all


def test_every_command_is_prefixed_with_bot_name(conn: sqlite3.Connection) -> None:
    tree = app_commands.CommandTree(discord.Client(intents=discord.Intents.none()))
    register_all(tree, conn, "2026-27", {})
    assert [c.name for c in tree.get_commands()] == [
        "psek-nba-standings",
        "psek-nba-points",
        "psek-nba-chart",
        "psek-nba-schedule",
        "psek-nba-participants",
        "psek-nba-rules",
        "psek-nba-money",
        "psek-nba-register",
        "psek-nba-add",
        "psek-nba-approve",
        "psek-nba-paid",
        "psek-nba-edit",
        "psek-nba-remove",
        "psek-nba-reset",
    ]


def test_only_server_managers_see_admin_commands(conn: sqlite3.Connection) -> None:
    tree = app_commands.CommandTree(discord.Client(intents=discord.Intents.none()))
    register_all(tree, conn, "2026-27", {})
    hidden = {
        c.name
        for c in tree.get_commands()
        if c.default_permissions and c.default_permissions.manage_guild
    }
    assert hidden == {
        "psek-nba-add",
        "psek-nba-approve",
        "psek-nba-paid",
        "psek-nba-edit",
        "psek-nba-remove",
        "psek-nba-reset",
    }
