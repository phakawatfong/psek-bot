import sqlite3
from collections.abc import Callable, Coroutine
from typing import Any

import discord
from discord import app_commands

from fantasy_bot.bot.commands.formatting import display_name, points, ranked
from fantasy_bot.models import StandingRow
from fantasy_bot.services.standings import get_standings


def format_standings(rows: list[StandingRow], gameweek: int | None) -> str:
    title = f"**Gameweek {gameweek} standings**" if gameweek else "**Season standings**"
    if not rows:
        return f"{title}\nNo approved participants yet."
    leader, last = rows[0].points, rows[-1].rank
    lines = [
        f"{ranked(r.rank, last)}{display_name(r.name)} {points(r.points)} pts"
        + (f" (-{points(leader - r.points)})" if r.points < leader else "")
        for r in rows
    ]
    return "\n".join([title, *lines])


def handler(conn: sqlite3.Connection, season_id: str) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(gameweek="Show one gameweek instead of the whole season")
    async def handle(
        interaction: discord.Interaction, gameweek: app_commands.Range[int, 1, 30] | None = None
    ) -> None:
        await interaction.response.send_message(
            format_standings(get_standings(conn, season_id, gameweek), gameweek),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    return handle
