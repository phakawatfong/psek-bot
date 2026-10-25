"""Who is in the pool, as stored from seed/participants.csv."""

from collections.abc import Mapping, Sequence

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.orm import Session

from fantasy_bot.database import tables as t
from fantasy_bot.models.participant import ParticipantId, ParticipantName
from fantasy_bot.repositories.queries import ENTRY_OF_PARTICIPANT, MANAGER_NAME, TEAM_NAME


def current(session: Session, season_id: str) -> dict[int, int]:
    """Entry id -> first gameweek, for everyone in the pool now."""
    rows = session.execute(
        select(t.Participant.entry_id, t.Participant.joined_gameweek).where(
            t.Participant.season_id == season_id
        )
    )
    return {entry_id: gameweek for entry_id, gameweek in rows}


def names(session: Session, season_id: str) -> dict[ParticipantId, ParticipantName]:
    """Each participant's nbafantasy team and manager name."""
    rows = session.execute(
        select(t.Participant.participant_id, TEAM_NAME, MANAGER_NAME)
        .select_from(t.Participant)
        .outerjoin(t.Entry, ENTRY_OF_PARTICIPANT)
        .where(t.Participant.season_id == season_id)
    )
    return {ParticipantId(pid): ParticipantName(team, manager) for pid, team, manager in rows}


def entry_ids(session: Session, season_id: str) -> list[int]:
    """Every participant's nbafantasy entry, the teams the sync follows."""
    return list(
        session.scalars(
            select(t.Participant.entry_id)
            .where(t.Participant.season_id == season_id)
            .order_by(t.Participant.entry_id)
        )
    )


def league_entry_ids(session: Session, season_id: str) -> set[int]:
    """Every team in the league, as stored by the last sync."""
    return set(session.scalars(select(t.Entry.entry_id).where(t.Entry.season_id == season_id)))


def apply(
    session: Session,
    season_id: str,
    add: Mapping[int, int],
    change: Mapping[int, int],
    remove: Sequence[int],
) -> None:
    """Add, re-date, and remove participants. The caller commits."""
    if add:
        session.execute(
            insert(t.Participant),
            [
                {"season_id": season_id, "entry_id": entry_id, "joined_gameweek": gameweek}
                for entry_id, gameweek in add.items()
            ],
        )
    for entry_id, gameweek in change.items():
        session.execute(
            update(t.Participant)
            .where(t.Participant.season_id == season_id, t.Participant.entry_id == entry_id)
            .values(joined_gameweek=gameweek)
        )
    if remove:
        session.execute(
            delete(t.Participant).where(
                t.Participant.season_id == season_id, t.Participant.entry_id.in_(remove)
            )
        )


def export_rows(session: Session, season_id: str) -> list[tuple[int, int, str]]:
    """(entry id, first gameweek, team name) for everyone in the pool, by entry id."""
    rows = session.execute(
        select(
            t.Participant.entry_id,
            t.Participant.joined_gameweek,
            func.coalesce(t.Entry.entry_name, ""),
        )
        .select_from(t.Participant)
        .outerjoin(t.Entry, ENTRY_OF_PARTICIPANT)
        .where(t.Participant.season_id == season_id)
        .order_by(t.Participant.entry_id)
    )
    return [(entry_id, gameweek, name) for entry_id, gameweek, name in rows]
