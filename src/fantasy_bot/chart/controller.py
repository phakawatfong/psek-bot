import asyncio
import io
import sqlite3
from collections.abc import Callable, Coroutine
from typing import Any

import discord

from fantasy_bot.bot.charts import points_race_png
from fantasy_bot.services.standings import get_points_history


def handler(
    conn: sqlite3.Connection, season_id: str
) -> Callable[[discord.Interaction], Coroutine[Any, Any, None]]:
    async def handle(interaction: discord.Interaction) -> None:
        history = get_points_history(conn, season_id)
        if not history.series:
            await interaction.response.send_message("No points synced yet.")
            return
        # Drawing takes about a second: acknowledge first, draw off the event loop.
        await interaction.response.defer(thinking=True)
        png = await asyncio.to_thread(points_race_png, history)
        await interaction.followup.send(
            file=discord.File(io.BytesIO(png), filename="points-race.png")
        )

    return handle
