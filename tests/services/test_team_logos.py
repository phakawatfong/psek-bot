import asyncio
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from fantasy_bot.clients import nbafantasy
from fantasy_bot.clients import team_logos as logo_client
from fantasy_bot.services import team_logos


@pytest.mark.parametrize("existing", [{"AAA"}, {"AAA", "BBB"}])
def test_only_missing_team_logos_are_downloaded(
    monkeypatch: pytest.MonkeyPatch, existing: set[str]
) -> None:
    client = Mock(
        fetch=AsyncMock(
            return_value={
                "teams": [
                    {"id": 1, "name": "Alpha", "short_name": "AAA"},
                    {"id": 2, "name": "Bravo", "short_name": "BBB"},
                ],
                "elements": [],
                "phases": [],
                "events": [],
            }
        )
    )

    @asynccontextmanager
    async def open_client() -> Any:
        yield client

    download = AsyncMock(return_value={"BBB": b"image"})
    monkeypatch.setattr(nbafantasy, "open_client", open_client)
    monkeypatch.setattr(logo_client, "fetch_logos", download)
    logos = asyncio.run(team_logos.get_missing_logos(existing))
    client.fetch.assert_awaited_once_with("bootstrap-static/")
    if "BBB" in existing:
        download.assert_not_awaited()
        assert logos == {}
    else:
        download.assert_awaited_once_with(["BBB"])
        assert logos == {"BBB": b"image"}
