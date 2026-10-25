"""The Discord client: registers every command (controllers/routes.py) and syncs nbafantasy on a
timer."""

import logging

import discord
from discord import app_commands
from discord.ext import tasks
from sqlalchemy.orm import Session, sessionmaker

from fantasy_bot.config.league import LeagueConfig
from fantasy_bot.controllers.routes import register_all
from fantasy_bot.controllers.team_emojis import load_team_emojis
from fantasy_bot.services.sync import sync_now

log = logging.getLogger(__name__)


class FantasyBot(discord.Client):
    def __init__(
        self, sessions: sessionmaker[Session], league: LeagueConfig, guild_id: int | None
    ) -> None:
        super().__init__(intents=discord.Intents.default())
        self.sessions = sessions
        self.league = league
        self.tree = app_commands.CommandTree(self)
        self.guild = discord.Object(id=guild_id) if guild_id else None
        self.sync_loop = tasks.loop(minutes=league.sync_interval_minutes)(self.sync_once)
        self.team_icons: dict[str, str] = {}
        register_all(self.tree, sessions, league.season_id, self.team_icons)

    async def setup_hook(self) -> None:
        # Guild sync shows commands instantly; global sync can take a while to appear. It also
        # removes commands this version no longer has.
        if self.guild:
            self.tree.copy_global_to(guild=self.guild)
        await self.tree.sync(guild=self.guild)
        await load_team_emojis(self, self.team_icons)
        self.sync_loop.start()

    async def sync_once(self) -> None:
        try:
            with self.sessions() as session:
                result = await sync_now(
                    session, self.league.season_id, self.league.participants_file
                )
        except Exception:
            log.exception("nbafantasy sync failed; will retry next interval")
            return
        log.info("synced days %s for %s entries", result.days_synced, result.entries)
