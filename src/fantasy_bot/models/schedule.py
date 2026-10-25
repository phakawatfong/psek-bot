"""The fantasy calendar and games shown by the schedule command."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ScheduleGame:
    away_team: str
    home_team: str
    kickoff: datetime | None
    away_score: int | None
    home_score: int | None
    finished: bool


@dataclass(frozen=True)
class ScheduleDay:
    gameweek: int
    day: int  # within this gameweek, not the season-wide event id
    event_id: int
    deadline: datetime
    finished: bool
    games: list[ScheduleGame] = field(default_factory=list)
    upcoming: bool = False
