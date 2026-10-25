import pytest

from fantasy_bot.config.settings import ConfigError, Settings
from fantasy_bot.models import PoolRules

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


def test_pool_rules_default_to_100_a_week_split_50_30_20() -> None:
    assert Settings.from_env(VALID).pool_rules == PoolRules(10000, (5000, 3000, 2000))


def test_pool_rules_read_plain_money_and_percentages() -> None:
    env = VALID | {"WEEKLY_BUY_IN": "50.50", "PAYOUT_SPLIT": "60, 25, 15"}
    assert Settings.from_env(env).pool_rules == PoolRules(5050, (6000, 2500, 1500))


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("PAYOUT_SPLIT", "50,30,10", "adding up to 100"),
        ("PAYOUT_SPLIT", "70,30,0", "adding up to 100"),
        ("PAYOUT_SPLIT", "50,thirty,20", "must be a number"),
        ("PAYOUT_SPLIT", "33.333,33.333,33.334", "at most two decimals"),
        ("WEEKLY_BUY_IN", "-5", "can't be negative"),
        ("WEEKLY_BUY_IN", "lots", "must be a number"),
    ],
)
def test_bad_pool_rules_stop_the_bot_with_a_clear_reason(
    key: str, value: str, message: str
) -> None:
    with pytest.raises(ConfigError, match=message):
        Settings.from_env(VALID | {key: value})
