"""Writes for the nbafantasy sync. Every write converges, so re-running a sync is safe."""

import json
import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import astuple, fields
from typing import Any

from fantasy_bot.models import (
    Day,
    Entry,
    EntryDay,
    Fixture,
    Mismatch,
    Pick,
    Player,
    PlayerStat,
    Team,
)


def _upsert(
    conn: sqlite3.Connection, table: str, key: tuple[str, ...], season_id: str, rows: Sequence[Any]
) -> None:
    """Insert rows, updating the non-key columns of rows that already exist."""
    if not rows:
        return
    columns = ["season_id", *(f.name for f in fields(rows[0]))]
    updates = ", ".join(f"{c} = excluded.{c}" for c in columns if c not in ("season_id", *key))
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})"
        f" ON CONFLICT (season_id, {', '.join(key)}) DO UPDATE SET {updates}",
        [(season_id, *astuple(row)) for row in rows],
    )


def upsert_teams(conn: sqlite3.Connection, season_id: str, rows: Sequence[Team]) -> None:
    _upsert(conn, "nba_team", ("team_id",), season_id, rows)


def upsert_players(conn: sqlite3.Connection, season_id: str, rows: Sequence[Player]) -> None:
    _upsert(conn, "player", ("player_id",), season_id, rows)


def upsert_days(conn: sqlite3.Connection, season_id: str, rows: Sequence[Day]) -> None:
    _upsert(conn, "day", ("day_id",), season_id, rows)


def upsert_fixtures(conn: sqlite3.Connection, season_id: str, rows: Sequence[Fixture]) -> None:
    _upsert(conn, "fixture", ("fixture_id",), season_id, rows)


def upsert_entries(conn: sqlite3.Connection, season_id: str, rows: Sequence[Entry]) -> None:
    _upsert(conn, "entry", ("entry_id",), season_id, rows)


def upsert_entry_day(conn: sqlite3.Connection, season_id: str, row: EntryDay) -> None:
    _upsert(conn, "fact_entry_day", ("entry_id", "day_id"), season_id, [row])


def replace_day_stats(
    conn: sqlite3.Connection, season_id: str, day_id: int, rows: Sequence[PlayerStat]
) -> None:
    """Replace a day's stats wholesale, so a stat nbafantasy later removes doesn't linger."""
    conn.execute(
        "DELETE FROM fact_player_stat WHERE season_id = ? AND fixture_id IN"
        " (SELECT fixture_id FROM fixture WHERE season_id = ? AND day_id = ?)",
        (season_id, season_id, day_id),
    )
    _upsert(conn, "fact_player_stat", ("fixture_id", "player_id", "stat"), season_id, rows)


def replace_picks(
    conn: sqlite3.Connection, season_id: str, entry_id: int, day_id: int, rows: Sequence[Pick]
) -> None:
    conn.execute(
        "DELETE FROM fact_pick WHERE season_id = ? AND entry_id = ? AND day_id = ?",
        (season_id, entry_id, day_id),
    )
    _upsert(conn, "fact_pick", ("entry_id", "day_id", "player_id"), season_id, rows)


def save_raw(
    conn: sqlite3.Connection, season_id: str, request_key: str, body: Any, fetched_at: str
) -> None:
    conn.execute(
        "INSERT INTO raw_api_response VALUES (?, 'nbafantasy', ?, ?, ?)"
        " ON CONFLICT (season_id, source, request_key)"
        " DO UPDATE SET fetched_at = excluded.fetched_at, body = excluded.body",
        (season_id, request_key, fetched_at, json.dumps(body)),
    )


def tracked_entry_ids(conn: sqlite3.Connection, season_id: str) -> list[int]:
    rows = conn.execute(
        "SELECT entry_id FROM participant WHERE season_id = ? ORDER BY entry_id", (season_id,)
    )
    return [entry_id for (entry_id,) in rows]


def final_day_ids(conn: sqlite3.Connection, season_id: str) -> set[int]:
    rows = conn.execute("SELECT day_id FROM day WHERE season_id = ? AND facts_final", (season_id,))
    return {day_id for (day_id,) in rows}


def synced_entry_days(conn: sqlite3.Connection, season_id: str) -> set[tuple[int, int]]:
    rows = conn.execute(
        "SELECT entry_id, day_id FROM fact_entry_day WHERE season_id = ?", (season_id,)
    )
    return {(entry_id, day_id) for entry_id, day_id in rows}


def mark_day_final(conn: sqlite3.Connection, season_id: str, day_id: int) -> None:
    conn.execute(
        "UPDATE day SET facts_final = 1 WHERE season_id = ? AND day_id = ?", (season_id, day_id)
    )


def reconcile_mismatches(
    conn: sqlite3.Connection, season_id: str, day_ids: Iterable[int]
) -> list[Mismatch]:
    wanted = list(day_ids)
    placeholders = ", ".join("?" * len(wanted))
    rows = conn.execute(
        "SELECT entry_id, day_id, official, computed FROM v_entry_day_reconcile"
        f" WHERE season_id = ? AND official != computed AND day_id IN ({placeholders})"
        " ORDER BY day_id, entry_id",
        (season_id, *wanted),
    )
    return [Mismatch(*row) for row in rows]


def start_sync_run(conn: sqlite3.Connection, season_id: str, started_at: str) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO sync_run (season_id, started_at) VALUES (?, ?)", (season_id, started_at)
        )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def finish_sync_run(
    conn: sqlite3.Connection,
    run_id: int,
    finished_at: str,
    days_synced: int | None,
    error: str | None = None,
) -> None:
    with conn:
        conn.execute(
            "UPDATE sync_run SET finished_at = ?, days_synced = ?, error = ? WHERE sync_run_id = ?",
            (finished_at, days_synced, error, run_id),
        )
