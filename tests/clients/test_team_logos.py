import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest

from fantasy_bot.clients import team_logos

PNG = team_logos.PNG_SIGNATURE + b"synthetic-image"


@pytest.mark.parametrize(
    ("code", "slug"),
    [
        ("GSW", "gs"),
        ("NOP", "no"),
        ("NYK", "ny"),
        ("SAS", "sa"),
        ("UTA", "utah"),
        ("WAS", "wsh"),
        ("BOS", "bos"),
    ],
)
def test_team_code_mapping(code: str, slug: str) -> None:
    assert team_logos.logo_url(code).endswith(f"/{slug}.png&h=128&w=128")


def test_invalid_team_code_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid NBA team code"):
        team_logos.logo_url("../anything")


def response(body: bytes) -> AsyncMock:
    result = AsyncMock()
    result.__aenter__.return_value = result
    result.raise_for_status = Mock()

    async def chunks(size: int) -> AsyncIterator[bytes]:
        for start in range(0, len(body), size):
            yield body[start : start + size]

    result.content = Mock(iter_chunked=chunks)
    return result


def test_downloads_keep_valid_pngs_and_skip_bad_or_failed_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.get = Mock(
        side_effect=[
            response(b"<html>not an image</html>"),
            response(team_logos.PNG_SIGNATURE + b"x" * team_logos.MAX_LOGO_BYTES),
            aiohttp.ClientError("unavailable"),
            TimeoutError(),
            response(PNG),
        ]
    )
    monkeypatch.setattr(aiohttp, "ClientSession", Mock(return_value=session))
    assert asyncio.run(team_logos.fetch_logos(["AAA", "BBB", "CCC", "DDD", "EEE"])) == {"EEE": PNG}
    assert session.get.call_count == 5


def test_http_error_body_is_not_used_as_an_image(monkeypatch: pytest.MonkeyPatch) -> None:
    rejected = response(PNG)
    rejected.raise_for_status.side_effect = aiohttp.ClientError("HTTP 403")
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.get = Mock(return_value=rejected)
    monkeypatch.setattr(aiohttp, "ClientSession", Mock(return_value=session))
    assert asyncio.run(team_logos.fetch_logos(["AAA"])) == {}
