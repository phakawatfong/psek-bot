# Plan: restore NBA team logo emojis

Status: done. Schedule replies use application emojis with team-code fallback. All four checks
pass (133 tests); read-only downloads verified all 30 NBA team logos. No bot startup or live
Discord upload was performed; changes are uncommitted for owner review.

## Behaviour

Show an NBA team logo beside each team abbreviation in schedule replies. Keep the text
abbreviation so a missing emoji still leaves a readable matchup. These are NBA teams, not the
friends' fantasy teams.

Restore the earlier application-emoji approach: the emojis belong to the Discord application.
Find existing `nba_<TEAM>` emojis by name and reuse them. Download and upload only missing logos;
never delete or replace existing emojis automatically. The old implementation used ESPN's PNG
image CDN; verify the URLs and team-code mapping before restoring that client.

Load the emoji mapping during bot startup, with a 60-second total limit, five-second logo
downloads/uploads, and per-team failure handling.
Logo or upload failures must not stop command registration or the normal data sync. A later
restart retries missing logos; no additional recurring job. Use the public NBA Fantasy team
list so setup does not depend on participants or a previously synced database.

## Implementation

- Keep Discord emoji operations in `controllers/team_emojis.py`.
- Use `services/team_logos.py` to select missing NBA team logos and `clients/team_logos.py`
  for downloads. Avoid a service that only forwards a single client call.
- Wire the mapping through `discord_bot.py` and `controllers/routes.py` to the schedule
  controller. Preserve the other controllers' signatures; no new generic controller interface.
- Extend schedule formatting to show known emoji markup beside team codes and to keep all
  messages within Discord's length limit, including the extra emoji markup.
- Validate downloaded PNG signatures and sizes; bound download time and response size.
- Keep emoji IDs in memory; retrieve them from Discord on restart. No database migration,
  hard-coded emoji IDs, new slash command, or server-specific emoji management.

## Verification and release

Use mocked Discord calls and synthetic images to verify reuse, missing-only uploads, safe
failure, text fallback, team-code mapping, and long schedule replies. Run all four required
checks. Update README and handoff, and mark this plan done when implementation is complete.

Implement and test locally without connecting the bot. Starting the bot will create missing
application emojis and publish commands; ask the owner before a live run, per AGENTS.md.
