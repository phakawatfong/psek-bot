"""Reader for nbafantasy.nba.com's public, undocumented JSON API.

Fetching and parsing are separate so parsers can be tested against saved responses.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import aiohttp
from pydantic import TypeAdapter

from fantasy_bot.contracts.nbafantasy import (
    BootstrapPayload,
    EntryPayload,
    FixturePayload,
    LeagueStandingsPayload,
    LivePayload,
    PicksPayload,
)
from fantasy_bot.models.nbafantasy import (
    Bootstrap,
    Day,
    Entry,
    EntryDay,
    Fixture,
    LeagueTeam,
    Pick,
    Player,
    PlayerStat,
    Team,
)
from fantasy_bot.models.schedule import ScheduleDay, ScheduleGame

BASE_URL = "https://nbafantasy.nba.com/api/"
USER_AGENT = "psek-nba-bot/0.1 (private friends league)"
ATTEMPTS = 3
RETRY_STATUSES = {429, 500, 502, 503, 504}
POSITIONS = {1: "BC", 2: "FC"}
_FIXTURES = TypeAdapter(list[FixturePayload])


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


def league_path(league_id: int, page: int) -> str:
    return f"leagues-classic/{league_id}/standings/?page_standings={page}"


def live_path(day_id: int) -> str:
    return f"event/{day_id}/live/"


def entry_path(entry_id: int) -> str:
    return f"entry/{entry_id}/"


def picks_path(entry_id: int, day_id: int) -> str:
    return f"entry/{entry_id}/event/{day_id}/picks/"


# Parsers: raw JSON in, validated against nbafantasy_payloads, rows out.


def parse_bootstrap(raw: Any) -> Bootstrap:
    payload = BootstrapPayload.model_validate(raw)
    gameweeks = sorted(
        (p for p in payload.phases if p.name.startswith("Gameweek")), key=lambda p: p.start_event
    )
    gameweek_of = {
        day: number
        for number, phase in enumerate(gameweeks, start=1)
        for day in range(phase.start_event, phase.stop_event + 1)
    }
    return Bootstrap(
        teams=[Team(t.id, t.name, t.short_name) for t in payload.teams],
        players=[
            Player(
                player_id=p.id,
                nba_person_id=p.code,
                web_name=p.web_name,
                first_name=p.first_name,
                second_name=p.second_name,
                team_id=p.team,
                position=POSITIONS[p.element_type],
            )
            for p in payload.elements
        ],
        days=[
            Day(
                day_id=e.id,
                gameweek=gameweek_of[e.id],
                name=e.name,
                deadline_time=e.deadline_time,
                finished=e.finished,
                data_checked=e.data_checked,
            )
            for e in payload.events
        ],
    )


def parse_fixtures(raw: Any) -> list[Fixture]:
    fixtures = _FIXTURES.validate_python(raw)
    # Stored stats refer to started games, for which the database requires a kickoff time.
    if any(f.kickoff_time is None for f in fixtures):
        raise ValueError("Cannot sync a fixture without a kickoff time")
    return [
        Fixture(
            fixture_id=f.id,
            day_id=f.event,
            nba_game_id=f"{f.code:010d}",
            kickoff_time=f.kickoff_time,
            home_team_id=f.team_h,
            away_team_id=f.team_a,
            home_score=f.team_h_score,
            away_score=f.team_a_score,
            finished=f.finished,
        )
        for f in fixtures
        if f.kickoff_time is not None
    ]


def parse_schedule_calendar(raw: Any) -> tuple[list[ScheduleDay], dict[int, str]]:
    payload = BootstrapPayload.model_validate(raw)
    phases = [p for p in payload.phases if p.name.startswith("Gameweek ")]
    days = [
        ScheduleDay(
            gameweek=int(phase.name.removeprefix("Gameweek ")),
            day=event.id - phase.start_event + 1,
            event_id=event.id,
            deadline=_timestamp(event.deadline_time),
            finished=event.finished,
        )
        for phase in phases
        for event in payload.events
        if phase.start_event <= event.id <= phase.stop_event
    ]
    return sorted(days, key=lambda d: d.deadline), {t.id: t.short_name for t in payload.teams}


def parse_schedule_games(raw: Any, event_id: int, teams: dict[int, str]) -> list[ScheduleGame]:
    fixtures = _FIXTURES.validate_python(raw)
    if any(f.event != event_id for f in fixtures):
        raise ValueError("Fixtures do not belong to the requested fantasy day")
    games = [
        ScheduleGame(
            away_team=teams[f.team_a],
            home_team=teams[f.team_h],
            kickoff=_timestamp(f.kickoff_time) if f.kickoff_time else None,
            away_score=f.team_a_score,
            home_score=f.team_h_score,
            finished=f.finished,
        )
        for f in fixtures
    ]
    return sorted(games, key=lambda g: (g.kickoff is None, g.kickoff, g.away_team, g.home_team))


def _timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        raise ValueError("nbafantasy timestamp has no timezone")
    return timestamp


def parse_live(raw: Any) -> list[PlayerStat]:
    return [
        PlayerStat(game.fixture, element.id, s.identifier, s.value, s.points)
        for element in LivePayload.model_validate(raw).elements
        for game in element.explain
        for s in game.stats
    ]


def parse_entry(raw: Any) -> Entry:
    payload = EntryPayload.model_validate(raw)
    return Entry(
        entry_id=payload.id,
        entry_name=payload.name,
        manager_name=f"{payload.player_first_name} {payload.player_last_name}",
        started_day=payload.started_event,
    )


def parse_picks(raw: Any, entry_id: int, day_id: int) -> tuple[EntryDay, list[Pick]]:
    payload = PicksPayload.model_validate(raw)
    history = payload.entry_history
    entry_day = EntryDay(
        entry_id=entry_id,
        day_id=day_id,
        points=history.points,
        total_points=history.total_points,
        transfers_cost=history.event_transfers_cost,
        points_on_bench=history.points_on_bench,
        overall_rank=history.overall_rank,
    )
    picks = [
        Pick(entry_id, day_id, p.element, p.position, p.multiplier, p.is_captain)
        for p in payload.picks
    ]
    return entry_day, picks


def parse_league_page(raw: Any) -> tuple[list[LeagueTeam], bool]:
    """One page of a league's teams, and whether another page follows."""
    page = LeagueStandingsPayload.model_validate(raw).standings
    teams = [LeagueTeam(r.entry, r.entry_name, r.player_name) for r in page.results]
    return teams, page.has_next
