from dataclasses import dataclass

from fantasy_bot.models.participant import ParticipantId, ParticipantName


@dataclass(frozen=True)
class PointsSeries:
    participant_id: ParticipantId
    name: ParticipantName
    days: list[int]
    totals: list[int]  # season total after each day, in tenths


@dataclass(frozen=True)
class PointsHistory:
    series: list[PointsSeries]  # in participant order, so colors follow the team
    gameweek_of_day: dict[int, int]


@dataclass(frozen=True)
class GameweekSeries:
    participant_id: ParticipantId
    name: ParticipantName
    gameweeks: list[int]
    points: list[int]  # each gameweek's points after transfer costs, in tenths


@dataclass(frozen=True)
class GameweekPoints:
    series: list[GameweekSeries]  # in participant order, so colors follow the team
    not_final: list[int]  # gameweeks whose points can still change
