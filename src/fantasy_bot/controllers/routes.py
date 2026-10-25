"""Every slash command the bot has, and the controller that answers it.

Start here to see what the bot can do. Users type /psek-nba-<name>.
"""

from discord import app_commands
from sqlalchemy.orm import Session, sessionmaker

from fantasy_bot.controllers import chart, money, pool, schedule, standings

PREFIX = "psek-nba"


def register_all(
    tree: app_commands.CommandTree,
    sessions: sessionmaker[Session],
    season_id: str,
    team_icons: dict[str, str] | None = None,
) -> None:
    routes = [
        # (name, description shown in Discord, handler)
        (
            "standings",
            "Every team, 1st to last, by season points",
            standings.handler(sessions, season_id),
        ),
        (
            "money",
            "Each person's win or loss per gameweek and in total",
            money.handler(sessions, season_id),
        ),
        (
            "chart",
            "Picture of season points by day, or points per gameweek",
            chart.handler(sessions, season_id),
        ),
        (
            "pool",
            "One gameweek's pool: who put in what, and who wins what",
            pool.handler(sessions, season_id),
        ),
        (
            "schedule",
            "NBA matches by fantasy gameweek and day",
            schedule.handler(sessions, season_id, team_icons),
        ),
    ]
    for name, description, callback in routes:
        tree.add_command(
            app_commands.Command(
                name=f"{PREFIX}-{name}",
                description=description,
                callback=callback,
            )
        )
