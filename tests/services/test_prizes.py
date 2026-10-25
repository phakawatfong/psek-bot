import pytest

from fantasy_bot.models.money import Standing
from fantasy_bot.models.participant import ParticipantId
from fantasy_bot.services.prizes import PRIZES, season_totals, settle


def standings(*rows: tuple[int, int, int]) -> list[Standing]:
    return [Standing(ParticipantId(pid), points, buy_in) for pid, points, buy_in in rows]


def table(rows: list[Standing]) -> list[tuple[int, int, int, int]]:
    """(participant, rank, payout, net) for each team, best first."""
    return [(s.participant_id, s.rank, s.payout, s.net) for s in settle(rows)]


def test_the_prizes_are_50_30_15_5() -> None:
    assert PRIZES == (5000, 3000, 1500, 500)


def test_four_teams_take_50_30_15_5_of_the_pool() -> None:
    # Pool 4 x 1000 = 4000: 2000, 1200, 600, 200.
    rows = standings((1, 900, 1000), (2, 700, 1000), (3, 500, 1000), (4, 300, 1000))
    assert table(rows) == [
        (1, 1, 2000, 1000),
        (2, 2, 1200, 200),
        (3, 3, 600, -400),
        (4, 4, 200, -800),
    ]


def test_fifth_and_below_win_nothing() -> None:
    # Pool 5000: 2500, 1500, 750, 250, 0.
    rows = standings(*((pid, 1000 - 100 * pid, 1000) for pid in range(1, 6)))
    assert [payout for _, _, payout, _ in table(rows)] == [2500, 1500, 750, 250, 0]


def test_input_order_does_not_matter() -> None:
    rows = standings((4, 300, 1000), (2, 700, 1000), (1, 900, 1000), (3, 500, 1000))
    assert [(pid, payout) for pid, _, payout, _ in table(rows)] == [
        (1, 2000),
        (2, 1200),
        (3, 600),
        (4, 200),
    ]


def test_two_tied_for_second_each_get_22_5_percent() -> None:
    # 2nd and 3rd prizes (30% + 15%) / 2 = 22.5% of 4000 = 900 each.
    rows = standings((1, 900, 1000), (2, 700, 1000), (3, 700, 1000), (4, 300, 1000))
    assert table(rows) == [
        (1, 1, 2000, 1000),
        (2, 2, 900, -100),
        (3, 2, 900, -100),
        (4, 4, 200, -800),
    ]


def test_two_tied_for_fourth_share_its_5_percent() -> None:
    # 4th's 5% plus 5th's 0%, halved: 2.5% of 5000 = 125 each.
    rows = standings((1, 900, 1000), (2, 800, 1000), (3, 700, 1000), (4, 600, 1000), (5, 600, 1000))
    assert [(pid, rank, payout) for pid, rank, payout, _ in table(rows)][3:] == [
        (4, 4, 125),
        (5, 4, 125),
    ]


def test_everyone_tied_splits_the_pool_evenly() -> None:
    rows = standings(*((pid, 500, 1000) for pid in range(1, 5)))
    assert [payout for _, _, payout, _ in table(rows)] == [1000, 1000, 1000, 1000]


def test_fewer_than_four_teams_scale_the_prizes_up() -> None:
    # Two teams: 50/30 scaled to 100% is 62.5% and 37.5% of 2000.
    assert [payout for _, _, payout, _ in table(standings((1, 900, 1000), (2, 700, 1000)))] == [
        1250,
        750,
    ]
    # Three teams: 50/30/15 scaled to 100% of 3000 is 1578.95, 947.37, 473.68; the two
    # leftover cents go to the largest remainders, .95 and .68.
    rows = standings((1, 900, 1000), (2, 700, 1000), (3, 500, 1000))
    assert [payout for _, _, payout, _ in table(rows)] == [1579, 947, 474]


def test_rounding_always_pays_out_exactly_the_pool() -> None:
    # Pool 1001: 500.50, 300.30, 150.15, 50.05; the leftover cent goes to the .50.
    rows = standings((1, 900, 251), (2, 700, 250), (3, 500, 250), (4, 300, 250))
    payouts = [payout for _, _, payout, _ in table(rows)]
    assert (payouts, sum(payouts)) == ([501, 300, 150, 50], 1001)


def test_unequal_buy_ins_still_split_the_whole_pool() -> None:
    # Pool 2100 between three teams: 1105.26, 663.16, 331.58; the leftover cent goes to .58.
    rows = standings((1, 900, 100), (2, 700, 1000), (3, 500, 1000))
    assert table(rows) == [(1, 1, 1105, 1005), (2, 2, 663, -337), (3, 3, 332, -668)]


def test_no_participants_settles_nothing() -> None:
    assert settle([]) == []


def test_negative_buy_in_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        settle(standings((1, 900, -1)))


def test_season_totals_add_up_weeks_and_rank_by_net() -> None:
    week_1 = settle(standings((1, 900, 100), (2, 700, 100), (3, 500, 100), (4, 300, 100)))
    week_2 = settle(standings((1, 100, 100), (2, 700, 100), (3, 500, 100), (4, 600, 100)))
    # Week 1 pays 200/120/60/20 to 1/2/3/4; week 2 pays 200/120/60/20 to 2/4/3/1.
    assert [
        (t.participant_id, t.weeks, t.paid, t.won, t.net) for t in season_totals([week_1, week_2])
    ] == [
        (2, 2, 200, 320, 120),
        (1, 2, 200, 220, 20),
        (4, 2, 200, 140, -60),
        (3, 2, 200, 120, -80),
    ]
