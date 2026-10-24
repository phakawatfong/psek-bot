"""Copy nbafantasy data for the tracked entries into SQLite.

A sync only fetches what can still change or is still missing: games and stats for days
nbafantasy hasn't marked data_checked, and picks for each entry-day not stored yet (for
example, a friend who registers mid-season).
"""

import logging
import sqlite3
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any

from fantasy_bot.clients import nbafantasy as api
from fantasy_bot.models import Day, Entry, LeagueTeam, SyncResult
from fantasy_bot.repositories import sync as repo

Fetch = Callable[[str], Awaitable[Any]]
SCHEDULE_REFRESH = timedelta(hours=6)
MAX_LEAGUE_PAGES = 5  # 50 teams a page; a friends league is one page

log = logging.getLogger(__name__)


async def sync_now(conn: sqlite3.Connection, season_id: str) -> SyncResult:
    async with api.open_client() as client:
        return await sync_season(conn, client.fetch, season_id, datetime.now(UTC))


async def sync_season(
    conn: sqlite3.Connection, fetch: Fetch, season_id: str, now: datetime
) -> SyncResult:
    run_id = repo.start_sync_run(conn, season_id, now.isoformat())
    try:
        result = await _sync(conn, fetch, season_id, now)
    except Exception as e:
        repo.finish_sync_run(conn, run_id, datetime.now(UTC).isoformat(), None, repr(e))
        raise
    repo.finish_sync_run(conn, run_id, datetime.now(UTC).isoformat(), len(result.days_synced))
    return result


async def _sync(
    conn: sqlite3.Connection, fetch: Fetch, season_id: str, now: datetime
) -> SyncResult:
    stamp = now.isoformat()
    boot_raw = await fetch(api.bootstrap_path())
    boot = api.parse_bootstrap(boot_raw)
    league_teams = await _fetch_league(fetch, repo.league_id(conn, season_id))
    entries = await _fetch_entries(fetch, repo.tracked_entry_ids(conn, season_id))

    with conn:
        repo.save_raw(conn, season_id, api.bootstrap_path(), boot_raw, stamp)
        repo.upsert_teams(conn, season_id, boot.teams)
        repo.upsert_players(conn, season_id, boot.players)
        repo.upsert_days(conn, season_id, boot.days)
        repo.upsert_league_teams(conn, season_id, league_teams)
        repo.upsert_entries(conn, season_id, entries)

    await _sync_season_schedule(conn, fetch, season_id, now)
    final = repo.final_day_ids(conn, season_id)
    stored = repo.synced_entry_days(conn, season_id)
    synced: list[Day] = []
    for day in (d for d in boot.days if _started(d, now)):
        refresh_day = day.day_id not in final
        entry_ids = [
            e.entry_id
            for e in entries
            if e.started_day <= day.day_id
            and (refresh_day or (e.entry_id, day.day_id) not in stored)
        ]
        if refresh_day or entry_ids:
            await _sync_day(conn, fetch, season_id, day, entry_ids, refresh_day, stamp)
            synced.append(day)

    mismatches = repo.reconcile_mismatches(
        conn, season_id, [d.day_id for d in synced if d.data_checked]
    )
    for m in mismatches:
        log.warning("entry %s day %s: official %s, rebuilt %s", *vars(m).values())
    return SyncResult([d.day_id for d in synced], len(entries), mismatches)


async def _fetch_league(fetch: Fetch, league_id: int) -> list[LeagueTeam]:
    """Every team in the league, so friends can pick theirs when registering."""
    teams: list[LeagueTeam] = []
    for page in range(1, MAX_LEAGUE_PAGES + 1):
        page_teams, has_next = api.parse_league_page(await fetch(api.league_path(league_id, page)))
        teams += page_teams
        if not has_next:
            break
    return teams


async def _fetch_entries(fetch: Fetch, entry_ids: list[int]) -> list[Entry]:
    entries = []
    for entry_id in entry_ids:
        try:
            entries.append(api.parse_entry(await fetch(api.entry_path(entry_id))))
        except api.NotFound:
            log.warning("entry %s does not exist on nbafantasy; skipping it", entry_id)
    return entries


async def _sync_day(
    conn: sqlite3.Connection,
    fetch: Fetch,
    season_id: str,
    day: Day,
    entry_ids: list[int],
    refresh_day: bool,
    stamp: str,
) -> None:
    """Fetch picks for `entry_ids`, plus the day's games and stats when `refresh_day`."""
    day_raw = (
        (await fetch(api.fixtures_path(day.day_id)), await fetch(api.live_path(day.day_id)))
        if refresh_day
        else None
    )
    picks_raw: dict[int, Any] = {}
    for entry_id in entry_ids:
        with suppress(api.NotFound):  # nbafantasy has no picks for this entry on this day
            picks_raw[entry_id] = await fetch(api.picks_path(entry_id, day.day_id))

    with conn:  # one transaction per day: a failed fetch never leaves a half-written day
        if day_raw:
            fixtures_raw, live_raw = day_raw
            repo.save_raw(conn, season_id, api.fixtures_path(day.day_id), fixtures_raw, stamp)
            repo.save_raw(conn, season_id, api.live_path(day.day_id), live_raw, stamp)
            repo.upsert_fixtures(conn, season_id, api.parse_fixtures(fixtures_raw))
            repo.replace_day_stats(conn, season_id, day.day_id, api.parse_live(live_raw))
            if day.data_checked:
                repo.mark_day_final(conn, season_id, day.day_id)
        for entry_id, raw in picks_raw.items():
            repo.save_raw(conn, season_id, api.picks_path(entry_id, day.day_id), raw, stamp)
            entry_day, picks = api.parse_picks(raw, entry_id, day.day_id)
            repo.upsert_entry_day(conn, season_id, entry_day)
            repo.replace_picks(conn, season_id, entry_id, day.day_id, picks)


async def _sync_season_schedule(
    conn: sqlite3.Connection, fetch: Fetch, season_id: str, now: datetime
) -> None:
    """Every game of the season, so the schedule works for any day or gameweek.

    It is about 430KB, so it is refreshed only every SCHEDULE_REFRESH; scores for days in play
    stay current through each day's own fixtures fetch.
    """
    path = api.season_fixtures_path()
    fetched_at = repo.raw_fetched_at(conn, season_id, path)
    if fetched_at and now - datetime.fromisoformat(fetched_at) < SCHEDULE_REFRESH:
        return
    raw = await fetch(path)
    with conn:
        repo.save_raw(conn, season_id, path, raw, now.isoformat())
        repo.upsert_fixtures(conn, season_id, api.parse_fixtures(raw))


def _started(day: Day, now: datetime) -> bool:
    return datetime.fromisoformat(day.deadline_time) <= now
