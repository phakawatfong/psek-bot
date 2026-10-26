"""How a week's prize pool is split. Pure rules: no database, no Discord.

Money is in minor units (cents). Positive integer prize weights become exact Fraction shares;
recurring percentages are never rounded before payouts.
"""

from collections.abc import Iterable, Sequence
from fractions import Fraction
from itertools import groupby
from math import floor

from fantasy_bot.models.money import SeasonTotal, Settlement, Standing
from fantasy_bot.models.participant import ParticipantId
from fantasy_bot.services.prize_rules import PrizeError


def settle(standings: Sequence[Standing], weights: Sequence[int]) -> list[Settlement]:
    """Split one pool by rank. The rules, step by step:

    1. The pool is every buy-in added up.
    2. Teams are ranked by points, best first. Tied teams share a rank.
    3. Each place gets weight / sum(weights). Require exactly one positive weight per team.
    4. Tied teams pool the prizes of the places they cover and split them equally: two tied
       for 2nd each get half the combined 2nd and 3rd prizes.
    5. Payouts are whole cents. Rounding leftovers go to the largest fractional remainders,
       best rank first, so the payouts always add up to exactly the pool.
    """
    if any(s.buy_in < 0 for s in standings):
        raise ValueError("buy-ins cannot be negative")
    if not standings:
        return []
    if len(weights) != len(standings) or any(type(w) is not int or w <= 0 for w in weights):
        raise PrizeError("Provide one positive whole-number prize weight per participant.")

    pool = sum(s.buy_in for s in standings)  # step 1
    places = _ranked_places(standings)  # step 2
    shares = [Fraction(weight, sum(weights)) for weight in weights]  # step 3
    exact = _split_ties(places, shares, pool)  # step 4
    payouts = _round_to_pool([amount for _, _, amount in exact], pool)  # step 5
    if any(payout <= 0 for payout in payouts):
        raise PrizeError("This pool and split cannot give everyone at least one cent.")
    return [
        Settlement(s.participant_id, rank, s.points, s.buy_in, payout, payout - s.buy_in)
        for (s, rank, _), payout in zip(exact, payouts, strict=True)
    ]


def _ranked_places(standings: Sequence[Standing]) -> list[list[Standing]]:
    """Teams grouped by place, best first; a group holds every team tied on those points."""
    ordered = sorted(standings, key=lambda s: (-s.points, s.participant_id))
    return [list(tied) for _, tied in groupby(ordered, key=lambda s: s.points)]


def _split_ties(
    places: list[list[Standing]], shares: list[Fraction], pool: int
) -> list[tuple[Standing, int, Fraction]]:
    """(team, rank, exact amount) for every team: tied teams split their places' shares."""
    exact: list[tuple[Standing, int, Fraction]] = []
    for tied in places:
        first = len(exact)  # 0-based position of this group's first place
        each = pool * sum(shares[first : first + len(tied)], Fraction(0)) / len(tied)
        exact += [(s, first + 1, each) for s in tied]
    return exact


def _round_to_pool(amounts: list[Fraction], pool: int) -> list[int]:
    """Whole minor units that add up to `pool`: round down, then hand out the leftover units
    one at a time to the largest remainders (earlier entries, i.e. better ranks, win ties)."""
    rounded = [floor(a) for a in amounts]
    leftover = pool - sum(rounded)
    by_remainder = sorted(range(len(amounts)), key=lambda i: (rounded[i] - amounts[i], i))
    for i in by_remainder[:leftover]:
        rounded[i] += 1
    return rounded


def season_totals(weeks: Iterable[Sequence[Settlement]]) -> list[SeasonTotal]:
    """Add up each participant's weekly settlements. Best net first."""
    totals: dict[ParticipantId, tuple[int, int, int]] = {}
    for week in weeks:
        for s in week:
            played, paid, won = totals.get(s.participant_id, (0, 0, 0))
            totals[s.participant_id] = (played + 1, paid + s.buy_in, won + s.payout)
    rows = [SeasonTotal(pid, n, paid, won, won - paid) for pid, (n, paid, won) in totals.items()]
    return sorted(rows, key=lambda t: (-t.net, t.participant_id))
