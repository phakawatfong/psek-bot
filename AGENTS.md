# Agent guide

A Discord bot for a friends' NBA Fantasy league: standings, a weekly money pool, and charts.
What it does and how to run it: README.md. Current state and what to do next:
docs/handoff.md. Read both before starting.

## Guardrails

- The GitHub repo is public. `.env` (Discord token), `bot.db`, and `seed/participants.csv` (the
  friends' real teams) are git-ignored and stay that way. Example and test data use made-up teams
  and names.
- The owner reviews every change and commits it themselves: leave your work uncommitted and
  unpushed.
- Read `.env` by key name only (`grep -oE "^KEY="`); the token value stays unread.
- Test against a copy of the database: `cp bot.db /tmp/copy.db`, then
  `DB_PATH=/tmp/copy.db uv run --env-file .env fantasy-bot sync`. Starting the `bot` job uses the
  real token and changes the friends' Discord server, so ask the owner first.
- Big changes start as a plan in `docs/plans/` that the owner agrees to.

## Done means

All four pass: `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy`,
`uv run pytest -q`. README.md and the plan's Status line describe the code as it now is.

## Layout

Folders by layer; README.md → Layout has the map and reading order. `tests/test_layering.py`
enforces who may import whom, so a failing layering test means the code is in the wrong folder.
`tests/` mirrors `src/`.

## Conventions

- **Units are integers.** Points are tenths (nbafantasy's unit: 905.5 pts = 9055). Money is
  minor units (cents: 100.00 = 10000). Prize shares use positive integer weights from
  `seed/prizes.json`, selected by effective gameweek. Payouts are
  computed exactly with `Fraction`, then rounded to whole cents by largest remainder, so they always
  add up to the pool. Format only at the edge, in `controllers/formatting.py`.
- **Money is computed, never stored.** Every call recomputes the pools from the synced points
  (`v_gameweek_pool`). A gameweek counts once nbafantasy marks all its days `data_checked`.
- **Prize rules:** require one positive weight per eligible participant. Add later-gameweek rules
  when the split or participant count changes; never silently truncate or extrapolate prizes.
- **The buy-in is fixed per season.** It is saved when the season row is created; changing it
  would rewrite past weeks. A new buy-in needs a new `SEASON_ID`.
- **Schema:** the SQL files in `database/migrations/` are the source of truth (STRICT tables,
  CHECKs, views; no Alembic). To change it, add the next `NNN_name.sql` and update
  `database/tables.py` to match; `tests/database/test_tables.py` compares the two.
- **SQLAlchemy:** one short session per command or sync. Repositories only read and write; the
  service or job that owns the work commits. (The one exception: `start_sync_run` /
  `finish_sync_run` commit, so a failed sync is still recorded.) The mappings have no
  `relationship()`, so tests that add ORM objects across tables flush parents first.
- **Participants:** `seed/participants.csv` is the source of truth, applied on every sync. A
  missing file or any bad row changes nothing, so a typo never silently drops a friend.
- **Style:** plain, explicit names (the owner dislikes architecture jargon); one implementation
  means no interface; comments say why. Match the surrounding code. Line length 100.
