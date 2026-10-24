from fantasy_bot.clients.team_logos import fetch_logos


async def get_team_logos(team_codes: list[str]) -> dict[str, bytes]:
    """PNG logo per team code; teams whose logo couldn't be downloaded are missing."""
    return await fetch_logos(team_codes)
