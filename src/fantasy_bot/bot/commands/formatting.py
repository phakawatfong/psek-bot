import discord

from fantasy_bot.models import ParticipantName


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


MESSAGE_LIMIT = 2000  # Discord's maximum characters per message


def split_message(blocks: list[str], limit: int = MESSAGE_LIMIT) -> list[str]:
    """Pack blocks into as few messages as fit, breaking only between blocks."""
    # ponytail: assumes each block fits on its own; a day has at most 15 games (~1,800 chars)
    messages: list[str] = []
    for block in blocks:
        if messages and len(messages[-1]) + 2 + len(block) <= limit:
            messages[-1] += "\n\n" + block
        else:
            messages.append(block)
    return messages


def points(tenths: int) -> str:
    return f"{tenths / 10:.1f}"


def money(minor: int) -> str:
    return f"{minor / 100:,.2f}"
