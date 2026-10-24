import discord

from fantasy_bot.models import ParticipantName


def display_name(name: ParticipantName) -> str:
    # Team names are free text anyone can set, so markdown in them is shown literally.
    team = discord.utils.escape_markdown(name.team_name)
    manager = discord.utils.escape_markdown(name.manager_name)
    return f"{team} ({manager})" if manager else team


def points(tenths: int) -> str:
    return f"{tenths / 10:.1f}"


def money(minor: int) -> str:
    return f"{minor / 100:,.2f}"
