import sqlite3
from collections.abc import Callable, Coroutine, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

import discord
from discord import app_commands

from fantasy_bot.bot.commands.formatting import split_message
from fantasy_bot.models import DaySchedule, Game, GameweekSchedule
from fantasy_bot.services.schedule import (
    get_day_schedule,
    get_gameweek_schedule,
    get_upcoming_day_schedule,
)

# The league plays from Thailand, which has no daylight saving, so a fixed offset is exact.
DISPLAY_TZ = timezone(timedelta(hours=7), "UTC+7")
NOTHING_SYNCED = "No schedule synced yet."


def local(kickoff_time: str) -> datetime:
    return datetime.fromisoformat(kickoff_time).astimezone(DISPLAY_TZ)


def team(code: str, icons: Mapping[str, str]) -> str:
    """The team's logo emoji (once uploaded) beside its code."""
    return f"{icons[code]} {code}" if code in icons else code


def format_game(game: Game, icons: Mapping[str, str], day_date: str) -> str:
    tip_off = local(game.kickoff_time)
    # A game after midnight UTC+7 falls on the next date, so it says which.
    when = tip_off.strftime("%H:%M")
    if tip_off.strftime("%a %d %b") != day_date:
        when = tip_off.strftime("%a %d %b %H:%M")
    away, home = team(game.away, icons), team(game.home, icons)
    if game.home_score is None or game.away_score is None:
        return f"{when} {away} @ {home}"
    status = "final" if game.finished else "live"
    return f"{when} {away} {game.away_score} @ {home} {game.home_score} ({status})"


def format_day(day: DaySchedule, icons: Mapping[str, str]) -> str:
    if not day.games:
        return f"**{day.day_name}**\nNo games synced for this day yet."
    day_date = local(day.games[0].kickoff_time).strftime("%a %d %b")
    games = [format_game(g, icons, day_date) for g in day.games]
    return "\n".join([f"**{day.day_name}** ({day_date}, UTC+7)", *games])


def format_schedule(day: DaySchedule | None, icons: Mapping[str, str]) -> str:
    return format_day(day, icons) if day else "That gameweek has no such day."


def format_gameweek(week: GameweekSchedule | None, icons: Mapping[str, str]) -> list[str]:
    """One or more messages: a gameweek's games run past Discord's 2,000-character limit."""
    if week is None:
        return ["No schedule synced for that gameweek yet."]
    return split_message([format_day(day, icons) for day in week.days])


def handler(
    conn: sqlite3.Connection, season_id: str, icons: Mapping[str, str]
) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(
        gameweek="Gameweek number; with no day, shows the whole week",
        day="Day of the gameweek (1 = its first day); leave both empty for the upcoming day",
    )
    async def handle(
        interaction: discord.Interaction,
        gameweek: app_commands.Range[int, 1, 30] | None = None,
        day: app_commands.Range[int, 1, 10] | None = None,
    ) -> None:
        if day:
            messages = [format_schedule(get_day_schedule(conn, season_id, day, gameweek), icons)]
        elif gameweek:
            messages = format_gameweek(get_gameweek_schedule(conn, season_id, gameweek), icons)
        else:
            day_schedule = get_upcoming_day_schedule(conn, season_id)
            messages = [format_day(day_schedule, icons) if day_schedule else NOTHING_SYNCED]
        await interaction.response.send_message(messages[0])
        for message in messages[1:]:
            await interaction.followup.send(message)

    return handle
