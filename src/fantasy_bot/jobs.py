"""Step 3 of every run: the jobs, by the name typed on the command line."""

import asyncio
from collections.abc import Callable
from datetime import date
from pathlib import Path

from fantasy_bot.database.connection import backup
from fantasy_bot.dependencies import Dependencies
from fantasy_bot.discord_bot import FantasyBot
from fantasy_bot.services.participants import export_csv
from fantasy_bot.services.sync import sync_now


def bot(dependencies: Dependencies) -> None:
    """run the Discord bot (default)"""
    discord = dependencies.config.discord
    FantasyBot(dependencies.sessions, dependencies.config.league, discord.guild_id).run(
        discord.token,
        log_handler=None,  # logging is already set up by main
    )


def sync(dependencies: Dependencies) -> None:
    """apply the participants file, copy nbafantasy data once, and exit"""
    league = dependencies.config.league
    with dependencies.sessions() as session:
        result = asyncio.run(sync_now(session, league.season_id, league.participants_file))
    print(
        f"Synced days {result.days_synced or 'none'} for {result.entries} entries,"
        f" {len(result.mismatches)} point mismatches"
    )


def backup_database(dependencies: Dependencies) -> None:
    """write today's copy of the database to a backups folder beside it"""
    folder = Path(dependencies.config.database.path).parent / "backups"
    print(f"Backed up to {backup(dependencies.engine, folder, date.today())}")


def export_participants(dependencies: Dependencies) -> None:
    """print today's participants as a participants.csv"""
    with dependencies.sessions() as session:
        print(export_csv(session, dependencies.config.league.season_id), end="")


JOBS: dict[str, Callable[[Dependencies], None]] = {
    "bot": bot,
    "sync": sync,
    "backup": backup_database,
    "export-participants": export_participants,
}
