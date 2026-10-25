from collections.abc import Callable, Coroutine
from typing import Any

import discord
from sqlalchemy.orm import Session, sessionmaker

from fantasy_bot.controllers.formatting import display_name, points, ranked
from fantasy_bot.models.standings import StandingRow
from fantasy_bot.services.standings import get_standings


def format_standings(rows: list[StandingRow]) -> str:
    title = "**Season standings**"
    if not rows:
        return f"{title}\nNo participants yet."
    leader, last = rows[0].points, rows[-1].rank
    lines = [
        f"{ranked(r.rank, last)}{display_name(r.name)} {points(r.points)} pts"
        + (f" (-{points(leader - r.points)})" if r.points < leader else "")
        for r in rows
    ]
    return "\n".join([title, *lines])


def handler(
    sessions: sessionmaker[Session], season_id: str
) -> Callable[[discord.Interaction], Coroutine[Any, Any, None]]:
    async def handle(interaction: discord.Interaction) -> None:
        with sessions() as session:
            rows = get_standings(session, season_id)
        await interaction.response.send_message(
            format_standings(rows),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    return handle
