import os

from fantasy_bot.adapters.discord_bot import FantasyBot
from fantasy_bot.adapters.sqlite.db import connect, migrate
from fantasy_bot.adapters.sqlite.repository import SqliteRepository

DEFAULT_SPLIT_BP = [5000, 3000, 2000]


def main() -> None:
    conn = connect(os.environ.get("DB_PATH", "bot.db"))
    migrate(conn)
    repo = SqliteRepository(conn)
    season_id = os.environ["SEASON_ID"]
    repo.ensure_season(season_id, int(os.environ["LEAGUE_ID"]), DEFAULT_SPLIT_BP)
    guild_id = os.environ.get("DISCORD_GUILD_ID")
    bot = FantasyBot(repo, season_id, int(guild_id) if guild_id else None)
    bot.run(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    main()
