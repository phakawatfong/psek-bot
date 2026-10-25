"""Reading values out of .env, with errors that say what to fix."""

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation


class ConfigError(Exception):
    pass


def required(env: Mapping[str, str], keys: list[str]) -> None:
    """Name every missing key at once, so one restart is enough to fix them all."""
    missing = [key for key in keys if not env.get(key)]
    if missing:
        raise ConfigError(f"Missing {', '.join(missing)} in .env (see .env.example)")


def whole_number(env: Mapping[str, str], key: str) -> int:
    try:
        return int(env[key])
    except ValueError:
        raise ConfigError(f"{key} must be a number, got {env[key]!r}") from None


def hundredths(value: str, key: str) -> int:
    """A number with at most two decimals, times 100: "50" -> 5000, "50.5" -> 5050."""
    try:
        scaled = Decimal(value.strip()) * 100
    except InvalidOperation:
        raise ConfigError(f"{key} must be a number, got {value!r}") from None
    if scaled != scaled.to_integral_value():
        raise ConfigError(f"{key} allows at most two decimals, got {value!r}")
    return int(scaled)
