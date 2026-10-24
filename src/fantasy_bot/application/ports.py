from typing import Protocol

from fantasy_bot.domain.payout import Standing


class Repository(Protocol):
    def season_standings(self, season_id: str) -> list[Standing]: ...

    def payout_split(self, season_id: str) -> list[int]: ...
