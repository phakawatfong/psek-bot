"""Copy nbafantasy data for the participants' entries into SQLite.

Each sync first makes the participants match seed/participants.csv (see services/participants.py).

A sync only fetches what can still change or is still missing: games and stats for days
nbafantasy hasn't marked data_checked, and picks for each entry-day not stored yet (for
example, a friend who registers mid-season).
"""

import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from fantasy_bot.clients import nbafantasy as api
from fantasy_bot.models.nbafantasy import Day, Entry, LeagueTeam, SyncResult
from fantasy_bot.repositories import nbafantasy as repo
from fantasy_bot.repositories import participants, season
from fantasy_bot.services.participants import apply_file

Fetch = Callable[[str], Awaitable[Any]]
MAX_LEAGUE_PAGES = 5  # 50 teams a page; a friends league is one page

log = logging.getLogger(__name__)


async def sync_now(
    session: Session, season_id: str, participants_file: Path | None = None
) -> SyncResult:
    async with api.open_client() as client:
        return await sync_season(
            session, client.fetch, season_id, datetime.now(UTC), participants_file
        )


async def sync_season(
    session: Session,
    fetch: Fetch,
    season_id: str,
    now: datetime,
    participants_file: Path | None = None,
) -> SyncResult:
    run_id = repo.start_sync_run(session, season_id, now.isoformat())
    try:
        result = await _sync(session, fetch, season_id, now, participants_file)
    except Exception as e:
        session.rollback()  # drop the failed step's partial writes; earlier steps stay committed
        repo.finish_sync_run(session, run_id, datetime.now(UTC).isoformat(), None, repr(e))
        raise
    repo.finish_sync_run(session, run_id, datetime.now(UTC).isoformat(), len(result.days_synced))
    return result


async def _sync(
    session: Session,
    fetch: Fetch,
    season_id: str,
    now: datetime,
    participants_file: Path | None,
) -> SyncResult:
    stamp = now.isoformat()
    boot_raw = await fetch(api.bootstrap_path())
    boot = api.parse_bootstrap(boot_raw)
    league_teams = await _fetch_league(fetch, season.league_id(session, season_id))
    repo.save_raw(session, season_id, api.bootstrap_path(), boot_raw, stamp)
    repo.upsert_teams(session, season_id, boot.teams)
    repo.upsert_players(session, season_id, boot.players)
    repo.upsert_days(session, season_id, boot.days)
    repo.upsert_league_teams(session, season_id, league_teams)
    session.commit()

    # After the league's teams are stored (the file is checked against them) and before
    # fetching entries, so someone just added gets their points in this same sync.
    if participants_file is not None:
        _apply_participants(session, season_id, participants_file)

    entries = await _fetch_entries(fetch, participants.entry_ids(session, season_id))
    repo.upsert_entries(session, season_id, entries)
    session.commit()

    final = repo.final_day_ids(session, season_id)
    stored = repo.synced_entry_days(session, season_id)
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
            await _sync_day(session, fetch, season_id, day, entry_ids, refresh_day, stamp)
            synced.append(day)

    mismatches = repo.reconcile_mismatches(
        session, season_id, [d.day_id for d in synced if d.data_checked]
    )
    for m in mismatches:
        log.warning("entry %s day %s: official %s, rebuilt %s", *vars(m).values())
    return SyncResult([d.day_id for d in synced], len(entries), mismatches)


def _apply_participants(session: Session, season_id: str, path: Path) -> None:
    update = apply_file(session, season_id, path)
    for problem in update.problems:
        log.warning("participants file: %s", problem)
    if update.applied and (update.added or update.changed or update.removed):
        log.info(
            "participants file: added %s, changed start week of %s, removed %s",
            update.added or "nobody",
            update.changed or "nobody",
            update.removed or "nobody",
        )


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
    session: Session,
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

    # One commit per day, after every fetch: a failed fetch never leaves a half-written day.
    if day_raw:
        fixtures_raw, live_raw = day_raw
        repo.save_raw(session, season_id, api.fixtures_path(day.day_id), fixtures_raw, stamp)
        repo.save_raw(session, season_id, api.live_path(day.day_id), live_raw, stamp)
        repo.upsert_fixtures(session, season_id, api.parse_fixtures(fixtures_raw))
        repo.replace_day_stats(session, season_id, day.day_id, api.parse_live(live_raw))
        if day.data_checked:
            repo.mark_day_final(session, season_id, day.day_id)
    for entry_id, raw in picks_raw.items():
        repo.save_raw(session, season_id, api.picks_path(entry_id, day.day_id), raw, stamp)
        entry_day, picks = api.parse_picks(raw, entry_id, day.day_id)
        repo.upsert_entry_day(session, season_id, entry_day)
        repo.replace_picks(session, season_id, entry_id, day.day_id, picks)
    session.commit()


def _started(day: Day, now: datetime) -> bool:
    return datetime.fromisoformat(day.deadline_time) <= now
