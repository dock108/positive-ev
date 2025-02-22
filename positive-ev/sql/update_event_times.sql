-- First, create a backup of current data
CREATE TABLE betting_data_backup AS SELECT * FROM betting_data;

-- Update event times to standard format
UPDATE betting_data
SET event_time = (
    SELECT strftime('%Y-%m-%d %H:%M', 
        substr(event_time, instr(event_time, ', ') + 2, 4) || '-' ||  -- year
        CASE substr(event_time, 5, 3)  -- month
            WHEN 'Jan' THEN '01'
            WHEN 'Feb' THEN '02'
            WHEN 'Mar' THEN '03'
            WHEN 'Apr' THEN '04'
            WHEN 'May' THEN '05'
            WHEN 'Jun' THEN '06'
            WHEN 'Jul' THEN '07'
            WHEN 'Aug' THEN '08'
            WHEN 'Sep' THEN '09'
            WHEN 'Oct' THEN '10'
            WHEN 'Nov' THEN '11'
            WHEN 'Dec' THEN '12'
        END || '-' ||
        CASE  -- day
            WHEN length(substr(event_time, 9, 2)) = 1 
            THEN '0' || substr(event_time, 9, 1)
            ELSE substr(event_time, 9, 2)
        END || ' ' ||
        CASE  -- convert 12-hour to 24-hour time
            WHEN substr(event_time, -2) = 'PM' AND substr(event_time, -8, 2) != '12'
            THEN (cast(substr(event_time, -8, 2) as integer) + 12) || substr(event_time, -6, 3)
            WHEN substr(event_time, -2) = 'AM' AND substr(event_time, -8, 2) = '12'
            THEN '00' || substr(event_time, -6, 3)
            ELSE substr(event_time, -8, 5)
        END
    )
)
WHERE event_time LIKE '%, % at %';

-- Verify the changes
SELECT 
    bet_id,
    event_time as new_time,
    (SELECT event_time FROM betting_data_backup WHERE bet_id = b.bet_id) as old_time
FROM betting_data b
WHERE event_time != (SELECT event_time FROM betting_data_backup WHERE bet_id = b.bet_id)
LIMIT 5;