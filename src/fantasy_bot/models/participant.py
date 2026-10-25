"""Who is in the pool: how a participant is named, and the rows of seed/participants.csv."""

from dataclasses import dataclass
from typing import NewType

ParticipantId = NewType("ParticipantId", int)


@dataclass(frozen=True)
class ParticipantName:
    team_name: str
    manager_name: str


@dataclass(frozen=True)
class ParticipantSeed:
    """One row of seed/participants.csv."""

    line: int  # in the file, for error messages
    entry_id: int
    from_gameweek: int


@dataclass(frozen=True)
class ParticipantsUpdate:
    applied: bool  # False: the file was missing or had problems, and nothing changed
    added: list[int]  # entry ids
    changed: list[int]  # entry ids whose start gameweek moved
    removed: list[int]
    problems: list[str]
