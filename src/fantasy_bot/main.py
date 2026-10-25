"""Program entry point: pyproject.toml maps the `fantasy-bot` command to main().

After parsing the job name (default: bot), main() loads config, prepares the database,
and calls the matching function in jobs.JOBS. Config reads the process environment;
`uv run --env-file .env` supplies it for local runs.

For the default job, continue in jobs.bot(), then discord_bot.FantasyBot. It registers
controllers/routes.py and starts the sync timer; Discord then dispatches incoming commands
to their controllers. The sync, backup, and export-participants jobs run once and exit.
"""

import argparse
import logging
import sys

from fantasy_bot.config import ConfigError, load_config
from fantasy_bot.dependencies import load_dependencies
from fantasy_bot.jobs import JOBS


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    job = parse_job()
    try:
        config = load_config()
    except ConfigError as e:
        sys.exit(f"Config error: {e}")
    dependencies = load_dependencies(config)
    JOBS[job](dependencies)


def parse_job() -> str:
    parser = argparse.ArgumentParser(prog="fantasy-bot")
    parser.add_argument(
        "job",
        nargs="?",
        choices=list(JOBS),
        default="bot",
        help=". ".join(f"{name}: {run.__doc__}" for name, run in JOBS.items()),
    )
    job: str = parser.parse_args().job
    return job


if __name__ == "__main__":
    main()
