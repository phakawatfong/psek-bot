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
from fantasy_bot.services.registration import (
    AddResult,
    AdminResult,
    add_for_member,
    approve,
    record_payment,
)

NOT_REGISTERED = "That team hasn't registered. Ask them to run /psek-nba-register first."


def format_add(result: AddResult, member: discord.abc.User | None) -> str:
    team = team_name(result.team)
    match result.outcome:
        case "added":
            owner = (
                f" for {member.mention}"
                if member
                else "; its owner can link it by running /psek-nba-register"
            )
            return f"Added {team} to the pool from gameweek {result.gameweek}{owner}."
        case "already_registered":
            return f"{team} is already registered. Use /psek-nba-approve if it's waiting."
        case "member_has_other_team":
            return f"That member already has {team}. It's one team per person."
        case "not_in_league":
            return "That team isn't in the league. Start typing its name and pick it."


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


def add_handler(
    conn: sqlite3.Connection, season_id: str
) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        team="A league team nobody has registered yet",
        member="The friend whose team it is (optional: they can link it later themselves)",
        from_gameweek="First gameweek it pays and plays (default: the next one not started)",
    )
    @app_commands.autocomplete(team=team_autocomplete(conn, season_id, status="unregistered"))
    async def handle(
        interaction: discord.Interaction,
        team: int,
        member: discord.Member | None = None,
        from_gameweek: app_commands.Range[int, 1, 30] | None = None,
    ) -> None:
        result = add_for_member(
            conn,
            season_id,
            team,
            member.id if member else None,
            from_gameweek,
            datetime.now(UTC),
        )
        await interaction.response.send_message(
            format_add(result, member), allowed_mentions=discord.AllowedMentions.none()
        )

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
