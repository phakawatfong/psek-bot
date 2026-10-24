"""Friends joining the pool: register a team, an admin approves it, payments are recorded."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from fantasy_bot.models import PLACEHOLDER_MAX_ID, LeagueTeam
from fantasy_bot.repositories import registration as repo
from fantasy_bot.repositories import schedule
from fantasy_bot.services.schedule import current_gameweek

RegisterOutcome = Literal[
    "registered",  # new, pending approval
    "claimed",  # the team was entered by hand with a placeholder id; now linked to this user
    "already_yours",
    "taken",  # another Discord user owns this team
    "has_other_team",  # this user already registered a different team
    "not_in_league",
]


@dataclass(frozen=True)
class RegisterResult:
    outcome: RegisterOutcome
    team: LeagueTeam | None = None
    gameweek: int | None = None  # first gameweek in the pool, for "registered"


@dataclass(frozen=True)
class AdminResult:
    done: bool  # False: the team hasn't registered
    team: LeagueTeam | None = None
    gameweek: int | None = None


def register(
    conn: sqlite3.Connection, season_id: str, discord_user_id: int, entry_id: int, now: datetime
) -> RegisterResult:
    team = repo.league_team(conn, season_id, entry_id)
    if team is None:
        return RegisterResult("not_in_league")
    mine = repo.by_user(conn, season_id, discord_user_id)
    if mine and mine.entry_id == entry_id:
        return RegisterResult("already_yours", team)
    if mine:
        return RegisterResult("has_other_team", repo.league_team(conn, season_id, mine.entry_id))

    existing = repo.by_entry(conn, season_id, entry_id)
    if existing and existing.discord_user_id < PLACEHOLDER_MAX_ID:
        repo.link_user(conn, existing.participant_id, discord_user_id)
        return RegisterResult("claimed", team)
    if existing:
        return RegisterResult("taken", team)

    gameweek = joining_gameweek(conn, season_id, now)
    repo.add(conn, season_id, discord_user_id, entry_id, gameweek, now.isoformat())
    return RegisterResult("registered", team, gameweek)


def joining_gameweek(conn: sqlite3.Connection, season_id: str, now: datetime) -> int:
    """The current gameweek if it hasn't started yet, else the next: nobody joins mid-week."""
    gameweek = current_gameweek(conn, season_id)
    if gameweek is None:
        return 1
    starts_at = schedule.gameweek_starts_at(conn, season_id, gameweek)
    return gameweek if starts_at and datetime.fromisoformat(starts_at) > now else gameweek + 1


def approve(
    conn: sqlite3.Connection, season_id: str, entry_id: int, from_gameweek: int | None = None
) -> AdminResult:
    """Put a registered team in the pool; `from_gameweek` overrides the week it starts paying."""
    found = repo.by_entry(conn, season_id, entry_id)
    if found is None:
        return AdminResult(False)
    repo.approve(conn, found.participant_id, from_gameweek)
    return AdminResult(True, repo.league_team(conn, season_id, entry_id), from_gameweek)


def record_payment(
    conn: sqlite3.Connection,
    season_id: str,
    entry_id: int,
    amount_minor: int,
    direction: Literal["in", "out"],
    note: str | None,
    now: datetime,
) -> AdminResult:
    """Real money: 'in' when a friend pays the pot, 'out' when the pot pays a friend."""
    if amount_minor <= 0:
        raise ValueError("payment amounts are positive; use direction for in or out")
    found = repo.by_entry(conn, season_id, entry_id)
    if found is None:
        return AdminResult(False)
    kind = "paid_in" if direction == "in" else "paid_out"
    repo.add_payment(conn, found.participant_id, kind, amount_minor, note, now.isoformat())
    return AdminResult(True, repo.league_team(conn, season_id, entry_id))


def find_teams(
    conn: sqlite3.Connection, season_id: str, text: str, status: str | None = None
) -> list[LeagueTeam]:
    """Teams matching typed text, for the command dropdowns."""
    return repo.search_teams(conn, season_id, text, status)
