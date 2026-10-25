"""Admin commands for fixing registration mistakes: edit, remove, reset.

Admin-only in the same way as the commands in admin.py. See docs/plans/fixing-mistakes.md.
"""

import sqlite3
from collections.abc import Callable, Coroutine
from typing import Any

import discord
from discord import app_commands

from fantasy_bot.bot.commands.formatting import money
from fantasy_bot.bot.commands.register import team_name
from fantasy_bot.bot.commands.teams import team_autocomplete
from fantasy_bot.models import PLACEHOLDER_MAX_ID, LeagueTeam
from fantasy_bot.services.registration import (
    EditResult,
    RemoveResult,
    ResetResult,
    edit,
    remove,
    reset,
    reset_preview,
)

NOT_REGISTERED = "That team hasn't registered, so there's nothing to change."
CONFIRM_SECONDS = 60


def gameweeks(first: int, last: int) -> str:
    return f"gameweek {first}" if first == last else f"gameweeks {first}-{last}"


def format_edit(result: EditResult) -> str:
    team = team_name(result.team)
    match result.outcome:
        case "not_registered":
            return NOT_REGISTERED
        case "nothing_to_change":
            return f"Nothing to change for {team}."
        case "member_has_other_team":
            return f"That member already has {team}. It's one team per person."
        case "updated":
            changes = []
            if result.new_gameweek is not None and result.old_gameweek is not None:
                old, new = result.old_gameweek, result.new_gameweek
                changes.append(
                    f"from gameweek {old} → {new}"
                    f" (money for {gameweeks(min(old, new), max(old, new) - 1)} is recalculated)"
                )
            if result.new_member_id is not None:
                changes.append(f"linked to <@{result.new_member_id}>")
            return f"Updated {team}: {'; '.join(changes)}."


def payments_summary(result: RemoveResult) -> str:
    if result.payments == 0:
        return "no payment records"
    parts = [f"{money(result.paid_in)} in"] if result.paid_in else []
    parts += [f"{money(result.paid_out)} out"] if result.paid_out else []
    records = "record" if result.payments == 1 else "records"
    return f"{result.payments} payment {records}: {', '.join(parts)}"


def format_remove(result: RemoveResult) -> str:
    if not result.done or result.team is None:
        return NOT_REGISTERED
    linked = result.discord_user_id is not None and result.discord_user_id >= PLACEHOLDER_MAX_ID
    owner = f"linked to <@{result.discord_user_id}>" if linked else "not linked to Discord"
    undo = undo_command(
        result.team, result.discord_user_id if linked else None, result.joined_gameweek
    )
    again = ", then record the payments again with /psek-nba-paid" if result.payments else ""
    return (
        f"Removed {team_name(result.team)} (in from gameweek {result.joined_gameweek}, {owner};"
        f" {payments_summary(result)}). Money from gameweek {result.joined_gameweek} on is"
        f" recalculated.\nTo undo: {undo}{again}."
    )


def undo_command(team: LeagueTeam, member_id: int | None, gameweek: int | None) -> str:
    member = f" member:<@{member_id}>" if member_id else ""
    return f"`/psek-nba-add team:{team.entry_name}{member} from_gameweek:{gameweek}`"


def format_reset_question(preview: ResetResult, season_id: str) -> str:
    return (
        f"This removes all {preview.teams} teams and {preview.payments} payment records of"
        f" season {season_id}. Points data and the prize rules stay. Are you sure?"
    )


def format_reset_done(result: ResetResult) -> str:
    return (
        f"Removed {result.teams} teams and {result.payments} payment records. Points data and"
        " the prize rules are unchanged. The nightly backups in /data/backups can restore them."
    )


class ConfirmReset(discord.ui.View):
    """Red confirm and grey cancel buttons, shown only to the admin who asked."""

    def __init__(self, do_reset: Callable[[], str], asked: discord.Interaction) -> None:
        super().__init__(timeout=CONFIRM_SECONDS)
        self.do_reset = do_reset
        self.asked = asked

    @discord.ui.button(label="Yes, remove everyone", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button["ConfirmReset"]
    ) -> None:
        self.stop()
        await interaction.response.edit_message(content=self.do_reset(), view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button["ConfirmReset"]
    ) -> None:
        self.stop()
        await interaction.response.edit_message(content="Cancelled. Nothing changed.", view=None)

    async def on_timeout(self) -> None:
        await self.asked.edit_original_response(content="No answer, so nothing changed.", view=None)


def edit_handler(
    conn: sqlite3.Connection, season_id: str
) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(
        team="A registered team",
        from_gameweek="New first gameweek it pays and plays",
        member="Link the team to this Discord account instead",
    )
    @app_commands.autocomplete(team=team_autocomplete(conn, season_id, status="registered"))
    async def handle(
        interaction: discord.Interaction,
        team: int,
        from_gameweek: app_commands.Range[int, 1, 30] | None = None,
        member: discord.Member | None = None,
    ) -> None:
        result = edit(conn, season_id, team, from_gameweek, member.id if member else None)
        await interaction.response.send_message(
            format_edit(result), allowed_mentions=discord.AllowedMentions.none()
        )

    return handle


def remove_handler(
    conn: sqlite3.Connection, season_id: str
) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(team="The registered team to take out of the pool")
    @app_commands.autocomplete(team=team_autocomplete(conn, season_id, status="registered"))
    async def handle(interaction: discord.Interaction, team: int) -> None:
        await interaction.response.send_message(
            format_remove(remove(conn, season_id, team)),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    return handle


def reset_handler(
    conn: sqlite3.Connection, season_id: str
) -> Callable[[discord.Interaction], Coroutine[Any, Any, None]]:
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def handle(interaction: discord.Interaction) -> None:
        preview = reset_preview(conn, season_id)
        if preview.teams == 0 and preview.payments == 0:
            await interaction.response.send_message("Nothing to reset.", ephemeral=True)
            return
        view = ConfirmReset(lambda: format_reset_done(reset(conn, season_id)), interaction)
        await interaction.response.send_message(
            format_reset_question(preview, season_id), view=view, ephemeral=True
        )

    return handle
