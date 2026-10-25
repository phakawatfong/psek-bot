from dataclasses import dataclass

from fantasy_bot.models.money import Settlement
from fantasy_bot.models.participant import ParticipantName


@dataclass(frozen=True)
class PoolLine:
    name: ParticipantName
    settlement: Settlement


@dataclass(frozen=True)
class Pool:
    gameweek: int
    final: bool
    lines: list[PoolLine]  # best first
