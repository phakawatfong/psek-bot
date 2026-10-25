"""Start here. Every run does the same three steps:

1. load the config from .env                       config/
2. load what every job needs: database, season     dependencies.py
3. run the job named on the command line           jobs.py
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
        config = load_config()  # 1.
    except ConfigError as e:
        sys.exit(f"Config error: {e}")
    dependencies = load_dependencies(config)  # 2.
    JOBS[job](dependencies)  # 3.


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
