from sqlalchemy.orm import Session

from fantasy_bot.models.participant import ParticipantName
from fantasy_bot.models.standings import StandingRow
from fantasy_bot.services.standings import get_standings

SEASON = "2026-27"


def named(team: str) -> ParticipantName:
    return ParticipantName(team, "manager")


def test_standings_rank_every_team_by_latest_total(seeded: Session) -> None:
    assert get_standings(seeded, SEASON) == [
        StandingRow(1, named("Bravo"), 900),
        StandingRow(2, named("Alpha"), 700),
        StandingRow(3, named("Charlie"), 500),
        StandingRow(4, named("Delta"), 0),
    ]
