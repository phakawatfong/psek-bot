"""Reader for nbafantasy.nba.com's public, undocumented JSON API.

Fetching and parsing are separate so parsers can be tested against saved responses.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aiohttp

from fantasy_bot.models import (
    Bootstrap,
    Day,
    Entry,
    EntryDay,
    Fixture,
    Pick,
    Player,
    PlayerStat,
    Team,
)

BASE_URL = "https://nbafantasy.nba.com/api/"
USER_AGENT = "psek-nba-bot/0.1 (private friends league)"
ATTEMPTS = 3
RETRY_STATUSES = {429, 500, 502, 503, 504}
POSITIONS = {1: "BC", 2: "FC"}


class NotFound(Exception):
    pass


class FetchError(Exception):
    pass


class NbaFantasyClient:
    def __init__(self, session: aiohttp.ClientSession, delay_s: float = 0.5) -> None:
        self._session = session
        self._delay_s = delay_s

    async def fetch(self, path: str) -> Any:
        """GET BASE_URL + path as JSON. Pauses before each request; retries transient errors."""
        url = BASE_URL + path
        problem = ""
        for attempt in range(1, ATTEMPTS + 1):
            await asyncio.sleep(self._delay_s)
            try:
                async with self._session.get(url) as resp:
                    if resp.status == 404:
                        raise NotFound(url)
                    if resp.status not in RETRY_STATUSES:
                        resp.raise_for_status()
                        return await resp.json()
                    problem = f"HTTP {resp.status}"
            except (aiohttp.ClientConnectionError, TimeoutError) as e:
                problem = repr(e)
            if attempt < ATTEMPTS:
                await asyncio.sleep(2**attempt)
        raise FetchError(f"{url} failed {ATTEMPTS} times, last: {problem}")


@asynccontextmanager
async def open_client() -> AsyncIterator[NbaFantasyClient]:
    async with aiohttp.ClientSession(
        headers={"User-Agent": USER_AGENT}, timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        yield NbaFantasyClient(session)


# Request paths.


def bootstrap_path() -> str:
    return "bootstrap-static/"


def fixtures_path(day_id: int) -> str:
    return f"fixtures/?event={day_id}"


def live_path(day_id: int) -> str:
    return f"event/{day_id}/live/"


def entry_path(entry_id: int) -> str:
    return f"entry/{entry_id}/"


def picks_path(entry_id: int, day_id: int) -> str:
    return f"entry/{entry_id}/event/{day_id}/picks/"


# Parsers: raw JSON in, rows out.


def parse_bootstrap(raw: Any) -> Bootstrap:
    gameweeks = sorted(
        (p for p in raw["phases"] if p["name"].startswith("Gameweek")),
        key=lambda p: p["start_event"],
    )
    gameweek_of = {
        day: number
        for number, phase in enumerate(gameweeks, start=1)
        for day in range(phase["start_event"], phase["stop_event"] + 1)
    }
    return Bootstrap(
        teams=[Team(t["id"], t["name"], t["short_name"]) for t in raw["teams"]],
        players=[
            Player(
                player_id=p["id"],
                nba_person_id=p["code"],
                web_name=p["web_name"],
                first_name=p["first_name"],
                second_name=p["second_name"],
                team_id=p["team"],
                position=POSITIONS[p["element_type"]],
            )
            for p in raw["elements"]
        ],
        days=[
            Day(
                day_id=e["id"],
                gameweek=gameweek_of[e["id"]],
                name=e["name"],
                deadline_time=e["deadline_time"],
                finished=e["finished"],
                data_checked=e["data_checked"],
            )
            for e in raw["events"]
        ],
    )


def parse_fixtures(raw: Any) -> list[Fixture]:
    return [
        Fixture(
            fixture_id=f["id"],
            day_id=f["event"],
            nba_game_id=f"{f['code']:010d}",
            kickoff_time=f["kickoff_time"],
            home_team_id=f["team_h"],
            away_team_id=f["team_a"],
            home_score=f["team_h_score"],
            away_score=f["team_a_score"],
            finished=f["finished"],
        )
        for f in raw
    ]


def parse_live(raw: Any) -> list[PlayerStat]:
    return [
        PlayerStat(game["fixture"], element["id"], s["identifier"], s["value"], s["points"])
        for element in raw["elements"]
        for game in element["explain"]
        for s in game["stats"]
    ]


def parse_entry(raw: Any) -> Entry:
    return Entry(
        entry_id=raw["id"],
        entry_name=raw["name"],
        manager_name=f"{raw['player_first_name']} {raw['player_last_name']}",
        started_day=raw["started_event"],
    )


def parse_picks(raw: Any, entry_id: int, day_id: int) -> tuple[EntryDay, list[Pick]]:
    history = raw["entry_history"]
    entry_day = EntryDay(
        entry_id=entry_id,
        day_id=day_id,
        points=history["points"],
        total_points=history["total_points"],
        transfers_cost=history["event_transfers_cost"],
        points_on_bench=history["points_on_bench"],
        overall_rank=history["overall_rank"],
    )
    picks = [
        Pick(entry_id, day_id, p["element"], p["position"], p["multiplier"], p["is_captain"])
        for p in raw["picks"]
    ]
    return entry_day, picks
