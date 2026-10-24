"""The points race: every team's season total after each day, drawn as a PNG for Discord."""

import io

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from fantasy_bot.models import PointsHistory, PointsSeries

# Dark steps of the dataviz reference palette in its fixed slot order; validate_palette.js
# passes all checks for these on SURFACE. Discord is mostly used in dark mode.
SERIES_COLORS = [
    "#3987e5",
    "#d95926",
    "#199e70",
    "#c98500",
    "#d55181",
    "#008300",
    "#9085e9",
    "#e66767",
]
SURFACE = "#1a1a19"
TEXT = "#f0efec"
TEXT_MUTED = "#c3c2b7"
GRID = "#383835"
DPI = 200  # twice the 100-dpi design size, so the image stays sharp when Discord scales it
DIRECT_LABEL_MAX = 4  # more teams than this are identified by the legend alone
MIN_LABEL_GAP = 0.06  # share of the y-range two end labels need between them


def px(n: float) -> float:
    """A design-size pixel in matplotlib points."""
    return n * 72 / 100


def series_colors(series: list[PointsSeries]) -> dict[int, str]:
    """Slot colors in participant order, so a team keeps its color whatever its rank."""
    # ponytail: past 8 teams this would need small multiples, not a 9th hue
    return {s.participant_id: color for s, color in zip(series, SERIES_COLORS, strict=False)}


def points_race_png(history: PointsHistory) -> bytes:
    series = history.series[: len(SERIES_COLORS)]
    colors = series_colors(series)
    fig = Figure(figsize=(6.4, 3.6), dpi=DPI, facecolor=SURFACE)
    ax: Axes = fig.subplots()
    _style_axes(ax)

    for s in series:
        totals = [t / 10 for t in s.totals]
        color = colors[s.participant_id]
        ax.plot(
            s.days,
            totals,
            color=color,
            linewidth=px(2),
            solid_capstyle="round",
            solid_joinstyle="round",
            # The total rides in the legend too, so it survives a skipped end label.
            label=f"{s.name.team_name}  {totals[-1]:.1f}",
        )
        ax.plot(
            s.days[-1:],
            totals[-1:],
            marker="o",
            color=color,
            markersize=px(9),
            markeredgecolor=SURFACE,
            markeredgewidth=px(2),
            zorder=3,
        )

    # Only after plotting: before it, the autoscaled top is still 1 and would freeze there.
    ax.set_ylim(bottom=0)
    _gameweek_marks(ax, history, series)
    if len(series) <= DIRECT_LABEL_MAX:
        _end_labels(ax, series)
    _legend(ax, series)

    ax.set_title("Season points after each day", loc="left", color=TEXT, fontsize=10, pad=14)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor=SURFACE, bbox_inches="tight", pad_inches=0.15)
    return buffer.getvalue()


def _style_axes(ax: Axes) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.spines["bottom"].set_linewidth(px(1))
    ax.grid(axis="y", color=GRID, linewidth=px(1))
    ax.set_axisbelow(True)
    ax.tick_params(colors=TEXT_MUTED, labelsize=7, length=0, pad=4)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel("Day", color=TEXT_MUTED, fontsize=7)
    ax.set_ylabel("Season points", color=TEXT_MUTED, fontsize=7)


def _gameweek_marks(ax: Axes, history: PointsHistory, series: list[PointsSeries]) -> None:
    """A hairline and a small "GW n" label where each gameweek starts."""
    days = sorted({d for s in series for d in s.days})
    first, last = days[0], days[-1]
    starts: dict[int, int] = {}
    for day in range(first, last + 1):
        gameweek = history.gameweek_of_day.get(day)
        if gameweek is not None and gameweek not in starts.values():
            starts[day] = gameweek
    for day, gameweek in starts.items():
        if day > first:
            ax.axvline(day - 0.5, color=GRID, linewidth=px(1), zorder=0)
        ax.text(
            max(day - 0.5, first),
            1.0,
            f"GW {gameweek}",
            transform=ax.get_xaxis_transform(),
            color=TEXT_MUTED,
            fontsize=6,
            va="bottom",
        )


def _end_labels(ax: Axes, series: list[PointsSeries]) -> None:
    """Each line's latest total beside its end dot, skipping any that would collide."""
    y_range = max(max(s.totals) for s in series) / 10 or 1
    placed: list[float] = []
    for s in sorted(series, key=lambda s: s.totals[-1], reverse=True):
        y = s.totals[-1] / 10
        if any(abs(y - other) < MIN_LABEL_GAP * y_range for other in placed):
            continue  # the legend still names it
        placed.append(y)
        ax.annotate(
            f"{y:.1f}",
            (s.days[-1], y),
            xytext=(px(10), 0),
            textcoords="offset points",
            va="center",
            color=TEXT,
            fontsize=7,
            annotation_clip=False,
        )


def _legend(ax: Axes, series: list[PointsSeries]) -> None:
    """Teams listed best-first, each with its line key; text stays in the text color."""
    handles, labels = ax.get_legend_handles_labels()
    ranked = sorted(
        zip(handles, labels, series, strict=True), key=lambda h: h[2].totals[-1], reverse=True
    )
    ax.legend(
        [h for h, _, _ in ranked],
        [label for _, label, _ in ranked],
        loc="upper left",
        frameon=False,
        labelcolor=TEXT,
        fontsize=7,
        handlelength=1.4,
    )
