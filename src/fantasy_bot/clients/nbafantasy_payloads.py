"""The contract for nbafantasy's JSON: every field the bot reads, with its type.

Fields nbafantasy adds are ignored. A field we read that disappears, is renamed, or changes type
fails validation with an error naming it, before anything is written to the database.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Payload(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore", frozen=True)


# bootstrap-static/


class TeamPayload(Payload):
    id: int
    name: str
    short_name: str


class PhasePayload(Payload):
    name: str  # "Overall" or "Gameweek N"
    start_event: int
    stop_event: int


class EventPayload(Payload):
    id: int
    name: str
    deadline_time: str
    finished: bool
    data_checked: bool


class ElementPayload(Payload):
    id: int
    code: int  # NBA.com person id
    web_name: str
    first_name: str
    second_name: str
    team: int
    element_type: Literal[1, 2]  # 1 back court, 2 front court


class BootstrapPayload(Payload):
    teams: list[TeamPayload]
    phases: list[PhasePayload]
    events: list[EventPayload]
    elements: list[ElementPayload]


# fixtures/?event=N  (a JSON list of these)


class FixturePayload(Payload):
    id: int
    event: int
    code: int  # NBA.com game id without its leading zeros
    kickoff_time: str
    team_h: int
    team_a: int
    team_h_score: int | None
    team_a_score: int | None
    finished: bool


# event/N/live/


class ExplainStatPayload(Payload):
    identifier: str
    value: int
    points: int


class ExplainFixturePayload(Payload):
    fixture: int
    stats: list[ExplainStatPayload]


class LiveElementPayload(Payload):
    id: int
    explain: list[ExplainFixturePayload]


class LivePayload(Payload):
    elements: list[LiveElementPayload]


# entry/N/


class EntryPayload(Payload):
    id: int
    name: str
    player_first_name: str
    player_last_name: str
    started_event: int


# entry/N/event/M/picks/


class EntryHistoryPayload(Payload):
    points: int
    total_points: int
    event_transfers_cost: int
    points_on_bench: int
    overall_rank: int | None


class PickPayload(Payload):
    element: int
    position: int
    multiplier: int
    is_captain: bool


class PicksPayload(Payload):
    entry_history: EntryHistoryPayload
    picks: list[PickPayload]


# leagues-classic/N/standings/?page_standings=P


class LeagueStandingRowPayload(Payload):
    entry: int
    entry_name: str
    player_name: str


class LeagueStandingsPagePayload(Payload):
    has_next: bool
    results: list[LeagueStandingRowPayload]


class LeagueStandingsPayload(Payload):
    standings: LeagueStandingsPagePayload
