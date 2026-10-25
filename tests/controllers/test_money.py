from fantasy_bot.controllers.money import format_money
from fantasy_bot.models.money import MoneyRow, SeasonMoney, SeasonTotal
from fantasy_bot.models.participant import ParticipantId, ParticipantName

JK = ParticipantName("jkslots", "pisit manoo")
GO = ParticipantName("GO-GO Team `x`", "")


def test_one_row_per_final_gameweek_one_column_per_person() -> None:
    season = SeasonMoney(
        10000,
        [1, 2],
        [
            MoneyRow(
                JK, SeasonTotal(ParticipantId(1), 2, 20000, 32000, 12000), {1: 10000, 2: 2000}
            ),
            MoneyRow(GO, SeasonTotal(ParticipantId(2), 1, 10000, 2000, -8000), {2: -8000}),
        ],
        [3],
    )
    # GO joined in GW2, so GW1 shows "-"; its name is cut to fit and loses its backticks.
    assert format_money(season) == (
        "**Money after 2 final gameweeks** (100.00 a week each, paid 50/30/15/5)\n"
        "```\n"
        "       jkslots  GO-GO Team\n"
        "GW1    +100.00           -\n"
        "GW2     +20.00      -80.00\n"
        "Total  +120.00      -80.00\n"
        "```\n"
        "GW3 is not final yet: /psek-nba-pool shows it so far."
    )


def test_before_any_final_gameweek() -> None:
    assert format_money(SeasonMoney(10000, [], [], [1, 2])) == (
        "**Money after 0 final gameweeks** (100.00 a week each, paid 50/30/15/5)\n"
        "No final gameweeks yet.\n"
        "GW1, GW2 are not final yet: /psek-nba-pool shows it so far."
    )
