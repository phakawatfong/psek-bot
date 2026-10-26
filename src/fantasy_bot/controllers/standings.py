from collections.abc import Callable, Coroutine
from typing import Any

import discord
from discord import app_commands
from sqlalchemy.orm import Session, sessionmaker

from fantasy_bot.controllers.formatting import display_name, points, ranked
from fantasy_bot.models.standings import GameweekStandings
from fantasy_bot.services.gameweeks import GameweekError
from fantasy_bot.services.standings import get_standings


def format_standings(standings: GameweekStandings) -> str:
    status = "final" if standings.final else "provisional"
    title = f"**Gameweek {standings.gameweek} standings** ({status})"
    rows = standings.rows
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
) -> Callable[..., Coroutine[Any, Any, None]]:
    @app_commands.describe(gameweek="Which gameweek (default: current fantasy gameweek)")
    async def handle(
        interaction: discord.Interaction, gameweek: app_commands.Range[int, 1] | None = None
    ) -> None:
        try:
            with sessions() as session:
                text = format_standings(get_standings(session, season_id, gameweek))
        except GameweekError as error:
            text = str(error)
        await interaction.response.send_message(
            text,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    return handle
