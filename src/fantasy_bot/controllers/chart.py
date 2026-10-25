import asyncio
import io
from collections.abc import Callable, Coroutine
from functools import partial
from typing import Any, Literal

import discord
from discord import app_commands
from sqlalchemy.orm import Session, sessionmaker

from fantasy_bot.services.chart import get_gameweek_points, get_points_history
from fantasy_bot.services.chart_drawing import points_by_gameweek_png, points_race_png


def handler(
    sessions: sessionmaker[Session], season_id: str
) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(
        by="day: season total after each day (default). gameweek: points in each gameweek"
    )
    async def handle(
        interaction: discord.Interaction, by: Literal["day", "gameweek"] = "day"
    ) -> None:
        with sessions() as session:
            draw = _by_day(session, season_id) if by == "day" else _by_gameweek(session, season_id)
        if draw is None:
            await interaction.response.send_message("No points synced yet.")
            return
        # Drawing takes about a second: acknowledge first, draw off the event loop.
        await interaction.response.defer(thinking=True)
        png = await asyncio.to_thread(draw)
        await interaction.followup.send(
            file=discord.File(io.BytesIO(png), filename=f"points-by-{by}.png")
        )

    return handle


def _by_day(session: Session, season_id: str) -> Callable[[], bytes] | None:
    history = get_points_history(session, season_id)
    return partial(points_race_png, history) if history.series else None


def _by_gameweek(session: Session, season_id: str) -> Callable[[], bytes] | None:
    weekly = get_gameweek_points(session, season_id)
    return partial(points_by_gameweek_png, weekly) if weekly.series else None
