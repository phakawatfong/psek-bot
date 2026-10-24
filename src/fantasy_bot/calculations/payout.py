from collections.abc import Iterable, Sequence
from fractions import Fraction
from itertools import groupby
from math import floor

from fantasy_bot.models import ParticipantId, SeasonTotal, Settlement, Standing

FULL_POOL_BP = 10_000


def settle(standings: Sequence[Standing], split_bp: Sequence[int]) -> list[Settlement]:
    """Rank by points and divide the pool of all buy-ins by `split_bp` (basis points per rank).

    Tied participants share the combined shares of the ranks they occupy. With fewer
    participants than paid ranks, the used shares are scaled up so the whole pool is paid.
    Rounding leftovers go to the largest fractional remainders, best rank first, so the
    payouts always sum to exactly the pool.
    """
    if sum(split_bp) != FULL_POOL_BP or any(bp <= 0 for bp in split_bp):
        raise ValueError(f"split must be positive basis points summing to 10000, got {split_bp}")
    if any(s.buy_in < 0 for s in standings):
        raise ValueError("buy-ins cannot be negative")
    if not standings:
        return []

    pool = sum(s.buy_in for s in standings)
    ordered = sorted(standings, key=lambda s: (-s.points, s.participant_id))
    paid_bp = list(split_bp[: len(ordered)])
    rank_bp = paid_bp + [0] * (len(ordered) - len(paid_bp))

    exact: list[tuple[Standing, int, Fraction]] = []
    for _, tied in groupby(ordered, key=lambda s: s.points):
        group = list(tied)
        first = len(exact)
        group_bp = sum(rank_bp[first : first + len(group)])
        each = Fraction(pool * group_bp, sum(paid_bp) * len(group))
        exact += [(s, first + 1, each) for s in group]

    payouts = [floor(share) for _, _, share in exact]
    leftover = pool - sum(payouts)
    by_remainder = sorted(range(len(exact)), key=lambda i: (payouts[i] - exact[i][2], i))
    for i in by_remainder[:leftover]:
        payouts[i] += 1

    return [
        Settlement(s.participant_id, rank, s.points, s.buy_in, payout, payout - s.buy_in)
        for (s, rank, _), payout in zip(exact, payouts, strict=True)
    ]


def season_totals(weeks: Iterable[Sequence[Settlement]]) -> list[SeasonTotal]:
    """Add up each participant's weekly settlements. Best net first."""
    totals: dict[ParticipantId, tuple[int, int, int]] = {}
    for week in weeks:
        for s in week:
            played, paid, won = totals.get(s.participant_id, (0, 0, 0))
            totals[s.participant_id] = (played + 1, paid + s.buy_in, won + s.payout)
    rows = [SeasonTotal(pid, n, paid, won, won - paid) for pid, (n, paid, won) in totals.items()]
    return sorted(rows, key=lambda t: (-t.net, t.participant_id))
