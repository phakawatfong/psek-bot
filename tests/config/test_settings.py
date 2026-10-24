import pytest

from fantasy_bot.config.settings import ConfigError, Settings

VALID = {"DISCORD_TOKEN": "t", "LEAGUE_ID": "14", "SEASON_ID": "2026-27"}


def test_minimal_env_uses_defaults() -> None:
    assert Settings.from_env(VALID) == Settings(
        discord_token="t", league_id=14, season_id="2026-27", guild_id=None, db_path="bot.db"
    )


def test_optional_values_are_parsed() -> None:
    env = VALID | {"DISCORD_GUILD_ID": "123", "DB_PATH": "/data/bot.db"}
    settings = Settings.from_env(env)
    assert (settings.guild_id, settings.db_path) == (123, "/data/bot.db")


def test_all_missing_keys_are_named_at_once() -> None:
    with pytest.raises(ConfigError, match=r"Missing DISCORD_TOKEN, SEASON_ID in \.env"):
        Settings.from_env({"LEAGUE_ID": "14", "SEASON_ID": ""})


def test_non_numeric_id_is_explained() -> None:
    with pytest.raises(ConfigError, match="LEAGUE_ID must be a number, got 'abc'"):
        Settings.from_env(VALID | {"LEAGUE_ID": "abc"})
