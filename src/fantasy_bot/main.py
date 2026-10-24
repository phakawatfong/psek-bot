import argparse
import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

from fantasy_bot.bot.client import FantasyBot
from fantasy_bot.config.settings import ConfigError, Settings
from fantasy_bot.repositories.database import backup, connect, migrate
from fantasy_bot.repositories.seasons import ensure_season
from fantasy_bot.services.sync import sync_now


def main() -> None:
    parser = argparse.ArgumentParser(prog="fantasy-bot")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["bot", "sync", "backup"],
        default="bot",
        help=(
            "bot: run the Discord bot (default). sync: copy nbafantasy data once and exit."
            " backup: write today's copy of the database to a backups folder beside it."
        ),
    )
    command = parser.parse_args().command
    try:
        settings = Settings.from_env()
    except ConfigError as e:
        sys.exit(f"Config error: {e}")

    conn = connect(settings.db_path)
    migrate(conn)
    ensure_season(
        conn,
        settings.season_id,
        settings.league_id,
        settings.payout_split_bp,
        settings.weekly_buy_in_minor,
    )

    if command == "backup":
        print(
            f"Backed up to {backup(conn, Path(settings.db_path).parent / 'backups', date.today())}"
        )
        return

    if command == "sync":
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        result = asyncio.run(sync_now(conn, settings.season_id))
        print(
            f"Synced days {result.days_synced or 'none'} for {result.entries} entries,"
            f" {len(result.mismatches)} point mismatches"
        )
        return

    bot = FantasyBot(conn, settings.season_id, settings.guild_id, settings.sync_interval_minutes)
    bot.run(settings.discord_token)


if __name__ == "__main__":
    main()
