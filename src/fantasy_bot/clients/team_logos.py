"""NBA team logos as small PNGs, from ESPN's public image CDN.

nba.com's logo CDN refuses non-browser requests; ESPN's resizer returns 128x128 PNGs of a few
KB, well under Discord's 256KB emoji limit.
"""

import aiohttp

USER_AGENT = "psek-nba-bot/0.1 (private friends league)"
# ESPN's team codes where they differ from nbafantasy's short names.
ESPN_CODES = {"GSW": "gs", "NOP": "no", "NYK": "ny", "SAS": "sa", "UTA": "utah", "WAS": "wsh"}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def logo_url(team_code: str) -> str:
    slug = ESPN_CODES.get(team_code, team_code.lower())
    return f"https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/{slug}.png&h=128&w=128"


async def fetch_logos(team_codes: list[str]) -> dict[str, bytes]:
    """PNG bytes per team code. A team whose logo can't be fetched is left out."""
    logos: dict[str, bytes] = {}
    async with aiohttp.ClientSession(
        headers={"User-Agent": USER_AGENT}, timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        for code in team_codes:
            try:
                async with session.get(logo_url(code)) as resp:
                    body = await resp.read()
            except (aiohttp.ClientError, TimeoutError):
                continue
            if resp.status == 200 and body.startswith(PNG_SIGNATURE):
                logos[code] = body
    return logos
