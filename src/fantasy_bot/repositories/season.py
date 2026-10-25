"""The season row: which league it follows and its weekly buy-in."""

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from fantasy_bot.database import tables as t


def ensure_season(
    session: Session, season_id: str, league_id: int, weekly_buy_in_minor: int
) -> None:
    """Create the season with its weekly buy-in once; later calls leave it untouched. The caller
    commits.

    Money is recomputed from facts on every call, so changing the buy-in mid-season would
    rewrite every past week.
    """
    session.execute(
        insert(t.Season)
        .values(season_id=season_id, league_id=league_id, weekly_buy_in_minor=weekly_buy_in_minor)
        .on_conflict_do_nothing()
    )


def weekly_buy_in(session: Session, season_id: str) -> int:
    buy_in = session.scalar(
        select(t.Season.weekly_buy_in_minor).where(t.Season.season_id == season_id)
    )
    assert buy_in is not None, f"season {season_id} doesn't exist"
    return buy_in


def league_id(session: Session, season_id: str) -> int:
    value = session.scalar(select(t.Season.league_id).where(t.Season.season_id == season_id))
    assert value is not None, f"season {season_id} doesn't exist"
    return value
