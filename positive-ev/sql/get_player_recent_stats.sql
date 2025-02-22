SELECT DISTINCT 
    pb.points, pb.rebounds, pb.assists, 
    pb.steals, pb.blocks, pb.turnovers, 
    COALESCE(pb.made_threes, 0) as made_threes,
    gb.game_date
FROM player_boxscores pb
JOIN game_boxscores gb ON pb.game_id = gb.game_id
WHERE pb.player_name = ?
    AND DATE(gb.game_date) < DATE(?)
    AND pb.points IS NOT NULL  -- Ensure we have actual stats
ORDER BY gb.game_date DESC
LIMIT 20 