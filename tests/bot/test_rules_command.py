from fantasy_bot.bot.commands.rules import format_rules, ordinal, tie_example
from fantasy_bot.models import PoolRules


def test_rules_state_this_seasons_numbers_in_plain_words() -> None:
    text = format_rules(PoolRules(10000, (5000, 3000, 2000)), "2026-27")
    assert text.splitlines()[:5] == [
        "**Prize pool rules, season 2026-27**",
        "- **Buy-in:** 100.00 per person, every gameweek from the one they joined.",
        "- **Weekly pool:** 100.00 times the number of teams in it that week.",
        "- **Prizes:** by that gameweek's points after transfer costs: 1st 50%, 2nd 30%,"
        " 3rd 20%. Everyone else wins nothing that week.",
        "- **Ties:** tied teams share the prizes of the places they cover equally: two teams"
        " tied for 2nd each get (30% + 20%) / 2 = 25%.",
    ]


def test_tie_example_follows_the_split() -> None:
    assert [tie_example(split) for split in [(6000, 4000), (10000,)]] == [
        "two teams tied for 1st each get (60% + 40%) / 2 = 50%.",
        "two teams tied for 1st each get half of it.",
    ]


def test_ordinals() -> None:
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22)] == [
        "1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd"
    ]  # fmt: skip
