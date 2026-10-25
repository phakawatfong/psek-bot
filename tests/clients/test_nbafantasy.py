import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from fantasy_bot.clients.nbafantasy import (
    parse_bootstrap,
    parse_entry,
    parse_fixtures,
    parse_live,
    parse_picks,
)
from fantasy_bot.models.nbafantasy import Entry

FIXTURES = Path(__file__).parents[1] / "fixtures" / "nbafantasy"


def saved(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def test_saved_real_responses_satisfy_the_contract() -> None:
    boot = parse_bootstrap(saved("bootstrap.json"))
    counts = (
        len(boot.teams),
        len(boot.players),
        [(d.day_id, d.gameweek) for d in boot.days],
        len(parse_fixtures(saved("fixtures_4.json"))),
        len(parse_live(saved("live_4.json"))),
        len(parse_picks(saved("picks_34409_4.json"), 34409, 4)[1]),
    )
    assert counts == (30, 10, [(4, 1)], 12, 10, 10)


def test_new_fields_from_nbafantasy_are_ignored() -> None:
    raw = saved("entry_34409.json") | {"brand_new_field": {"anything": 1}}
    assert parse_entry(raw) == Entry(34409, "Test Team", "Test Manager", 1)


def test_missing_field_fails_naming_it() -> None:
    raw = saved("entry_34409.json")
    del raw["started_event"]
    with pytest.raises(ValidationError, match="started_event\n  Field required"):
        parse_entry(raw)


def test_changed_type_fails_instead_of_being_coerced() -> None:
    raw = saved("picks_34409_4.json")
    raw["entry_history"]["points"] = "130"
    with pytest.raises(ValidationError, match=r"entry_history\.points\n  Input should be"):
        parse_picks(raw, 34409, 4)


def test_unknown_position_is_rejected() -> None:
    raw = saved("bootstrap.json")
    raw["elements"][0]["element_type"] = 3
    with pytest.raises(ValidationError, match=r"elements\.0\.element_type"):
        parse_bootstrap(raw)
