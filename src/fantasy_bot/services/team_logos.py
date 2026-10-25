"""Choose missing logos from the NBA Fantasy team list, independent of the pool."""

from fantasy_bot.clients import nbafantasy, team_logos


async def get_missing_logos(existing_codes: set[str]) -> dict[str, bytes]:
    async with nbafantasy.open_client() as client:
        bootstrap = nbafantasy.parse_bootstrap(await client.fetch(nbafantasy.bootstrap_path()))
    missing = sorted({team.short_name for team in bootstrap.teams} - existing_codes)
    return await team_logos.fetch_logos(missing) if missing else {}
