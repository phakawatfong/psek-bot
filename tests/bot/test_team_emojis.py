import asyncio
from dataclasses import dataclass, field

import discord
import pytest

from fantasy_bot.bot.team_emojis import load_team_emojis
from fantasy_bot.clients.team_logos import logo_url


@dataclass
class FakeEmoji:
    name: str
    id: int

    def __str__(self) -> str:
        return f"<:{self.name}:{self.id}>"


@dataclass
class FakeClient:
    existing: list[FakeEmoji]
    reject: set[str] = field(default_factory=set)
    uploaded: list[str] = field(default_factory=list)

    async def fetch_application_emojis(self) -> list[FakeEmoji]:
        return self.existing

    async def create_application_emoji(self, *, name: str, image: bytes) -> FakeEmoji:
        if name in self.reject:
            raise discord.HTTPException(FakeResponse(), "rejected")
        self.uploaded.append(name)
        return FakeEmoji(name, 100 + len(self.uploaded))


class FakeResponse:
    status = 400
    reason = "Bad Request"


async def logos_except_chi(codes: list[str]) -> dict[str, bytes]:
    return {code: b"\x89PNG" for code in codes if code != "CHI"}


def test_reuses_uploaded_emojis_and_uploads_only_missing_ones() -> None:
    client = FakeClient([FakeEmoji("nba_ATL", 1), FakeEmoji("someone_else", 2)])
    icons = asyncio.run(load_team_emojis(client, ["ATL", "BOS"], logos_except_chi))  # type: ignore[arg-type]
    assert (icons, client.uploaded) == (
        {"ATL": "<:nba_ATL:1>", "BOS": "<:nba_BOS:101>"},
        ["nba_BOS"],
    )


@pytest.mark.parametrize("reject", [set(), {"nba_BOS"}])
def test_teams_without_a_logo_or_upload_fall_back_to_codes(reject: set[str]) -> None:
    client = FakeClient([], reject=reject)
    icons = asyncio.run(load_team_emojis(client, ["BOS", "CHI"], logos_except_chi))  # type: ignore[arg-type]
    assert "CHI" not in icons and ("BOS" in icons) == (not reject)


def test_espn_codes_differ_for_six_teams() -> None:
    assert "/nba/500/gs.png" in logo_url("GSW") and "/nba/500/atl.png" in logo_url("ATL")
