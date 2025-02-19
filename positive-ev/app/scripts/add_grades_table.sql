CREATE TABLE IF NOT EXISTS bet_grades (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    bet_id TEXT NOT NULL,
    grade VARCHAR(1) NOT NULL,
    calculated_at DATETIME NOT NULL,
    ev_score FLOAT,
    timing_score FLOAT,
    historical_edge FLOAT,
    composite_score FLOAT NOT NULL,
    thirty_day_roi FLOAT,
    similar_bets_count INTEGER,
    FOREIGN KEY(bet_id) REFERENCES betting_data (bet_id)
); 