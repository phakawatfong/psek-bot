-- Participants now come from seed/participants.csv (see docs/plans/simplify.md), so a
-- participant is just a team and the gameweek it joined: no Discord account, no approval step.
-- SQLite can't drop a column that's part of a UNIQUE constraint, so the table is rebuilt.
-- Pending registrations were never in the pool, so only approved ones are kept.

DROP VIEW v_season_standings;
DROP VIEW v_gameweek_pool;

CREATE TABLE participant_new (
    participant_id INTEGER PRIMARY KEY,
    season_id TEXT NOT NULL REFERENCES season,
    entry_id INTEGER NOT NULL,                  -- nbafantasy entry (team) id
    joined_gameweek INTEGER NOT NULL CHECK (joined_gameweek >= 1),
    UNIQUE (season_id, entry_id)
) STRICT;

INSERT INTO participant_new (participant_id, season_id, entry_id, joined_gameweek)
SELECT participant_id, season_id, entry_id, joined_gameweek
FROM participant
WHERE status = 'approved';

DROP TABLE participant;
ALTER TABLE participant_new RENAME TO participant;

CREATE VIEW v_season_standings AS
SELECT p.season_id, p.participant_id, p.entry_id, e.entry_name,
       COALESCE((SELECT f.total_points
                 FROM fact_entry_day f
                 WHERE f.season_id = p.season_id AND f.entry_id = p.entry_id
                 ORDER BY f.day_id DESC
                 LIMIT 1), 0) AS total_points
FROM participant p
LEFT JOIN entry e USING (season_id, entry_id);

-- Each gameweek that has synced points, with one row per participant in that week's pool.
-- final = 1 once nbafantasy has marked every day of the gameweek data_checked.
CREATE VIEW v_gameweek_pool AS
WITH gameweek AS (
    SELECT season_id, gameweek, MIN(data_checked) AS final
    FROM day
    GROUP BY season_id, gameweek
)
SELECT w.season_id, w.gameweek, w.final, p.participant_id,
       s.weekly_buy_in_minor AS buy_in_minor,
       COALESCE(g.points - g.transfers_cost, 0) AS points
FROM gameweek w
JOIN season s ON s.season_id = w.season_id
JOIN participant p ON p.season_id = w.season_id AND p.joined_gameweek <= w.gameweek
LEFT JOIN v_entry_gameweek g
  ON g.season_id = p.season_id AND g.entry_id = p.entry_id AND g.gameweek = w.gameweek
WHERE EXISTS (
    SELECT 1 FROM fact_entry_day f JOIN day d USING (season_id, day_id)
    WHERE f.season_id = w.season_id AND d.gameweek = w.gameweek
);
