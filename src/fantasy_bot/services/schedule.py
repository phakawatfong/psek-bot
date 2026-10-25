"""Fetch the selected fantasy day's schedule without writing to the database."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import aiohttp

from fantasy_bot.clients import nbafantasy as api
from fantasy_bot.models.schedule import ScheduleDay

log = logging.getLogger(__name__)
Fetch = Callable[[str], Awaitable[Any]]


class ScheduleError(Exception):
    """A schedule selection or availability problem safe to show in Discord."""


async def get_schedule(gameweek: int | None = None, day: int | None = None) -> list[ScheduleDay]:
    try:
        # Bound the whole request, including retries and whole-week requests.
        async with asyncio.timeout(90), api.open_client() as client:
            return await fetch_schedule(client.fetch, datetime.now(UTC), gameweek, day)
    except (aiohttp.ClientError, TimeoutError, api.FetchError, api.NotFound, ValueError, KeyError):
        log.exception("Could not fetch the fantasy schedule")
        raise ScheduleError(
            "Schedule is unavailable from nbafantasy. Please try again later."
        ) from None


async def fetch_schedule(
    fetch: Fetch, now: datetime, gameweek: int | None = None, day: int | None = None
) -> list[ScheduleDay]:
    calendar, teams = api.parse_schedule_calendar(await fetch(api.bootstrap_path()))
    selected = select_days(calendar, now, gameweek, day)
    result = []
    for selected_day in selected:
        raw = await fetch(api.fixtures_path(selected_day.event_id))
        result.append(
            replace(
                selected_day,
                games=api.parse_schedule_games(raw, selected_day.event_id, teams),
                upcoming=selected_day.deadline > now,
            )
        )
    return result


def select_days(
    calendar: list[ScheduleDay], now: datetime, gameweek: int | None, day: int | None
) -> list[ScheduleDay]:
    if not calendar:
        raise ScheduleError("No fantasy schedule is available yet.")
    calendar = sorted(calendar, key=lambda d: d.deadline)
    if gameweek is None:
        last = calendar[-1]
        if now >= last.deadline and last.finished:
            raise ScheduleError(
                "The fantasy season has ended. Choose a gameweek to view its games."
            )
        current = next((d for d in reversed(calendar) if d.deadline <= now), calendar[0])
        gameweek = current.gameweek
        if day is None:
            day = current.day
    week = sorted((d for d in calendar if d.gameweek == gameweek), key=lambda d: d.day)
    if not week:
        raise ScheduleError(f"Gameweek {gameweek} is not in the fantasy schedule.")
    if day is None:
        return week
    selected = [d for d in week if d.day == day]
    if not selected:
        choices = ", ".join(str(d.day) for d in week)
        raise ScheduleError(f"Gameweek {gameweek} has days {choices}. Choose one of those days.")
    return selected
