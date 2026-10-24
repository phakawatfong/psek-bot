from fantasy_bot.bot.commands.money import format_season, format_week
from fantasy_bot.models import (
    MoneyLine,
    ParticipantId,
    ParticipantName,
    SeasonMoney,
    SeasonMoneyRow,
    SeasonTotal,
    Settlement,
    WeekMoney,
)

JK = ParticipantName("jkslots", "pisit manoo")
GO = ParticipantName("GO-GO Team", "")


def week(final: bool) -> WeekMoney:
    return WeekMoney(
        3,
        final,
        [
            MoneyLine(JK, Settlement(ParticipantId(1), 1, 9055, 10000, 15000, 5000)),
            MoneyLine(GO, Settlement(ParticipantId(2), 2, 7000, 10000, 5000, -5000)),
        ],
    )


def test_week_shows_pool_points_winnings_and_signed_net() -> None:
    assert format_week(week(final=True)) == (
        "**Gameweek 3 pool 200.00** (final)\n"
        "1. jkslots (pisit manoo) 905.5 pts, wins 150.00, net +50.00\n"
        "2. GO-GO Team 700.0 pts, wins 50.00, net -50.00"
    )
    assert format_week(None) == "No points synced for that gameweek yet."


def test_season_lists_totals_then_the_week_in_progress() -> None:
    season = SeasonMoney(
        10000,
        [1, 2],
        [
            SeasonMoneyRow(JK, SeasonTotal(ParticipantId(1), 2, 20000, 32000, 12000)),
            SeasonMoneyRow(GO, SeasonTotal(ParticipantId(2), 2, 20000, 8000, -12000)),
        ],
        week(final=False),
    )
    assert format_season(season) == (
        "**Season after 2 final weeks** (100.00 per week each)\n"
        "1. jkslots (pisit manoo) paid 200.00, won 320.00, net +120.00\n"
        "2. GO-GO Team paid 200.00, won 80.00, net -120.00\n"
        "\n"
        "**Gameweek 3 pool 200.00** (so far, may still change)\n"
        "1. jkslots (pisit manoo) 905.5 pts, wins 150.00, net +50.00\n"
        "2. GO-GO Team 700.0 pts, wins 50.00, net -50.00"
    )


def test_season_before_any_final_week() -> None:
    assert format_season(SeasonMoney(10000, [], [], None)) == (
        "**Season after 0 final weeks** (100.00 per week each)\nNo final weeks yet."
    )
