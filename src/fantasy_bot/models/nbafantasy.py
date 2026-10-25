"""nbafantasy rows. Field names match the table columns in database/migrations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Team:
    team_id: int
    name: str
    short_name: str


@dataclass(frozen=True)
class Player:
    player_id: int
    nba_person_id: int
    web_name: str
    first_name: str
    second_name: str
    team_id: int
    position: str  # 'BC' back court or 'FC' front court


@dataclass(frozen=True)
class Day:
    day_id: int
    gameweek: int
    name: str
    deadline_time: str
    finished: bool
    data_checked: bool  # nbafantasy's flag that the day's points are final


@dataclass(frozen=True)
class Fixture:
    fixture_id: int
    day_id: int
    nba_game_id: str
    kickoff_time: str
    home_team_id: int
    away_team_id: int
    home_score: int | None
    away_score: int | None
    finished: bool


@dataclass(frozen=True)
class PlayerStat:
    fixture_id: int
    player_id: int
    stat: str
    value: int
    points: int


@dataclass(frozen=True)
class Entry:
    entry_id: int
    entry_name: str
    manager_name: str
    started_day: int


@dataclass(frozen=True)
class LeagueTeam:
    entry_id: int
    entry_name: str
    manager_name: str


@dataclass(frozen=True)
class EntryDay:
    entry_id: int
    day_id: int
    points: int
    total_points: int
    transfers_cost: int
    points_on_bench: int
    overall_rank: int | None


@dataclass(frozen=True)
class Pick:
    entry_id: int
    day_id: int
    player_id: int
    position: int
    multiplier: int
    is_captain: bool


@dataclass(frozen=True)
class Bootstrap:
    teams: list[Team]
    players: list[Player]
    days: list[Day]


@dataclass(frozen=True)
class Mismatch:
    entry_id: int
    day_id: int
    official: int
    computed: int


@dataclass(frozen=True)
class SyncResult:
    days_synced: list[int]
    entries: int
    mismatches: list[Mismatch]
