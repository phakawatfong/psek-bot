import json
from pathlib import Path
from typing import Any

import pytest

from fantasy_bot.models.prizes import PrizeRule
from fantasy_bot.services.prize_rules import PrizeError, load_rules, weights_for

SIX = (120, 70, 50, 30, 20, 10)
SEVEN = (7, 6, 5, 4, 3, 2, 1)  # Synthetic rule, not the league's chosen seven-place split.


def test_rules_take_effect_by_gameweek_without_rewriting_earlier_weeks(tmp_path: Path) -> None:
    path = tmp_path / "prizes.json"
    path.write_text(json.dumps([{"from_gameweek": 2, "weights": SIX}]))
    old = load_rules(path)
    path.write_text(
        json.dumps([{"from_gameweek": 2, "weights": SIX}, {"from_gameweek": 4, "weights": SEVEN}])
    )
    rules = load_rules(path)
    assert weights_for(rules, 2, 6) == weights_for(old, 2, 6) == SIX
    assert weights_for(rules, 3, 6) == SIX
    assert weights_for(rules, 4, 7) == SEVEN
    assert weights_for(rules, 10, 7) == SEVEN


@pytest.mark.parametrize(
    "raw",
    [
        [],
        {},
        [{"from_gameweek": 2}],
        [{"from_gameweek": 0, "weights": [1]}],
        [{"from_gameweek": True, "weights": [1]}],
        [{"from_gameweek": 2, "weights": []}],
        [{"from_gameweek": 2, "weights": [1, 0]}],
        [{"from_gameweek": 2, "weights": [1, -1]}],
        [{"from_gameweek": 2, "weights": [True]}],
        [{"from_gameweek": 2, "weights": [1.5]}],
        [{"from_gameweek": 2, "weights": ["10"]}],
        [{"from_gameweek": 2, "weights": [1, 2]}],
        [{"from_gameweek": 2, "weights": [1], "typo": 1}],
        [{"from_gameweek": 2, "weights": [1]}, {"from_gameweek": 2, "weights": [1]}],
        [{"from_gameweek": 3, "weights": [1]}, {"from_gameweek": 2, "weights": [1]}],
    ],
)
def test_bad_rule_file_is_rejected_as_a_whole(tmp_path: Path, raw: Any) -> None:
    path = tmp_path / "prizes.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(PrizeError):
        load_rules(path)


def test_missing_or_invalid_json_is_explained(tmp_path: Path) -> None:
    path = tmp_path / "prizes.json"
    with pytest.raises(PrizeError, match="Cannot read prize rules"):
        load_rules(path)
    path.write_text("{not json")
    with pytest.raises(PrizeError, match="Cannot read prize rules"):
        load_rules(path)


def test_count_mismatch_and_before_start_are_explained() -> None:
    rules = [PrizeRule(2, SIX)]
    with pytest.raises(PrizeError, match="starts in GW2"):
        weights_for(rules, 1, 6)
    with pytest.raises(PrizeError, match=r"7 eligible participants.*6 places"):
        weights_for(rules, 2, 7)
