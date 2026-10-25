from fantasy_bot.controllers.pool import format_pool
from fantasy_bot.models.money import Settlement
from fantasy_bot.models.participant import ParticipantId, ParticipantName
from fantasy_bot.models.pool import Pool, PoolLine


def line(pid: int, team: str, rank: int, points: int, payout: int) -> PoolLine:
    return PoolLine(
        ParticipantName(team, ""),
        Settlement(ParticipantId(pid), rank, points, 10000, payout, payout - 10000),
    )


def test_pool_shows_buy_ins_winnings_and_each_share() -> None:
    # Three teams, so 50/30/15 is scaled up to fill the pool.
    pool = Pool(
        2,
        False,
        [
            line(1, "jkslots", 1, 9055, 15789),
            line(2, "GO", 2, 7000, 9474),
            line(3, "Dream", 3, 10, 4737),
        ],
    )
    assert format_pool(pool, None) == (
        "**Gameweek 2 pool: 300.00** (so far, may still change)\n"
        "1. 🏆 jkslots 905.5 pts: put in 100.00, wins 157.89 (52.6%), net +57.89\n"
        "2. GO 700.0 pts: put in 100.00, wins 94.74 (31.6%), net -5.26\n"
        "3. 🐢 Dream 1.0 pts: put in 100.00, wins 47.37 (15.8%), net -52.63"
    )


def test_ties_share_a_rank_and_the_four_place_split() -> None:
    pool = Pool(
        1,
        True,
        [
            line(1, "A", 1, 900, 20000),
            line(2, "B", 2, 700, 9000),
            line(3, "C", 2, 700, 9000),
            line(4, "D", 4, 1, 2000),
        ],
    )
    assert format_pool(pool, 1).splitlines()[1:] == [
        "1. 🏆 A 90.0 pts: put in 100.00, wins 200.00 (50%), net +100.00",
        "2. B 70.0 pts: put in 100.00, wins 90.00 (22.5%), net -10.00",
        "2. C 70.0 pts: put in 100.00, wins 90.00 (22.5%), net -10.00",
        "4. 🐢 D 0.1 pts: put in 100.00, wins 20.00 (5%), net -80.00",
    ]


def test_no_points_yet() -> None:
    assert format_pool(None, 7) == "No points synced for gameweek 7 yet."
    assert format_pool(None, None) == "No points yet."
