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
class ParticipantName:
    team_name: str
    manager_name: str


@dataclass(frozen=True)
class MoneyLine:
    name: ParticipantName
    settlement: Settlement


@dataclass(frozen=True)
class PoolWeek:
    gameweek: int
    final: bool  # every day of the gameweek is data_checked
    standings: list[Standing]


@dataclass(frozen=True)
class WeekMoney:
    gameweek: int
    final: bool
    lines: list[MoneyLine]


@dataclass(frozen=True)
class SeasonTotal:
    participant_id: ParticipantId
    weeks: int
    paid: int
    won: int
    net: int


@dataclass(frozen=True)
class SeasonMoneyRow:
    name: ParticipantName
    total: SeasonTotal


@dataclass(frozen=True)
class SeasonMoney:
    weekly_buy_in: int
    settled_weeks: list[int]
    rows: list[SeasonMoneyRow]  # best net first
    in_progress: WeekMoney | None  # the latest week, if not final yet


@dataclass(frozen=True)
class StandingRow:
    rank: int
    name: ParticipantName
    points: int


@dataclass(frozen=True)
class DayPointsRow:
    rank: int
    name: ParticipantName
    points: int  # that day
    total_points: int  # season total after that day


@dataclass(frozen=True)
class DayPoints:
    day_id: int
    day_name: str
    final: bool
    rows: list[DayPointsRow]


@dataclass(frozen=True)
class Game:
    kickoff_time: str
    home: str
    away: str
    home_score: int | None
    away_score: int | None
    finished: bool


@dataclass(frozen=True)
class DaySchedule:
    day_id: int
    day_name: str
    games: list[Game]


@dataclass(frozen=True)
class ParticipantRow:
    name: ParticipantName
    entry_id: int
    joined_gameweek: int
    status: str


# nbafantasy rows. Field names match the table columns in repositories/migrations.


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
