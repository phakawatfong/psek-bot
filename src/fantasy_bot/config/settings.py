import os
from collections.abc import Mapping
from dataclasses import dataclass


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    discord_token: str
    league_id: int
    season_id: str
    guild_id: int | None
    db_path: str
    payout_split_bp: tuple[int, ...] = (5000, 3000, 2000)
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
        )


def _int(env: Mapping[str, str], key: str) -> int:
    try:
        return int(env[key])
    except ValueError:
        raise ConfigError(f"{key} must be a number, got {env[key]!r}") from None
