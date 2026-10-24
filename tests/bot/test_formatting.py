from fantasy_bot.bot.commands.formatting import split_message
from fantasy_bot.bot.commands.participants import format_participants
from fantasy_bot.bot.commands.points import format_day_points
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


def test_schedule_uses_discord_local_time_and_away_at_home() -> None:
    day = DaySchedule(
        3,
        "Gameweek 1 - Day 3",
        [
            Game("2026-10-23T20:00:00Z", "MIL", "ATL", 125, 132, True),
            Game("2026-10-24T00:30:00Z", "BOS", "NYK", None, None, False),
        ],
    )
    assert format_schedule(day, {}) == (
        "**Gameweek 1 - Day 3**\n"
        "<t:1792785600:t> ATL 132 @ MIL 125 (final)\n"
        "<t:1792801800:t> NYK @ BOS"
    )


def test_participants_mark_pending_ones() -> None:
    rows = [
        ParticipantRow(JK, 31818, 1, "approved"),
        ParticipantRow(ParticipantName("entry 40823", ""), 40823, 3, "pending"),
    ]
    assert format_participants(rows) == (
        "**Participants (2)**\n- jkslots (pisit manoo)\n- entry 40823 (pending approval)"
    )


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
        "<t:1792801800:t> <:nba_NYK:1> NYK @ <:nba_BOS:2> BOS"
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
