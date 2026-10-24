import sqlite3
from collections.abc import Callable, Coroutine
from typing import Any

import discord

from fantasy_bot.bot.commands.formatting import money
from fantasy_bot.models import PoolRules
from fantasy_bot.services.rules import get_rules


def ordinal(n: int) -> str:
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def percent(bp: int) -> str:
    return f"{bp / 100:g}%"


def tie_example(split_bp: tuple[int, ...]) -> str:
    """The tie rule worked through with this season's own numbers."""
    if len(split_bp) < 2:
        return "two teams tied for 1st each get half of it."
    first = 1 if len(split_bp) == 2 else 2  # tie across the last two paid places
    a, b = split_bp[first - 1], split_bp[first]
    return (
        f"two teams tied for {ordinal(first)} each get ({percent(a)} + {percent(b)}) / 2"
        f" = {percent((a + b) // 2)}."
    )


def format_rules(rules: PoolRules, season_id: str) -> str:
    buy_in = money(rules.weekly_buy_in_minor)
    prizes = ", ".join(
        f"{ordinal(place)} {percent(bp)}" for place, bp in enumerate(rules.split_bp, start=1)
    )
    return "\n".join(
        [
            f"**Prize pool rules, season {season_id}**",
            f"- **Buy-in:** {buy_in} per person, every gameweek from the one they joined.",
            f"- **Weekly pool:** {buy_in} times the number of teams in it that week.",
            f"- **Prizes:** by that gameweek's points after transfer costs: {prizes}."
            " Everyone else wins nothing that week.",
            "- **Ties:** tied teams share the prizes of the places they cover equally: "
            + tie_example(rules.split_bp),
            "- **Fewer teams than prizes:** the prizes in use are scaled up so the whole pool"
            " is still paid out.",
            "- **Rounding:** whole cents; a leftover cent goes to whoever lost most to rounding.",
            "- **When a week counts:** once nbafantasy marks every day of the gameweek final."
            " Until then /psek-nba-money shows it as so far.",
            "- **Fixed all season:** these rules never change mid-season, so past weeks never"
            " change.",
        ]
    )


def handler(
    conn: sqlite3.Connection, season_id: str
) -> Callable[[discord.Interaction], Coroutine[Any, Any, None]]:
    async def handle(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(format_rules(get_rules(conn, season_id), season_id))

    return handle
