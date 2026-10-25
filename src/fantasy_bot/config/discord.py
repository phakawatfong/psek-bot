from collections.abc import Mapping
from dataclasses import dataclass

from fantasy_bot.config.env import whole_number


@dataclass(frozen=True)
class DiscordConfig:
    token: str
    guild_id: int | None = None  # set to show commands in one server instantly

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "DiscordConfig":
        guild_id = whole_number(env, "DISCORD_GUILD_ID") if env.get("DISCORD_GUILD_ID") else None
        return cls(token=env["DISCORD_TOKEN"], guild_id=guild_id)
