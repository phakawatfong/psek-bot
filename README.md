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
compose up -d --build'`. **Logs**: `docker compose logs -f bot` (capped at 30MB).

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
| `/psek-nba-participants` | Registered teams, entry ids, the gameweek each joined, and who is still pending |
| `/psek-nba-money [gameweek]` | Season money over every final week plus the current week so far, or one week's pool |

## Team logos

On first start (or right after the first sync, once teams are known) the bot uploads the 30 NBA
team logos as its own application emojis, named `nba_ATL`, `nba_BOS`, and so on. They belong to
the bot, so they work in every server without any server permission, and later starts reuse
them. You can see or delete them in the Developer Portal under your application's **Emojis**
tab. Logos come from ESPN's public image CDN; if one can't be fetched, that team shows its code.

## Weekly pool

Everyone pays `WEEKLY_BUY_IN` (default 100) each gameweek from the week they joined. Each week's
pool is split 50/30/20 by that week's points, net of transfer costs. Nothing is stored: every
`/psek-nba-money` recomputes the weeks from the synced points. A week counts toward the season
once nbafantasy marks all its days final. The buy-in and split are saved when the season is
created and never change after that, because changing them would rewrite every past week.

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
