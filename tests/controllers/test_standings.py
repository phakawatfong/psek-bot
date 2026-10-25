from fantasy_bot.controllers.standings import format_standings
from fantasy_bot.models.participant import ParticipantName
from fantasy_bot.models.standings import StandingRow

JK = ParticipantName("jkslots", "pisit manoo")
GO = ParticipantName("GO-GO Team", "settakarn")


def test_standings_show_gap_to_leader() -> None:
    rows = [StandingRow(1, JK, 4760), StandingRow(2, GO, 4500)]
    assert format_standings(rows) == (
        "**Season standings**\n"
        "1. 🏆 jkslots (pisit manoo) 476.0 pts\n"
        "2. 🐢 GO-GO Team (settakarn) 450.0 pts (-26.0)"
    )


def test_no_participants_yet() -> None:
    assert format_standings([]) == "**Season standings**\nNo participants yet."


def test_ties_share_the_first_and_last_badges() -> None:
    dream, kids = ParticipantName("Dream team", ""), ParticipantName("kidsgodspeed", "")
    rows = [
        StandingRow(1, JK, 500),
        StandingRow(1, GO, 500),
        StandingRow(3, dream, 400),
        StandingRow(4, kids, 300),
        StandingRow(4, ParticipantName("Late", ""), 300),
    ]
    assert format_standings(rows).splitlines()[1:] == [
        "1. 🏆 jkslots (pisit manoo) 50.0 pts",
        "1. 🏆 GO-GO Team (settakarn) 50.0 pts",
        "3. Dream team 40.0 pts (-10.0)",
        "4. 🐢 kidsgodspeed 30.0 pts (-20.0)",
        "4. 🐢 Late 30.0 pts (-20.0)",
    ]


def test_everyone_tied_means_no_last_place() -> None:
    rows = [StandingRow(1, JK, 0), StandingRow(1, GO, 0)]
    assert format_standings(rows).splitlines()[1:] == [
        "1. 🏆 jkslots (pisit manoo) 0.0 pts",
        "1. 🏆 GO-GO Team (settakarn) 0.0 pts",
    ]
