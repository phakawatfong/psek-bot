# Plan: fixing registration mistakes from Discord

Status: built. Reset clears payments too, as proposed.

## Goal

Let an admin fix registration mistakes from Discord, without server access:

- correct a team's start week or the Discord account it is linked to,
- take a team out of the pool,
- start the season's registrations over.

## Commands

All three are admin-only: hidden from members without **Manage Server**, the same as
`/psek-nba-add`, `/psek-nba-approve`, and `/psek-nba-paid` (see "Who is an admin" in the README).

### `/psek-nba-edit team: [from_gameweek:] [member:]`

- `team`: dropdown of every registered team, pending or approved.
- `from_gameweek`: the first gameweek the team pays and plays.
- `member`: re-link the team to a different Discord account.
- Leaves the team's status alone: a pending team stays pending.
- Replies:
  - "Updated **jkslots**: from gameweek 1 → 2."
  - "Nothing to change." when neither option is given.
  - "That member already has **Dream team**. It's one team per person."
  - "That team hasn't registered." for a team not in the pool.

### `/psek-nba-remove team:`

- `team`: the same dropdown of every registered team.
- Deletes the team's registration and its payment records together, in one transaction.
- The reply says what was removed and exactly how to undo it, e.g.:

  > Removed **jkslots** (in from gameweek 1, linked to @pisit; 2 payment records: 200.00 in).
  > To undo: `/psek-nba-add team:jkslots member:@pisit from_gameweek:1`, then record the
  > payments again with `/psek-nba-paid`.

### `/psek-nba-reset`

- Replies privately, visible only to the admin who ran it, with a red **Yes, remove everyone**
  button and a **Cancel** button. The buttons expire after 60 seconds; nothing happens unless
  the admin confirms.
- Confirming deletes every registration and payment record for this season, then reports how
  many of each were removed and that the nightly backup (`/data/backups`) can restore them.

## What stays untouched

- Points data synced from nbafantasy: games, picks, player stats, daily totals.
- The season's money rules: weekly buy-in and payout split.
- Other seasons.

## Code changes

| Layer | Change |
|---|---|
| `repositories/registration.py` | `set_start(participant, gameweek)`; `remove(participant)` deleting payments then the registration in one transaction; `reset(season)`; a `"registered"` filter for `search_teams` (any status) |
| `services/registration.py` | `edit()`, `remove()`, `reset()` returning plain results: `EditResult`, `RemoveResult`, `ResetResult` |
| `bot/commands/admin.py` | the three handlers, their reply text, and a `ConfirmReset` button view |
| `bot/commands/__init__.py` | three new routes (14 commands in total) |
| `README.md` | a "Fixing mistakes" section |

## Behavior to be aware of

- Money is recomputed from the stored points on every call. Changing a team's start week or
  removing it therefore changes the pool, and possibly the payouts, of every week it touches,
  including weeks that are already final. The replies name the gameweeks affected.
- Payment records are deleted with their team rather than left without one. The remove reply
  lists the amounts so they can be recorded again.

## Tests

- Services:
  - edit the start week, the member, both, and neither;
  - edit to a member who already has a team;
  - remove a team with and without payments;
  - removing one team leaves the others intact;
  - reset clears every registration and payment but no points data;
  - each command against a team that isn't registered.
- Reply formatting for each outcome, including the undo line.
- Routes: 14 commands; `edit`, `remove`, and `reset` are hidden from non-admins.
- The reset confirm action is tested as a plain function. The buttons themselves need one check
  in real Discord.

## Out of scope

- Undoing a single payment. Record the opposite with `/psek-nba-paid` instead.
- A history of edits.

## Open question

Should `/psek-nba-reset` also clear payments? Proposed: **yes**, so a reset means starting
completely fresh. Keeping payments while removing every team would leave them attached to no
one.
