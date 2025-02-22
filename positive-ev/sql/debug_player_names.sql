-- Find similar player names and their game stats
WITH similar_names AS (
    SELECT DISTINCT player_name 
    FROM player_boxscores 
    WHERE LOWER(player_name) LIKE LOWER(?) 
       OR LOWER(player_name) LIKE LOWER(?) 
       OR LOWER(?) LIKE LOWER(player_name)
),
player_game_stats AS (
    SELECT 
        pb.player_name,
        COUNT(DISTINCT pb.game_id) as game_count,
        MIN(gb.game_date) as first_game,
        MAX(gb.game_date) as last_game
    FROM player_boxscores pb
    JOIN game_boxscores gb ON pb.game_id = gb.game_id
    WHERE pb.player_name = ?
    AND (
        pb.points IS NOT NULL OR
        pb.rebounds IS NOT NULL OR
        pb.assists IS NOT NULL OR
        pb.steals IS NOT NULL OR
        pb.blocks IS NOT NULL OR
        pb.turnovers IS NOT NULL OR
        pb.made_threes IS NOT NULL
    )
    GROUP BY pb.player_name
)
SELECT 
    (SELECT GROUP_CONCAT(player_name, ', ') FROM similar_names) as similar_names,
    COALESCE(pgs.game_count, 0) as game_count,
    pgs.first_game,
    pgs.last_game
FROM player_game_stats pgs 