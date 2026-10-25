from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseConfig:
    path: str = "bot.db"  # a SQLite file; backups go to a backups/ folder beside it

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "DatabaseConfig":
        return cls(path=env.get("DB_PATH") or cls.path)
