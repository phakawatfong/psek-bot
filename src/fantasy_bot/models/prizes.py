from dataclasses import dataclass


@dataclass(frozen=True)
class PrizeRule:
    from_gameweek: int
    weights: tuple[int, ...]
