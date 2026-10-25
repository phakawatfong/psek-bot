import sqlite3
from datetime import UTC, datetime
from typing import Any

from fantasy_bot.models import DEFAULT_RULES
from fantasy_bot.repositories.registration import by_entry
from fantasy_bot.repositories.seasons import season_rules
from fantasy_bot.services.registration import (
    EditResult,
    RemoveResult,
    ResetResult,
    edit,
    record_payment,
    register,
    remove,
    reset,
    reset_preview,
)

SEASON = "2026-27"
NOW = datetime(2026, 10, 25, tzinfo=UTC)
ALICE, BOB = 312345678901234567, 412345678901234567


def one(conn: sqlite3.Connection, sql: str) -> Any:
    return conn.execute(sql).fetchone()[0]


def test_edit_moves_the_start_week_and_keeps_the_status(league: sqlite3.Connection) -> None:
    result = edit(league, SEASON, 101, 2, None)
    found = by_entry(league, SEASON, 101)
    assert (result.outcome, result.old_gameweek, result.new_gameweek) == ("updated", 1, 2)
    assert found is not None and (found.joined_gameweek, found.status) == (2, "approved")


def test_edit_relinks_the_member_and_can_do_both_at_once(league: sqlite3.Connection) -> None:
    result = edit(league, SEASON, 101, 3, ALICE)
    found = by_entry(league, SEASON, 101)
    assert (result.new_gameweek, result.new_member_id) == (3, ALICE)
    assert found is not None and (found.discord_user_id, found.joined_gameweek) == (ALICE, 3)


def test_pending_team_stays_pending_after_an_edit(league: sqlite3.Connection) -> None:
    register(league, SEASON, BOB, 106, NOW)
    edit(league, SEASON, 106, 1, None)
    found = by_entry(league, SEASON, 106)
    assert found is not None and (found.status, found.joined_gameweek) == ("pending", 1)


def test_edit_with_nothing_new_changes_nothing(league: sqlite3.Connection) -> None:
    assert [
        edit(league, SEASON, 101, None, None).outcome,
        edit(league, SEASON, 101, 1, 11).outcome,  # its current week and id
    ] == ["nothing_to_change", "nothing_to_change"]


def test_edit_refuses_a_member_with_another_team_and_unknown_teams(
    league: sqlite3.Connection,
) -> None:
    register(league, SEASON, ALICE, 101, NOW)  # Alice claims Alpha
    taken = edit(league, SEASON, 102, None, ALICE)
    assert (taken.outcome, taken.team and taken.team.entry_name) == (
        "member_has_other_team",
        "Alpha",
    )
    assert edit(league, SEASON, 999, 2, None) == EditResult("not_registered")


def test_remove_takes_out_the_team_and_its_payments_only(league: sqlite3.Connection) -> None:
    record_payment(league, SEASON, 102, 10000, "in", None, NOW)
    record_payment(league, SEASON, 102, 20000, "out", None, NOW)
    record_payment(league, SEASON, 103, 10000, "in", None, NOW)
    result = remove(league, SEASON, 102)
    assert (result.done, result.joined_gameweek, result.discord_user_id) == (True, 1, 12)
    assert (result.payments, result.paid_in, result.paid_out) == (2, 10000, 20000)
    assert by_entry(league, SEASON, 102) is None
    assert (
        one(league, "SELECT count(*) FROM participant"),
        one(league, "SELECT count(*) FROM ledger"),
    ) == (4, 1)


def test_remove_without_payments_and_of_an_unknown_team(league: sqlite3.Connection) -> None:
    assert remove(league, SEASON, 101).payments == 0
    assert remove(league, SEASON, 999) == RemoveResult(False)


def test_reset_clears_teams_and_payments_but_not_points_or_rules(
    league: sqlite3.Connection,
) -> None:
    record_payment(league, SEASON, 101, 10000, "in", None, NOW)
    record_payment(league, SEASON, 102, 10000, "in", None, NOW)
    points_before = one(league, "SELECT count(*) FROM fact_entry_day")
    assert reset_preview(league, SEASON) == ResetResult(teams=5, payments=2)
    assert reset(league, SEASON) == ResetResult(teams=5, payments=2)
    assert (
        one(league, "SELECT count(*) FROM participant"),
        one(league, "SELECT count(*) FROM ledger"),
        one(league, "SELECT count(*) FROM fact_entry_day"),
    ) == (0, 0, points_before)
    assert season_rules(league, SEASON) == DEFAULT_RULES
    assert reset_preview(league, SEASON) == ResetResult(0, 0)
