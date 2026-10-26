"""Prize weights take effect from a gameweek; older weeks retain their earlier rules."""

import json
from collections.abc import Sequence
from pathlib import Path

from fantasy_bot.models.prizes import PrizeRule


class PrizeError(ValueError):
    """A prize-rule problem that can be explained in a command reply."""


def load_rules(path: Path) -> list[PrizeRule]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise PrizeError(
            "Cannot read prize rules. Check PRIZES_FILE and its JSON contents."
        ) from None
    if not isinstance(raw, list) or not raw:
        raise PrizeError("Prize rules must be a non-empty list of gameweeks and weights.")
    rules = []
    last_week = 0
    for row in raw:
        if not isinstance(row, dict) or set(row) != {"from_gameweek", "weights"}:
            raise PrizeError("Each prize rule needs only from_gameweek and weights.")
        week, weights = row["from_gameweek"], row["weights"]
        if type(week) is not int or week <= last_week:
            raise PrizeError("Prize rules need positive, strictly increasing from_gameweek values.")
        if not isinstance(weights, list) or not weights:
            raise PrizeError(f"GW{week}: weights must be a non-empty list.")
        if any(type(w) is not int or w <= 0 for w in weights):
            raise PrizeError(f"GW{week}: every prize weight must be a positive whole number.")
        if weights != sorted(weights, reverse=True):
            raise PrizeError(f"GW{week}: prize weights must be in descending order (ties allowed).")
        rules.append(PrizeRule(week, tuple(weights)))
        last_week = week
    return rules


def weights_for(rules: Sequence[PrizeRule], gameweek: int, people: int) -> tuple[int, ...]:
    rule = next((rule for rule in reversed(rules) if rule.from_gameweek <= gameweek), None)
    if rule is None:
        raise PrizeError(f"The money pool starts in GW{rules[0].from_gameweek}.")
    if len(rule.weights) != people:
        raise PrizeError(
            f"GW{gameweek} has {people} eligible participants, but its prize rule has "
            f"{len(rule.weights)} places. Update the participants or add a matching prize rule."
        )
    return rule.weights
