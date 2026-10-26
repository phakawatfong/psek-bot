import pytest

from fantasy_bot.models.money import Standing
from fantasy_bot.models.participant import ParticipantId
from fantasy_bot.services.prize_rules import PrizeError
from fantasy_bot.services.prizes import season_totals, settle

WEIGHTS = (120, 70, 50, 30, 20, 10)


def standings(n: int = 6, buy_in: int = 5000) -> list[Standing]:
    return [Standing(ParticipantId(i), (n - i) * 100, buy_in) for i in range(1, n + 1)]


def test_six_people_pay_50_and_get_the_agreed_payouts() -> None:
    result = settle(standings(), WEIGHTS)
    assert [r.payout for r in result] == [12000, 7000, 5000, 3000, 2000, 1000]
    assert [r.net for r in result] == [7000, 2000, 0, -2000, -3000, -4000]
    assert sum(r.payout for r in result) == 30000
    assert sum(r.net for r in result) == 0


def test_weights_scale_with_pool_without_rounding_percentages() -> None:
    result = settle(standings(buy_in=10000), WEIGHTS)
    assert [r.payout for r in result] == [24000, 14000, 10000, 6000, 4000, 2000]


def test_input_order_does_not_change_result() -> None:
    assert settle(list(reversed(standings())), WEIGHTS) == settle(standings(), WEIGHTS)


def test_tied_second_and_third_share_their_prizes() -> None:
    rows = standings()
    rows[2] = Standing(rows[2].participant_id, rows[1].points, 5000)
    result = settle(rows, WEIGHTS)
    assert [r.rank for r in result] == [1, 2, 2, 4, 5, 6]
    assert [r.payout for r in result] == [12000, 6000, 6000, 3000, 2000, 1000]


def test_everyone_tied_splits_evenly() -> None:
    rows = [Standing(ParticipantId(i), 0, 5000) for i in range(6)]
    assert [r.payout for r in settle(rows, WEIGHTS)] == [5000] * 6


def test_seventh_person_requires_explicit_seven_place_rule() -> None:
    with pytest.raises(PrizeError, match="one positive"):
        settle(standings(7), WEIGHTS)
    result = settle(standings(7), (7, 6, 5, 4, 3, 2, 1))
    assert len(result) == 7 and all(r.payout > 0 for r in result)
    assert sum(r.payout for r in result) == 35000


@pytest.mark.parametrize("n", range(1, 11))
def test_matching_positive_weights_pay_everyone_and_exhaust_pool(n: int) -> None:
    result = settle(standings(n, buy_in=1001), tuple(range(n, 0, -1)))
    assert all(r.payout > 0 for r in result)
    assert sum(r.payout for r in result) == n * 1001


def test_largest_remainder_uses_whole_cents() -> None:
    rows = [Standing(ParticipantId(1), 100, 51), Standing(ParticipantId(2), 90, 50)]
    assert [r.payout for r in settle(rows, (2, 1))] == [67, 34]


@pytest.mark.parametrize("weights", [(1,), (1, 0), (1, -1)])
def test_invalid_weights_are_rejected(weights: tuple[int, ...]) -> None:
    with pytest.raises(PrizeError):
        settle(standings(2), weights)


def test_insufficient_pool_is_explained() -> None:
    with pytest.raises(PrizeError, match="at least one cent"):
        settle(standings(2, buy_in=1), (1000, 1))


def test_negative_buy_in_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        settle(standings(1, buy_in=-1), (1,))


def test_no_participants_settles_nothing() -> None:
    assert settle([], ()) == []


def test_weekly_nets_accumulate() -> None:
    first = settle(standings(), WEIGHTS)
    second = settle([Standing(r.participant_id, -r.points, 5000) for r in standings()], WEIGHTS)
    totals = season_totals([first, second])
    assert sum(t.net for t in totals) == 0
    assert all(t.weeks == 2 and t.paid == 10000 for t in totals)
    assert {t.participant_id: t.net for t in totals} == {
        1: 3000,
        2: -1000,
        3: -2000,
        4: -2000,
        5: -1000,
        6: 3000,
    }
