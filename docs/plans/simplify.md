# Plan: simplify the bot to four commands, a participants file, and feature folders

Status: done; fixed prizes and season-only summaries superseded by configurable-prizes.md.
Steps 1-5 (deleted what's going away; seed/participants.csv; feature folders;
SQLAlchemy; fixed 50/30/15/5 prizes; pool command, money by gameweek, chart by gameweek). The
feature folders of section 3 were then replaced by folders by layer: see layer-folders.md. Decisions are recorded at the end. Step 2
moved the file into a `seed/` folder (see README: Docker mounts the folder so editors that
replace files on save still work). Step 3 added a small `shared/` package for the types and
reply helpers every feature uses. Step 3b kept the SQL migrations as the schema's source of
truth (not Alembic) and checks the SQLAlchemy mappings against them in
tests/database/test_tables.py. Step 4 dropped the per-season payout_rank table (migration 006).

## Why

The bot has grown to 14 slash commands, 44 source files (~3,400 lines), one shared `models.py`
for everything, and registration logic (register, claim, approve, add, edit, remove, reset) that
is more machinery than a group of friends needs. It is hard to know where to start, as a user or
as a maintainer.

The goal is less: four commands everyone understands, participants kept in one file, and code
organised so each command can be read on its own.

## 1. Four commands

Every command starts with `/psek-nba-`. Nothing else is registered with Discord.

| Command | Shows |
|---|---|
| `/psek-nba-standings` | Every team, 1st to last, by season points |
| `/psek-nba-money` | Each person's money: running total, and win/loss per gameweek |
| `/psek-nba-chart [by]` | Points over time: per day (line, default) or per gameweek (bars) |
| `/psek-nba-pool [gameweek]` | One gameweek's pool: what each person put in, the total, and who won what (default: the latest) |

Sketch of the replies (team names shortened):

```
/psek-nba-standings
Season standings
1. 🏆 jkslots (pisit manoo)        476.0
2.    GO-GO Team (settakarn)        450.0
3.    Dream team (Nuttasit)         393.0
4. 🐢 kidsgodspeed (Phakawat)       362.0

/psek-nba-money
Money after 2 final gameweeks (buy-in 100 a week)
              GW1     GW2    Total
jkslots      +100     -95       +5
GO-GO         +20    +100     +120
Dream         -40     -20      -60
kidsgod       -80      +15     -65
GW3 is in progress: /psek-nba-pool shows it so far.

/psek-nba-pool gameweek:2
Gameweek 2 pool: 400.00 (4 × 100.00), final
Put in: jkslots 100, GO-GO 100, Dream 100, kidsgod 100
1st GO-GO Team      200.00 (50%)
2nd jkslots         120.00 (30%)
3rd kidsgodspeed     60.00 (15%)
4th Dream team       20.00 (5%)
```

Removed commands and what replaces them:

| Removed | Replaced by |
|---|---|
| `points` (per-day table) | `chart` |
| `schedule` (+ team logo emojis) | nothing; not part of the goal |
| `participants` | the participants file (section 2) |
| `rules` | the prize table in this doc, the README, and `money/prizes.py` |
| `register`, `add`, `approve`, `edit`, `remove`, `reset` | the participants file |
| `paid` (real-payment ledger, "owes / is owed") | nothing; settle up outside the bot |

## 2. Participants: one file, not commands

Participants are declared in `participants.csv`, which the bot reads on every sync. The file is
the source of truth: add a row to add someone, change a row to fix a mistake, delete a row to
remove someone.

```csv
entry_id,from_gameweek,name
31818,1,pisit
40823,1,settakarn
40791,1,nuttasit
40334,1,phakawat
```

