import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from discord import app_commands
from sqlalchemy import Engine

from fantasy_bot.config.league import LeagueConfig
from fantasy_bot.controllers import schedule
from fantasy_bot.controllers.routes import register_all
from fantasy_bot.database.connection import sessions
from fantasy_bot.discord_bot import FantasyBot


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


def test_schedule_uses_icons_loaded_after_registration(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    tree = app_commands.CommandTree(discord.Client(intents=discord.Intents.none()))
    icons: dict[str, str] = {}
    register_all(tree, sessions(engine), "test", icons)
    icons["AAA"] = "<:nba_AAA:1>"
    monkeypatch.setattr(schedule, "get_schedule", AsyncMock(return_value=[]))
    format_reply = Mock(return_value=["schedule"])
    monkeypatch.setattr(schedule, "format_schedule", format_reply)
    interaction = Mock(response=Mock(defer=AsyncMock()), followup=Mock(send=AsyncMock()))
    command = tree.get_command("psek-nba-schedule")
    assert isinstance(command, app_commands.Command)
    # This route is a plain callback, not a bound cog method (Discord types cover both).
    callback = cast(Callable[..., Coroutine[Any, Any, None]], command.callback)
    asyncio.run(callback(interaction))
    assert format_reply.call_args.args == ([], icons)
    assert format_reply.call_args.args[1] is icons


def test_failed_emoji_setup_still_starts_normal_sync(engine: Engine) -> None:
    bot = FantasyBot(sessions(engine), LeagueConfig(14, "test"), None)
    bot.tree.sync = AsyncMock()  # type: ignore[method-assign]
    bot.fetch_application_emojis = AsyncMock(side_effect=TimeoutError())  # type: ignore[method-assign]
    start = Mock()
    bot.sync_loop.start = start  # type: ignore[method-assign]
    asyncio.run(bot.setup_hook())
    start.assert_called_once()
    assert bot.team_icons == {}
