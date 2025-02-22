WITH parsed_dates AS (
    SELECT *,
        -- Convert event_time to 24-hour format for comparison
        CASE 
            WHEN substr(event_time, -2) = 'PM' AND substr(event_time, -8, 2) != '12'
            THEN cast(substr(event_time, -8, 2) as integer) + 12
            WHEN substr(event_time, -2) = 'AM' AND substr(event_time, -8, 2) = '12'
            THEN 0
            ELSE cast(substr(event_time, -8, 2) as integer)
        END || ':' || substr(event_time, -5, 2) as event_hour,
        -- Get hour from timestamp
        substr(timestamp, 12, 2) || ':' || substr(timestamp, 15, 2) as bet_hour
    FROM betting_data b
    LEFT JOIN bet_outcome_evaluation boe ON b.bet_id = boe.bet_id
    WHERE boe.outcome IN ('WIN', 'LOSS')
),
time_filtered_bets AS (
    SELECT 
        bet_id, timestamp, ev_percent, event_time, event_teams, 
        sport_league, bet_type, description, odds, sportsbook, 
        bet_size, win_probability, boe.outcome as result,
        -- Calculate minutes between bet time and event time
        (
            (cast(substr(event_hour, 1, 2) as integer) * 60 + cast(substr(event_hour, 4, 2) as integer)) -
            (cast(substr(bet_hour, 1, 2) as integer) * 60 + cast(substr(bet_hour, 4, 2) as integer))
        ) as minutes_to_event,
        -- Get first odds for each bet_id
        FIRST_VALUE(odds) OVER (PARTITION BY bet_id ORDER BY timestamp) as first_odds,
        -- Get last odds for each bet_id
        LAST_VALUE(odds) OVER (PARTITION BY bet_id ORDER BY timestamp 
            RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as final_odds
    FROM parsed_dates
),
filtered_latest AS (
    -- Get only the latest entry for each bet_id that meets time criteria
    SELECT *, 
           ROW_NUMBER() OVER (PARTITION BY bet_id ORDER BY timestamp DESC) as rn
    FROM time_filtered_bets
    WHERE minutes_to_event >= 20
)
SELECT 
    bet_id, timestamp, ev_percent, event_time, event_teams, 
    sport_league, bet_type, description, first_odds, final_odds, 
    sportsbook, bet_size, win_probability, result, minutes_to_event
FROM filtered_latest
WHERE rn = 1
ORDER BY bet_id, timestamp 