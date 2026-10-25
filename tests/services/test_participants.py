from pathlib import Path

from sqlalchemy.orm import Session

from fantasy_bot.models.participant import ParticipantSeed
from fantasy_bot.repositories.participants import current
from fantasy_bot.services.participants import apply_file, export_csv, parse

SEASON = "2026-27"


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "participants.csv"
    path.write_text(text)
    return path


def test_parse_reads_rows_skipping_comments_blank_lines_and_names() -> None:
    text = (
        "# who is in\n"
        "entry_id,from_gameweek,name\n"
        "\n"
        "31818,1,pisit\n"
        '40823, 2 ,"settakarn, joined late"\n'
        "40791,1\n"
    )
    assert parse(text) == (
        [ParticipantSeed(4, 31818, 1), ParticipantSeed(5, 40823, 2), ParticipantSeed(6, 40791, 1)],
        [],
    )


def test_parse_explains_every_bad_row_by_line() -> None:
    text = "entry_id,from_gameweek\n31818,1\nabc,1\n40823,0\n31818,2\n"
    seeds, problems = parse(text)
    assert seeds == [ParticipantSeed(2, 31818, 1)]
    assert problems == [
        "line 3: entry_id should be a team number, got 'abc,1'",
        "line 4: from_gameweek should be 1 or more, got '40823,0'",
        "line 5: entry 31818 is already on line 2",
    ]


def test_parse_needs_the_header() -> None:
    assert parse("31818,1\n")[1] == ["line 1: the header should start with entry_id,from_gameweek"]
    assert parse("# only a comment\n")[1][0].startswith("the file has no header")


def test_file_adds_moves_and_removes_participants(league: Session, tmp_path: Path) -> None:
    # Before: 101-104 from gameweek 1. The file keeps 101, moves 102, drops 103-104, adds 106.
    path = write(tmp_path, "entry_id,from_gameweek\n101,1\n102,2\n106,3\n")
    update = apply_file(league, SEASON, path)
    assert (update.applied, update.added, update.changed, update.removed) == (
        True,
        [106],
        [102],
        [103, 104],
    )
    assert current(league, SEASON) == {101: 1, 102: 2, 106: 3}
    again = apply_file(league, SEASON, path)
    assert (again.added, again.changed, again.removed) == ([], [], [])


def test_one_bad_row_changes_nothing(league: Session, tmp_path: Path) -> None:
    before = current(league, SEASON)
    path = write(tmp_path, "entry_id,from_gameweek\n101,1\n999,1\n")
    update = apply_file(league, SEASON, path)
    assert (update.applied, update.problems) == (
        False,
        ["line 3: entry 999 is not a team in the league"],
    )
    assert current(league, SEASON) == before


def test_missing_file_changes_nothing(league: Session, tmp_path: Path) -> None:
    before = current(league, SEASON)
    update = apply_file(league, SEASON, tmp_path / "nope.csv")
    assert not update.applied and update.problems[0].endswith("so participants are unchanged")
    assert current(league, SEASON) == before


def test_export_writes_todays_participants_as_a_file_that_reads_back(
    league: Session, tmp_path: Path
) -> None:
    text = export_csv(league, SEASON)
    assert text.splitlines()[:3] == ["entry_id,from_gameweek,name", "101,1,Alpha", "102,1,Bravo"]
    update = apply_file(league, SEASON, write(tmp_path, text))
    assert (update.applied, update.added, update.changed, update.removed) == (True, [], [], [])
