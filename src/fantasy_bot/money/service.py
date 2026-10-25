"""Weekly pools, computed from the stored facts on every call. Nothing here is saved."""

import sqlite3

from fantasy_bot.calculations.payout import season_totals, settle
from fantasy_bot.models import (
    MoneyLine,
    ParticipantId,
    ParticipantName,
    PoolWeek,
    SeasonMoney,
    SeasonMoneyRow,
    WeekMoney,
)
from fantasy_bot.repositories import pool, registration, seasons, standings


def get_week_money(conn: sqlite3.Connection, season_id: str, gameweek: int) -> WeekMoney | None:
    """One gameweek's pool split by its points; None if the week has no synced points yet."""
    week = next((w for w in pool.pool_weeks(conn, season_id) if w.gameweek == gameweek), None)
    if week is None:
        return None
    return _week_money(week, seasons.payout_split(conn, season_id), _names(conn, season_id))


def get_season_money(conn: sqlite3.Connection, season_id: str) -> SeasonMoney:
    """Totals over every final week, with real payments recorded so far, plus the latest week
    as it stands if it isn't final."""
    weeks = pool.pool_weeks(conn, season_id)
    split = seasons.payout_split(conn, season_id)
    names = _names(conn, season_id)
    settled = [w for w in weeks if w.final]
    totals = season_totals(settle(w.standings, split) for w in settled)
    payments = registration.payment_totals(conn, season_id)
    latest = weeks[-1] if weeks else None
    return SeasonMoney(
        rules=seasons.season_rules(conn, season_id),
        settled_weeks=[w.gameweek for w in settled],
        rows=[
            SeasonMoneyRow(names[t.participant_id], t, *payments.get(t.participant_id, (0, 0)))
            for t in totals
        ],
        in_progress=_week_money(latest, split, names) if latest and not latest.final else None,
    )


def _week_money(
    week: PoolWeek, split: list[int], names: dict[ParticipantId, ParticipantName]
) -> WeekMoney:
    lines = [MoneyLine(names[s.participant_id], s) for s in settle(week.standings, split)]
    return WeekMoney(week.gameweek, week.final, lines)


def _names(conn: sqlite3.Connection, season_id: str) -> dict[ParticipantId, ParticipantName]:
    return standings.participant_names(conn, season_id)
