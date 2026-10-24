import pytest

from fantasy_bot.bot.commands.admin import format_approve, format_payment
from fantasy_bot.bot.commands.register import format_register
from fantasy_bot.models import LeagueTeam
from fantasy_bot.services.registration import AdminResult, RegisterResult

FOX = LeagueTeam(106, "Foxtrot", "fox manager")


@pytest.mark.parametrize(
    ("result", "reply"),
    [
        (
            RegisterResult("registered", FOX, 2),
            "Registered **Foxtrot (fox manager)**. An admin needs to approve it; once approved"
            " you're in the pool from gameweek 2.",
        ),
        (
            RegisterResult("claimed", FOX),
            "Linked **Foxtrot (fox manager)** to your Discord account. Nothing else changes.",
        ),
        (
            RegisterResult("not_in_league"),
            "That team isn't in the league. Start typing your team name and pick it.",
        ),
    ],
)
def test_register_replies(result: RegisterResult, reply: str) -> None:
    assert format_register(result) == reply


def test_admin_replies() -> None:
    assert format_approve(AdminResult(True, FOX, 1)) == (
        "Approved **Foxtrot (fox manager)**; it's in the pool from gameweek 1."
    )
    assert format_payment(AdminResult(True, FOX), 10000, "in") == (
        "Recorded: **Foxtrot (fox manager)** paid in 100.00."
    )
    assert format_approve(AdminResult(False)).startswith("That team hasn't registered")
