from fantasy_bot.adapters.discord_bot import render_money
from fantasy_bot.application.services import MoneyLine
from fantasy_bot.domain.payout import ParticipantId, Settlement


def test_empty_season_says_so() -> None:
    assert render_money([]) == "No approved participants yet."


def test_money_lines_show_points_in_units_and_signed_net() -> None:
    lines = [
        MoneyLine(111, Settlement(ParticipantId(1), 1, 9055, 100000, 150000, 50000)),
        MoneyLine(222, Settlement(ParticipantId(2), 2, 7000, 100000, 50000, -50000)),
    ]
    assert render_money(lines) == (
        "**Pool 2,000.00**\n"
        "1. <@111> 905.5 pts, payout 1,500.00, net +500.00\n"
        "2. <@222> 700.0 pts, payout 500.00, net -500.00"
    )
