# Plan: folders by layer, and a main.py that reads top to bottom

Status: done, together with simplify.md step 5. Shared SQL expressions now live in
repositories/queries.py. README's Program flow diagrams and main.py document startup and command handling
separately; the existing layout is retained after discussing MVC. Replaces section 3 ("Code organised by
feature") of simplify.md; the rest of that plan stands.

## Why

The feature folders (standings/, money/, chart/, …) made each command self-contained, but there
was no obvious place to start reading, and the wiring was spread out: `main.py` mixed argument
parsing, config, migrations and four jobs, and the Discord client built its own dependencies.
Three commands each had their own repository querying the same points tables.

With four commands and about 2,300 lines, folders by layer give one reading order:
`main.py` → `controllers/` (what the bot can do) → `services/` (how) → `repositories/` (data).

## Layout

```
src/fantasy_bot/
  main.py              1. load config  2. load dependencies  3. run the job
  dependencies.py      step 2: database, sessions, season row
  jobs.py              step 3: bot | sync | backup | export-participants
  discord_bot.py       the Discord client: registers the routes, runs the sync loop
  config/              .env, read once at start-up, one small typed config per concern
    discord.py         token, guild id
    database.py        db path
    league.py          league id, season id, weekly buy-in, participants file, sync interval
    env.py             ConfigError and the parsing helpers the three share
  contracts/
    nbafantasy.py      pydantic models of nbafantasy's JSON payloads (what we receive)
  models/              our own data, one file per area (what we work with)
    participant.py  standings.py  money.py  pool.py  chart.py  nbafantasy.py
  controllers/         one slash command per file: call one service, format the reply
    routes.py          the table of every command: name, description, controller
    standings.py  money.py  pool.py  chart.py
    formatting.py      reply helpers the controllers share (names, points, money)
  services/            one job each; combine repositories (and the client) to do it
    standings.py  money.py  pool.py  chart.py  participants.py  sync.py
    prizes.py          the 50/30/15/5 split, pure functions; used by money and pool
    chart_drawing.py   the PNGs
  repositories/        SQL, one file per kind of data, shared by any service that needs it
    points.py          season table, points per day, points per gameweek and pool
    participants.py    who is in the pool, and their names
    season.py          the season row and its weekly buy-in
    nbafantasy.py      the sync's writes
    queries.py         SQL expressions repositories share (naming a participant)
  clients/
    nbafantasy.py      HTTP calls to nbafantasy, parsing payloads into models
  database/
    connection.py      engine, sessions, migrations, backups
    tables.py          SQLAlchemy mappings of the tables and views
    migrations/        the schema, as SQL files
```

`main.py`:

```python
def main():
    job = parse_job()
    config = load_config()  # 1. .env -> typed configs
    dependencies = load_dependencies(config)  # 2. database, sessions, season row
    JOBS[job](dependencies)  # 3. bot | sync | backup | export-participants
```

`load_dependencies()` is a plain function returning a small dataclass. No dependency-injection framework.

## Rules, enforced by tests/test_layering.py

Each folder may import only the folders below it:

| Folder | May import |
|---|---|
| `controllers/` | services, models |
| `services/` | repositories, clients, models |
| `repositories/` | database, models |
| `clients/` | contracts, models |
| `models/`, `contracts/`, `config/`, `database/` | nothing of ours |

- Only `controllers/` and `discord_bot.py` import discord.
- Only `services/chart_drawing.py` imports matplotlib.
- `main.py` and `discord_bot.py` wire everything, so they may import anything.

## Other changes in the same move

- `PoolRules` (a wrapper around one number) becomes a plain `weekly_buy_in_minor: int`.
- `shared/` goes away: names and ids move to `models/participant.py`, reply helpers to
  `controllers/formatting.py`.
- Tests mirror the new folders (`tests/services/test_money.py`, …).

## Order of work

1. Move files and rewrite imports; behaviour unchanged, tests green.
2. Merge the per-command repositories into `repositories/points.py` and `participants.py`.
3. Split config, and rewrite `main.py` as config → dependencies → job.
4. Then simplify.md step 5 (`/psek-nba-pool`, money by gameweek, `chart by:gameweek`).
