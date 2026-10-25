"""Each person's money over the season, computed from the stored points on every call."""

from collections import defaultdict

from sqlalchemy.orm import Session

from fantasy_bot.models.money import MoneyRow, SeasonMoney
from fantasy_bot.models.participant import ParticipantId
from fantasy_bot.repositories import participants, points, season
from fantasy_bot.services.prizes import season_totals, settle


def get_season_money(session: Session, season_id: str) -> SeasonMoney:
    """Win or loss per final gameweek and in total. Weeks still being played are only named."""
    weeks = points.pool_weeks(session, season_id)
    names = participants.names(session, season_id)
    settled = {w.gameweek: settle(w.standings) for w in weeks if w.final}
    nets: dict[ParticipantId, dict[int, int]] = defaultdict(dict)
    for gameweek, settlements in settled.items():
        for s in settlements:
            nets[s.participant_id][gameweek] = s.net
    return SeasonMoney(
        weekly_buy_in=season.weekly_buy_in(session, season_id),
        gameweeks=list(settled),
        rows=[
            MoneyRow(names[t.participant_id], t, nets[t.participant_id])
            for t in season_totals(settled.values())
        ],
        not_final=[w.gameweek for w in weeks if not w.final],
    )
