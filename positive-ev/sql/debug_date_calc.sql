SELECT date(
    '2025' || '-' ||
    CASE substr(?, instr(?, ', ') + 2, 3)
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
    CASE 
        WHEN length(substr(?, instr(?, ', ') + 6, 2)) = 1
        THEN '0' || substr(?, instr(?, ', ') + 6, 1)
        ELSE substr(?, instr(?, ', ') + 6, 2)
    END
) as calculated_date 