import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import Engine

from fantasy_bot.controllers import schedule
from fantasy_bot.database.connection import sessions
from fantasy_bot.models.schedule import ScheduleDay, ScheduleGame
from fantasy_bot.services.schedule import ScheduleError

DAY = ScheduleDay(2, 1, 7, datetime(2026, 10, 26, 22, 30, tzinfo=UTC), False)
GAME = ScheduleGame("ALP", "BRV", datetime(2026, 10, 26, 23, tzinfo=UTC), None, None, False)


def test_bangkok_date_and_completed_scores() -> None:
    game = replace(GAME, away_score=99, home_score=101, finished=True)
    [reply] = schedule.format_schedule([replace(DAY, games=[game])])
    assert "Gameweek 2 · Day 1" in reply
    assert "27 Oct 2026 06:00 · ALP @ BRV — Final 99-101" in reply


def test_tbd_empty_day_and_upcoming_label() -> None:
    days = [replace(DAY, games=[replace(GAME, kickoff=None)], upcoming=True), replace(DAY, day=2)]
    [reply] = schedule.format_schedule(days)
    assert "(upcoming)" in reply
    assert "Time TBD · ALP @ BRV" in reply
    assert "No games listed" in reply
    assert "Live" not in reply


def test_whole_week_reply_keeps_every_game_within_message_limit() -> None:
    days = [replace(DAY, day=n, games=[GAME] * 15) for n in range(1, 8)]
    replies = schedule.format_schedule(days)
    assert len(replies) > 1
    assert all(len(reply) <= 2000 for reply in replies)
    assert sum(reply.count("ALP @ BRV") for reply in replies) == 105
    assert sum(reply.count("Gameweek 2 · Day") for reply in replies) == 7


def test_team_markdown_is_escaped() -> None:
    [reply] = schedule.format_schedule([replace(DAY, games=[replace(GAME, away_team="**ALP**")])])
    assert r"\*\*ALP\*\*" in reply


@pytest.mark.parametrize("failed", [False, True])
def test_handler_defers_before_fetch_and_sends_followup(
    engine: Engine, monkeypatch: pytest.MonkeyPatch, failed: bool
) -> None:
    interaction = Mock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()

    async def get_schedule(gameweek: int | None, day: int | None) -> list[ScheduleDay]:
        interaction.response.defer.assert_awaited_once_with(thinking=True)
        assert (gameweek, day) == (2, 1)
        if failed:
            raise ScheduleError("Schedule is unavailable. Please try again later.")
        return [replace(DAY, games=[GAME])]

    monkeypatch.setattr(schedule, "get_schedule", get_schedule)
    asyncio.run(schedule.handler(sessions(engine), "test")(interaction, 2, 1))
    interaction.followup.send.assert_awaited_once()
    call = interaction.followup.send.call_args
    assert ("unavailable" if failed else "ALP @ BRV") in call.args[0]
    assert call.kwargs["allowed_mentions"].everyone is False
