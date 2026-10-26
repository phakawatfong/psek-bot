from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from sqlalchemy.orm import Session, sessionmaker

from fantasy_bot.controllers.formatting import display_name, money, signed, split_reply
from fantasy_bot.models.money import SeasonMoney
from fantasy_bot.models.pool import Pool
from fantasy_bot.services.gameweeks import GameweekError
from fantasy_bot.services.money import get_season_money
from fantasy_bot.services.pool import get_pool
from fantasy_bot.services.prize_rules import PrizeError, load_rules

NAME_WIDTH = 10  # team names are cut to this in the table's header


def format_money(season: SeasonMoney) -> str:
    """A table of net win or loss: one row per final gameweek, one column per person, best
    total first. Gameweeks grow down the page, so the table stays narrow all season."""
    weeks = season.gameweeks
    title = (
        f"**Money after {len(weeks)} final gameweek{'s' * (len(weeks) != 1)}**"
        f" ({money(season.weekly_buy_in)} a week each)"
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
        parts.append(
            f"{listed} {verb} not final yet: /psek-nba-money gameweek:N shows provisional net."
        )
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


def format_week_money(pool: Pool) -> str:
    status = "final" if pool.final else "provisional; excluded from season total"
    rows = [f"**Gameweek {pool.gameweek} net win/loss** ({status})"]
    rows.extend(f"{display_name(line.name)}: {signed(line.settlement.net)}" for line in pool.lines)
    rows.append("Net = payout minus buy-in. /psek-nba-pool shows the calculation.")
    return "\n".join(rows)


def handler(
    sessions: sessionmaker[Session], season_id: str, prizes_file: Path
) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(
        gameweek="Which gameweek (default: current fantasy gameweek)",
        season="Show all finalized weeks and accumulated totals instead",
    )
    async def handle(
        interaction: discord.Interaction,
        gameweek: app_commands.Range[int, 1] | None = None,
        season: bool = False,
    ) -> None:
        try:
            if season and gameweek is not None:
                raise GameweekError("Choose a gameweek or season:true, not both.")
            rules = load_rules(prizes_file)
            with sessions() as session:
                text = (
                    format_money(get_season_money(session, season_id, rules))
                    if season
                    else format_week_money(get_pool(session, season_id, rules, gameweek))
                )
        except (GameweekError, PrizeError) as error:
            text = str(error)
        messages = split_reply(text)
        await interaction.response.send_message(
            messages[0], allowed_mentions=discord.AllowedMentions.none()
        )
        for message in messages[1:]:
            await interaction.followup.send(
                message, allowed_mentions=discord.AllowedMentions.none()
            )

    return handle
