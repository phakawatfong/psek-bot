from dataclasses import dataclass

from fantasy_bot.models.participant import ParticipantId, ParticipantName


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
class PoolWeek:
    gameweek: int
    final: bool  # every day of the gameweek is data_checked
    standings: list[Standing]


@dataclass(frozen=True)
class SeasonTotal:
    participant_id: ParticipantId
    weeks: int
    paid: int
    won: int
    net: int


@dataclass(frozen=True)
class MoneyRow:
    name: ParticipantName
    total: SeasonTotal
    net_by_gameweek: dict[int, int]  # only the final gameweeks they played in


@dataclass(frozen=True)
class SeasonMoney:
    weekly_buy_in: int
    gameweeks: list[int]  # final gameweeks, oldest first
    rows: list[MoneyRow]  # best total first
    not_final: list[int]  # gameweeks with points that can still change
