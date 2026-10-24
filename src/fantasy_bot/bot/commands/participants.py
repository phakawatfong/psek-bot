import sqlite3
from collections.abc import Callable, Coroutine
from typing import Any

import discord

from fantasy_bot.bot.commands.formatting import display_name
from fantasy_bot.models import PLACEHOLDER_MAX_ID, ParticipantRow
from fantasy_bot.services.participants import list_participants

GROUPS = [
    ("approved", "In the pool"),
    ("pending", "Waiting for approval"),
    ("unregistered", "Not registered yet"),
]


def owner(row: ParticipantRow) -> str:
    """Who registered the team. <@id> shows their name; the reply turns off pings."""
    if row.discord_user_id is None:
        return ""
    if row.discord_user_id < PLACEHOLDER_MAX_ID:
        return ", not linked to Discord yet"
    return f", <@{row.discord_user_id}>"


def format_participants(rows: list[ParticipantRow]) -> str:
    if not rows:
        return "No teams yet: the league's teams appear after the first sync."
    blocks = [
        "\n".join([f"**{title}**", *(f"- {display_name(r.name)}{owner(r)}" for r in group)])
        for status, title in GROUPS
        if (group := [r for r in rows if r.status == status])
    ]
    return "\n\n".join(blocks)


def handler(
    conn: sqlite3.Connection, season_id: str
) -> Callable[[discord.Interaction], Coroutine[Any, Any, None]]:
    async def handle(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            format_participants(list_participants(conn, season_id)),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    return handle
