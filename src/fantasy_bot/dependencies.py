"""Step 2 of every run: everything a job needs, built once from the config."""

import logging
from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from fantasy_bot.config import Config
from fantasy_bot.database.connection import create, migrate, sessions
from fantasy_bot.repositories import season

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Dependencies:
    config: Config
    engine: Engine
    sessions: sessionmaker[Session]  # open one per command or sync: `with sessions() as s:`


def load_dependencies(config: Config) -> Dependencies:
    """Open and migrate the database, and create the season row on the first run."""
    engine = create(config.database.path)
    migrate(engine)
    session_factory = sessions(engine)
    _ensure_season(session_factory, config)
    return Dependencies(config, engine, session_factory)


def _ensure_season(session_factory: sessionmaker[Session], config: Config) -> None:
    league = config.league
    with session_factory() as session:
        season.ensure_season(
            session, league.season_id, league.league_id, league.weekly_buy_in_minor
        )
        session.commit()
        buy_in = season.weekly_buy_in(session, league.season_id)
    if buy_in != league.weekly_buy_in_minor:
        log.warning(
            "WEEKLY_BUY_IN is %g in .env, but this season uses %g. The buy-in is fixed for a"
            " season so past weeks never change; use a new SEASON_ID to change it.",
            league.weekly_buy_in_minor / 100,
            buy_in / 100,
        )
