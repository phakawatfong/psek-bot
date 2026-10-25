"""How a week's prize pool is split. Pure rules: no database, no Discord.

Money is in minor units (cents) and percentages in basis points (5000 = 50%) so every step is
exact; nothing is ever a float.
"""

from collections.abc import Iterable, Sequence
from fractions import Fraction
from itertools import groupby
from math import floor

from fantasy_bot.models import ParticipantId, SeasonTotal, Settlement, Standing

FULL_POOL_BP = 10_000  # 100%


def settle(standings: Sequence[Standing], split_bp: Sequence[int]) -> list[Settlement]:
    """Split one pool by rank. The rules, step by step:

    1. The pool is every buy-in added up.
    2. Teams are ranked by points, best first. Tied teams share a rank.
    3. Each paid place gets its share of the pool, e.g. [5000, 3000, 2000] is 50/30/20.
       With fewer teams than paid places, the shares in use are scaled up so the whole pool is
       still paid: two teams with 50/30/20 get 62.5% and 37.5%.
    4. Tied teams pool the shares of the places they cover and split them equally: two tied
       for 2nd under 50/30/20 each get (30% + 20%) / 2 = 25%.
    5. Payouts are whole cents. Rounding leftovers go to the largest fractional remainders,
       best rank first, so the payouts always add up to exactly the pool.
    """
    check_split(split_bp)
    if any(s.buy_in < 0 for s in standings):
        raise ValueError("buy-ins cannot be negative")
    if not standings:
        return []

    pool = sum(s.buy_in for s in standings)  # step 1
    places = _ranked_places(standings)  # step 2
    shares = _place_shares(split_bp, len(standings))  # step 3
    exact = _split_ties(places, shares, pool)  # step 4
    payouts = _round_to_pool([amount for _, _, amount in exact], pool)  # step 5
    return [
        Settlement(s.participant_id, rank, s.points, s.buy_in, payout, payout - s.buy_in)
        for (s, rank, _), payout in zip(exact, payouts, strict=True)
    ]


def check_split(split_bp: Sequence[int]) -> None:
    if sum(split_bp) != FULL_POOL_BP or any(bp <= 0 for bp in split_bp):
        raise ValueError(f"split must be positive basis points summing to 10000, got {split_bp}")


def _ranked_places(standings: Sequence[Standing]) -> list[list[Standing]]:
    """Teams grouped by place, best first; a group holds every team tied on those points."""
    ordered = sorted(standings, key=lambda s: (-s.points, s.participant_id))
    return [list(tied) for _, tied in groupby(ordered, key=lambda s: s.points)]


def _place_shares(split_bp: Sequence[int], teams: int) -> list[Fraction]:
    """Each place's exact share of the pool. Places past the paid ones get nothing."""
    paid = list(split_bp[:teams])
    return [Fraction(bp, sum(paid)) for bp in paid] + [Fraction(0)] * (teams - len(paid))


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
