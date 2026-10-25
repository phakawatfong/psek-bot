-- 1 once a day's facts were synced after nbafantasy marked it data_checked.
-- Such days are final and never fetched again.
ALTER TABLE day ADD COLUMN facts_final INTEGER NOT NULL DEFAULT 0 CHECK (facts_final IN (0, 1));

-- First day an entry played (nbafantasy started_event); earlier days have no picks to fetch.
ALTER TABLE entry ADD COLUMN started_day INTEGER NOT NULL DEFAULT 1;

-- When each sync ran and what it did, for the "as of" line and for debugging.
CREATE TABLE sync_run (
    sync_run_id INTEGER PRIMARY KEY,
    season_id TEXT NOT NULL REFERENCES season,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    days_synced INTEGER,
    error TEXT
) STRICT;

-- Official day total next to the total rebuilt from picks x player stats. They should match;
-- a difference means a parser bug or an API change.
CREATE VIEW v_entry_day_reconcile AS
SELECT ed.season_id, ed.entry_id, ed.day_id, d.data_checked,
       ed.points AS official,
       COALESCE(SUM(p.multiplier * ps.points), 0) AS computed
FROM fact_entry_day ed
JOIN day d USING (season_id, day_id)
LEFT JOIN fact_pick p USING (season_id, entry_id, day_id)
LEFT JOIN (
    SELECT s.season_id, f.day_id, s.player_id, SUM(s.points) AS points
    FROM fact_player_stat s
    JOIN fixture f USING (season_id, fixture_id)
    GROUP BY s.season_id, f.day_id, s.player_id
) ps ON ps.season_id = p.season_id AND ps.day_id = p.day_id AND ps.player_id = p.player_id
GROUP BY ed.season_id, ed.entry_id, ed.day_id;
