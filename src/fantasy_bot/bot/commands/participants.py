import sqlite3
from collections.abc import Callable, Coroutine
from typing import Any

import discord

from fantasy_bot.bot.commands.formatting import display_name
from fantasy_bot.models import ParticipantRow
from fantasy_bot.services.participants import list_participants


def format_participants(rows: list[ParticipantRow]) -> str:
    if not rows:
        return "Nobody has registered yet."
    lines = [
        f"- {display_name(r.name)}" + (" (pending approval)" if r.status == "pending" else "")
        for r in rows
    ]
    return "\n".join([f"**Participants ({len(rows)})**", *lines])


def handler(
    conn: sqlite3.Connection, season_id: str
) -> Callable[[discord.Interaction], Coroutine[Any, Any, None]]:
    async def handle(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            format_participants(list_participants(conn, season_id)),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    return handle
