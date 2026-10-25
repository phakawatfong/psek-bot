from pathlib import Path

import pytest

from fantasy_bot.config import Config, ConfigError, load_config
from fantasy_bot.config.database import DatabaseConfig
from fantasy_bot.config.discord import DiscordConfig
from fantasy_bot.config.league import LeagueConfig

VALID = {"DISCORD_TOKEN": "t", "LEAGUE_ID": "14", "SEASON_ID": "2026-27"}


def test_minimal_env_uses_defaults() -> None:
    assert load_config(VALID) == Config(
        DiscordConfig(token="t", guild_id=None),
        DatabaseConfig(path="bot.db"),
        LeagueConfig(
            league_id=14,
            season_id="2026-27",
            weekly_buy_in_minor=10000,
            participants_file=Path("seed/participants.csv"),
            sync_interval_minutes=10,
        ),
    )


def test_optional_values_are_parsed() -> None:
    env = VALID | {
        "DISCORD_GUILD_ID": "123",
        "DB_PATH": "/data/bot.db",
        "PARTICIPANTS_FILE": "/seed/participants.csv",
    }
    config = load_config(env)
    assert (config.discord.guild_id, config.database.path, config.league.participants_file) == (
        123,
        "/data/bot.db",
        Path("/seed/participants.csv"),
    )


def test_all_missing_keys_are_named_at_once() -> None:
    with pytest.raises(ConfigError, match=r"Missing DISCORD_TOKEN, SEASON_ID in \.env"):
        load_config({"LEAGUE_ID": "14", "SEASON_ID": ""})


def test_non_numeric_id_is_explained() -> None:
    with pytest.raises(ConfigError, match="LEAGUE_ID must be a number, got 'abc'"):
        load_config(VALID | {"LEAGUE_ID": "abc"})


def test_buy_in_reads_plain_money() -> None:
    assert load_config(VALID | {"WEEKLY_BUY_IN": "50.50"}).league.weekly_buy_in_minor == 5050


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("-5", "can't be negative"),
        ("10.005", "at most two decimals"),
        ("lots", "must be a number"),
    ],
)
def test_bad_buy_in_stops_the_bot_with_a_clear_reason(value: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(VALID | {"WEEKLY_BUY_IN": value})
