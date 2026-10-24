import sqlite3
from datetime import UTC, datetime

import pytest

from fantasy_bot.repositories.registration import by_entry
from fantasy_bot.services.money import get_season_money
from fantasy_bot.services.registration import (
    approve,
    find_teams,
    joining_gameweek,
    record_payment,
    register,
)

SEASON = "2026-27"
NOW = datetime(2026, 10, 25, tzinfo=UTC)
ALICE, BOB = 312345678901234567, 412345678901234567  # real Discord ids are 17-20 digits


@pytest.fixture
def league(seeded: sqlite3.Connection) -> sqlite3.Connection:
    """The seeded league plus Foxtrot (106), a league team nobody has registered.

    Seeded participants 101-105 were entered by hand with placeholder ids 11-15.
    """
    seeded.execute(
        "INSERT INTO entry (season_id, entry_id, entry_name, manager_name)"
        " VALUES (?, 106, 'Foxtrot', 'fox manager')",
        (SEASON,),
    )
    seeded.commit()
    return seeded


def test_new_team_registers_as_pending_from_next_gameweek(league: sqlite3.Connection) -> None:
    result = register(league, SEASON, ALICE, 106, NOW)
    # Gameweek 1 (days 1-2) is under way on NOW, so Alice starts in gameweek 2.
    assert (result.outcome, result.gameweek) == ("registered", 2)
    found = by_entry(league, SEASON, 106)
    assert found is not None and (found.discord_user_id, found.status) == (ALICE, "pending")


def test_team_entered_with_a_placeholder_is_claimed_keeping_its_place(
    league: sqlite3.Connection,
) -> None:
    assert register(league, SEASON, ALICE, 101, NOW).outcome == "claimed"
    found = by_entry(league, SEASON, 101)
    assert found is not None and (found.discord_user_id, found.status) == (ALICE, "approved")


def test_a_claimed_team_cannot_be_taken_and_one_team_per_person(
    league: sqlite3.Connection,
) -> None:
    register(league, SEASON, ALICE, 101, NOW)
    assert [
        register(league, SEASON, BOB, 101, NOW).outcome,
        register(league, SEASON, ALICE, 101, NOW).outcome,
        register(league, SEASON, ALICE, 106, NOW).outcome,
        register(league, SEASON, BOB, 999, NOW).outcome,
    ] == ["taken", "already_yours", "has_other_team", "not_in_league"]


def test_joining_before_a_gameweek_starts_means_that_gameweek(
    league: sqlite3.Connection,
) -> None:
    before_any_deadline = datetime(2026, 10, 1, tzinfo=UTC)
    assert (
        joining_gameweek(league, SEASON, before_any_deadline),
        joining_gameweek(league, SEASON, NOW),
    ) == (1, 2)


def test_approve_puts_team_in_pool_and_can_backdate_its_start(league: sqlite3.Connection) -> None:
    register(league, SEASON, ALICE, 106, NOW)
    result = approve(league, SEASON, 106, from_gameweek=1)
    found = by_entry(league, SEASON, 106)
    assert result.done and found is not None and found.status == "approved"
    assert (
        league.execute("SELECT joined_gameweek FROM participant WHERE entry_id = 106").fetchone()[0]
        == 1
    )
    assert not approve(league, SEASON, 999).done


def test_payments_count_toward_each_balance(league: sqlite3.Connection) -> None:
    # Gameweek 1 is final: Bravo won 200.00 of the 400.00 pool, Delta won nothing.
    record_payment(league, SEASON, 102, 10000, "in", "gw1", NOW)
    record_payment(league, SEASON, 102, 20000, "out", None, NOW)
    record_payment(league, SEASON, 104, 10000, "in", None, NOW)
    rows = {r.name.team_name: r.balance for r in get_season_money(league, SEASON).rows}
    assert (rows["Bravo"], rows["Delta"], rows["Alpha"]) == (0, 0, 2000)
    assert not record_payment(league, SEASON, 999, 100, "in", None, NOW).done
    with pytest.raises(ValueError, match="positive"):
        record_payment(league, SEASON, 102, 0, "in", None, NOW)


def test_team_search_matches_team_or_manager_and_filters_by_status(
    league: sqlite3.Connection,
) -> None:
    register(league, SEASON, ALICE, 106, NOW)
    assert [t.entry_id for t in find_teams(league, SEASON, "fox")] == [106]
    assert [t.entry_id for t in find_teams(league, SEASON, "", "pending")] == [105, 106]
    assert len(find_teams(league, SEASON, "manager", "approved")) == 4
