# Plan: configurable weekly prizes and summaries

Status: done. Effective-gameweek weights, GW2 participation and current-gameweek defaults are
implemented. All four required checks pass (180 tests). The owner will add the two missing
participants and apply the files on Lightsail. Changes are uncommitted; no live bot was started.

## Rules agreed

- Six participants pay 50 each: a pool of 300 pays 120/70/50/30/20/10 before ties.
- These are relative weights, converted to exact Fraction shares that total 100%. Do not
  round recurring percentages before calculating payouts. Round payouts to cents by largest
  remainder; every participant must receive a positive payout.
- Require one positive weight per eligible participant. A seventh participant needs an
  explicit seven-place split; do not truncate, extrapolate or share the last prize.
- Everyone starts in GW2. Update the local private participants file; the owner must apply
  the same start weeks and all six participants on Lightsail. Only four exist locally.

## Configuration

Store rules in `seed/prizes.json`, an ordered list of objects with `from_gameweek` and `weights`.
The initial rule starts at GW2 with the agreed six weights. The latest rule whose start is
at or before a gameweek applies to that week. Add a later rule when people join or the split
changes, leaving earlier rules intact. Editing an earlier rule intentionally recalculates
the weeks it covers, just like changing the participants file.

Read and validate the whole file per money/pool request; invalid or missing configuration
produces an explanatory reply, never an invented payout. No database migration is needed.
Docker already mounts the seed folder; `PRIZES_FILE` selects another path when needed.
The buy-in remains fixed per season and independent of this change.

## Commands

- `/psek-nba-standings [gameweek]`: weekly points, ranks and gap to leader, after transfer costs.
- `/psek-nba-pool [gameweek]`: weekly pool, buy-ins, payout and net.
- `/psek-nba-money [gameweek] [season]`: weekly net by default; `season:true` shows finalized
  weeks and cumulative totals. Reject a gameweek together with `season:true`.
- All weekly defaults use fantasy deadline boundaries. No fallback to an older synced week.
  Mark unfinished results provisional and exclude them from season money totals.
- Keep schedule and chart behaviours unchanged.

## Checks and finish

Test exact six-person payouts, explicit seven-person rules, ties, rounding, invalid files,
count mismatches, effective-week changes, GW1 exclusion, current-week boundaries, missing data,
weekly/season command options and long money replies. Run all four required checks, update
README, AGENTS.md's prize-unit convention and handoff. Leave changes uncommitted. Do not start
the live bot or reset the database.
