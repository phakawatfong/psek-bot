from dataclasses import dataclass
from typing import NewType

ParticipantId = NewType("ParticipantId", int)


@dataclass(frozen=True)
class Standing:
    participant_id: ParticipantId
    points: int  # tenths of a fantasy point, as nbafantasy reports them
    buy_in: int  # minor currency units


@dataclass(frozen=True)
class Settlement:
    participant_id: ParticipantId
    rank: int
    points: int
    buy_in: int
    payout: int
    net: int


@dataclass(frozen=True)
class MoneyLine:
    discord_user_id: int
    settlement: Settlement
