from typing import Protocol

from fantasy_bot.domain.payout import ParticipantId, Standing


class Repository(Protocol):
    def season_standings(self, season_id: str) -> list[Standing]: ...

    def payout_split(self, season_id: str) -> list[int]: ...

    def discord_user_ids(self, season_id: str) -> dict[ParticipantId, int]: ...
