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

4. **Optional: bring your local data** (registered participants) instead of starting empty:

   ```bash
   scp bot.db ubuntu@<server-ip>:/tmp/bot.db
   ssh ubuntu@<server-ip> 'cd /opt/psek-bot && docker compose stop bot && docker compose cp /tmp/bot.db bot:/data/bot.db && docker compose start bot'
   ```

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

Every command is listed in one routes table in `src/fantasy_bot/bot/commands/__init__.py`, and
every name starts with `psek-nba-`.

| Command | Shows |
|---|---|
| `/psek-nba-standings [gameweek]` | Teams ranked by season points (or one gameweek), with the gap to the leader |
| `/psek-nba-points [gameweek] [day]` | Each team's points on the latest day, one day of a gameweek (`day:1` = its first day), or every played day of a gameweek, with season totals, marked live or final |
| `/psek-nba-chart` | A picture of every team's season points growing day by day, with gameweek boundaries |
| `/psek-nba-schedule [gameweek] [day]` | NBA games for the upcoming day (the first not yet finished), a whole gameweek, or one day of it (`day:1` = its first day), with team logos and dates and times in UTC+7 |
| `/psek-nba-participants` | Every team in the league: in the pool, waiting for approval, or not registered yet, with who registered each |
| `/psek-nba-rules` | The season's prize pool rules in plain words: buy-in, split, ties, rounding, when a week counts |
| `/psek-nba-money [gameweek]` | Season money over every final week plus the current week so far, or one week's pool |
| `/psek-nba-register team` | Join the pool: start typing your nbafantasy team and pick it |
| `/psek-nba-add team [member] [from_gameweek]` | Admin: put a friend's team straight into the pool, linked to their Discord account if given |
| `/psek-nba-approve team [from_gameweek]` | Admin: let a registered team into the pool, optionally from an earlier gameweek |
| `/psek-nba-paid team amount [direction] [note]` | Admin: record real money paid into (`in`) or out of (`out`) the pot |
| `/psek-nba-edit team [from_gameweek] [member]` | Admin: change a registered team's start week or linked Discord account |
| `/psek-nba-remove team` | Admin: take a team out of the pool with its payment records; the reply says how to undo it |
| `/psek-nba-reset` | Admin: remove every team and payment record this season, after a confirm button |

## Team logos

On first start (or right after the first sync, once teams are known) the bot uploads the 30 NBA
team logos as its own application emojis, named `nba_ATL`, `nba_BOS`, and so on. They belong to
the bot, so they work in every server without any server permission, and later starts reuse
them. You can see or delete them in the Developer Portal under your application's **Emojis**
tab. Logos come from ESPN's public image CDN; if one can't be fetched, that team shows its code.

## Registering friends

1. Each friend runs `/psek-nba-register` and picks their team from the dropdown, which lists every
   team in the league (refreshed each sync). It records their Discord account and marks them
   pending, starting from the next gameweek, or the current one if it hasn't started.
2. An admin runs `/psek-nba-approve`. Use `from_gameweek:1` to backdate friends who were in from
   the start.
3. Or an admin adds teams for everyone with `/psek-nba-add`, which puts a team straight into the
   pool. Pick the friend as `member` to link their Discord account now; leave it empty and the
   team gets a placeholder id they can claim later.
4. A team entered by hand with a placeholder Discord id is claimed by the first friend who
   registers it: only its Discord id changes, its approval and start week stay. A team already
   linked to a real account can't be taken by someone else.

Record real money with `/psek-nba-paid` as it moves. `/psek-nba-money` then shows, for each
person, whether they owe the pot, are owed by it, or are settled: their season net, plus what
they paid in, minus what they were paid out.

## Fixing mistakes

| Mistake | Fix |
|---|---|
| Wrong start week | `/psek-nba-edit team:… from_gameweek:N` |
| Team linked to the wrong person | `/psek-nba-edit team:… member:@right-person` |
| Team added by mistake | `/psek-nba-remove team:…`; its reply gives the exact command to undo it |
| Everything is a mess | `/psek-nba-reset`, then add everyone again; it asks for confirmation first |

These only change registrations and payment records: points synced from nbafantasy, the prize
rules, and other seasons are never touched. Because money is recomputed from points on every
call, moving a start week or removing a team changes the pools of the weeks it covered, including
finished ones; the replies name those weeks. The nightly backups in `/data/backups` are the last
resort.

## Who is an admin

Discord decides, not the bot: it checks before a command ever reaches the bot. By default
`/psek-nba-approve` and `/psek-nba-paid` work only for the server owner and members of a role with
the **Manage Server** permission, and everyone else doesn't even see them.

To see who that is: **Server Settings > Roles**, open each role, and look for Manage Server.

To make someone an admin of the pool without giving them Manage Server (which also lets them
change the whole server): **Server Settings > Integrations >** the bot **>** `/psek-nba-approve`
(and again for `/psek-nba-paid`) **> Add Roles or Members**, and allow a role such as "Pool admin"
or the people themselves. Discord applies these overrides, so nothing in the bot changes.

## Weekly pool

Two settings in `.env` define the money, both in plain units:

| Setting | Default | Meaning |
|---|---|---|
| `WEEKLY_BUY_IN` | `100` | What each person pays into each gameweek's pool, from the week they joined |
| `PAYOUT_SPLIT` | `50,30,20` | Percent of the weekly pool for 1st, 2nd, 3rd, and so on; must add up to 100 |

Each week's pool is split by that week's points, net of transfer costs. `/psek-nba-rules` states
every rule with this season's numbers, and the steps are in `calculations/payout.py: settle()`. Nothing is stored: every
`/psek-nba-money` recomputes the weeks from the synced points. A week counts toward the season
once nbafantasy marks all its days final. The buy-in and split are saved when the season is
created and never change after that, because changing them would rewrite every past week. If
`.env` later says something different, the bot logs a warning naming both values and keeps the
season's; use a new `SEASON_ID` to start a season with new rules.

## Layout

Imports only point down this list. Services never import `discord`, so the same data can feed
a reply, a chart, or a scheduled post.

```
src/fantasy_bot/
  main.py          start-up: load settings, migrate the database, start the bot
  config/          Settings read from the environment
  bot/             Discord: client, routes table and one handler module per command in commands/
  services/        one job each, e.g. money.get_money_summary; returns plain data
  clients/         outside APIs (nbafantasy); fetch + parse JSON into models
  repositories/    SQL only, plus migrations/
  calculations/    pure rules, e.g. payout.settle
  models.py        dataclasses shared by every layer
```

`tests/` mirrors this layout.

## Develop

```bash
uv run pytest -q
uv run ruff check . && uv run ruff format --check . && uv run mypy
```
