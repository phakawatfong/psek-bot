"""Start here. Every run does the same three things:

1. load the config from .env
2. build what every job needs: the migrated database and the season row
3. run the job named on the command line (default: the Discord bot)
"""

import argparse
import asyncio
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from fantasy_bot.config import Config, ConfigError, load_config
from fantasy_bot.database.connection import backup, create, migrate, sessions
from fantasy_bot.discord_bot import FantasyBot
from fantasy_bot.repositories import season
from fantasy_bot.services.participants import export_csv
from fantasy_bot.services.sync import sync_now


@dataclass(frozen=True)
class App:
    config: Config
    engine: Engine
    sessions: sessionmaker[Session]


def main() -> None:
    command = parse_args()
    try:
        config = load_config()  # 1.
    except ConfigError as e:
        sys.exit(f"Config error: {e}")
    app = build(config)  # 2.
    job, _ = JOBS[command]
    job(app)  # 3.


def parse_args() -> str:
    parser = argparse.ArgumentParser(prog="fantasy-bot")
    parser.add_argument(
        "command",
        nargs="?",
        choices=list(JOBS),
        default="bot",
        help=" ".join(f"{name}: {help}." for name, (_, help) in JOBS.items()),
    )
    command: str = parser.parse_args().command
    return command


def build(config: Config) -> App:
    """Open and migrate the database, and create the season row on the first run."""
    engine = create(config.database.path)
    migrate(engine)
    session_factory = sessions(engine)
    league = config.league
    with session_factory() as session:
        season.ensure_season(
            session, league.season_id, league.league_id, league.weekly_buy_in_minor
        )
        session.commit()
        buy_in = season.weekly_buy_in(session, league.season_id)
    if buy_in != league.weekly_buy_in_minor:
        print(
            f"WARNING: WEEKLY_BUY_IN is {league.weekly_buy_in_minor / 100:g} in .env, but this"
            f" season uses {buy_in / 100:g}. The buy-in is fixed for a season so past weeks"
            " never change; use a new SEASON_ID to change it.",
            file=sys.stderr,
        )
    return App(config, engine, session_factory)


def run_bot(app: App) -> None:
    bot = FantasyBot(app.sessions, app.config.league, app.config.discord.guild_id)
    bot.run(app.config.discord.token)


def run_sync(app: App) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    league = app.config.league
    with app.sessions() as session:
        result = asyncio.run(sync_now(session, league.season_id, league.participants_file))
    print(
        f"Synced days {result.days_synced or 'none'} for {result.entries} entries,"
        f" {len(result.mismatches)} point mismatches"
    )


def run_backup(app: App) -> None:
    folder = Path(app.config.database.path).parent / "backups"
    print(f"Backed up to {backup(app.engine, folder, date.today())}")


def run_export_participants(app: App) -> None:
    with app.sessions() as session:
        print(export_csv(session, app.config.league.season_id), end="")


# Every job, by the name typed on the command line.
JOBS: dict[str, tuple[Callable[[App], None], str]] = {
    "bot": (run_bot, "run the Discord bot (default)"),
    "sync": (run_sync, "apply the participants file, copy nbafantasy data once, and exit"),
    "backup": (run_backup, "write today's copy of the database to a backups folder beside it"),
    "export-participants": (
        run_export_participants,
        "print today's participants as a participants.csv",
    ),
}


if __name__ == "__main__":
    main()
