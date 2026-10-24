from fantasy_bot.bot.commands.formatting import split_message
from fantasy_bot.bot.commands.participants import format_participants
from fantasy_bot.bot.commands.points import format_day_points, format_gameweek_points
from fantasy_bot.bot.commands.schedule import format_gameweek, format_schedule
from fantasy_bot.bot.commands.standings import format_standings
from fantasy_bot.models import (
    DayPoints,
    DayPointsRow,
    DaySchedule,
    Game,
    GameweekSchedule,
    ParticipantName,
    ParticipantRow,
    StandingRow,
)

JK = ParticipantName("jkslots", "pisit manoo")
GO = ParticipantName("GO-GO Team", "settakarn")


def test_standings_show_gap_to_leader() -> None:
    rows = [StandingRow(1, JK, 4760), StandingRow(2, GO, 4500)]
    assert format_standings(rows, None) == (
        "**Season standings**\n"
        "1. 🏆 jkslots (pisit manoo) 476.0 pts\n"
        "2. 🐢 GO-GO Team (settakarn) 450.0 pts (-26.0)"
    )


def test_gameweek_standings_title_and_empty_case() -> None:
    assert format_standings([], 3) == "**Gameweek 3 standings**\nNo approved participants yet."


def test_day_points_say_whether_they_can_still_change() -> None:
    report = DayPoints(5, "Gameweek 1 - Day 5", False, [DayPointsRow(1, GO, 2120, 6620)])
    assert format_day_points(report) == (
        "**Gameweek 1 - Day 5** (live, may still change)\n"
        "1. 🏆 GO-GO Team (settakarn) 212.0 pts (season 662.0)"
    )
    assert format_day_points(None) == "No points synced for that day yet."


def test_schedule_shows_date_and_times_in_utc_plus_7_away_at_home() -> None:
    day = DaySchedule(
        3,
        "Gameweek 1 - Day 3",
        [
            Game("2026-10-23T20:00:00Z", "MIL", "ATL", 125, 132, True),
            Game("2026-10-24T00:30:00Z", "BOS", "NYK", None, None, False),
        ],
    )
    assert format_schedule(day, {}) == (
        "**Gameweek 1 - Day 3** (Sat 24 Oct, UTC+7)\n"
        "03:00 ATL 132 @ MIL 125 (final)\n"
        "07:30 NYK @ BOS"
    )


def test_game_past_midnight_utc_plus_7_names_its_date() -> None:
    day = DaySchedule(
        3,
        "Gameweek 1 - Day 3",
        [
            Game("2026-10-23T12:00:00Z", "MIL", "ATL", None, None, False),
            Game("2026-10-23T17:30:00Z", "BOS", "NYK", None, None, False),
        ],
    )
    assert format_schedule(day, {}).splitlines() == [
        "**Gameweek 1 - Day 3** (Fri 23 Oct, UTC+7)",
        "19:00 ATL @ MIL",
        "Sat 24 Oct 00:30 NYK @ BOS",
    ]


def test_participants_group_every_league_team_and_show_who_owns_it() -> None:
    rows = [
        ParticipantRow(JK, 31818, "approved", 312345678901234567, 1),
        ParticipantRow(GO, 40823, "approved", 2, 1),  # entered by hand: placeholder id
        ParticipantRow(ParticipantName("Dream team", ""), 40791, "pending", 412345678901234567, 2),
        ParticipantRow(ParticipantName("Bench Mob", "x"), 55555, "unregistered"),
    ]
    assert format_participants(rows) == (
        "**In the pool**\n"
        "- jkslots (pisit manoo), <@312345678901234567>\n"
        "- GO-GO Team (settakarn), not linked to Discord yet\n"
        "\n"
        "**Waiting for approval**\n"
        "- Dream team, <@412345678901234567>\n"
        "\n"
        "**Not registered yet**\n"
        "- Bench Mob (x)"
    )
    assert format_participants([]).startswith("No teams yet")


def test_ties_share_the_first_and_last_badges() -> None:
    dream, kids = ParticipantName("Dream team", ""), ParticipantName("kidsgodspeed", "")
    rows = [
        StandingRow(1, JK, 500),
        StandingRow(1, GO, 500),
        StandingRow(3, dream, 400),
        StandingRow(4, kids, 300),
        StandingRow(4, ParticipantName("Late", ""), 300),
    ]
    assert format_standings(rows, None).splitlines()[1:] == [
        "1. 🏆 jkslots (pisit manoo) 50.0 pts",
        "1. 🏆 GO-GO Team (settakarn) 50.0 pts",
        "3. Dream team 40.0 pts (-10.0)",
        "4. 🐢 kidsgodspeed 30.0 pts (-20.0)",
        "4. 🐢 Late 30.0 pts (-20.0)",
    ]


def test_everyone_tied_means_no_last_place() -> None:
    rows = [StandingRow(1, JK, 0), StandingRow(1, GO, 0)]
    assert format_standings(rows, 2).splitlines()[1:] == [
        "1. 🏆 jkslots (pisit manoo) 0.0 pts",
        "1. 🏆 GO-GO Team (settakarn) 0.0 pts",
    ]


def test_schedule_shows_team_logo_emojis_once_loaded() -> None:
    day = DaySchedule(
        5, "Gameweek 1 - Day 5", [Game("2026-10-24T00:30:00Z", "BOS", "NYK", None, None, False)]
    )
    icons = {"NYK": "<:nba_NYK:1>", "BOS": "<:nba_BOS:2>"}
    assert format_schedule(day, icons).splitlines()[1] == (
        "07:30 <:nba_NYK:1> NYK @ <:nba_BOS:2> BOS"
    )


def test_split_message_packs_blocks_without_breaking_them() -> None:
    assert split_message(["a" * 900, "b" * 900, "c" * 900], limit=2000) == [
        "a" * 900 + "\n\n" + "b" * 900,
        "c" * 900,
    ]


def test_long_gameweek_becomes_several_messages_split_at_days() -> None:
    games = [Game("2026-10-24T00:30:00Z", "BOS", "NYK", None, None, False)] * 12
    icons = {"NYK": "<:nba_NYK:1234567890123456789>", "BOS": "<:nba_BOS:1234567890123456789>"}
    week = GameweekSchedule(
        2, [DaySchedule(d, f"Gameweek 2 - Day {d}", games) for d in range(7, 13)]
    )
    messages = format_gameweek(week, icons)
    assert len(messages) > 1 and all(len(m) <= 2000 for m in messages)
    assert all(m.startswith("**Gameweek 2 - Day") for m in messages)
    assert sum(m.count("**Gameweek 2 - Day") for m in messages) == 6


def test_missing_day_says_the_gameweek_has_no_such_day() -> None:
    assert format_schedule(None, {}) == "That gameweek has no such day."


def test_gameweek_points_list_each_day_and_handle_an_unplayed_week() -> None:
    days = [
        DayPoints(d, f"Gameweek 1 - Day {d}", True, [DayPointsRow(1, GO, 100 * d, 300 * d)])
        for d in (1, 2)
    ]
    assert format_gameweek_points(days) == [
        "**Gameweek 1 - Day 1** (final)\n1. 🏆 GO-GO Team (settakarn) 10.0 pts (season 30.0)\n\n"
        "**Gameweek 1 - Day 2** (final)\n1. 🏆 GO-GO Team (settakarn) 20.0 pts (season 60.0)"
    ]
    assert format_gameweek_points([]) == ["No points synced for that gameweek yet."]
