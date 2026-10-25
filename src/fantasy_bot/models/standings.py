from dataclasses import dataclass

from fantasy_bot.models.participant import ParticipantName


@dataclass(frozen=True)
class StandingRow:
    rank: int
    name: ParticipantName
    points: int
