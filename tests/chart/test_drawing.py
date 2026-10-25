from fantasy_bot.bot.charts import SERIES_COLORS, points_race_png, series_colors
from fantasy_bot.models import ParticipantId, ParticipantName, PointsHistory, PointsSeries


def team(pid: int, totals: list[int]) -> PointsSeries:
    return PointsSeries(
        ParticipantId(pid), ParticipantName(f"team {pid}", ""), list(range(1, 7)), totals
    )


def test_colors_follow_the_team_not_its_rank() -> None:
    leader_first = [team(1, [9] * 6), team(2, [5] * 6)]
    leader_second = [team(1, [5] * 6), team(2, [9] * 6)]
    assert (
        series_colors(leader_first)
        == series_colors(leader_second)
        == {
            1: SERIES_COLORS[0],
            2: SERIES_COLORS[1],
        }
    )


def test_chart_is_a_png() -> None:
    history = PointsHistory(
        [team(1, [10, 30, 30, 60, 80, 120]), team(2, [20, 20, 50, 70, 90, 100])],
        {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2},
    )
    png = points_race_png(history)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 10_000


def test_chart_keeps_its_size_with_real_point_scales() -> None:
    # Regression: the y-axis was frozen at 0-1 before plotting, so end labels for totals in
    # the hundreds stretched the image to over 260,000 pixels tall.
    history = PointsHistory([team(1, [660, 2850, 2850, 4760, 5000, 5100])], {})
    png = points_race_png(history)
    width, height = int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")
    assert width < 1400 and height < 900
