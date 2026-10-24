import sqlite3
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any

import discord
from discord import app_commands

from fantasy_bot.models import DaySchedule, Game
from fantasy_bot.services.schedule import get_schedule


def format_game(game: Game) -> str:
    # Discord renders <t:...:t> in each reader's own time zone.
    tip_off = f"<t:{int(datetime.fromisoformat(game.kickoff_time).timestamp())}:t>"
    if game.home_score is None or game.away_score is None:
        return f"{tip_off} {game.away} @ {game.home}"
    status = "final" if game.finished else "live"
    return f"{tip_off} {game.away} {game.away_score} @ {game.home} {game.home_score} ({status})"


def format_schedule(day: DaySchedule | None) -> str:
    if day is None:
        return "No schedule synced for that day yet."
    if not day.games:
        return f"**{day.day_name}**\nNo games synced for this day yet."
    return "\n".join([f"**{day.day_name}**", *(format_game(g) for g in day.games)])


def handler(conn: sqlite3.Connection, season_id: str) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(day="nbafantasy day number; leave empty for the next unfinished day")
    async def handle(
        interaction: discord.Interaction, day: app_commands.Range[int, 1, 200] | None = None
    ) -> None:
        await interaction.response.send_message(format_schedule(get_schedule(conn, season_id, day)))

    return handle
