from dataclasses import dataclass

from fantasy_bot.application.ports import Repository
from fantasy_bot.domain.payout import Settlement, settle


@dataclass(frozen=True)
class MoneyLine:
    discord_user_id: int
    settlement: Settlement


def money_summary(repo: Repository, season_id: str) -> list[MoneyLine]:
    users = repo.discord_user_ids(season_id)
    settlements = settle(repo.season_standings(season_id), repo.payout_split(season_id))
    return [MoneyLine(users[s.participant_id], s) for s in settlements]
