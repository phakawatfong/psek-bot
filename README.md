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

The bot creates `bot.db` on first start. Type `/money` in your server to check it responds.

## Layout

Imports only point down this list. Services never import `discord`, so the same data can feed
a reply, a chart, or a scheduled post.

```
src/fantasy_bot/
  main.py          start-up: load settings, migrate the database, start the bot
  config/          Settings read from the environment
  bot/             Discord: client, and one module per slash command in commands/
  services/        one job each, e.g. money.get_money_summary; returns plain data
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
