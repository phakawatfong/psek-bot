import sqlite3
from collections.abc import Callable, Coroutine
from typing import Any

import discord

from fantasy_bot.models import MoneyLine
from fantasy_bot.services.money import get_money_summary


def format_money(lines: list[MoneyLine]) -> str:
    if not lines:
        return "No approved participants yet."
    pool = sum(line.settlement.buy_in for line in lines)
    rows = [
        f"{s.rank}. <@{line.discord_user_id}> {s.points / 10:.1f} pts,"
        f" payout {s.payout / 100:,.2f}, net {s.net / 100:+,.2f}"
        for line in lines
        for s in [line.settlement]
    ]
    return "\n".join([f"**Pool {pool / 100:,.2f}**", *rows])


def handler(
    conn: sqlite3.Connection, season_id: str
) -> Callable[[discord.Interaction], Coroutine[Any, Any, None]]:
    async def handle(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            format_money(get_money_summary(conn, season_id)),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    return handle
