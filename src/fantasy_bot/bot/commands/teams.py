"""The team picker shared by register, approve, and paid: type part of a name, pick from a list."""

import sqlite3
from collections.abc import Callable, Coroutine
from typing import Any

import discord
from discord import app_commands

from fantasy_bot.services.registration import find_teams

CHOICE_NAME_LIMIT = 100  # Discord's maximum length for a choice label


def team_autocomplete(
    conn: sqlite3.Connection, season_id: str, status: str | None
) -> Callable[[discord.Interaction, str], Coroutine[Any, Any, list[app_commands.Choice[int]]]]:
    """Dropdown of league teams matching what was typed; `status` limits it to registered ones."""

    async def suggest(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        return [
            app_commands.Choice(
                name=f"{t.entry_name} ({t.manager_name})"[:CHOICE_NAME_LIMIT], value=t.entry_id
            )
            for t in find_teams(conn, season_id, current, status)
        ]

    return suggest
