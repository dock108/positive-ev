WITH game_date AS (
    SELECT date(?) as event_date  -- Now we can just use the date directly
),
team_games AS (
    SELECT COUNT(DISTINCT gb.game_id) as total_team_games
    FROM game_boxscores gb
    WHERE gb.game_date < (SELECT event_date FROM game_date)
    AND gb.team IN (
        SELECT DISTINCT team 
        FROM player_boxscores pb2 
        JOIN game_boxscores gb2 ON pb2.game_id = gb2.game_id 
        WHERE pb2.player_name = ?
    )
),
player_games AS (
    SELECT COUNT(*) as games_played
    FROM player_boxscores pb
    JOIN game_boxscores gb ON pb.game_id = gb.game_id
    WHERE pb.player_name = ?
    AND gb.game_date < (SELECT event_date FROM game_date)
    AND (
        pb.points IS NOT NULL OR
        pb.rebounds IS NOT NULL OR
        pb.assists IS NOT NULL OR
        pb.steals IS NOT NULL OR
        pb.blocks IS NOT NULL OR
        pb.turnovers IS NOT NULL OR
        pb.made_threes IS NOT NULL
    )
)
SELECT 
    pg.games_played,
    tg.total_team_games,
    ROUND(CAST(pg.games_played AS FLOAT) / tg.total_team_games * 100, 2) as health_percentage
FROM player_games pg, team_games tg 