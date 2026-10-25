"""The schedule reply: fantasy days with tip-off times in Bangkok."""

from collections.abc import Callable, Coroutine
from typing import Any
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from sqlalchemy.orm import Session, sessionmaker

from fantasy_bot.models.schedule import ScheduleDay, ScheduleGame
from fantasy_bot.services.schedule import ScheduleError, get_schedule

BANGKOK = ZoneInfo("Asia/Bangkok")


def format_schedule(days: list[ScheduleDay], team_icons: dict[str, str] | None = None) -> list[str]:
    """Split at lines so a whole week fits in Discord without dropping games."""
    lines = ["**NBA schedule — Bangkok time (UTC+7)**"]
    for day in days:
        upcoming = " (upcoming)" if day.upcoming else ""
        lines.extend(["", f"**Gameweek {day.gameweek} · Day {day.day}**{upcoming}"])
        lines.extend(_game_line(game, team_icons or {}) for game in day.games)
        if not day.games:
            lines.append("No games listed for this fantasy day.")
    messages: list[str] = []
    message = ""
    for line in lines:
        # Team abbreviations come from an external API; cap a line even if that data is bad.
        line = line[:1900]
        if len(message) + len(line) + 1 > 2000:
            messages.append(message)
            message = "**NBA schedule — continued (Bangkok time)**"
        message = f"{message}\n{line}" if message else line
    if message:
        messages.append(message)
    return messages


def _game_line(game: ScheduleGame, team_icons: dict[str, str]) -> str:
    when = (
        game.kickoff.astimezone(BANGKOK).strftime("%d %b %Y %H:%M") if game.kickoff else "Time TBD"
    )
    away = discord.utils.escape_markdown(game.away_team)
    home = discord.utils.escape_markdown(game.home_team)
    if icon := team_icons.get(game.away_team):
        away = f"{icon} {away}"
    if icon := team_icons.get(game.home_team):
        home = f"{icon} {home}"
    score = ""
    if game.finished:
        score = (
            f" — Final {game.away_score}-{game.home_score}"
            if game.away_score is not None and game.home_score is not None
            else " — Final"
        )
    return f"{when} · {away} @ {home}{score}"


def handler(
    sessions: sessionmaker[Session], season_id: str, team_icons: dict[str, str] | None = None
) -> Callable[..., Coroutine[Any, Any, None]]:
    # Match the routes table's controller signature; this command only reads the public API.
    @app_commands.describe(
        gameweek="Fantasy gameweek (default: current; gameweek alone shows every day)",
        day="Day within the gameweek (default with no options: current fantasy day)",
    )
    async def handle(
        interaction: discord.Interaction,
        gameweek: app_commands.Range[int, 1] | None = None,
        day: app_commands.Range[int, 1] | None = None,
    ) -> None:
        await interaction.response.defer(thinking=True)
        try:
            messages = format_schedule(await get_schedule(gameweek, day), team_icons)
        except ScheduleError as error:
            messages = [str(error)]
        for message in messages:
            await interaction.followup.send(
                message, allowed_mentions=discord.AllowedMentions.none()
            )

    return handle
