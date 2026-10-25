from fantasy_bot.bot.commands.fixes import (
    format_edit,
    format_remove,
    format_reset_done,
    format_reset_question,
    payments_summary,
)
from fantasy_bot.models import LeagueTeam
from fantasy_bot.services.registration import EditResult, RemoveResult, ResetResult

JK = LeagueTeam(31818, "jkslots", "pisit manoo")
PISIT = 312345678901234567


def test_edit_replies_say_what_changed_and_which_weeks_are_recalculated() -> None:
    assert format_edit(EditResult("updated", JK, 1, 2, None)) == (
        "Updated **jkslots (pisit manoo)**: from gameweek 1 → 2"
        " (money for gameweek 1 is recalculated)."
    )
    assert format_edit(EditResult("updated", JK, 4, 1, PISIT)) == (
        "Updated **jkslots (pisit manoo)**: from gameweek 4 → 1"
        f" (money for gameweeks 1-3 is recalculated); linked to <@{PISIT}>."
    )
    assert format_edit(EditResult("nothing_to_change", JK)) == (
        "Nothing to change for **jkslots (pisit manoo)**."
    )


def test_remove_reply_includes_the_exact_undo() -> None:
    result = RemoveResult(True, JK, 1, PISIT, 2, 20000, 0)
    assert format_remove(result) == (
        f"Removed **jkslots (pisit manoo)** (in from gameweek 1, linked to <@{PISIT}>;"
        " 2 payment records: 200.00 in). Money from gameweek 1 on is recalculated.\n"
        f"To undo: `/psek-nba-add team:jkslots member:<@{PISIT}> from_gameweek:1`,"
        " then record the payments again with /psek-nba-paid."
    )


def test_remove_reply_for_a_placeholder_team_without_payments() -> None:
    assert format_remove(RemoveResult(True, JK, 2, 3)) == (
        "Removed **jkslots (pisit manoo)** (in from gameweek 2, not linked to Discord;"
        " no payment records). Money from gameweek 2 on is recalculated.\n"
        "To undo: `/psek-nba-add team:jkslots from_gameweek:2`."
    )
    assert format_remove(RemoveResult(False)).startswith("That team hasn't registered")


def test_payments_summary_names_only_what_happened() -> None:
    assert [
        payments_summary(RemoveResult(True, JK, 1, 1, n, paid_in, paid_out))
        for n, paid_in, paid_out in [(1, 0, 5000), (3, 10000, 5000)]
    ] == ["1 payment record: 50.00 out", "3 payment records: 100.00 in, 50.00 out"]


def test_reset_asks_with_counts_then_reports() -> None:
    assert format_reset_question(ResetResult(4, 2), "2026-27") == (
        "This removes all 4 teams and 2 payment records of season 2026-27."
        " Points data and the prize rules stay. Are you sure?"
    )
    assert format_reset_done(ResetResult(4, 2)).startswith("Removed 4 teams and 2 payment records.")
