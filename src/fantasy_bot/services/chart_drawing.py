"""The points charts, drawn as PNGs for Discord: season total after each day (lines), and
points in each gameweek (bars)."""

import io

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from fantasy_bot.models.chart import GameweekPoints, PointsHistory, PointsSeries
from fantasy_bot.models.participant import ParticipantId

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
GROUP_WIDTH = 0.8  # share of a gameweek's slot its bars fill


def px(n: float) -> float:
    """A design-size pixel in matplotlib points."""
    return n * 72 / 100


def series_colors(participants: list[ParticipantId]) -> dict[int, str]:
    """Slot colors in participant order, so a team keeps its color whatever its rank."""
    # ponytail: past 8 teams this would need small multiples, not a 9th hue
    return dict(zip(participants, SERIES_COLORS, strict=False))


def points_race_png(history: PointsHistory) -> bytes:
    series = history.series[: len(SERIES_COLORS)]
    colors = series_colors([s.participant_id for s in series])
    fig = Figure(figsize=(6.4, 3.6), dpi=DPI, facecolor=SURFACE)
    ax: Axes = fig.subplots()
    _style_axes(ax, "Day", "Season points")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))

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
    return _png(fig)


def points_by_gameweek_png(weekly: GameweekPoints) -> bytes:
    """Grouped bars: one group per gameweek, one bar per team, in participant order."""
    series = weekly.series[: len(SERIES_COLORS)]
    colors = series_colors([s.participant_id for s in series])
    gameweeks = sorted({gw for s in series for gw in s.gameweeks})
    slot = {gw: i for i, gw in enumerate(gameweeks)}
    fig = Figure(figsize=(6.4, 3.6), dpi=DPI, facecolor=SURFACE)
    ax: Axes = fig.subplots()
    _style_axes(ax, "Gameweek", "Points in the gameweek")

    width = GROUP_WIDTH / len(series)
    for i, s in enumerate(series):
        offset = (i - (len(series) - 1) / 2) * width
        ax.bar(
            [slot[gw] + offset for gw in s.gameweeks],
            [p / 10 for p in s.points],
            width=width,
            color=colors[s.participant_id],
            edgecolor=SURFACE,  # the 2px surface gap between neighbouring bars
            linewidth=px(2),
            label=s.name.team_name,
        )
    ax.set_xticks(
        range(len(gameweeks)),
        [f"{gw}" + ("\nso far" if gw in weekly.not_final else "") for gw in gameweeks],
    )
    ax.axhline(0, color=GRID, linewidth=px(1))
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.0),
        ncols=min(len(series), 4),
        frameon=False,
        labelcolor=TEXT,
        fontsize=7,
        handlelength=1.0,
        borderaxespad=0.2,
    )
    ax.set_title("Points in each gameweek", loc="left", color=TEXT, fontsize=10, pad=24)
    return _png(fig)


def _png(fig: Figure) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor=SURFACE, bbox_inches="tight", pad_inches=0.15)
    return buffer.getvalue()


def _style_axes(ax: Axes, xlabel: str, ylabel: str) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.spines["bottom"].set_linewidth(px(1))
    ax.grid(axis="y", color=GRID, linewidth=px(1))
    ax.set_axisbelow(True)
    ax.tick_params(colors=TEXT_MUTED, labelsize=7, length=0, pad=4)
    ax.set_xlabel(xlabel, color=TEXT_MUTED, fontsize=7)
    ax.set_ylabel(ylabel, color=TEXT_MUTED, fontsize=7)


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
