"""Reuse the application's NBA emojis and upload missing logos once at startup."""

import asyncio
import logging

import discord

from fantasy_bot.services.team_logos import get_missing_logos

log = logging.getLogger(__name__)
PREFIX = "nba_"
SETUP_TIMEOUT_SECONDS = 60


async def load_team_emojis(client: discord.Client, team_icons: dict[str, str]) -> None:
    """Fill the shared mapping in place, retaining successes if a later operation fails."""
    try:
        # Logos are optional: a slow CDN or Discord rate limit must not block startup forever.
        async with asyncio.timeout(SETUP_TIMEOUT_SECONDS):
            for emoji in await client.fetch_application_emojis():
                if emoji.name and emoji.name.startswith(PREFIX):
                    team_icons[emoji.name.removeprefix(PREFIX)] = str(emoji)
            for code, png in (await get_missing_logos(set(team_icons))).items():
                try:
                    async with asyncio.timeout(5):
                        emoji = await client.create_application_emoji(name=PREFIX + code, image=png)
                    team_icons[code] = str(emoji)
                except (discord.HTTPException, TimeoutError):
                    log.warning("Could not upload the %s team emoji", code, exc_info=True)
    except Exception:
        # A failed optional startup step must not prevent commands or the points sync.
        log.exception("Team emoji setup incomplete; missing logos will use team codes")
