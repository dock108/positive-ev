-- First, create a backup of current data
CREATE TABLE betting_data_backup_fix AS SELECT * FROM betting_data;

-- Test the conversion with a SELECT before updating
SELECT 
    event_time as original_time,
    -- Extract time components
    trim(substr(event_time, instr(event_time, 'at ') + 3, 
         instr(substr(event_time, instr(event_time, 'at ') + 3), ' '))) as hour,
    substr(event_time, -5, 2) as minute,
    substr(event_time, -2) as ampm,
    -- Extract date components
    substr(event_time, instr(event_time, ', ') + 2, 
           instr(substr(event_time, instr(event_time, ', ') + 2), ' ') - 1) as month,
    trim(substr(event_time, 
           instr(event_time, ', ') + 2 + length('Jan '),
           instr(substr(event_time, instr(event_time, ', ') + 2 + length('Jan ')), ','))) as day,
    substr(event_time, 
           instr(event_time, ', ') + 2 + length('Jan 5, '),
           4) as year,
    -- Build the final timestamp
    substr(event_time, 
           instr(event_time, ', ') + 2 + length('Jan 5, '),
           4) || '-' ||  -- year
    CASE substr(event_time, instr(event_time, ', ') + 2, 3)
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
    printf('%02d', cast(trim(substr(event_time, 
           instr(event_time, ', ') + 2 + length('Jan '),
           instr(substr(event_time, instr(event_time, ', ') + 2 + length('Jan ')), ','))) as integer)) || ' ' ||
    CASE 
        WHEN substr(event_time, -2) = 'PM' AND cast(trim(substr(event_time, instr(event_time, 'at ') + 3, 
             instr(substr(event_time, instr(event_time, 'at ') + 3), ' '))) as integer) != 12
        THEN printf('%02d', cast(trim(substr(event_time, instr(event_time, 'at ') + 3, 
             instr(substr(event_time, instr(event_time, 'at ') + 3), ' '))) as integer) + 12)
        WHEN substr(event_time, -2) = 'AM' AND cast(trim(substr(event_time, instr(event_time, 'at ') + 3, 
             instr(substr(event_time, instr(event_time, 'at ') + 3), ' '))) as integer) = 12
        THEN '00'
        ELSE printf('%02d', cast(trim(substr(event_time, instr(event_time, 'at ') + 3, 
             instr(substr(event_time, instr(event_time, 'at ') + 3), ' '))) as integer))
    END || ':' || substr(event_time, -5, 2) as formatted_time
FROM betting_data
WHERE event_time NOT LIKE '____-__-__ __:__'
LIMIT 5;

-- If the SELECT looks good, perform the update
UPDATE betting_data
SET event_time = 
    substr(event_time, 
           instr(event_time, ', ') + 2 + length('Jan 5, '),
           4) || '-' ||  -- year
    CASE substr(event_time, instr(event_time, ', ') + 2, 3)
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
    printf('%02d', cast(trim(substr(event_time, 
           instr(event_time, ', ') + 2 + length('Jan '),
           instr(substr(event_time, instr(event_time, ', ') + 2 + length('Jan ')), ','))) as integer)) || ' ' ||
    CASE 
        WHEN substr(event_time, -2) = 'PM' AND cast(trim(substr(event_time, instr(event_time, 'at ') + 3, 
             instr(substr(event_time, instr(event_time, 'at ') + 3), ' '))) as integer) != 12
        THEN printf('%02d', cast(trim(substr(event_time, instr(event_time, 'at ') + 3, 
             instr(substr(event_time, instr(event_time, 'at ') + 3), ' '))) as integer) + 12)
        WHEN substr(event_time, -2) = 'AM' AND cast(trim(substr(event_time, instr(event_time, 'at ') + 3, 
             instr(substr(event_time, instr(event_time, 'at ') + 3), ' '))) as integer) = 12
        THEN '00'
        ELSE printf('%02d', cast(trim(substr(event_time, instr(event_time, 'at ') + 3, 
             instr(substr(event_time, instr(event_time, 'at ') + 3), ' '))) as integer))
    END || ':' || substr(event_time, -5, 2)
WHERE event_time NOT LIKE '____-__-__ __:__';

-- Verify the changes
SELECT 
    bet_id,
    event_time as new_time,
    (SELECT event_time FROM betting_data_backup_fix WHERE bet_id = b.bet_id) as old_time
FROM betting_data b
WHERE event_time != (SELECT event_time FROM betting_data_backup_fix WHERE bet_id = b.bet_id)
LIMIT 5;

-- Show any problematic records that didn't convert
SELECT bet_id, event_time
FROM betting_data 
WHERE event_time NOT LIKE '____-__-__ __:__'
LIMIT 5;

-- First, show what we're going to update
SELECT bet_id, event_time, 
       REPLACE(event_time, '2024', '2025') as fixed_time
FROM betting_data 
WHERE event_time LIKE '%2024%';

-- Then do the update
UPDATE betting_data 
SET event_time = REPLACE(event_time, '2024', '2025')
WHERE event_time LIKE '%2024%';

-- Verify the changes
SELECT bet_id, 
       event_time as new_time,
       (SELECT event_time FROM betting_data_backup_fix WHERE bet_id = b.bet_id) as old_time
FROM betting_data b
WHERE event_time != (SELECT event_time FROM betting_data_backup_fix WHERE bet_id = b.bet_id); 