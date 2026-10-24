from fantasy_bot.application.ports import Repository
from fantasy_bot.domain.payout import Settlement, settle


def money_summary(repo: Repository, season_id: str) -> list[Settlement]:
    return settle(repo.season_standings(season_id), repo.payout_split(season_id))
