-- Buy-ins are weekly and the same for everyone, so the amount lives on the season. Money is
-- recomputed from facts on every call, so this is fixed per season: changing it would rewrite
-- every past week.
ALTER TABLE season ADD COLUMN weekly_buy_in_minor INTEGER NOT NULL DEFAULT 10000
    CHECK (weekly_buy_in_minor >= 0);

-- First gameweek a participant pays into and plays for.
ALTER TABLE participant ADD COLUMN joined_gameweek INTEGER NOT NULL DEFAULT 1
    CHECK (joined_gameweek >= 1);

DROP VIEW v_season_standings;
ALTER TABLE participant DROP COLUMN buy_in_minor;

CREATE VIEW v_season_standings AS
SELECT p.season_id, p.participant_id, p.discord_user_id, p.entry_id, e.entry_name,
       COALESCE((SELECT f.total_points
                 FROM fact_entry_day f
                 WHERE f.season_id = p.season_id AND f.entry_id = p.entry_id
                 ORDER BY f.day_id DESC
                 LIMIT 1), 0) AS total_points
FROM participant p
LEFT JOIN entry e USING (season_id, entry_id)
WHERE p.status = 'approved';

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
JOIN participant p
  ON p.season_id = w.season_id AND p.status = 'approved' AND p.joined_gameweek <= w.gameweek
LEFT JOIN v_entry_gameweek g
  ON g.season_id = p.season_id AND g.entry_id = p.entry_id AND g.gameweek = w.gameweek
WHERE EXISTS (
    SELECT 1 FROM fact_entry_day f JOIN day d USING (season_id, day_id)
    WHERE f.season_id = w.season_id AND d.gameweek = w.gameweek
);
