-- Conventions: times are ISO-8601 UTC text, money is integer minor units,
-- fantasy points are integer tenths (as nbafantasy reports them).

-- Pool and participants: the only data no upstream API has.

CREATE TABLE season (
    season_id TEXT PRIMARY KEY,                 -- e.g. '2026-27'
    league_id INTEGER NOT NULL,                 -- nbafantasy classic league id
    locked_at TEXT                              -- NULL while registration and bets are open
) STRICT;

CREATE TABLE payout_rank (
    season_id TEXT NOT NULL REFERENCES season,
    rank INTEGER NOT NULL CHECK (rank >= 1),
    share_bp INTEGER NOT NULL CHECK (share_bp > 0),  -- basis points; a season's ranks sum to 10000
    PRIMARY KEY (season_id, rank)
) STRICT;

CREATE TABLE participant (
    participant_id INTEGER PRIMARY KEY,
    season_id TEXT NOT NULL REFERENCES season,
    discord_user_id INTEGER NOT NULL,
    entry_id INTEGER NOT NULL,                  -- nbafantasy entry (team) id
    buy_in_minor INTEGER NOT NULL CHECK (buy_in_minor >= 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved')),
    registered_at TEXT NOT NULL,
    UNIQUE (season_id, discord_user_id),
    UNIQUE (season_id, entry_id)
) STRICT;

CREATE TABLE ledger (
    ledger_id INTEGER PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES participant,
    kind TEXT NOT NULL CHECK (kind IN ('paid_in', 'paid_out')),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    note TEXT,
    created_at TEXT NOT NULL
) STRICT;

-- nbafantasy dimensions. Its ids restart every season, so season_id is in every key.

CREATE TABLE nba_team (
    season_id TEXT NOT NULL REFERENCES season,
    team_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    PRIMARY KEY (season_id, team_id)
) STRICT;

CREATE TABLE player (
    season_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,                 -- nbafantasy element id
    nba_person_id INTEGER NOT NULL,             -- element.code; joins to nba_api
    web_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    second_name TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    position TEXT NOT NULL CHECK (position IN ('BC', 'FC')),
    PRIMARY KEY (season_id, player_id),
    FOREIGN KEY (season_id, team_id) REFERENCES nba_team
) STRICT;

CREATE TABLE day (
    season_id TEXT NOT NULL REFERENCES season,
    day_id INTEGER NOT NULL,                    -- nbafantasy event id
    gameweek INTEGER NOT NULL,                  -- from bootstrap phases
    name TEXT NOT NULL,
    deadline_time TEXT NOT NULL,
    finished INTEGER NOT NULL CHECK (finished IN (0, 1)),
    data_checked INTEGER NOT NULL CHECK (data_checked IN (0, 1)),  -- 1 = points are final
    PRIMARY KEY (season_id, day_id)
) STRICT;

CREATE TABLE fixture (
    season_id TEXT NOT NULL,
    fixture_id INTEGER NOT NULL,
    day_id INTEGER NOT NULL,
    nba_game_id TEXT NOT NULL,                  -- fixture.code zero-padded to 10; joins to nba_api
    kickoff_time TEXT NOT NULL,
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    finished INTEGER NOT NULL CHECK (finished IN (0, 1)),
    PRIMARY KEY (season_id, fixture_id),
    FOREIGN KEY (season_id, day_id) REFERENCES day,
    FOREIGN KEY (season_id, home_team_id) REFERENCES nba_team,
    FOREIGN KEY (season_id, away_team_id) REFERENCES nba_team
) STRICT;

CREATE TABLE entry (
    season_id TEXT NOT NULL REFERENCES season,
    entry_id INTEGER NOT NULL,
    entry_name TEXT NOT NULL,
    manager_name TEXT NOT NULL,
    PRIMARY KEY (season_id, entry_id)
) STRICT;

-- Facts, finest grain first.

CREATE TABLE fact_player_stat (
    season_id TEXT NOT NULL,
    fixture_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    stat TEXT NOT NULL,                         -- 'points_scored', 'rebounds', ...
    value INTEGER NOT NULL,
    points INTEGER NOT NULL,
    PRIMARY KEY (season_id, fixture_id, player_id, stat),
    FOREIGN KEY (season_id, fixture_id) REFERENCES fixture,
    FOREIGN KEY (season_id, player_id) REFERENCES player
) STRICT;

CREATE TABLE fact_pick (
    season_id TEXT NOT NULL,
    entry_id INTEGER NOT NULL,
    day_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    position INTEGER NOT NULL,                  -- 1-5 starters, 6-10 bench
    multiplier INTEGER NOT NULL,                -- 0 bench, 1 starter, more for captain
    is_captain INTEGER NOT NULL CHECK (is_captain IN (0, 1)),
    PRIMARY KEY (season_id, entry_id, day_id, player_id),
    FOREIGN KEY (season_id, entry_id) REFERENCES entry,
    FOREIGN KEY (season_id, day_id) REFERENCES day,
    FOREIGN KEY (season_id, player_id) REFERENCES player
) STRICT;

CREATE TABLE fact_entry_day (
    season_id TEXT NOT NULL,
    entry_id INTEGER NOT NULL,
    day_id INTEGER NOT NULL,
    points INTEGER NOT NULL,                    -- official day total, for reconciling picks x stats
    total_points INTEGER NOT NULL,              -- official running season total
    transfers_cost INTEGER NOT NULL,
    points_on_bench INTEGER NOT NULL,
    overall_rank INTEGER,
    PRIMARY KEY (season_id, entry_id, day_id),
    FOREIGN KEY (season_id, entry_id) REFERENCES entry,
    FOREIGN KEY (season_id, day_id) REFERENCES day
) STRICT;

CREATE TABLE raw_api_response (
    season_id TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('nbafantasy', 'nba_api')),
    request_key TEXT NOT NULL,                  -- e.g. 'event/4/live/'
    fetched_at TEXT NOT NULL,
    body TEXT NOT NULL,
    PRIMARY KEY (season_id, source, request_key)
) STRICT;

-- Marts.

CREATE VIEW v_entry_gameweek AS
SELECT f.season_id, f.entry_id, d.gameweek,
       SUM(f.points) AS points,
       SUM(f.transfers_cost) AS transfers_cost,
       COUNT(*) AS days_played
FROM fact_entry_day f
JOIN day d USING (season_id, day_id)
GROUP BY f.season_id, f.entry_id, d.gameweek;

CREATE VIEW v_season_standings AS
SELECT p.season_id, p.participant_id, p.discord_user_id, p.entry_id, e.entry_name,
       p.buy_in_minor,
       COALESCE((SELECT f.total_points
                 FROM fact_entry_day f
                 WHERE f.season_id = p.season_id AND f.entry_id = p.entry_id
                 ORDER BY f.day_id DESC
                 LIMIT 1), 0) AS total_points
FROM participant p
LEFT JOIN entry e USING (season_id, entry_id)
WHERE p.status = 'approved';
