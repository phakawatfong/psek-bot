# Plan: schedule by gameweek and day

Status: done. Fifth command registered with fantasy day defaults and on-demand API fetching.
All four required checks pass (111 tests). Read-only API verification returned all seven days
and 49 games for GW2; no live Discord connection or database writes were performed.

## Command

`/psek-nba-schedule [gameweek] [day]`

| Options | Selection |
|---|---|
| Both | That day within that gameweek |
| Day only | That day within the current gameweek |
| Neither | Current gameweek and current fantasy day |
| Gameweek only | All days in that gameweek |

Day means the day number within a gameweek (for example GW2 Day1), not the season-wide event
id. Use bootstrap phase start/stop events to map between them; weeks can have different lengths.
Reject a day outside its selected week's range with a helpful message.

## Current day and output

The current day is the fantasy day whose deadline has passed most recently, until the next
day's deadline. Before the first deadline, select the first day and label it upcoming. After
the last day is finished, say the season has ended for default selections; explicit selections
still work. Use timezone-aware timestamps. The owner confirmed fantasy days, which are not
necessarily the same as today's Bangkok calendar date.

Show the gameweek and day, Bangkok date and tip-off time, away team versus home team, and
completed status/scores where available. Show all games on the selected day, including games
already completed, so the schedule does not disappear during the day. Do not infer live status
solely from the scheduled tip-off. Show a clear message for an empty day or unavailable data.

## Smallest implementation

The existing sync stores all day metadata but fetches fixtures only for started days
(`services/sync.py: _started`). It cannot currently answer future-day requests from SQLite.

Fetch bootstrap and the selected day's fixtures on demand through the existing
nbafantasy client. A whole-week request fetches each selected day sequentially using the
client's existing pacing. This is a deliberate exception to other commands reading stored
data: it avoids adding season-wide future fixture fetching to every ten-minute sync.

- Add `services/schedule.py` to resolve the selection and fetch fixtures and team names.
- Add a small `models/schedule.py` result and `controllers/schedule.py` for formatting and reply.
- Register the fifth command in `controllers/routes.py`; preserve the existing folder rules.
- Defer the Discord reply before network requests; handle unavailable API data clearly and
  split long whole-week replies to fit Discord's message limit.
- Reuse the existing client and payload contracts. Schedule parsers map phase event ranges to
  day numbers and allow a missing kickoff time; the stored-fixture parser still rejects it.
  Verified actual bootstrap/future fixtures, and tested the time-TBD case with synthetic data.
- No new scheduler, database writes, schema migration, logos or additional external API.

## Validation and documentation

Test all four option combinations, day numbering across week boundaries, varying week lengths,
deadline boundaries, before/after season, empty days, API errors, Bangkok time conversion and
long replies. Use made-up data. Verify command registration and all four required checks.

Update README's commands, layout and data-flow explanation to include the on-demand schedule
command. Mark this plan done and update the handoff after implementation and checks pass.

The existing season's buy-in of 100 remains a separate unresolved decision; this feature does
not change any buy-in or historical pool calculation.
