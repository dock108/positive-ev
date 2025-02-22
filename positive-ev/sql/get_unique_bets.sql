WITH ValidBets AS (
    -- First get the first odds for each unique bet
    SELECT 
        b.event_teams, b.description, b.event_time,
        MIN(b.timestamp) as first_timestamp,
        MIN(b.odds) as first_odds
    FROM betting_data b
    LEFT JOIN bet_outcome_evaluation boe ON b.bet_id = boe.bet_id
    WHERE boe.outcome IN ('WIN', 'LOSS')
    GROUP BY b.event_teams, b.description, b.event_time
),
BetCategories AS (
    -- Count stat categories in each bet description
    SELECT 
        b.*,
        CASE 
            WHEN description LIKE '%Points%' AND description NOT LIKE '%Rebounds%' AND description NOT LIKE '%Assists%' THEN 1
            WHEN description LIKE '%Rebounds%' AND description NOT LIKE '%Points%' AND description NOT LIKE '%Assists%' THEN 1
            WHEN description LIKE '%Assists%' AND description NOT LIKE '%Points%' AND description NOT LIKE '%Rebounds%' THEN 1
            WHEN description LIKE '%Points%Rebounds%' OR description LIKE '%Rebounds%Points%' THEN 2
            WHEN description LIKE '%Points%Assists%' OR description LIKE '%Assists%Points%' THEN 2
            WHEN description LIKE '%Rebounds%Assists%' OR description LIKE '%Assists%Rebounds%' THEN 2
            WHEN description LIKE '%Points%Rebounds%Assists%' THEN 3
            ELSE 1
        END as stat_categories,
        CAST(REPLACE(ev_percent, '%', '') AS FLOAT) as ev_numeric,  -- Convert EV to numeric
        -- Extract player name (everything before any stat type)
        CASE
            WHEN instr(description, ' Points + ') > 0 THEN substr(description, 1, instr(description, ' Points + ') - 1)
            WHEN instr(description, ' Points ') > 0 THEN substr(description, 1, instr(description, ' Points ') - 1)
            WHEN instr(description, ' Rebounds + ') > 0 THEN substr(description, 1, instr(description, ' Rebounds + ') - 1)
            WHEN instr(description, ' Rebounds ') > 0 THEN substr(description, 1, instr(description, ' Rebounds ') - 1)
            WHEN instr(description, ' Assists + ') > 0 THEN substr(description, 1, instr(description, ' Assists + ') - 1)
            WHEN instr(description, ' Assists ') > 0 THEN substr(description, 1, instr(description, ' Assists ') - 1)
            ELSE description
        END as player_name
    FROM betting_data b
),
TimedBets AS (
    -- Then join back to get full bet details with optimal timing
    SELECT 
        b.bet_id,
        b.timestamp,
        b.ev_percent,
        b.event_time,
        b.event_teams,
        b.sport_league,
        b.bet_type,
        b.description,
        b.odds as final_odds,
        vb.first_odds,
        b.sportsbook,
        b.bet_size,
        b.win_probability,
        boe.outcome as result,
        CAST((julianday(b.event_time) - julianday(b.timestamp)) * 24 * 60 as integer) as mins_to_event,
        b.stat_categories,
        ROW_NUMBER() OVER (
            PARTITION BY b.event_teams, b.event_time, b.player_name
            ORDER BY 
                -- Prioritize simpler bets and higher EV
                b.stat_categories,
                -b.ev_numeric,  -- Negative to sort descending (highest EV first)
                CASE 
                    WHEN CAST((julianday(b.event_time) - julianday(b.timestamp)) * 24 * 60 as integer) BETWEEN 20 AND 30 THEN 0
                    WHEN CAST((julianday(b.event_time) - julianday(b.timestamp)) * 24 * 60 as integer) > 30 THEN 1
                    ELSE 2
                END,
                ABS(CAST((julianday(b.event_time) - julianday(b.timestamp)) * 24 * 60 as integer) - 30)
        ) as rn
    FROM BetCategories b
    JOIN ValidBets vb ON b.event_teams = vb.event_teams 
        AND b.description = vb.description 
        AND b.event_time = vb.event_time
    LEFT JOIN bet_outcome_evaluation boe ON b.bet_id = boe.bet_id
    WHERE boe.outcome IN ('WIN', 'LOSS')
)
SELECT *
FROM TimedBets
WHERE rn = 1
ORDER BY event_time 