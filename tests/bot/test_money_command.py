from fantasy_bot.bot.commands.money import format_money
from fantasy_bot.models import MoneyLine, ParticipantId, ParticipantName, Settlement


def test_empty_season_says_so() -> None:
    assert format_money([]) == "No approved participants yet."


def test_money_lines_show_names_points_and_signed_net() -> None:
    lines = [
        MoneyLine(
            ParticipantName("jkslots", "pisit manoo"),
            Settlement(ParticipantId(1), 1, 9055, 100000, 150000, 50000),
        ),
        MoneyLine(
            ParticipantName("entry 40823", ""),
            Settlement(ParticipantId(2), 2, 7000, 100000, 50000, -50000),
        ),
    ]
    assert format_money(lines) == (
        "**Pool 2,000.00**\n"
        "1. jkslots (pisit manoo) 905.5 pts, payout 1,500.00, net +500.00\n"
        "2. entry 40823 700.0 pts, payout 500.00, net -500.00"
    )


def test_markdown_in_team_names_is_shown_literally() -> None:
    line = MoneyLine(
        ParticipantName("**WIN**", "a_b_c"), Settlement(ParticipantId(1), 1, 0, 0, 0, 0)
    )
    assert format_money([line]).splitlines()[1].startswith(r"1. \*\*WIN\*\* (a\_b\_c)")
