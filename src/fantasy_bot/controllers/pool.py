from collections.abc import Callable, Coroutine
from typing import Any

import discord
from discord import app_commands
from sqlalchemy.orm import Session, sessionmaker

from fantasy_bot.controllers.formatting import display_name, money, points, ranked, signed
from fantasy_bot.models.pool import Pool
from fantasy_bot.services.pool import get_pool


def format_pool(pool: Pool | None, gameweek: int | None) -> str:
    if pool is None:
        return f"No points synced for gameweek {gameweek} yet." if gameweek else "No points yet."
    total = sum(line.settlement.buy_in for line in pool.lines)
    status = "final" if pool.final else "so far, may still change"
    last = pool.lines[-1].settlement.rank
    rows = [
        f"{ranked(s.rank, last)}{display_name(line.name)} {points(s.points)} pts:"
        f" put in {money(s.buy_in)}, wins {money(s.payout)}{_share(s.payout, total)},"
        f" net {signed(s.net)}"
        for line in pool.lines
        for s in [line.settlement]
    ]
    return "\n".join([f"**Gameweek {pool.gameweek} pool: {money(total)}** ({status})", *rows])


def _share(payout: int, total: int) -> str:
    """The payout as a share of the pool: 50%, 22.5%, 52.6% (three teams)."""
    return f" ({payout * 100 / total:.3g}%)" if total else ""


def handler(
    sessions: sessionmaker[Session], season_id: str
) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(gameweek="Which gameweek (default: the latest)")
    async def handle(
        interaction: discord.Interaction, gameweek: app_commands.Range[int, 1, 30] | None = None
    ) -> None:
        with sessions() as session:
            text = format_pool(get_pool(session, season_id, gameweek), gameweek)
        await interaction.response.send_message(
            text, allowed_mentions=discord.AllowedMentions.none()
        )

    return handle
