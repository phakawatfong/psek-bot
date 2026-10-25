import discord

from fantasy_bot.models.participant import ParticipantName


def display_name(name: ParticipantName) -> str:
    # Team names are free text anyone can set, so markdown in them is shown literally.
    team = discord.utils.escape_markdown(name.team_name)
    manager = discord.utils.escape_markdown(name.manager_name)
    return f"{team} ({manager})" if manager else team


FIRST = "🏆"
LAST = "🐢"


def ranked(rank: int, last_rank: int) -> str:
    """The "N. " prefix for a ranked line, with a badge for first and last place.

    Ties share a rank, so every team tied for first or last gets the badge. When everyone is
    tied there is no last place.
    """
    if rank == 1:
        return f"{rank}. {FIRST} "
    if rank == last_rank:
        return f"{rank}. {LAST} "
    return f"{rank}. "


def points(tenths: int) -> str:
    return f"{tenths / 10:.1f}"


def money(minor: int) -> str:
    return f"{minor / 100:,.2f}"


def signed(minor: int) -> str:
    return f"{'+' if minor >= 0 else ''}{money(minor)}"


def percentages(split_bp: tuple[int, ...]) -> str:
    """(5000, 3000, 1500, 500) -> "50/30/15/5"."""
    return "/".join(f"{bp / 100:g}" for bp in split_bp)
