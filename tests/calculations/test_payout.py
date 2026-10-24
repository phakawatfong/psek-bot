import pytest

from fantasy_bot.calculations.payout import settle
from fantasy_bot.models import ParticipantId, Standing

SPLIT = [5000, 3000, 2000]


def standings(*rows: tuple[int, int, int]) -> list[Standing]:
    return [Standing(ParticipantId(pid), points, buy_in) for pid, points, buy_in in rows]


def table(rows: list[Standing], split: list[int] = SPLIT) -> list[tuple[int, int, int, int]]:
    return [(s.participant_id, s.rank, s.payout, s.net) for s in settle(rows, split)]


def test_top_three_take_50_30_20_of_the_pool() -> None:
    rows = standings((1, 900, 1000), (2, 700, 1000), (3, 500, 1000), (4, 300, 1000))
    assert table(rows) == [
        (1, 1, 2000, 1000),
        (2, 2, 1200, 200),
        (3, 3, 800, -200),
        (4, 4, 0, -1000),
    ]


def test_input_order_does_not_matter() -> None:
    rows = standings((4, 300, 1000), (2, 700, 1000), (1, 900, 1000), (3, 500, 1000))
    assert [r[:3] for r in table(rows)] == [(1, 1, 2000), (2, 2, 1200), (3, 3, 800), (4, 4, 0)]


def test_tie_for_second_splits_second_and_third_shares() -> None:
    rows = standings((1, 900, 1000), (2, 700, 1000), (3, 700, 1000), (4, 300, 1000))
    assert table(rows) == [(1, 1, 2000, 1000), (2, 2, 1000, 0), (3, 2, 1000, 0), (4, 4, 0, -1000)]


def test_tie_for_third_shares_third_place_with_unpaid_rank() -> None:
    rows = standings((1, 900, 1000), (2, 700, 1000), (3, 500, 1000), (4, 500, 1000))
    assert table(rows) == [
        (1, 1, 2000, 1000),
        (2, 2, 1200, 200),
        (3, 3, 400, -600),
        (4, 3, 400, -600),
    ]


def test_fewer_players_than_paid_ranks_scales_shares_up() -> None:
    rows = standings((1, 900, 1000), (2, 700, 1000))
    assert table(rows) == [(1, 1, 1250, 250), (2, 2, 750, -250)]


def test_rounding_leftover_goes_to_largest_remainder() -> None:
    rows = standings((1, 900, 334), (2, 700, 334), (3, 500, 333))
    assert [r[2] for r in table(rows)] == [501, 300, 200]


def test_three_way_tie_never_loses_a_unit() -> None:
    rows = standings((1, 500, 334), (2, 500, 333), (3, 500, 333))
    assert [r[2] for r in table(rows)] == [334, 333, 333]


def test_unequal_buy_ins_use_a_flat_split_of_the_whole_pool() -> None:
    rows = standings((1, 900, 100), (2, 700, 1000), (3, 500, 1000))
    assert table(rows) == [(1, 1, 1050, 950), (2, 2, 630, -370), (3, 3, 420, -580)]


def test_no_participants_settles_nothing() -> None:
    assert settle([], SPLIT) == []


@pytest.mark.parametrize("split", [[5000, 3000], [5000, 5000, 0], [6000, 6000, -2000]])
def test_invalid_split_is_rejected(split: list[int]) -> None:
    with pytest.raises(ValueError, match="basis points"):
        settle(standings((1, 900, 1000)), split)


def test_negative_buy_in_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        settle(standings((1, 900, -1)), SPLIT)
