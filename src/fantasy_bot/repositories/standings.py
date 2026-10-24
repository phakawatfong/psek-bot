import sqlite3
from itertools import groupby

from fantasy_bot.models import (
    DayPointsRow,
    ParticipantId,
    ParticipantName,
    ParticipantRow,
    PointsSeries,
    StandingRow,
)

# Name columns for queries over `participant p LEFT JOIN entry e`; before the first sync an
# entry has no row yet, so it is named by its id.
NAMES = "COALESCE(e.entry_name, 'entry ' || p.entry_id), COALESCE(e.manager_name, '')"
PARTICIPANTS = (
    "participant p LEFT JOIN entry e ON e.season_id = p.season_id AND e.entry_id = p.entry_id"
)


def participant_names(
    conn: sqlite3.Connection, season_id: str
) -> dict[ParticipantId, ParticipantName]:
    rows = conn.execute(
        f"SELECT p.participant_id, {NAMES} FROM {PARTICIPANTS} WHERE p.season_id = ?",
        (season_id,),
    )
    return {ParticipantId(pid): ParticipantName(team, manager) for pid, team, manager in rows}


def season_table(conn: sqlite3.Connection, season_id: str) -> list[StandingRow]:
    rows = conn.execute(
        f"SELECT RANK() OVER (ORDER BY s.total_points DESC), {NAMES}, s.total_points"
        f" FROM {PARTICIPANTS}"
        " JOIN v_season_standings s ON s.participant_id = p.participant_id"
        " WHERE s.season_id = ? ORDER BY 1, 2",
        (season_id,),
    )
    return [StandingRow(rank, ParticipantName(t, m), pts) for rank, t, m, pts in rows]


def gameweek_table(conn: sqlite3.Connection, season_id: str, gameweek: int) -> list[StandingRow]:
    """Points scored in one gameweek, net of transfer costs like the season total."""
    rows = conn.execute(
        f"SELECT RANK() OVER (ORDER BY COALESCE(g.points - g.transfers_cost, 0) DESC), {NAMES},"
        " COALESCE(g.points - g.transfers_cost, 0)"
        f" FROM {PARTICIPANTS}"
        " LEFT JOIN v_entry_gameweek g"
        "  ON g.season_id = p.season_id AND g.entry_id = p.entry_id AND g.gameweek = ?"
        " WHERE p.season_id = ? AND p.status = 'approved' ORDER BY 1, 2",
        (gameweek, season_id),
    )
    return [StandingRow(rank, ParticipantName(t, m), pts) for rank, t, m, pts in rows]


def day_table(conn: sqlite3.Connection, season_id: str, day_id: int) -> list[DayPointsRow]:
    """Teams that played on `day_id`. A team that hadn't started yet has no row that day and is
    left out, rather than shown as scoring 0."""
    rows = conn.execute(
        f"SELECT RANK() OVER (ORDER BY f.points DESC), {NAMES}, f.points, f.total_points"
        f" FROM {PARTICIPANTS}"
        " JOIN fact_entry_day f"
        "  ON f.season_id = p.season_id AND f.entry_id = p.entry_id AND f.day_id = ?"
        " WHERE p.season_id = ? AND p.status = 'approved' ORDER BY 1, 2",
        (day_id, season_id),
    )
    return [
        DayPointsRow(rank, ParticipantName(t, m), pts, total) for rank, t, m, pts, total in rows
    ]


def latest_synced_day(conn: sqlite3.Connection, season_id: str) -> int | None:
    day_id: int | None = conn.execute(
        "SELECT max(day_id) FROM fact_entry_day WHERE season_id = ?", (season_id,)
    ).fetchone()[0]
    return day_id


def day_info(conn: sqlite3.Connection, season_id: str, day_id: int) -> tuple[str, bool] | None:
    """The day's name and whether its points are final, or None for an unknown day."""
    row = conn.execute(
        "SELECT name, data_checked FROM day WHERE season_id = ? AND day_id = ?",
        (season_id, day_id),
    ).fetchone()
    return (row[0], bool(row[1])) if row else None


def participant_list(conn: sqlite3.Connection, season_id: str) -> list[ParticipantRow]:
    rows = conn.execute(
        f"SELECT {NAMES}, p.entry_id, p.joined_gameweek, p.status FROM {PARTICIPANTS}"
        " WHERE p.season_id = ? ORDER BY p.status, 1",
        (season_id,),
    )
    return [
        ParticipantRow(ParticipantName(t, m), entry_id, joined, status)
        for t, m, entry_id, joined, status in rows
    ]


def daily_totals(conn: sqlite3.Connection, season_id: str) -> list[PointsSeries]:
    """Each approved team's season total after every synced day, in participant order."""
    rows = conn.execute(
        f"SELECT p.participant_id, {NAMES}, f.day_id, f.total_points FROM {PARTICIPANTS}"
        " JOIN fact_entry_day f ON f.season_id = p.season_id AND f.entry_id = p.entry_id"
        " WHERE p.season_id = ? AND p.status = 'approved'"
        " ORDER BY p.participant_id, f.day_id",
        (season_id,),
    ).fetchall()
    return [
        PointsSeries(
            ParticipantId(pid),
            ParticipantName(group[0][1], group[0][2]),
            [day for *_, day, _ in group],
            [total for *_, total in group],
        )
        for pid, rows_of_pid in groupby(rows, key=lambda r: r[0])
        for group in [list(rows_of_pid)]
    ]


def gameweek_of_day(conn: sqlite3.Connection, season_id: str) -> dict[int, int]:
    rows = conn.execute("SELECT day_id, gameweek FROM day WHERE season_id = ?", (season_id,))
    return {day_id: gameweek for day_id, gameweek in rows}
