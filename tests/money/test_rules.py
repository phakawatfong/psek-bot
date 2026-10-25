from fantasy_bot.models import PoolRules
from fantasy_bot.services.rules import config_drift, percentages

SEASON_RULES = PoolRules(10000, (5000, 3000, 2000))


def test_matching_config_has_no_drift() -> None:
    assert config_drift(SEASON_RULES, SEASON_RULES) == []


def test_drift_says_what_env_wants_and_what_stays_in_force() -> None:
    assert config_drift(SEASON_RULES, PoolRules(20000, (6000, 4000))) == [
        "WEEKLY_BUY_IN is 200 in .env, but this season uses 100",
        "PAYOUT_SPLIT is 60/40 in .env, but this season uses 50/30/20",
    ]


def test_percentages_drop_needless_decimals() -> None:
    assert percentages((3334, 3333, 3333)) == "33.34/33.33/33.33"
