import discord
from discord import app_commands

from fantasy_bot.application.ports import Repository
from fantasy_bot.application.services import MoneyLine, money_summary


def render_money(lines: list[MoneyLine]) -> str:
    if not lines:
        return "No approved participants yet."
    pool = sum(line.settlement.buy_in for line in lines)
    rows = [
        f"{s.rank}. <@{line.discord_user_id}> {s.points / 10:.1f} pts,"
        f" payout {s.payout / 100:,.2f}, net {s.net / 100:+,.2f}"
        for line in lines
        for s in [line.settlement]
    ]
    return "\n".join([f"**Pool {pool / 100:,.2f}**", *rows])


class FantasyBot(discord.Client):
    def __init__(self, repo: Repository, season_id: str, guild_id: int | None) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.guild = discord.Object(id=guild_id) if guild_id else None

        @self.tree.command(description="Show the pool, each payout, and each person's net")
        async def money(interaction: discord.Interaction) -> None:
            await interaction.response.send_message(
                render_money(money_summary(repo, season_id)),
                allowed_mentions=discord.AllowedMentions.none(),
            )

    async def setup_hook(self) -> None:
        # Guild sync shows commands instantly; global sync can take a while to appear.
        if self.guild:
            self.tree.copy_global_to(guild=self.guild)
        await self.tree.sync(guild=self.guild)
