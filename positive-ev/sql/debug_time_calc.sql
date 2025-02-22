WITH parsed_dates AS (
    SELECT 
        bet_id, timestamp, event_time,
        -- Convert event_time to 24-hour format
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
    LIMIT 5
)
SELECT 
    bet_id, 
    timestamp, 
    event_time,
    event_hour,
    bet_hour,
    (
        (cast(substr(event_hour, 1, 2) as integer) * 60 + cast(substr(event_hour, 4, 2) as integer)) -
        (cast(substr(bet_hour, 1, 2) as integer) * 60 + cast(substr(bet_hour, 4, 2) as integer))
    ) as minutes_to_event,
    CASE WHEN (
        (cast(substr(event_hour, 1, 2) as integer) * 60 + cast(substr(event_hour, 4, 2) as integer)) -
        (cast(substr(bet_hour, 1, 2) as integer) * 60 + cast(substr(bet_hour, 4, 2) as integer))
    ) >= 20 THEN 'YES' ELSE 'NO' END as meets_criteria
FROM parsed_dates 