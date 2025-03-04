-- Database schema for the betting chatbot

-- Users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    plan TEXT CHECK( plan IN ('free', 'premium') ) DEFAULT 'free',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Positive EV bets imported from the main system
CREATE TABLE IF NOT EXISTS positive_ev_bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bet_id TEXT UNIQUE,
    game TEXT NOT NULL,
    bet_description TEXT NOT NULL,
    sportsbook TEXT NOT NULL,
    odds TEXT NOT NULL,
    ev_percent REAL NOT NULL,
    win_probability REAL,
    sport VARCHAR(50) DEFAULT 'nba',
    league VARCHAR(50) DEFAULT 'NBA',
    event_time TIMESTAMP,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track user usage for free tier limitations
CREATE TABLE IF NOT EXISTS user_usage (
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    recommendation_count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, date),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Track timeout enforcement for rule violations
CREATE TABLE IF NOT EXISTS timeout_tracker (
    user_id INTEGER NOT NULL,
    timeout_until TIMESTAMP,
    violations INTEGER DEFAULT 0,
    PRIMARY KEY (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Chat history for context
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    message TEXT NOT NULL,
    role TEXT CHECK( role IN ('user', 'assistant') ) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_positive_ev_bets_sport ON positive_ev_bets(sport, league);
CREATE INDEX IF NOT EXISTS idx_positive_ev_bets_event_time ON positive_ev_bets(event_time);
CREATE INDEX IF NOT EXISTS idx_chat_history_user_session ON chat_history(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_timestamp ON chat_history(timestamp);
