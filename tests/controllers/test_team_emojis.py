import asyncio
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from fantasy_bot.controllers import team_emojis


def emoji(name: str, identifier: int) -> discord.PartialEmoji:
    return discord.PartialEmoji(name=name, id=identifier)


def test_reuses_existing_emojis_and_uploads_only_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Mock(
        fetch_application_emojis=AsyncMock(return_value=[emoji("nba_AAA", 1), emoji("other", 2)]),
        create_application_emoji=AsyncMock(return_value=emoji("nba_BBB", 3)),
    )
    download = AsyncMock(return_value={"BBB": b"png"})
    monkeypatch.setattr(team_emojis, "get_missing_logos", download)
    icons: dict[str, str] = {}
    asyncio.run(team_emojis.load_team_emojis(client, icons))
    download.assert_awaited_once_with({"AAA"})
    client.create_application_emoji.assert_awaited_once_with(name="nba_BBB", image=b"png")
    assert icons == {"AAA": "<:nba_AAA:1>", "BBB": "<:nba_BBB:3>"}


@pytest.mark.parametrize("failure", [TimeoutError(), discord.Forbidden(Mock(status=403), "Denied")])
def test_one_failed_upload_keeps_other_emojis(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    client = Mock(
        fetch_application_emojis=AsyncMock(return_value=[emoji("nba_AAA", 1)]),
        create_application_emoji=AsyncMock(side_effect=[failure, emoji("nba_CCC", 3)]),
    )
    monkeypatch.setattr(
        team_emojis, "get_missing_logos", AsyncMock(return_value={"BBB": b"b", "CCC": b"c"})
    )
    icons: dict[str, str] = {}
    asyncio.run(team_emojis.load_team_emojis(client, icons))
    assert icons == {"AAA": "<:nba_AAA:1>", "CCC": "<:nba_CCC:3>"}


def test_download_failure_keeps_existing_emojis(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Mock(
        fetch_application_emojis=AsyncMock(return_value=[emoji("nba_AAA", 1)]),
        create_application_emoji=AsyncMock(),
    )
    monkeypatch.setattr(
        team_emojis, "get_missing_logos", AsyncMock(side_effect=ValueError("bad API"))
    )
    icons: dict[str, str] = {}
    asyncio.run(team_emojis.load_team_emojis(client, icons))
    assert icons == {"AAA": "<:nba_AAA:1>"}
    client.create_application_emoji.assert_not_awaited()


def test_cannot_list_emojis_does_not_blindly_upload_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Mock(fetch_application_emojis=AsyncMock(side_effect=TimeoutError()))
    download = AsyncMock()
    monkeypatch.setattr(team_emojis, "get_missing_logos", download)
    icons: dict[str, str] = {}
    asyncio.run(team_emojis.load_team_emojis(client, icons))
    download.assert_not_awaited()
    assert icons == {}


def test_total_setup_timeout_returns_without_stopping_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(team_emojis, "SETUP_TIMEOUT_SECONDS", 0)
    client = Mock()

    async def slow_fetch() -> list[discord.Emoji]:
        await asyncio.sleep(10)
        return []

    client.fetch_application_emojis = slow_fetch
    icons: dict[str, str] = {}
    asyncio.run(team_emojis.load_team_emojis(client, icons))
    assert icons == {}
