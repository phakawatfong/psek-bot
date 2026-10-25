from fantasy_bot.models.chart import GameweekPoints, GameweekSeries, PointsHistory, PointsSeries
from fantasy_bot.models.participant import ParticipantId, ParticipantName
from fantasy_bot.services.chart_drawing import (
    SERIES_COLORS,
    points_by_gameweek_png,
    points_race_png,
    series_colors,
)


def team(pid: int, totals: list[int]) -> PointsSeries:
    return PointsSeries(
        ParticipantId(pid), ParticipantName(f"team {pid}", ""), list(range(1, 7)), totals
    )


def test_colors_follow_the_team_not_its_rank() -> None:
    ids = [ParticipantId(1), ParticipantId(2)]
    assert series_colors(ids) == {1: SERIES_COLORS[0], 2: SERIES_COLORS[1]}


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


def size(png: bytes) -> tuple[int, int]:
    return int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")


def test_gameweek_chart_is_a_png_of_normal_size() -> None:
    weekly = GameweekPoints(
        [
            GameweekSeries(
                ParticipantId(1), ParticipantName("team 1", ""), [1, 2, 3], [4410, 3950, 120]
            ),
            GameweekSeries(ParticipantId(2), ParticipantName("team 2", ""), [2, 3], [5100, 300]),
        ],
        not_final=[3],
    )
    png = points_by_gameweek_png(weekly)
    width, height = size(png)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and width < 1400 and height < 900
