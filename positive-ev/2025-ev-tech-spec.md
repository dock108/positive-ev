# Technical Specifications: Parsing NBA Box Scores and Resolving Bets

---

## Objective
Extend the existing betting data pipeline by adding the capability to:
1. Scrape NBA box scores daily, including player and team statistics.
2. Store NBA box score data in a structured database table for historical analysis.
3. Match unresolved bets (from the `betting_data` table) with NBA box score data based on bet type, player/team, and conditions.
4. Automatically determine bet results (`Win` or `Loss`) and update the database.

---

## Architecture Overview

### Data Sources
- **NBA Box Scores**: Web scraping from reliable sources (e.g., ESPN, NBA.com).
- **Betting Data**: Existing SQLite database (`betting_data.db`).

### Steps
1. Scrape and parse NBA box scores for the current date.
2. Save box score data to the `nba_box_scores` table in the SQLite database.
3. Loop through unresolved bets in the `betting_data` table and match them to the box score data.
4. Determine results based on conditions in `Description` (e.g., "Under 59.5" or "Brandon Clarke Under 6.5").
5. Update the `Result` field in the `betting_data` table.

---

## Database Design

### **1. NBA Box Scores Table**
```sql
CREATE TABLE IF NOT EXISTS nba_box_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT,
    teams TEXT,
    player_name TEXT,
    stat_category TEXT,
    stat_value REAL
);
```

- **Fields**:
  - `game_date`: Date of the game (e.g., "2025-01-04").
  - `teams`: Teams involved in the game (e.g., "Denver Nuggets vs San Antonio Spurs").
  - `player_name`: Name of the player (if applicable).
  - `stat_category`: Statistic category (e.g., "Points", "Rebounds", "Total Points").
  - `stat_value`: Value of the statistic (e.g., "59.5" or "7").

### **2. Betting Data Table** (Existing)
```sql
CREATE TABLE IF NOT EXISTS betting_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bet_id TEXT,
    timestamp TEXT,
    ev_percent TEXT,
    event_time TEXT,
    event_teams TEXT,
    sport_league TEXT,
    bet_type TEXT,
    description TEXT,
    odds TEXT,
    sportsbook TEXT,
    bet_size TEXT,
    win_probability TEXT,
    result TEXT DEFAULT ''
);
```

---

## Data Matching Process

### Input: Example Bet
```json
{
    "bet_id": "3494ab0c3b491b428ceb635249bfdb7a",
    "event_teams": "Memphis Grizzlies vs Golden State Warriors",
    "description": "Brandon Clarke Under 6.5",
    "bet_type": "Player Rebounds"
}
```

### Steps
1. **Find Relevant Game**:
   - Match `event_teams` from `betting_data` with `teams` in `nba_box_scores`.

2. **Identify Bet Type**:
   - Parse the `description` field:
     - **Player Name**: Extracted as "Brandon Clarke".
     - **Condition**: Extracted as "Under 6.5".

3. **Query Box Scores**:
   - Search `nba_box_scores` for:
     - `teams='Memphis Grizzlies vs Golden State Warriors'`
     - `player_name='Brandon Clarke'`
     - `stat_category='Rebounds'`

4. **Compare Stat**:
   - Compare `stat_value` with the bet condition:
     - If `stat_value < 6.5`: Update `result='Win'`.
     - Otherwise: Update `result='Loss'`.

---

## Workflow

### 1. Daily Box Score Scraping
- Scrape NBA box scores for the current date.
- Extract:
  - Team stats (e.g., "Total Points").
  - Player stats (e.g., "Rebounds", "Points", etc.).
- Save data to `nba_box_scores`.

### 2. Bet Result Resolution
- Query unresolved bets (`result=''`) from `betting_data`.
- Match bets to box scores based on `event_teams`, `description`, and `bet_type`.
- Parse `description` to identify:
  - Target player or stat (e.g., "Brandon Clarke", "Under 6.5").
- Compare box score data to bet conditions.
- Update `result` field in the `betting_data` table with `Win` or `Loss`.

---

## Challenges and Considerations

### Standardizing Player Names
- Handle variations like "B. Clarke" vs "Brandon Clarke".
- Use a mapping function or fuzzy matching to align names.

### Parsing Descriptions
- Extract clear conditions (e.g., "Under 6.5") from varied bet descriptions.

### Handling Missing Data
- If a player or team stat is unavailable, leave the result unresolved for manual review.

### Scaling for Other Sports
- Design the pipeline to accommodate additional sports or leagues in the future.

---

## Tech Stack
- **Python**:
  - `requests` or `selenium` for web scraping.
  - `sqlite3` for database operations.
  - `re` for parsing descriptions.
- **Database**:
  - SQLite (`betting_data.db`).

---

## Next Steps
1. Develop the scraper for NBA box scores and populate the `nba_box_scores` table.
2. Implement a result-matching script to process unresolved bets.
3. Test the system with sample data for accuracy.
4. Add logging to monitor unmatched bets and identify edge cases.