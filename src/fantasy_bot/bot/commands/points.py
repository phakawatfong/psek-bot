import sqlite3
from collections.abc import Callable, Coroutine
from typing import Any

import discord
from discord import app_commands

from fantasy_bot.bot.commands.formatting import display_name, points
from fantasy_bot.models import DayPoints
from fantasy_bot.services.standings import get_day_points


def format_day_points(report: DayPoints | None) -> str:
    if report is None:
        return "No points synced for that day yet."
    status = "final" if report.final else "live, may still change"
    lines = [
        f"{r.rank}. {display_name(r.name)} {points(r.points)} pts (season {points(r.total_points)})"
        for r in report.rows
    ]
    return "\n".join([f"**{report.day_name}** ({status})", *lines])


def handler(conn: sqlite3.Connection, season_id: str) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(day="nbafantasy day number; leave empty for the latest day")
    async def handle(
        interaction: discord.Interaction, day: app_commands.Range[int, 1, 200] | None = None
    ) -> None:
        await interaction.response.send_message(
            format_day_points(get_day_points(conn, season_id, day)),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    return handle
