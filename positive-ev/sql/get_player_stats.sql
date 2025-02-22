WITH game_date AS (
    SELECT date(?) as event_date  -- Now we can just use the date directly
)
SELECT 
    pb.points, pb.rebounds, pb.assists,
    pb.steals, pb.blocks, pb.turnovers, pb.made_threes,
    gb.game_date
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
ORDER BY gb.game_date DESC
LIMIT 20 