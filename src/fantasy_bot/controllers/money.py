from collections.abc import Callable, Coroutine
from typing import Any

import discord
from sqlalchemy.orm import Session, sessionmaker

from fantasy_bot.controllers.formatting import money, percentages, signed
from fantasy_bot.models.money import SeasonMoney
from fantasy_bot.services.money import get_season_money
from fantasy_bot.services.prizes import PRIZES

NAME_WIDTH = 10  # team names are cut to this in the table's header


def format_money(season: SeasonMoney) -> str:
    """A table of net win or loss: one row per final gameweek, one column per person, best
    total first. Gameweeks grow down the page, so the table stays narrow all season."""
    weeks = season.gameweeks
    title = (
        f"**Money after {len(weeks)} final gameweek{'s' * (len(weeks) != 1)}**"
        f" ({money(season.weekly_buy_in)} a week each, paid {percentages(PRIZES)})"
    )
    parts = [title]
    if season.rows:
        header = ["", *(_short(r.name.team_name) for r in season.rows)]
        body = [
            [f"GW{gw}", *(_cell(r.net_by_gameweek.get(gw)) for r in season.rows)] for gw in weeks
        ]
        total = ["Total", *(signed(r.total.net) for r in season.rows)]
        parts.append(_code_table([header, *body, total]))
    else:
        parts.append("No final gameweeks yet.")
    if season.not_final:
        listed = ", ".join(f"GW{gw}" for gw in season.not_final)
        verb = "is" if len(season.not_final) == 1 else "are"
        parts.append(f"{listed} {verb} not final yet: /psek-nba-pool shows it so far.")
    return "\n".join(parts)


def _short(team_name: str) -> str:
    # Inside a code block markdown isn't parsed; only a backtick could end the block early.
    return team_name.replace("`", "'")[:NAME_WIDTH]


def _cell(net: int | None) -> str:
    return "-" if net is None else signed(net)  # "-": not in the pool that week


def _code_table(rows: list[list[str]]) -> str:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    # Labels on the left, numbers lined up on the right.
    lines = [
        "  ".join(
            c.ljust(w) if i == 0 else c.rjust(w)
            for i, (c, w) in enumerate(zip(row, widths, strict=True))
        )
        for row in rows
    ]
    return "```\n" + "\n".join(lines) + "\n```"


def handler(
    sessions: sessionmaker[Session], season_id: str
) -> Callable[[discord.Interaction], Coroutine[Any, Any, None]]:
    async def handle(interaction: discord.Interaction) -> None:
        with sessions() as session:
            text = format_money(get_season_money(session, season_id))
        await interaction.response.send_message(
            text, allowed_mentions=discord.AllowedMentions.none()
        )

    return handle
