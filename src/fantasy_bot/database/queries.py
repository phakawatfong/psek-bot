"""Query pieces every feature shares: naming a participant by its nbafantasy team."""

from sqlalchemy import Text, and_, cast, func, literal

from fantasy_bot.database import tables as t

# Outer-join condition from a participant to its team. Before the first sync a team has no
# entry row yet, so it's named by its id.
ENTRY_OF_PARTICIPANT = and_(
    t.Entry.season_id == t.Participant.season_id, t.Entry.entry_id == t.Participant.entry_id
)
TEAM_NAME = func.coalesce(
    t.Entry.entry_name, literal("entry ") + cast(t.Participant.entry_id, Text)
)
MANAGER_NAME = func.coalesce(t.Entry.manager_name, "")
