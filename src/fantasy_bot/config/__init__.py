"""Everything the bot reads from .env, checked once at start-up."""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from fantasy_bot.config.database import DatabaseConfig
from fantasy_bot.config.discord import DiscordConfig
from fantasy_bot.config.env import ConfigError, required
from fantasy_bot.config.league import LeagueConfig

__all__ = ["Config", "ConfigError", "load_config"]


@dataclass(frozen=True)
class Config:
    discord: DiscordConfig
    database: DatabaseConfig
    league: LeagueConfig


def load_config(env: Mapping[str, str] = os.environ) -> Config:
    required(env, ["DISCORD_TOKEN", "LEAGUE_ID", "SEASON_ID"])
    return Config(
        discord=DiscordConfig.from_env(env),
        database=DatabaseConfig.from_env(env),
        league=LeagueConfig.from_env(env),
    )
