import sqlite3

from fantasy_bot.models import PLACEHOLDER_MAX_ID, LeagueTeam, ParticipantId, Registration


def league_team(conn: sqlite3.Connection, season_id: str, entry_id: int) -> LeagueTeam | None:
    row = conn.execute(
        "SELECT entry_id, entry_name, manager_name FROM entry WHERE season_id = ? AND entry_id = ?",
        (season_id, entry_id),
    ).fetchone()
    return LeagueTeam(*row) if row else None


def search_teams(
    conn: sqlite3.Connection, season_id: str, text: str, status: str | None, limit: int = 25
) -> list[LeagueTeam]:
    """League teams whose team or manager name contains `text`.

    status None searches every team in the league; 'pending' or 'approved' only teams registered
    with that status; 'unregistered' only teams nobody has registered.
    """
    like = f"%{text.strip()}%"
    registered = "SELECT entry_id FROM participant WHERE season_id = e.season_id"
    if status == "unregistered":
        where, args = f" AND e.entry_id NOT IN ({registered})", []
    elif status:
        where, args = f" AND e.entry_id IN ({registered} AND status = ?)", [status]
    else:
        where, args = "", []
    rows = conn.execute(
        "SELECT e.entry_id, e.entry_name, e.manager_name FROM entry e"
        " WHERE e.season_id = ? AND (e.entry_name LIKE ? OR e.manager_name LIKE ?)"
        f"{where} ORDER BY e.entry_name LIMIT ?",
        (season_id, like, like, *args, limit),
    )
    return [LeagueTeam(*row) for row in rows]


def by_entry(conn: sqlite3.Connection, season_id: str, entry_id: int) -> Registration | None:
    return _one(conn, "entry_id", season_id, entry_id)


def by_user(conn: sqlite3.Connection, season_id: str, discord_user_id: int) -> Registration | None:
    return _one(conn, "discord_user_id", season_id, discord_user_id)


def add(
    conn: sqlite3.Connection,
    season_id: str,
    discord_user_id: int,
    entry_id: int,
    joined_gameweek: int,
    registered_at: str,
    status: str = "pending",
) -> None:
    with conn:
        conn.execute(
            "INSERT INTO participant (season_id, discord_user_id, entry_id, status,"
            " registered_at, joined_gameweek) VALUES (?, ?, ?, ?, ?, ?)",
            (season_id, discord_user_id, entry_id, status, registered_at, joined_gameweek),
        )


def next_placeholder_id(conn: sqlite3.Connection, season_id: str) -> int:
    """A Discord id no real account has, for a team added before its owner links it."""
    highest: int = conn.execute(
        "SELECT COALESCE(MAX(discord_user_id), 0) FROM participant"
        " WHERE season_id = ? AND discord_user_id < ?",
        (season_id, PLACEHOLDER_MAX_ID),
    ).fetchone()[0]
    return highest + 1


def link_user(conn: sqlite3.Connection, participant_id: int, discord_user_id: int) -> None:
    with conn:
        conn.execute(
            "UPDATE participant SET discord_user_id = ? WHERE participant_id = ?",
            (discord_user_id, participant_id),
        )


def approve(conn: sqlite3.Connection, participant_id: int, joined_gameweek: int | None) -> None:
    with conn:
        conn.execute(
            "UPDATE participant SET status = 'approved',"
            " joined_gameweek = COALESCE(?, joined_gameweek) WHERE participant_id = ?",
            (joined_gameweek, participant_id),
        )


def add_payment(
    conn: sqlite3.Connection,
    participant_id: int,
    kind: str,
    amount_minor: int,
    note: str | None,
    created_at: str,
) -> None:
    with conn:
        conn.execute(
            "INSERT INTO ledger (participant_id, kind, amount_minor, note, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (participant_id, kind, amount_minor, note, created_at),
        )


def payment_totals(
    conn: sqlite3.Connection, season_id: str
) -> dict[ParticipantId, tuple[int, int]]:
    """(paid in, paid out) per participant, in minor units."""
    rows = conn.execute(
        "SELECT l.participant_id,"
        " SUM(CASE WHEN l.kind = 'paid_in' THEN l.amount_minor ELSE 0 END),"
        " SUM(CASE WHEN l.kind = 'paid_out' THEN l.amount_minor ELSE 0 END)"
        " FROM ledger l JOIN participant p USING (participant_id)"
        " WHERE p.season_id = ? GROUP BY l.participant_id",
        (season_id,),
    )
    return {ParticipantId(pid): (paid_in, paid_out) for pid, paid_in, paid_out in rows}


def _one(conn: sqlite3.Connection, column: str, season_id: str, value: int) -> Registration | None:
    row = conn.execute(
        "SELECT participant_id, discord_user_id, entry_id, status FROM participant"
        f" WHERE season_id = ? AND {column} = ?",
        (season_id, value),
    ).fetchone()
    return Registration(ParticipantId(row[0]), row[1], row[2], row[3]) if row else None
