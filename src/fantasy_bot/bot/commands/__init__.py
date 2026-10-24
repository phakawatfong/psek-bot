import sqlite3
from collections.abc import Mapping

from discord import app_commands

from fantasy_bot.bot.commands import (
    admin,
    chart,
    money,
    participants,
    points,
    register,
    rules,
    schedule,
    standings,
)

PREFIX = "psek-nba"


def register_all(
    tree: app_commands.CommandTree,
    conn: sqlite3.Connection,
    season_id: str,
    team_icons: Mapping[str, str],
) -> None:
    """Every slash command the bot exposes. Users type /psek-nba-<name>.

    `team_icons` is filled in once the logo emojis are loaded; until then games show codes only.
    """
    routes = [
        # (name, description shown in Discord, handler)
        (
            "standings",
            "Rank teams by season points, or by one gameweek",
            standings.handler(conn, season_id),
        ),
        ("points", "Each team's points on one day", points.handler(conn, season_id)),
        (
            "chart",
            "Picture of every team's season points growing day by day",
            chart.handler(conn, season_id),
        ),
        (
            "schedule",
            "NBA games for a day or a whole gameweek, with scores once played",
            schedule.handler(conn, season_id, team_icons),
        ),
        (
            "participants",
            "Registered teams",
            participants.handler(conn, season_id),
        ),
        ("rules", "How the prize pool works this season", rules.handler(conn, season_id)),
        (
            "money",
            "Weekly pools, each person's net, and who still owes or is owed",
            money.handler(conn, season_id),
        ),
        ("register", "Join the pool with your nbafantasy team", register.handler(conn, season_id)),
        # Admin only: visible to members with Manage Server.
        (
            "add",
            "Add a friend's team straight into the pool",
            admin.add_handler(conn, season_id),
        ),
        (
            "approve",
            "Approve a registered team into the pool",
            admin.approve_handler(conn, season_id),
        ),
        (
            "paid",
            "Record real money paid into or out of the pot",
            admin.paid_handler(conn, season_id),
        ),
    ]
    for name, description, callback in routes:
        tree.add_command(
            app_commands.Command(
                name=f"{PREFIX}-{name}", description=description, callback=callback
            )
        )
