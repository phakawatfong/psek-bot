"""Admin-only commands.

Discord decides who may use them, on its own servers, before a command reaches the bot. By
default that's members with the Manage Server permission. A server owner can instead allow
chosen roles or people in Server Settings > Integrations > this bot > the command, so the bot
must not re-check Manage Server itself, or it would block exactly those people.
"""

import sqlite3
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any, Literal

import discord
from discord import app_commands

from fantasy_bot.bot.commands.formatting import money
from fantasy_bot.bot.commands.register import team_name
from fantasy_bot.bot.commands.teams import team_autocomplete
from fantasy_bot.services.registration import AdminResult, approve, record_payment

NOT_REGISTERED = "That team hasn't registered. Ask them to run /psek-nba-register first."


def format_approve(result: AdminResult) -> str:
    if not result.done:
        return NOT_REGISTERED
    start = f" from gameweek {result.gameweek}" if result.gameweek else ""
    return f"Approved {team_name(result.team)}; it's in the pool{start}."


def format_payment(result: AdminResult, amount_minor: int, direction: str) -> str:
    if not result.done:
        return NOT_REGISTERED
    what = "paid in" if direction == "in" else "was paid out"
    return f"Recorded: {team_name(result.team)} {what} {money(amount_minor)}."


def approve_handler(
    conn: sqlite3.Connection, season_id: str
) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        team="A registered team waiting for approval",
        from_gameweek="First gameweek it pays and plays (default: as registered)",
    )
    @app_commands.autocomplete(team=team_autocomplete(conn, season_id, status="pending"))
    async def handle(
        interaction: discord.Interaction,
        team: int,
        from_gameweek: app_commands.Range[int, 1, 30] | None = None,
    ) -> None:
        reply = format_approve(approve(conn, season_id, team, from_gameweek))
        await interaction.response.send_message(reply, ephemeral=True)

    return handle


def paid_handler(
    conn: sqlite3.Connection, season_id: str
) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        team="Whose money moved",
        amount="How much, e.g. 100",
        direction="in: they paid the pot; out: the pot paid them their winnings",
        note="Optional, e.g. 'gameweek 2'",
    )
    @app_commands.autocomplete(team=team_autocomplete(conn, season_id, status="approved"))
    async def handle(
        interaction: discord.Interaction,
        team: int,
        amount: app_commands.Range[float, 0.01, 1_000_000.0],
        direction: Literal["in", "out"] = "in",
        note: str | None = None,
    ) -> None:
        minor = round(amount * 100)
        result = record_payment(conn, season_id, team, minor, direction, note, datetime.now(UTC))
        # Public, so everyone sees the books change.
        await interaction.response.send_message(format_payment(result, minor, direction))

    return handle
