import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from fantasy_bot.models import DEFAULT_RULES, PoolRules


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    discord_token: str
    league_id: int
    season_id: str
    guild_id: int | None
    db_path: str
    # Used only when the season is first created; after that the season's stored rules win.
    pool_rules: PoolRules = field(default=DEFAULT_RULES)
    sync_interval_minutes: int = 10

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "Settings":
        missing = [k for k in ("DISCORD_TOKEN", "LEAGUE_ID", "SEASON_ID") if not env.get(k)]
        if missing:
            raise ConfigError(f"Missing {', '.join(missing)} in .env (see .env.example)")
        guild_id = env.get("DISCORD_GUILD_ID")
        return cls(
            discord_token=env["DISCORD_TOKEN"],
            league_id=_int(env, "LEAGUE_ID"),
            season_id=env["SEASON_ID"],
            guild_id=_int(env, "DISCORD_GUILD_ID") if guild_id else None,
            db_path=env.get("DB_PATH") or "bot.db",
            pool_rules=PoolRules(
                weekly_buy_in_minor=_buy_in(env.get("WEEKLY_BUY_IN")),
                split_bp=_split(env.get("PAYOUT_SPLIT")),
            ),
        )


def _int(env: Mapping[str, str], key: str) -> int:
    try:
        return int(env[key])
    except ValueError:
        raise ConfigError(f"{key} must be a number, got {env[key]!r}") from None


def _buy_in(value: str | None) -> int:
    """WEEKLY_BUY_IN in money, e.g. "100" or "50.50", as minor units."""
    if not value:
        return DEFAULT_RULES.weekly_buy_in_minor
    minor = _hundredths(value, "WEEKLY_BUY_IN")
    if minor < 0:
        raise ConfigError(f"WEEKLY_BUY_IN can't be negative, got {value!r}")
    return minor


def _split(value: str | None) -> tuple[int, ...]:
    """PAYOUT_SPLIT as percentages per place, e.g. "50,30,20", as basis points."""
    if not value:
        return DEFAULT_RULES.split_bp
    shares = tuple(_hundredths(part, "PAYOUT_SPLIT") for part in value.split(","))
    if any(bp <= 0 for bp in shares) or sum(shares) != 10_000:
        raise ConfigError(
            f"PAYOUT_SPLIT must be positive percentages adding up to 100, got {value!r}"
        )
    return shares


def _hundredths(value: str, key: str) -> int:
    """A number with at most two decimals, times 100: "50" -> 5000, "33.34" -> 3334."""
    try:
        scaled = Decimal(value.strip()) * 100
    except InvalidOperation:
        raise ConfigError(f"{key} must be a number, got {value!r}") from None
    if scaled != scaled.to_integral_value():
        raise ConfigError(f"{key} allows at most two decimals, got {value!r}")
    return int(scaled)
