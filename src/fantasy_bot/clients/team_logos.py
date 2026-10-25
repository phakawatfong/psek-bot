"""Download small NBA team PNGs from ESPN's public image CDN."""

import logging
import re

import aiohttp

from fantasy_bot.clients.nbafantasy import USER_AGENT

log = logging.getLogger(__name__)
ESPN_CODES = {"GSW": "gs", "NOP": "no", "NYK": "ny", "SAS": "sa", "UTA": "utah", "WAS": "wsh"}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_LOGO_BYTES = 256 * 1024


def logo_url(team_code: str) -> str:
    if not re.fullmatch(r"[A-Z]{2,4}", team_code):
        raise ValueError(f"Invalid NBA team code: {team_code!r}")
    slug = ESPN_CODES.get(team_code, team_code.lower())
    return f"https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/{slug}.png&h=128&w=128"


async def fetch_logos(team_codes: list[str]) -> dict[str, bytes]:
    """Skip failed or invalid downloads; one missing logo must not hide the others."""
    logos: dict[str, bytes] = {}
    async with aiohttp.ClientSession(
        headers={"User-Agent": USER_AGENT}, timeout=aiohttp.ClientTimeout(total=5)
    ) as session:
        for code in team_codes:
            try:
                async with session.get(logo_url(code)) as response:
                    response.raise_for_status()
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(16 * 1024):
                        body.extend(chunk)
                        if len(body) > MAX_LOGO_BYTES:
                            raise ValueError("Logo exceeds the emoji size limit")
                    if not body.startswith(PNG_SIGNATURE):
                        raise ValueError("Logo response is not a PNG")
                    logos[code] = bytes(body)
            except (aiohttp.ClientError, TimeoutError, ValueError):
                log.warning("Could not download the %s team logo", code, exc_info=True)
    return logos
