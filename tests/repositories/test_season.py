from sqlalchemy.orm import Session

from fantasy_bot.repositories.season import ensure_season, league_id, weekly_buy_in


def test_ensure_season_creates_once_and_never_changes_the_buy_in(session: Session) -> None:
    ensure_season(session, "2027-28", 99, 10000)
    ensure_season(session, "2027-28", 99, 20000)
    assert (weekly_buy_in(session, "2027-28"), league_id(session, "2027-28")) == (10000, 99)
