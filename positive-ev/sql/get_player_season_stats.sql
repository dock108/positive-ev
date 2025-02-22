WITH PlayerGames AS (
    -- Get distinct games where player has any stats
    SELECT DISTINCT gb.game_id, gb.game_date
    FROM game_boxscores gb
    JOIN player_boxscores pb ON gb.game_id = pb.game_id
    WHERE pb.player_name = ?
    AND pb.points IS NOT NULL  -- Ensure player actually played
),
TeamGames AS (
    -- Get all games in the date range
    SELECT DISTINCT game_id
    FROM game_boxscores
    WHERE DATE(game_date) < DATE(?)
    AND DATE(game_date) >= DATE(?, '-6 months')
)
SELECT 
    (SELECT COUNT(*) FROM PlayerGames) as games_played,
    (SELECT COUNT(*) FROM TeamGames) as total_games 