# mtg-league-leaderboard-bot

Discord bot for MegaGame Latvia that ingests MTG tournament results and posts a
monthly leaderboard. Runs as two GitHub Actions cron jobs.

## How it works

- **Daily `ingest`** polls the results channel (Discord REST), parses messages
  containing round-by-round Swiss pairings, and stores per-player round records
  in Supabase (deduplicated by Discord message ID; tournament date taken from the
  message timestamp).
- **Weekly `leaderboard`** sums points per attendee for the current calendar
  month and posts a rich embed to the leaderboard channel.

## Setup

### 1. Discord bot
1. Create an application + bot at the Discord Developer Portal.
2. Enable the **Message Content Intent** (Bot -> Privileged Gateway Intents).
3. Invite the bot to the server with read access to the results channel and
   send access to the leaderboard channel.
4. Copy the bot token and the two channel IDs.

### 2. Supabase
1. Create a Supabase project.
2. Run `supabase/schema.sql` in the SQL editor.
3. Copy the project URL and the service-role key.

### 3. GitHub secrets
Add these repository secrets (Settings -> Secrets -> Actions):
`DISCORD_BOT_TOKEN`, `RESULTS_CHANNEL_ID`, `LEADERBOARD_CHANNEL_ID`,
`SUPABASE_URL`, `SUPABASE_KEY`, `TIMEZONE`.

## Local development

```bash
python -m venv .venv && . .venv/Scripts/activate
pip install -e ".[dev]"
pytest -q
```

Copy `.env.example` to `.env` and fill it in to run locally:

```bash
python -m bot ingest
python -m bot leaderboard
```

## Manual verification

Both workflows support `workflow_dispatch` -- trigger them from the Actions tab
to run a real ingest or leaderboard post on demand.
