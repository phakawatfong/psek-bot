import sqlite3

import discord
from discord import app_commands

from fantasy_bot.bot.commands import register_all


class FantasyBot(discord.Client):
    def __init__(self, conn: sqlite3.Connection, season_id: str, guild_id: int | None) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.guild = discord.Object(id=guild_id) if guild_id else None
        register_all(self.tree, conn, season_id)

    async def setup_hook(self) -> None:
        # Guild sync shows commands instantly; global sync can take a while to appear.
        if self.guild:
            self.tree.copy_global_to(guild=self.guild)
        await self.tree.sync(guild=self.guild)
