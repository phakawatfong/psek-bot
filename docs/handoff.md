# Handoff

State on 2026-10-26, updated after configurable weekly prizes. Update this file when you finish
something on it, and delete items that are done.

## Where things stand

- `docs/plans/configurable-prizes.md` is done: effective-gameweek prize weights in
  `seed/prizes.json`, initialized to GW2 with 120/70/50/30/20/10. Every place must have a positive
  weight, with exactly as many places as eligible participants. Later rules preserve earlier
  weeks; editing earlier rules deliberately recalculates their covered weeks. No migration.
- Standings, pool and money now default to the current fantasy gameweek. Money accepts a selected
  gameweek or `season:true` for accumulated finalized-week totals. Provisional weeks are excluded.
- The four local private participant rows now start in GW2. The owner will add two more manually.
  On Lightsail, apply all six entries with `from_gameweek=2`, deploy the prize file, and restart
  the bot for its updated command options. No live bot, server change, or database reset was run.
  A count mismatch shows an explanation instead of guessing a payout. Existing buy-in remains
  unchanged; the server season must already use 50 for the agreed 300 pool.
- The earlier plans are done (their fixed-prize decisions are superseded): `docs/plans/simplify.md` (four commands, participants file, fixed
  50/30/15/5 prizes) and `docs/plans/layer-folders.md` (folders by layer; `main.py` is
  config → dependencies → job).
- `docs/plans/schedule.md` is done: `/psek-nba-schedule [gameweek] [day]` is the fifth command.
  Both options select that day; day alone uses the current gameweek; no options uses the current
  fantasy day; gameweek alone shows the whole week. Fantasy deadlines define day boundaries.
  Schedules fetch on demand, show Bangkok times and completed scores, and do not use the database.
- The current commit is `8e2a258` (`update readme`). Weekly-prize and summary changes are
  uncommitted for the owner's review. The owner stages and commits.
- `docs/plans/team-emojis.md` is done: schedule replies include NBA team logo emojis, reused
  from the bot application or uploaded once if missing. Setup runs at startup with a 60-second
  limit. Missing logos fall back to team codes and retry on the next restart; no additional
  scheduled job or database storage. All 30 public logo downloads were verified.
- Shared SQL expressions moved from `database/queries.py` to `repositories/queries.py`, next
  to their only callers. Behaviour is unchanged.
- After discussing MVC, the owner chose to keep the current structure and focus on reading
  the flow. README summarizes startup and a pool command with Mermaid diagrams and explains
  the package folder; main.py explains the entry point and where to read next. No runtime
  behaviour changed.
- The default weekly buy-in is now 50.00 (5000 minor units), also reflected in `.env.example`.
  Explicit environment settings and existing seasons keep their own buy-in. Historical
  migrations are unchanged; new seasons receive the configured amount explicitly.
- Checks rerun after configurable weekly prizes: 180 tests, ruff format,
  ruff check, and mypy pass.
  A read-only API check returned GW2's seven days and 49 games. The new command has not been
  published to Discord by this agent; restarting the updated bot registers it through the usual
  startup and uploads missing application emojis. Ask the owner before starting the live bot.
  No live bot or database sync was run during this cleanup. The previously reported sync on a
  copy of the real database applied the real
  participants file and synced all four teams. No gameweek is final yet, so `/psek-nba-money` shows
  an empty table and `/psek-nba-pool` shows gameweek 1 so far.

## Deferred ideas: discuss before changing

1. **Keep `discord_bot.py` at the top level for now.** It manages the client lifecycle and
   sync timer and imports config, which current controller import rules disallow. Moving it
   just to tidy the top level is not part of the agreed readability cleanup.
## Next work

1. **Deploy to the AWS Lightsail server (Ubuntu).** The owner does these steps on the server;
   help them through it. The repo is cloned at `~/psek-bot`. `deploy/setup.sh` didn't finish the
   first time ("docker: command not found"; possibly the apt lock on first boot). Ask the owner
   for `~/setup.log`, then re-run `sudo APP_DIR=$HOME/psek-bot bash deploy/setup.sh` inside tmux.
   After that: copy `.env` and `seed/participants.csv` to the server, then
   `docker compose up -d --build`. Steps are in README → Deploy to AWS Lightsail.
2. **`.env` inline comment.** The owner's `DISCORD_GUILD_ID` line has a `## …` comment after the
   value. `docker run --env-file` reads it as part of the value and stops on a config error.
   Docker Compose should strip it, but that hasn't been checked. Ask the owner to move the comment
   to its own line.

## Known limits (deliberate, fine for four friends)

- The charts have eight team colours; a ninth team would need small multiples.
- The `/psek-nba-money` table puts one person per column, about 10 characters each. Past about
  six people it wraps on phones.
- Bars have square ends: the chart style guide asks for rounded data-ends, which matplotlib has
  no simple way to draw.
