import sqlite3
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands

from fantasy_bot.bot.commands.formatting import display_name
from fantasy_bot.bot.commands.teams import team_autocomplete
from fantasy_bot.models import LeagueTeam, ParticipantName
from fantasy_bot.services.registration import RegisterResult, register


def team_name(team: LeagueTeam | None) -> str:
    if team is None:
        return "that team"
    return f"**{display_name(ParticipantName(team.entry_name, team.manager_name))}**"


def format_register(result: RegisterResult) -> str:
    team = team_name(result.team)
    match result.outcome:
        case "registered":
            return (
                f"Registered {team}. An admin needs to approve it; once approved you're in the"
                f" pool from gameweek {result.gameweek}."
            )
        case "claimed":
            return f"Linked {team} to your Discord account. Nothing else changes."
        case "already_yours":
            return f"{team} is already registered to you."
        case "taken":
            return f"{team} is registered to someone else. Ask an admin if that's wrong."
        case "has_other_team":
            return f"You already registered {team}. It's one team per person."
        case "not_in_league":
            return "That team isn't in the league. Start typing your team name and pick it."


def handler(conn: sqlite3.Connection, season_id: str) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(team="Start typing your nbafantasy team name and pick it from the list")
    @app_commands.autocomplete(team=team_autocomplete(conn, season_id, status=None))
    async def handle(interaction: discord.Interaction, team: int) -> None:
        result = register(conn, season_id, interaction.user.id, team, datetime.now(UTC))
        await interaction.response.send_message(format_register(result), ephemeral=True)

    return handle
