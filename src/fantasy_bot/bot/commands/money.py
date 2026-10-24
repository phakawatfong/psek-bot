import sqlite3
from collections.abc import Callable, Coroutine
from typing import Any

import discord
from discord import app_commands

from fantasy_bot.bot.commands.formatting import display_name, money, points
from fantasy_bot.models import SeasonMoney, WeekMoney
from fantasy_bot.services.money import get_season_money, get_week_money
from fantasy_bot.services.rules import percentages


def signed(minor: int) -> str:
    return f"{'+' if minor >= 0 else ''}{money(minor)}"


def settle_up(balance: int) -> str:
    """What's left to settle once recorded payments count: buy-ins owed, winnings unpaid."""
    if balance > 0:
        return f"is owed {money(balance)}"
    if balance < 0:
        return f"owes {money(-balance)}"
    return "settled"


def format_week(week: WeekMoney | None) -> str:
    if week is None:
        return "No points synced for that gameweek yet."
    pool = sum(line.settlement.buy_in for line in week.lines)
    status = "final" if week.final else "so far, may still change"
    rows = [
        f"{s.rank}. {display_name(line.name)} {points(s.points)} pts,"
        f" wins {money(s.payout)}, net {signed(s.net)}"
        for line in week.lines
        for s in [line.settlement]
    ]
    return "\n".join([f"**Gameweek {week.gameweek} pool {money(pool)}** ({status})", *rows])


def format_season(season: SeasonMoney) -> str:
    weeks = season.settled_weeks
    title = (
        f"**Season after {len(weeks)} final week{'s' * (len(weeks) != 1)}**"
        f" ({money(season.rules.weekly_buy_in_minor)} per week each,"
        f" paid {percentages(season.rules.split_bp)}; /psek-nba-rules explains)"
    )
    rows = [
        f"{i}. {display_name(r.name)} buy-ins {money(r.total.paid)},"
        f" won {money(r.total.won)}, net {signed(r.total.net)}, {settle_up(r.balance)}"
        for i, r in enumerate(season.rows, start=1)
    ] or ["No final weeks yet."]
    parts = ["\n".join([title, *rows])]
    if season.in_progress:
        parts.append(format_week(season.in_progress))
    return "\n\n".join(parts)


def handler(conn: sqlite3.Connection, season_id: str) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(gameweek="Show one gameweek's pool instead of the season total")
    async def handle(
        interaction: discord.Interaction, gameweek: app_commands.Range[int, 1, 30] | None = None
    ) -> None:
        text = (
            format_week(get_week_money(conn, season_id, gameweek))
            if gameweek
            else format_season(get_season_money(conn, season_id))
        )
        await interaction.response.send_message(
            text, allowed_mentions=discord.AllowedMentions.none()
        )

    return handle
