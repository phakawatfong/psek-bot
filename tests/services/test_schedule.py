import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from fantasy_bot.clients import nbafantasy as api
from fantasy_bot.services.schedule import ScheduleError, fetch_schedule, get_schedule


def bootstrap(finished: bool = False) -> dict[str, Any]:
    return {
        "teams": [
            {"id": 1, "name": "Alpha", "short_name": "ALP"},
            {"id": 2, "name": "Bravo", "short_name": "BRV"},
        ],
        "elements": [],
        "phases": [
            {"name": "Gameweek 1", "start_event": 1, "stop_event": 2},
            {"name": "Gameweek 2", "start_event": 3, "stop_event": 5},
        ],
        "events": [
            {
                "id": n,
                "name": f"Event {n}",
                "deadline_time": f"2026-10-{20 + n}T22:30:00Z",
                "finished": finished,
                "data_checked": finished,
            }
            for n in range(1, 6)
        ],
    }


def fixture(event: int) -> dict[str, Any]:
    return {
        "id": event,
        "event": event,
        "code": event,
        "kickoff_time": f"2026-10-{20 + event}T23:00:00Z",
        "team_h": 1,
        "team_a": 2,
        "team_h_score": None,
        "team_a_score": None,
        "finished": False,
    }


class FakeApi:
    def __init__(self) -> None:
        self.boot = bootstrap()
        self.calls: list[str] = []

    async def fetch(self, path: str) -> Any:
        self.calls.append(path)
        if path == api.bootstrap_path():
            return self.boot
        event = int(path.split("=")[1])
        return [fixture(event)]


@pytest.mark.parametrize(
    ("gameweek", "day", "events"),
    [(2, 3, [5]), (None, 2, [4]), (None, None, [3]), (1, None, [1, 2])],
)
def test_option_combinations_fetch_only_selected_days(
    gameweek: int | None, day: int | None, events: list[int]
) -> None:
    fake = FakeApi()
    now = datetime(2026, 10, 24, 1, tzinfo=UTC)
    days = asyncio.run(fetch_schedule(fake.fetch, now, gameweek, day))
    assert [d.event_id for d in days] == events
    assert fake.calls == [api.bootstrap_path(), *(api.fixtures_path(n) for n in events)]
    assert days[0].games[0].away_team == "BRV"


@pytest.mark.parametrize(
    ("stamp", "event", "upcoming"),
    [
        ("2026-10-20T00:00:00+00:00", 1, True),
        ("2026-10-23T22:29:59+00:00", 2, False),
        ("2026-10-23T22:30:00+00:00", 3, False),
        ("2026-10-24T05:30:00+07:00", 3, False),
        ("2026-10-24T17:00:00+00:00", 3, False),
    ],
)
def test_defaults_follow_deadlines_not_calendar_midnight(
    stamp: str, event: int, upcoming: bool
) -> None:
    days = asyncio.run(fetch_schedule(FakeApi().fetch, datetime.fromisoformat(stamp)))
    assert [(d.event_id, d.upcoming) for d in days] == [(event, upcoming)]


@pytest.mark.parametrize(("gameweek", "day"), [(None, None), (None, 1)])
def test_finished_season_requires_explicit_gameweek(gameweek: int | None, day: int | None) -> None:
    fake = FakeApi()
    fake.boot = bootstrap(finished=True)
    with pytest.raises(ScheduleError, match="season has ended"):
        asyncio.run(fetch_schedule(fake.fetch, datetime(2026, 11, 1, tzinfo=UTC), gameweek, day))
    days = asyncio.run(fetch_schedule(fake.fetch, datetime(2026, 11, 1, tzinfo=UTC), 2, 1))
    assert days[0].event_id == 3


@pytest.mark.parametrize(
    ("gameweek", "day", "message"),
    [(1, 3, "Gameweek 1 has days 1, 2"), (99, 1, "not in the fantasy schedule")],
)
def test_invalid_selection_does_not_fetch_fixtures(gameweek: int, day: int, message: str) -> None:
    fake = FakeApi()
    with pytest.raises(ScheduleError, match=message):
        asyncio.run(fetch_schedule(fake.fetch, datetime(2026, 10, 24, tzinfo=UTC), gameweek, day))
    assert fake.calls == [api.bootstrap_path()]


def test_empty_calendar_is_explained() -> None:
    fake = FakeApi()
    fake.boot["events"] = []
    with pytest.raises(ScheduleError, match="No fantasy schedule"):
        asyncio.run(fetch_schedule(fake.fetch, datetime(2026, 10, 24, tzinfo=UTC)))


@pytest.mark.parametrize(
    "error", [api.FetchError("offline"), api.NotFound("missing"), TimeoutError()]
)
def test_api_errors_become_safe_reply(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    client = Mock(fetch=AsyncMock(side_effect=error))

    @asynccontextmanager
    async def open_client() -> Any:
        yield client

    monkeypatch.setattr(api, "open_client", open_client)
    with pytest.raises(ScheduleError, match="unavailable from nbafantasy"):
        asyncio.run(get_schedule())


def test_unknown_kickoff_and_sorting() -> None:
    raw = [fixture(3) | {"kickoff_time": None}, fixture(3)]
    games = api.parse_schedule_games(raw, 3, {1: "ALP", 2: "BRV"})
    assert games[0].kickoff is not None
    assert games[1].kickoff is None


def test_mismatched_event_is_rejected() -> None:
    with pytest.raises(ValueError, match="requested fantasy day"):
        api.parse_schedule_games([fixture(3)], 4, {1: "ALP", 2: "BRV"})


def test_sync_still_rejects_missing_kickoff() -> None:
    with pytest.raises(ValueError, match="without a kickoff"):
        api.parse_fixtures([fixture(3) | {"kickoff_time": None}])
