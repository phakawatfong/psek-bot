import sqlite3

from fantasy_bot.models import ParticipantRow
from fantasy_bot.repositories.standings import participant_list


def list_participants(conn: sqlite3.Connection, season_id: str) -> list[ParticipantRow]:
    """Every registered team, approved first, then pending."""
    return participant_list(conn, season_id)
