from fantasy_bot.bot.commands.participants import format_participants
from fantasy_bot.bot.commands.points import format_day_points
from fantasy_bot.bot.commands.schedule import format_schedule
from fantasy_bot.bot.commands.standings import format_standings
from fantasy_bot.models import (
    DayPoints,
    DayPointsRow,
    DaySchedule,
    Game,
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
        "1. jkslots (pisit manoo) 476.0 pts\n"
        "2. GO-GO Team (settakarn) 450.0 pts (-26.0)"
    )


def test_gameweek_standings_title_and_empty_case() -> None:
    assert format_standings([], 3) == "**Gameweek 3 standings**\nNo approved participants yet."


def test_day_points_say_whether_they_can_still_change() -> None:
    report = DayPoints(5, "Gameweek 1 - Day 5", False, [DayPointsRow(1, GO, 2120, 6620)])
    assert format_day_points(report) == (
        "**Gameweek 1 - Day 5** (live, may still change)\n"
        "1. GO-GO Team (settakarn) 212.0 pts (season 662.0)"
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
    assert format_schedule(day) == (
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
        "**Participants (2)**\n"
        "- jkslots (pisit manoo), entry 31818, from gameweek 1\n"
        "- entry 40823, entry 40823, from gameweek 3 (pending approval)"
    )
