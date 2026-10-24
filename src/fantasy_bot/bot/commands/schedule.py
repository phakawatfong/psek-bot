import sqlite3
from collections.abc import Callable, Coroutine, Mapping
from datetime import datetime
from typing import Any

import discord
from discord import app_commands

from fantasy_bot.bot.commands.formatting import split_message
from fantasy_bot.models import DaySchedule, Game, GameweekSchedule
from fantasy_bot.services.schedule import get_gameweek_schedule, get_schedule


def team(code: str, icons: Mapping[str, str]) -> str:
    """The team's logo emoji (once uploaded) beside its code."""
    return f"{icons[code]} {code}" if code in icons else code


def format_game(game: Game, icons: Mapping[str, str]) -> str:
    # Discord renders <t:...:t> in each reader's own time zone.
    tip_off = f"<t:{int(datetime.fromisoformat(game.kickoff_time).timestamp())}:t>"
    away, home = team(game.away, icons), team(game.home, icons)
    if game.home_score is None or game.away_score is None:
        return f"{tip_off} {away} @ {home}"
    status = "final" if game.finished else "live"
    return f"{tip_off} {away} {game.away_score} @ {home} {game.home_score} ({status})"


def format_day(day: DaySchedule, icons: Mapping[str, str]) -> str:
    games = [format_game(g, icons) for g in day.games] or ["No games synced for this day yet."]
    return "\n".join([f"**{day.day_name}**", *games])


def format_schedule(day: DaySchedule | None, icons: Mapping[str, str]) -> str:
    return format_day(day, icons) if day else "No schedule synced for that day yet."


def format_gameweek(week: GameweekSchedule | None, icons: Mapping[str, str]) -> list[str]:
    """One or more messages: a gameweek's games run past Discord's 2,000-character limit."""
    if week is None:
        return ["No schedule synced for that gameweek yet."]
    return split_message([format_day(day, icons) for day in week.days])


def handler(
    conn: sqlite3.Connection, season_id: str, icons: Mapping[str, str]
) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(
        day="nbafantasy day number; leave empty for the next unfinished day",
        gameweek="Show every day of one gameweek instead",
    )
    async def handle(
        interaction: discord.Interaction,
        day: app_commands.Range[int, 1, 200] | None = None,
        gameweek: app_commands.Range[int, 1, 30] | None = None,
    ) -> None:
        if day and gameweek:
            await interaction.response.send_message(
                "Pick a day or a gameweek, not both.", ephemeral=True
            )
            return
        messages = (
            format_gameweek(get_gameweek_schedule(conn, season_id, gameweek), icons)
            if gameweek
            else [format_schedule(get_schedule(conn, season_id, day), icons)]
        )
        await interaction.response.send_message(messages[0])
        for message in messages[1:]:
            await interaction.followup.send(message)

    return handle
