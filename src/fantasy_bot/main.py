import sys

from fantasy_bot.bot.client import FantasyBot
from fantasy_bot.config.settings import ConfigError, Settings
from fantasy_bot.repositories.database import connect, migrate
from fantasy_bot.repositories.seasons import ensure_season


def main() -> None:
    try:
        settings = Settings.from_env()
    except ConfigError as e:
        sys.exit(f"Config error: {e}")
    conn = connect(settings.db_path)
    migrate(conn)
    ensure_season(conn, settings.season_id, settings.league_id, settings.payout_split_bp)
    FantasyBot(conn, settings.season_id, settings.guild_id).run(settings.discord_token)


if __name__ == "__main__":
    main()