- `entry_id`: the nbafantasy team id (from the team's URL). Must be a team in the league;
  rows that aren't are logged and skipped.
- `from_gameweek`: the first gameweek the person pays into and plays for.
- `name`: optional, only to make the file readable; replies use the nbafantasy team name.
- No Discord ids: nothing in the four commands needs them.

Where it lives: next to `.env` on the server, mounted read-only into the container. It is
git-ignored (`participants.example.csv` is committed), because the repo is public.

Adding someone: edit the file, then either wait for the next sync (≤ 10 minutes) or run
`docker compose run --rm bot sync`.

### Why a file and not an HTTP API endpoint

An API endpoint means opening a port on the server, adding authentication, and TLS. That is new
attack surface on a server that today accepts nothing but SSH, for something done a few times a
season. Editing a file over SSH gives the same "add a row" result with none of it. If an API is
wanted later (e.g. for a web page), it can be added on top of the same participants service.

## 3. Code organised by feature (replaced by layer-folders.md)

Each command gets its own folder with the same four parts, so "where do I start" always has the
same answer: open the folder named after the command.

```
src/fantasy_bot/
  main.py                    start-up: settings, database, sync loop, Discord bot
  config.py                  .env settings
  discord_bot.py             Discord client: registers the four controllers below
  standings/
    controller.py            the /psek-nba-standings command: calls the service, formats the reply
    service.py               get_standings(): the job, returns models
    repository.py            SQL for this feature only
    models.py                this feature's data contract (e.g. StandingRow)
  money/
    controller.py  service.py  repository.py  models.py
    prizes.py                the prize rules (section 4), pure functions
  chart/
    controller.py  service.py  repository.py  models.py
    drawing.py               the PNG
  pool/
    controller.py  service.py  repository.py  models.py
  participants/
    service.py               read participants.csv, validate, write to the database
    models.py
  nbafantasy/                data from nbafantasy, shared by every feature
    client.py  contracts.py  sync.py  repository.py
  database/
    connection.py  migrations/
```

Rules, enforced by `tests/test_layering.py`:

- Inside a feature: `controller → service → repository`, each using that feature's `models.py`.
- Only controllers import `discord`.
- Features never import each other. Shared needs go through `nbafantasy/` or `database/`.
- `pool` and `money` both need the prize rules: `pool` imports `money.prizes`, the one allowed
  cross-feature import, because there must be exactly one implementation of the payout.

## 4. Prize rules (final)

| Place | Share of the weekly pool |
|---|---|
| 1st | 50% |
| 2nd | 30% |
| 3rd | 15% |
| 4th | 5% |
| 5th and below | nothing |

- Weekly pool = buy-in × the number of people in it that gameweek.
- Ranking = that gameweek's points, after transfer costs.
- Ties: tied teams average the prizes of the places they cover. Two tied for 2nd each get
  (30% + 15%) / 2 = 22.5%. Two tied for 4th share 4th's 5% and 5th's 0%: 2.5% each.
- Fewer than 4 people: the prizes in use are scaled up so the whole pool is still paid. Three
  people get 50/30/15 scaled to 100%: 52.6%, 31.6%, 15.8%.
- Rounding: whole cents; leftover cents go to the largest remainders, so payouts always add up to
  the pool exactly.
- The split is fixed in code (`money/prizes.py`), not configurable. The buy-in stays in `.env` as
  `WEEKLY_BUY_IN`.

## What gets deleted

- 11 commands and their code: points, schedule, participants, rules, register, add, approve,
  edit, remove, reset, paid.
- Real-payment tracking: the `ledger` table, `/psek-nba-paid`, and the "owes / is owed" balance.
- Team logo emojis and the ESPN logo client.
- Registration logic: claiming, pending/approved status, placeholder Discord ids, the team
  search dropdowns.
- `PAYOUT_SPLIT`, the season rules table, and the `.env` drift warning for the split.
- Estimated: roughly a third of the source and tests.

The sync, the database, migrations, Docker, the setup script, and backups stay as they are.

## Order of work

Each step ends with the tests green and the bot runnable, so it can stop after any step.

1. **Delete what's going away** (subtract first, so later steps move less code).
2. **Participants file** replaces registration; migration from today's `participant` table.
3. **Restructure into feature folders** with per-feature models; behaviour unchanged.
4. **New prize rules** in `money/prizes.py`.
5. **New `money` (by gameweek) and `pool` views**, and `chart by:gameweek`.

Step 3b, added after step 3 started: **every database access through SQLAlchemy**, replacing
the raw SQL in each feature's `repository.py`. Done as its own step so the move (step 3) and the
rewrite are each checked on their own.

## Data migration

- The server's current `participant` rows (from `/psek-nba-add`) are replaced by whatever
  `participants.csv` says on the first sync after the change.
- Points data is kept; nothing is re-downloaded.
- The `ledger` table is dropped by a migration. It only ever held test payments.

## Decisions

1. **The 5% goes to 4th place.** With 5 or more people, 5th and below win nothing.
   With fewer than 4 people the used prizes scale up to fill the pool (today's rule).
2. **`/psek-nba-pool` shows buy-ins**: what each person put into that gameweek's pool, the
   total, and who won what. All computed; nothing is entered by hand.
3. **Real-payment tracking is dropped.** The bot shows what everyone won or lost; settling up
   happens outside the bot.
4. **Participants come from `participants.csv`.** No HTTP API endpoint.
