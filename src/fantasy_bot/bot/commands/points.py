import sqlite3
from collections.abc import Callable, Coroutine
from typing import Any

import discord
from discord import app_commands

from fantasy_bot.bot.commands.formatting import display_name, points, ranked, split_message
from fantasy_bot.models import DayPoints
from fantasy_bot.services.standings import (
    get_day_points,
    get_day_points_in_week,
    get_gameweek_points,
)


def format_day_points(report: DayPoints | None) -> str:
    if report is None:
        return "No points synced for that day yet."
    status = "final" if report.final else "live, may still change"
    last = report.rows[-1].rank if report.rows else 0
    lines = [
        f"{ranked(r.rank, last)}{display_name(r.name)} {points(r.points)} pts"
        f" (season {points(r.total_points)})"
        for r in report.rows
    ]
    return "\n".join([f"**{report.day_name}** ({status})", *lines])


def format_gameweek_points(days: list[DayPoints]) -> list[str]:
    if not days:
        return ["No points synced for that gameweek yet."]
    return split_message([format_day_points(day) for day in days])


def handler(conn: sqlite3.Connection, season_id: str) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(
        gameweek="Gameweek number; with no day, shows every played day of that week",
        day="Day of the gameweek (1 = its first day); leave both empty for the latest day",
    )
    async def handle(
        interaction: discord.Interaction,
        gameweek: app_commands.Range[int, 1, 30] | None = None,
        day: app_commands.Range[int, 1, 10] | None = None,
    ) -> None:
        if day:
            messages = [format_day_points(get_day_points_in_week(conn, season_id, day, gameweek))]
        elif gameweek:
            messages = format_gameweek_points(get_gameweek_points(conn, season_id, gameweek))
        else:
            messages = [format_day_points(get_day_points(conn, season_id))]
        no_pings = discord.AllowedMentions.none()
        await interaction.response.send_message(messages[0], allowed_mentions=no_pings)
        for message in messages[1:]:
            await interaction.followup.send(message, allowed_mentions=no_pings)

    return handle
