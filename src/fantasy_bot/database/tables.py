"""SQLAlchemy mappings of the database, for every query in the app.

The schema itself is defined by the SQL files in migrations/ (STRICT tables, CHECK constraints,
views), which this module mirrors; tests/database/test_tables.py fails if the two drift apart.
Nothing here creates tables.

Import it as a module, `from fantasy_bot.database import tables as t`, so `t.Day` (a table)
never clashes with a feature's own dataclass of the same name.
"""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    Table,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Season(Base):
    __tablename__ = "season"
    season_id: Mapped[str] = mapped_column(Text, primary_key=True)
    league_id: Mapped[int]
    locked_at: Mapped[str | None] = mapped_column(Text)
    weekly_buy_in_minor: Mapped[int]


class Participant(Base):
    __tablename__ = "participant"
    participant_id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[str] = mapped_column(Text, ForeignKey("season.season_id"))
    entry_id: Mapped[int]
    joined_gameweek: Mapped[int]


class NbaTeam(Base):
    __tablename__ = "nba_team"
    season_id: Mapped[str] = mapped_column(Text, ForeignKey("season.season_id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    short_name: Mapped[str] = mapped_column(Text)


class Player(Base):
    __tablename__ = "player"
    __table_args__ = (
        ForeignKeyConstraint(["season_id", "team_id"], ["nba_team.season_id", "nba_team.team_id"]),
    )
    season_id: Mapped[str] = mapped_column(Text, primary_key=True)
    player_id: Mapped[int] = mapped_column(primary_key=True)
    nba_person_id: Mapped[int]
    web_name: Mapped[str] = mapped_column(Text)
    first_name: Mapped[str] = mapped_column(Text)
    second_name: Mapped[str] = mapped_column(Text)
    team_id: Mapped[int]
    position: Mapped[str] = mapped_column(Text)


class Day(Base):
    __tablename__ = "day"
    season_id: Mapped[str] = mapped_column(Text, ForeignKey("season.season_id"), primary_key=True)
    day_id: Mapped[int] = mapped_column(primary_key=True)
    gameweek: Mapped[int]
    name: Mapped[str] = mapped_column(Text)
    deadline_time: Mapped[str] = mapped_column(Text)
    finished: Mapped[bool] = mapped_column(Boolean)
    data_checked: Mapped[bool] = mapped_column(Boolean)
    facts_final: Mapped[bool] = mapped_column(Boolean)


class Fixture(Base):
    __tablename__ = "fixture"
    __table_args__ = (
        ForeignKeyConstraint(["season_id", "day_id"], ["day.season_id", "day.day_id"]),
        ForeignKeyConstraint(
            ["season_id", "home_team_id"], ["nba_team.season_id", "nba_team.team_id"]
        ),
        ForeignKeyConstraint(
            ["season_id", "away_team_id"], ["nba_team.season_id", "nba_team.team_id"]
        ),
    )
    season_id: Mapped[str] = mapped_column(Text, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int]
    nba_game_id: Mapped[str] = mapped_column(Text)
    kickoff_time: Mapped[str] = mapped_column(Text)
    home_team_id: Mapped[int]
    away_team_id: Mapped[int]
    home_score: Mapped[int | None]
    away_score: Mapped[int | None]
    finished: Mapped[bool] = mapped_column(Boolean)


class Entry(Base):
    __tablename__ = "entry"
    season_id: Mapped[str] = mapped_column(Text, ForeignKey("season.season_id"), primary_key=True)
    entry_id: Mapped[int] = mapped_column(primary_key=True)
    entry_name: Mapped[str] = mapped_column(Text)
    manager_name: Mapped[str] = mapped_column(Text)
    started_day: Mapped[int]


class FactPlayerStat(Base):
    __tablename__ = "fact_player_stat"
    __table_args__ = (
        ForeignKeyConstraint(
            ["season_id", "fixture_id"], ["fixture.season_id", "fixture.fixture_id"]
        ),
        ForeignKeyConstraint(["season_id", "player_id"], ["player.season_id", "player.player_id"]),
    )
    season_id: Mapped[str] = mapped_column(Text, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(primary_key=True)
    stat: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[int]
    points: Mapped[int]


class FactPick(Base):
    __tablename__ = "fact_pick"
    __table_args__ = (
        ForeignKeyConstraint(["season_id", "entry_id"], ["entry.season_id", "entry.entry_id"]),
        ForeignKeyConstraint(["season_id", "day_id"], ["day.season_id", "day.day_id"]),
        ForeignKeyConstraint(["season_id", "player_id"], ["player.season_id", "player.player_id"]),
    )
    season_id: Mapped[str] = mapped_column(Text, primary_key=True)
    entry_id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(primary_key=True)
    position: Mapped[int]
    multiplier: Mapped[int]
    is_captain: Mapped[bool] = mapped_column(Boolean)


class FactEntryDay(Base):
    __tablename__ = "fact_entry_day"
    __table_args__ = (
        ForeignKeyConstraint(["season_id", "entry_id"], ["entry.season_id", "entry.entry_id"]),
        ForeignKeyConstraint(["season_id", "day_id"], ["day.season_id", "day.day_id"]),
    )
    season_id: Mapped[str] = mapped_column(Text, primary_key=True)
    entry_id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(primary_key=True)
    points: Mapped[int]
    total_points: Mapped[int]
    transfers_cost: Mapped[int]
    points_on_bench: Mapped[int]
    overall_rank: Mapped[int | None]


class RawApiResponse(Base):
    __tablename__ = "raw_api_response"
    season_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source: Mapped[str] = mapped_column(Text, primary_key=True)
    request_key: Mapped[str] = mapped_column(Text, primary_key=True)
    fetched_at: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)


class SyncRun(Base):
    __tablename__ = "sync_run"
    sync_run_id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[str] = mapped_column(Text, ForeignKey("season.season_id"))
    started_at: Mapped[str] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text)
    days_synced: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(Text)


# The views, read-only. Kept on their own MetaData so nothing could ever try to create them as
# tables; their SQL lives in migrations/.
views = MetaData()

entry_gameweek = Table(
    "v_entry_gameweek",
    views,
    Column("season_id", Text),
    Column("entry_id", Integer),
    Column("gameweek", Integer),
    Column("points", Integer),
    Column("transfers_cost", Integer),
    Column("days_played", Integer),
)

season_standings = Table(
    "v_season_standings",
    views,
    Column("season_id", Text),
    Column("participant_id", Integer),
    Column("entry_id", Integer),
    Column("entry_name", Text),
    Column("total_points", Integer),
)

gameweek_pool = Table(
    "v_gameweek_pool",
    views,
    Column("season_id", Text),
    Column("gameweek", Integer),
    Column("final", Boolean),
    Column("participant_id", Integer),
    Column("buy_in_minor", Integer),
    Column("points", Integer),
)

entry_day_reconcile = Table(
    "v_entry_day_reconcile",
    views,
    Column("season_id", Text),
    Column("entry_id", Integer),
    Column("day_id", Integer),
    Column("data_checked", Boolean),
    Column("official", Integer),
    Column("computed", Integer),
)
