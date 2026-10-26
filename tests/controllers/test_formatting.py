from fantasy_bot.controllers.formatting import signed, split_reply


def test_signed_money_always_shows_its_sign() -> None:
    assert (signed(5000), signed(0), signed(-526)) == ("+50.00", "+0.00", "-5.26")


def test_long_money_table_is_split_into_balanced_code_blocks() -> None:
    text = (
        "Season totals\n```\n"
        + "\n".join(f"GW{n} " + ("123.45 " * 20) for n in range(1, 31))
        + "\n```\nProvisional weeks excluded."
    )
    messages = split_reply(text)
    assert len(messages) > 1
    assert all(len(m) <= 2000 and m.count("```") % 2 == 0 for m in messages)
    combined = "\n".join(messages)
    for n in range(1, 31):
        assert combined.count(f"GW{n} ") == 1
    assert combined.endswith("Provisional weeks excluded.")
