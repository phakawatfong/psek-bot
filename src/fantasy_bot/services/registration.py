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


AddOutcome = Literal["added", "already_registered", "member_has_other_team", "not_in_league"]


@dataclass(frozen=True)
class AddResult:
    outcome: AddOutcome
    team: LeagueTeam | None = None
    gameweek: int | None = None


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


def add_for_member(
    conn: sqlite3.Connection,
    season_id: str,
    entry_id: int,
    discord_user_id: int | None,
    from_gameweek: int | None,
    now: datetime,
) -> AddResult:
    """An admin puts a team straight into the pool on a friend's behalf.

    With no Discord account given the team gets a placeholder id, and the friend links it later
    by running /psek-nba-register.
    """
    team = repo.league_team(conn, season_id, entry_id)
    if team is None:
        return AddResult("not_in_league")
    if repo.by_entry(conn, season_id, entry_id):
        return AddResult("already_registered", team)
    if discord_user_id is not None and (mine := repo.by_user(conn, season_id, discord_user_id)):
        return AddResult("member_has_other_team", repo.league_team(conn, season_id, mine.entry_id))
    user_id = discord_user_id or repo.next_placeholder_id(conn, season_id)
    gameweek = from_gameweek or joining_gameweek(conn, season_id, now)
    repo.add(conn, season_id, user_id, entry_id, gameweek, now.isoformat(), status="approved")
    return AddResult("added", team, gameweek)


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


# Fixing mistakes: see docs/plans/fixing-mistakes.md. None of these touch points or rules.

EditOutcome = Literal["updated", "nothing_to_change", "member_has_other_team", "not_registered"]


@dataclass(frozen=True)
class EditResult:
    outcome: EditOutcome
    team: LeagueTeam | None = None  # for member_has_other_team: the member's own team
    old_gameweek: int | None = None
    new_gameweek: int | None = None  # set only when the start week changed
    new_member_id: int | None = None  # set only when the linked account changed


@dataclass(frozen=True)
class RemoveResult:
    done: bool  # False: the team hasn't registered
    team: LeagueTeam | None = None
    joined_gameweek: int | None = None
    discord_user_id: int | None = None
    payments: int = 0
    paid_in: int = 0
    paid_out: int = 0


@dataclass(frozen=True)
class ResetResult:
    teams: int
    payments: int


def edit(
    conn: sqlite3.Connection,
    season_id: str,
    entry_id: int,
    from_gameweek: int | None,
    member_id: int | None,
) -> EditResult:
    """Change a registered team's start week and/or linked account; its status is kept."""
    found = repo.by_entry(conn, season_id, entry_id)
    if found is None:
        return EditResult("not_registered")
    team = repo.league_team(conn, season_id, entry_id)
    new_gameweek = from_gameweek if from_gameweek not in (None, found.joined_gameweek) else None
    new_member = member_id if member_id not in (None, found.discord_user_id) else None
    if new_member is not None and (theirs := repo.by_user(conn, season_id, new_member)):
        return EditResult(
            "member_has_other_team", repo.league_team(conn, season_id, theirs.entry_id)
        )
    if new_gameweek is None and new_member is None:
        return EditResult("nothing_to_change", team)
    if new_gameweek is not None:
        repo.set_start(conn, found.participant_id, new_gameweek)
    if new_member is not None:
        repo.link_user(conn, found.participant_id, new_member)
    return EditResult("updated", team, found.joined_gameweek, new_gameweek, new_member)


def remove(conn: sqlite3.Connection, season_id: str, entry_id: int) -> RemoveResult:
    """Take a team out of the pool with its payment records; the result says how to undo it."""
    found = repo.by_entry(conn, season_id, entry_id)
    if found is None:
        return RemoveResult(False)
    team = repo.league_team(conn, season_id, entry_id)
    payments, paid_in, paid_out = repo.remove(conn, found.participant_id)
    return RemoveResult(
        True, team, found.joined_gameweek, found.discord_user_id, payments, paid_in, paid_out
    )


def reset_preview(conn: sqlite3.Connection, season_id: str) -> ResetResult:
    """What a reset would remove, to show before asking for confirmation."""
    return ResetResult(*repo.count(conn, season_id))


def reset(conn: sqlite3.Connection, season_id: str) -> ResetResult:
    """Remove every registration and payment record of the season."""
    return ResetResult(*repo.reset(conn, season_id))
