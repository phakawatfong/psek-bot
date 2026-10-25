from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from fantasy_bot.config.env import ConfigError, hundredths, whole_number

DEFAULT_PARTICIPANTS_FILE = Path("seed/participants.csv")


@dataclass(frozen=True)
class LeagueConfig:
    league_id: int  # the nbafantasy league to follow
    season_id: str  # e.g. "2026-27"; a new id starts a new season with its own buy-in
    # Each person, each gameweek, in cents. Used only when the season is first created; after
    # that the season's stored buy-in wins.
    weekly_buy_in_minor: int = 10000
    participants_file: Path = DEFAULT_PARTICIPANTS_FILE
    sync_interval_minutes: int = 10

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "LeagueConfig":
        return cls(
            league_id=whole_number(env, "LEAGUE_ID"),
            season_id=env["SEASON_ID"],
            weekly_buy_in_minor=_buy_in(env.get("WEEKLY_BUY_IN")),
            participants_file=Path(env.get("PARTICIPANTS_FILE") or DEFAULT_PARTICIPANTS_FILE),
        )


def _buy_in(value: str | None) -> int:
    """WEEKLY_BUY_IN in money, e.g. "100" or "50.50", as minor units."""
    if not value:
        return LeagueConfig.weekly_buy_in_minor
    minor = hundredths(value, "WEEKLY_BUY_IN")
    if minor < 0:
        raise ConfigError(f"WEEKLY_BUY_IN can't be negative, got {value!r}")
    return minor
