-- First clean up exact duplicates keeping highest EV
WITH DuplicateBets AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY 
                event_time,
                event_teams,
                bet_type,
                -- Extract player name from any stat type
                CASE
                    WHEN instr(description, ' Points ') > 0 THEN substr(description, 1, instr(description, ' Points ') - 1)
                    WHEN instr(description, ' Rebounds ') > 0 THEN substr(description, 1, instr(description, ' Rebounds ') - 1)
                    WHEN instr(description, ' Assists ') > 0 THEN substr(description, 1, instr(description, ' Assists ') - 1)
                    WHEN instr(description, ' Blocks ') > 0 THEN substr(description, 1, instr(description, ' Blocks ') - 1)
                    WHEN instr(description, ' Steals ') > 0 THEN substr(description, 1, instr(description, ' Steals ') - 1)
                    WHEN instr(description, ' Turnovers ') > 0 THEN substr(description, 1, instr(description, ' Turnovers ') - 1)
                    ELSE description
                END
            ORDER BY 
                CAST(REPLACE(ev_percent, '%', '') AS FLOAT) DESC  -- Highest EV first
        ) as rn
    FROM model_work_table
)
DELETE FROM model_work_table 
WHERE bet_id IN (
    SELECT bet_id 
    FROM DuplicateBets 
    WHERE rn > 1
);

-- Then clean up combined stats, preferring simpler versions
WITH CombinedStats AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY 
                event_time,
                event_teams,
                -- Extract player name same as above
                CASE
                    WHEN instr(description, ' Points ') > 0 THEN substr(description, 1, instr(description, ' Points ') - 1)
                    WHEN instr(description, ' Rebounds ') > 0 THEN substr(description, 1, instr(description, ' Rebounds ') - 1)
                    WHEN instr(description, ' Assists ') > 0 THEN substr(description, 1, instr(description, ' Assists ') - 1)
                    WHEN instr(description, ' Blocks ') > 0 THEN substr(description, 1, instr(description, ' Blocks ') - 1)
                    WHEN instr(description, ' Steals ') > 0 THEN substr(description, 1, instr(description, ' Steals ') - 1)
                    WHEN instr(description, ' Turnovers ') > 0 THEN substr(description, 1, instr(description, ' Turnovers ') - 1)
                    ELSE description
                END,
                -- Group by base stat category
                CASE 
                    WHEN description LIKE '%Points%' THEN 'Points'
                    WHEN description LIKE '%Rebounds%' THEN 'Rebounds'
                    WHEN description LIKE '%Assists%' THEN 'Assists'
                    WHEN description LIKE '%Blocks%' THEN 'Blocks'
                    WHEN description LIKE '%Steals%' THEN 'Steals'
                    WHEN description LIKE '%Turnovers%' THEN 'Turnovers'
                    ELSE 'Other'
                END
            ORDER BY 
                -- Prefer simpler versions over combined
                CASE 
                    WHEN description LIKE '%+%' THEN 2
                    ELSE 1
                END,
                CAST(REPLACE(ev_percent, '%', '') AS FLOAT) DESC  -- If same complexity, take higher EV
        ) as rn
    FROM model_work_table
)
DELETE FROM model_work_table 
WHERE bet_id IN (
    SELECT bet_id 
    FROM CombinedStats 
    WHERE rn > 1
);