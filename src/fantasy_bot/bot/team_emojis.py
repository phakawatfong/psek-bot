"""Team logos as the bot's own Discord emojis, so messages can show them inline.

Application emojis belong to the bot, not a server: they work in every server it is in and need
no server permission. They are uploaded once and found again by name on every later start.
"""

import logging
from collections.abc import Awaitable, Callable

import discord

from fantasy_bot.services.team_logos import get_team_logos

PREFIX = "nba_"

log = logging.getLogger(__name__)


async def load_team_emojis(
    client: discord.Client,
    team_codes: list[str],
    get_logos: Callable[[list[str]], Awaitable[dict[str, bytes]]] = get_team_logos,
) -> dict[str, str]:
    """Emoji markup per team code, e.g. {"ATL": "<:nba_ATL:123>"}; uploads any missing logos."""
    emojis = {e.name: e for e in await client.fetch_application_emojis()}
    missing = [code for code in team_codes if PREFIX + code not in emojis]
    if missing:
        for code, png in (await get_logos(missing)).items():
            try:
                emojis[PREFIX + code] = await client.create_application_emoji(
                    name=PREFIX + code, image=png
                )
            except discord.HTTPException:
                log.warning("could not upload the %s logo emoji", code, exc_info=True)
    return {code: str(emojis[PREFIX + code]) for code in team_codes if PREFIX + code in emojis}
