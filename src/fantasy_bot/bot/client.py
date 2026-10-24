import logging
import sqlite3

import discord
from discord import app_commands
from discord.ext import tasks

from fantasy_bot.bot.commands import register_all
from fantasy_bot.bot.team_emojis import load_team_emojis
from fantasy_bot.services.schedule import team_codes
from fantasy_bot.services.sync import sync_now

log = logging.getLogger(__name__)


class FantasyBot(discord.Client):
    def __init__(
        self,
        conn: sqlite3.Connection,
        season_id: str,
        guild_id: int | None,
        sync_interval_minutes: int,
    ) -> None:
        super().__init__(intents=discord.Intents.default())
        self.conn = conn
        self.season_id = season_id
        self.tree = app_commands.CommandTree(self)
        self.guild = discord.Object(id=guild_id) if guild_id else None
        self.sync_loop = tasks.loop(minutes=sync_interval_minutes)(self.sync_once)
        self.team_icons: dict[str, str] = {}  # filled in place, so commands see updates
        register_all(self.tree, conn, season_id, self.team_icons)

    async def setup_hook(self) -> None:
        # Guild sync shows commands instantly; global sync can take a while to appear.
        if self.guild:
            self.tree.copy_global_to(guild=self.guild)
        await self.tree.sync(guild=self.guild)
        await self.load_team_icons()
        self.sync_loop.start()

    async def sync_once(self) -> None:
        try:
            result = await sync_now(self.conn, self.season_id)
        except Exception:
            log.exception("nbafantasy sync failed; will retry next interval")
            return
        log.info("synced days %s for %s entries", result.days_synced, result.entries)
        await self.load_team_icons()

    async def load_team_icons(self) -> None:
        """Upload any missing team logo emojis. Teams appear after the first sync, so this also
        runs after each sync until every team has its icon."""
        codes = team_codes(self.conn, self.season_id)
        if not codes or len(self.team_icons) == len(codes):
            return
        try:
            self.team_icons.update(await load_team_emojis(self, codes))
        except Exception:
            log.exception("could not load team logo emojis; games show team codes only")
