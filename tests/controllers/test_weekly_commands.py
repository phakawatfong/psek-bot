import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from discord import app_commands
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from fantasy_bot.controllers import money, pool, standings
from fantasy_bot.controllers.routes import register_all
from fantasy_bot.database.connection import sessions
from fantasy_bot.models.money import Settlement
from fantasy_bot.models.participant import ParticipantId, ParticipantName
from fantasy_bot.models.pool import Pool, PoolLine


def interaction() -> Mock:
    return Mock(response=Mock(send_message=AsyncMock()), followup=Mock(send=AsyncMock()))


@pytest.fixture
def prize_file(tmp_path: Path) -> Path:
    path = tmp_path / "prizes.json"
    path.write_text(
        json.dumps(
            [
                {"from_gameweek": 1, "weights": [50, 30, 15]},
                {"from_gameweek": 2, "weights": [50, 30, 15, 5]},
            ]
        )
    )
    return path


def test_money_weekly_provisional_and_season_total(
    engine: Engine, two_weeks: Session, prize_file: Path
) -> None:
    handle = money.handler(sessions(engine), "2026-27", prize_file)
    weekly = interaction()
    asyncio.run(handle(weekly, gameweek=2))
    text = weekly.response.send_message.call_args.args[0]
    assert "Gameweek 2 net win/loss" in text and "provisional" in text
    assert "Alpha (manager): +100.00" in text
    season = interaction()
    asyncio.run(handle(season, season=True))
    text = season.response.send_message.call_args.args[0]
    assert "Money after 1 final gameweek" in text
    assert "GW2 is not final yet" in text


def test_money_rejects_conflicting_options_before_reading_file(
    engine: Engine, tmp_path: Path
) -> None:
    reply = interaction()
    asyncio.run(
        money.handler(sessions(engine), "test", tmp_path / "missing")(
            reply, gameweek=2, season=True
        )
    )
    assert "not both" in reply.response.send_message.call_args.args[0]


def test_weekly_money_default_requests_current_week(
    engine: Engine, prize_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = Pool(
        2,
        False,
        [
            PoolLine(
                ParticipantName("Alpha", ""),
                Settlement(ParticipantId(1), 1, 100, 5000, 12000, 7000),
            )
        ],
    )
    get_pool = Mock(return_value=result)
    monkeypatch.setattr(money, "get_pool", get_pool)
    reply = interaction()
    asyncio.run(money.handler(sessions(engine), "test", prize_file)(reply))
    assert get_pool.call_args.args[-1] is None
    assert "Alpha: +70.00" in reply.response.send_message.call_args.args[0]


def test_pool_reports_missing_rules_and_wrong_participant_count(
    engine: Engine, two_weeks: Session, tmp_path: Path
) -> None:
    path = tmp_path / "rules.json"
    handle = pool.handler(sessions(engine), "2026-27", path)
    reply = interaction()
    asyncio.run(handle(reply, 2))
    assert "Cannot read prize rules" in reply.response.send_message.call_args.args[0]
    path.write_text('[{"from_gameweek":2,"weights":[120,70,50,30,20,10]}]')
    reply = interaction()
    asyncio.run(handle(reply, 2))
    assert "4 eligible participants" in reply.response.send_message.call_args.args[0]


def test_standings_can_select_week_without_prize_configuration(
    engine: Engine, two_weeks: Session
) -> None:
    reply = interaction()
    asyncio.run(standings.handler(sessions(engine), "2026-27")(reply, 2))
    text = reply.response.send_message.call_args.args[0]
    assert "Gameweek 2 standings" in text and "provisional" in text
    assert "Alpha (manager) 60.0 pts" in text


def test_registered_weekly_options(engine: Engine) -> None:
    import discord

    tree = app_commands.CommandTree(discord.Client(intents=discord.Intents.none()))
    register_all(tree, sessions(engine), "test")
    for name in ("standings", "pool", "money"):
        command = tree.get_command(f"psek-nba-{name}")
        assert isinstance(command, app_commands.Command)
        gw = command.parameters[0]
        assert (gw.name, gw.required, gw.min_value) == ("gameweek", False, 1)
        if name == "money":
            assert command.parameters[1].name == "season"
            assert command.parameters[1].default is False
