import discord
from discord import app_commands
from sqlalchemy import Engine

from fantasy_bot.controllers.routes import register_all
from fantasy_bot.database.connection import sessions


def test_every_command_is_prefixed_with_bot_name(engine: Engine) -> None:
    tree = app_commands.CommandTree(discord.Client(intents=discord.Intents.none()))
    register_all(tree, sessions(engine), "2026-27")
    assert [c.name for c in tree.get_commands()] == [
        "psek-nba-standings",
        "psek-nba-money",
        "psek-nba-chart",
        "psek-nba-pool",
        "psek-nba-schedule",
    ]


def test_chart_offers_day_and_gameweek(engine: Engine) -> None:
    tree = app_commands.CommandTree(discord.Client(intents=discord.Intents.none()))
    register_all(tree, sessions(engine), "2026-27")
    chart = tree.get_command("psek-nba-chart")
    assert isinstance(chart, app_commands.Command)
    [by] = chart.parameters
    assert (by.name, [c.value for c in by.choices], by.required) == (
        "by",
        ["day", "gameweek"],
        False,
    )


def test_schedule_offers_optional_positive_gameweek_and_day(engine: Engine) -> None:
    tree = app_commands.CommandTree(discord.Client(intents=discord.Intents.none()))
    register_all(tree, sessions(engine), "2026-27")
    schedule = tree.get_command("psek-nba-schedule")
    assert isinstance(schedule, app_commands.Command)
    assert [(p.name, p.required, p.min_value) for p in schedule.parameters] == [
        ("gameweek", False, 1),
        ("day", False, 1),
    ]
