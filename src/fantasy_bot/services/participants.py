"""Participants come from seed/participants.csv, the one source of truth.

Every sync makes the participant table match the file exactly: a new row adds someone, a changed
`from_gameweek` moves their start, a deleted row removes them. Two safety rules:

- A missing file changes nothing. It means the file hasn't been created yet, not "remove everyone".
- If any row has a problem, nothing changes and every problem is reported. Applying only the good
  rows would silently drop the person with the typo and change everyone's money.
"""

import csv
import io
from pathlib import Path

from sqlalchemy.orm import Session

from fantasy_bot.models.participant import ParticipantSeed, ParticipantsUpdate
from fantasy_bot.repositories import participants as repo

COLUMNS = ["entry_id", "from_gameweek"]  # then optionally "name", ignored by the bot


def parse(text: str) -> tuple[list[ParticipantSeed], list[str]]:
    """Rows and problems. Blank lines and lines starting with # are skipped."""
    lines = [
        (number, line)
        for number, line in enumerate(text.splitlines(), start=1)
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines:
        return [], ["the file has no header; the first line should be: entry_id,from_gameweek,name"]
    header_line, header = lines[0]
    columns = [c.strip().lower() for c in next(csv.reader([header]))]
    if columns[:2] != COLUMNS:
        return [], [f"line {header_line}: the header should start with entry_id,from_gameweek"]

    seeds: list[ParticipantSeed] = []
    problems: list[str] = []
    seen: dict[int, int] = {}
    for number, line in lines[1:]:
        cells = [c.strip() for c in next(csv.reader([line]))]
        entry_id = _whole_number(cells[0] if cells else "")
        gameweek = _whole_number(cells[1] if len(cells) > 1 else "")
        if entry_id is None or entry_id < 1:
            problems.append(f"line {number}: entry_id should be a team number, got {line!r}")
        elif gameweek is None or gameweek < 1:
            problems.append(f"line {number}: from_gameweek should be 1 or more, got {line!r}")
        elif entry_id in seen:
            problems.append(f"line {number}: entry {entry_id} is already on line {seen[entry_id]}")
        else:
            seen[entry_id] = number
            seeds.append(ParticipantSeed(number, entry_id, gameweek))
    return seeds, problems


def apply_file(session: Session, season_id: str, path: Path) -> ParticipantsUpdate:
    """Make the season's participants match the file; see the module docstring for the rules."""
    if not path.is_file():
        return _not_applied([f"{path} not found, so participants are unchanged"])
    seeds, problems = parse(path.read_text(encoding="utf-8"))
    league = repo.league_entry_ids(session, season_id)
    problems += [
        f"line {s.line}: entry {s.entry_id} is not a team in the league"
        for s in seeds
        if s.entry_id not in league
    ]
    if problems:
        return _not_applied(problems)

    wanted = {s.entry_id: s.from_gameweek for s in seeds}
    now = repo.current(session, season_id)
    add = {e: g for e, g in wanted.items() if e not in now}
    change = {e: g for e, g in wanted.items() if e in now and now[e] != g}
    remove = sorted(set(now) - set(wanted))
    repo.apply(session, season_id, add, change, remove)
    session.commit()  # all of the file's changes, or none
    return ParticipantsUpdate(True, sorted(add), sorted(change), remove, [])


def export_csv(session: Session, season_id: str) -> str:
    """Today's participants as a participants.csv, e.g. to create the file the first time."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow([*COLUMNS, "name"])
    writer.writerows(repo.export_rows(session, season_id))
    return out.getvalue()


def _whole_number(cell: str) -> int | None:
    return int(cell) if cell.isdigit() else None


def _not_applied(problems: list[str]) -> ParticipantsUpdate:
    return ParticipantsUpdate(False, [], [], [], problems)
