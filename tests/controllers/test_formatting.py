from fantasy_bot.controllers.formatting import percentages, signed


def test_percentages_drop_needless_decimals() -> None:
    assert percentages((5000, 3000, 1500, 500)) == "50/30/15/5"
    assert percentages((3334, 3333, 3333)) == "33.34/33.33/33.33"


def test_signed_money_always_shows_its_sign() -> None:
    assert (signed(5000), signed(0), signed(-526)) == ("+50.00", "+0.00", "-5.26")
