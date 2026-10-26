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


def split_reply(text: str) -> list[str]:
    """Keep long season tables below Discord's limit, closing/reopening their code blocks."""
    messages: list[str] = []
    current = ""
    in_code = False
    for line in text.splitlines():
        # Lines normally fit easily; even an unusually long external name must fit.
        for start in range(0, max(len(line), 1), 1900):
            part = line[start : start + 1900]
            if len(current) + len(part) + 5 > 2000:
                messages.append(current + ("\n```" if in_code else ""))
                current = "```" if in_code else ""
            current = f"{current}\n{part}" if current else part
            if part == "```":
                in_code = not in_code
    if current:
        messages.append(current)
    return messages or ["No results."]
