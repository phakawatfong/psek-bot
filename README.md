# fantasy-bot

Discord bot that summarizes an [NBA Fantasy](https://nbafantasy.nba.com) league and settles the friends' betting pool.

## Run it locally

1. Create the Discord bot (once).
   - Go to https://discord.com/developers/applications and click **New Application**.
   - **Bot** tab: click **Reset Token** and copy the token. No privileged intents are needed.
   - **OAuth2 → URL Generator**: tick scopes `bot` and `applications.commands`, then the bot permission
     `Send Messages`. Open the generated URL and add the bot to a test server.
2. Get the IDs.
   - Server ID: in Discord, turn on **Settings → Advanced → Developer Mode**, then right-click your
     server and choose **Copy Server ID**.
   - League ID: the number in your league's URL on nbafantasy.nba.com.
3. Configure and start.

   ```bash
   cp .env.example .env    # then fill in DISCORD_TOKEN, DISCORD_GUILD_ID, LEAGUE_ID
   uv run --env-file .env fantasy-bot
   ```

The bot creates `bot.db` on first start. Type `/psek-nba-money` in your server to check it responds.

## Sync nbafantasy data

The bot syncs every 10 minutes on its own. To sync once by hand and exit:

```bash
uv run --env-file .env fantasy-bot sync
```

A sync stores games and per-player stats for every day that has started, and picks for every
registered participant. Days nbafantasy marks final are never fetched again, except to backfill a
participant who registered later. Each sync rebuilds every team's day total from picks × player
stats and logs a warning if it differs from nbafantasy's official total.

## Run with Docker

```bash
docker compose up -d --build          # start the bot, restarting it if it crashes
docker compose run --rm bot sync      # one sync, same database
docker compose logs -f bot
```

The database lives in the `bot-data` volume at `/data/bot.db`, so it survives rebuilds.

## Deploy to AWS Lightsail

One small Ubuntu server running the container. The bot only makes outgoing connections, so the
server needs no open ports except SSH.

1. **In AWS** (once): set a Budget alert (e.g. $10/month). Create a Lightsail instance:
   Linux/Unix, **Ubuntu 24.04**, the smallest plan **with IPv4**, region Singapore. Paste
   `deploy/setup.sh` into **Add launch script**, turn on **automatic snapshots**, and attach a
   static IP. In the instance's Networking tab keep only SSH (22), ideally limited to your IP.
2. **Wait** a few minutes for the launch script; it logs to `/var/log/cloud-init-output.log`.
   It installs everything it needs (git, curl, cron, Docker), so a bare image is fine, but it
   only supports Ubuntu and Debian: on Amazon Linux it stops with a message saying so.
   (Without a launch script, SSH in and run `curl -fsSL
   https://raw.githubusercontent.com/phakawatfong/psek-bot/main/deploy/setup.sh | sudo bash`.)
3. **Copy secrets and start**, from your computer:

   ```bash
   scp .env ubuntu@<server-ip>:/opt/psek-bot/.env
   ssh ubuntu@<server-ip> 'chmod 600 /opt/psek-bot/.env && cd /opt/psek-bot && docker compose up -d --build'
   ```

4. **Say who's in the pool**: create `seed/participants.csv` on the server (see
   [Participants](#participants)). Until it exists the pool stays as it is, and the bot logs a
   warning on every sync.

Stop any bot you run locally first: two processes with the same token both answer commands.

**Update** to the latest code: `ssh ubuntu@<server-ip> 'cd /opt/psek-bot && git pull && docker
compose up -d --build'`. Run git as `ubuntu`, not with `sudo`: the repo belongs to `ubuntu`, and
git refuses to work in it as root. **Logs**: `docker compose logs -f bot` (capped at 30MB).

**Backups**: Lightsail snapshots the whole server daily. Separately, cron runs `fantasy-bot
backup` at 03:00 UTC, writing `/data/backups/bot-YYYY-MM-DD.db` in the volume and keeping 14
days. To restore one: `docker compose stop bot`, copy the chosen backup over `/data/bot.db`
(`docker compose run --rm --entrypoint cp bot /data/backups/bot-2026-10-25.db /data/bot.db`),
then `docker compose start bot`.

## Commands

Every command is listed in one routes table, `src/fantasy_bot/controllers/routes.py`, and every
name starts with `psek-nba-`.

| Command | Shows |
|---|---|
| `/psek-nba-standings` | Every team, 1st to last, by season points, with the gap to the leader |
| `/psek-nba-money` | Each person's win or loss in every final gameweek, and the season total |
| `/psek-nba-pool [gameweek]` | One gameweek's pool: what each person put in, their points, and what they win (default: the latest gameweek, even if it isn't final yet) |
| `/psek-nba-chart [by]` | A picture: `day` (default) is every team's season total after each day; `gameweek` is each team's points in every gameweek, as bars |

## Participants

Who is in the pool is one file: `seed/participants.csv`. Every sync (every 10 minutes, and when the
bot starts) makes the pool match it exactly.

```csv
entry_id,from_gameweek,name
31818,1,pisit
40823,2,settakarn
```

- `entry_id`: the number in the team's nbafantasy URL, e.g. `nbafantasy.nba.com/entry/31818`.
- `from_gameweek`: the first gameweek they pay into and play for.
- `name`: optional, only to make the file readable.
- Lines starting with `#` and blank lines are ignored.

| To | Do |
|---|---|
| Add someone | Add a row |
| Fix someone's start week | Change their `from_gameweek` |
| Remove someone | Delete their row |
| Apply it now instead of within 10 minutes | `docker compose run --rm bot sync` (or `uv run --env-file .env fantasy-bot sync` locally) |
| Create the file from who's in the pool today | `docker compose run --rm bot export-participants > seed/participants.csv` |

Two safety rules: a **missing file** changes nothing, and **any bad row** (a typo, a duplicate, a
team not in the league) means nothing changes. Either way the sync log says why, with line
numbers. Moving a start week or removing someone changes the pools of the weeks it covered,
including finished ones, because money is recomputed from points.

The file is git-ignored because the repo is public; `seed/participants.example.csv` shows the
format. Docker mounts the whole `seed/` folder read-only, so any editor's save is seen.

## Weekly pool

`WEEKLY_BUY_IN` in `.env` (default `100`) is what each person pays into each gameweek's pool, from
the week they joined. Each week's pool is split by that week's points, net of transfer costs:

| Place | Share of the pool |
|---|---|
| 1st | 50% |
| 2nd | 30% |
| 3rd | 15% |
| 4th | 5% |
| 5th and below | nothing |

- **Ties** average the prizes of the places they cover: two tied for 2nd each get
  (30% + 15%) / 2 = 22.5%; two tied for 4th share its 5%.
- **Fewer than 4 people**: the prizes in use scale up so the whole pool is paid; three people
  get 52.6%, 31.6%, 15.8%.
- **Rounding**: whole cents; leftover cents go to the largest remainders, so payouts always add
  up to the pool exactly.

The split is the same every season and lives in one place, `PRIZES` in `services/prizes.py`, whose
`settle()` docstring walks through these steps. Nothing is stored: every `/psek-nba-money`
recomputes the weeks from the synced points, so a week counts toward the season once nbafantasy
marks all its days final. The buy-in is saved when the season is created and never changes after
that, because changing it would rewrite every past week. If `.env` later says something
different, the bot logs a warning naming both values and keeps the season's.

## Layout

Folders by layer. To follow how a command works, read in this order: `main.py`, then
`controllers/routes.py` (every command), then that command's controller, its service, and the
repositories it uses.

```
src/fantasy_bot/
  main.py           1. load the config  2. build the database and season  3. run the job
  discord_bot.py    the Discord client: registers the routes, runs the sync loop
  config/           .env, one small typed config each for discord, database, league
  contracts/        nbafantasy's JSON payloads, as pydantic models (what we receive)
  models/           our own data, one file per area (what we work with)
  controllers/      one file per slash command: call a service, format the reply
  services/         one job each: standings, money, pool, chart, participants, sync;
                    prizes.py is the 50/30/15/5 split, chart_drawing.py the PNGs
  repositories/     SQL, one file per kind of data: points, participants, season, nbafantasy
  clients/          HTTP calls to nbafantasy
  database/         SQLAlchemy engine and sessions, table mappings, migrations
```

Each folder imports only the ones below it: controllers → services → repositories → database,
services → clients → contracts, and everything may use models. Only controllers import
`discord`, and only `services/chart_drawing.py` imports matplotlib. `tests/test_layering.py`
fails the build if any of this drifts. `tests/` mirrors `src/`.

All database access goes through SQLAlchemy: queries are `select()`/`insert()` statements on the
mappings in `database/tables.py`, and each command or sync uses its own short session. The
schema itself is the SQL in `database/migrations/` (STRICT tables, CHECKs, views);
`tests/database/test_tables.py` fails if the mappings and the migrations disagree. To change the
schema, add a migration file and update `tables.py` to match.

## Develop

```bash
uv run pytest -q
uv run ruff check . && uv run ruff format --check . && uv run mypy
```
