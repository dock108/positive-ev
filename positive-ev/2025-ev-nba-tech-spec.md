# Technical Specifications: NBA Box Score Storage and Result Resolution

---

## Objective
Enhance the betting data pipeline by:
1. Storing NBA box scores daily in the same SQLite database (`betting_data.db`) but in a separate table.
2. Allowing the script to accept a specific date as input to process missed or redo days.
3. Comparing unresolved bets from the `betting_data` table with stored box score data to determine results.
4. Setting the result to `PEND MANUAL` if a bet cannot be resolved for a given day.

---

## Architecture Overview

### Data Sources
- **NBA Box Scores**: Scraped from reliable sources (e.g., ESPN, NBA.com) for a specific date.
- **Betting Data**: Existing SQLite table storing bet details.

### Steps
1. Scrape NBA box scores for the specified date.
2. Store box scores in the `nba_box_scores` table.
3. Query unresolved bets from the `betting_data` table for the corresponding date.
4. Match each unresolved bet to the corresponding box score based on teams, players, and bet descriptions.
5. Determine results (`Win`, `Loss`) or mark as `PEND MANUAL` if no match or sufficient data is found.

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

- **Modified Field**:
  - `result`: Will be updated to `Win`, `Loss`, or `PEND MANUAL`.

---

## Workflow

### 1. Accept a Date Input
- Add an optional command-line argument or input prompt for the target date.
- If no date is provided, default to the current date.

### 2. Scrape and Store NBA Box Scores
- Scrape box scores for the specified date.
- Parse:
  - Team stats (e.g., "Total Points").
  - Player stats (e.g., "Rebounds", "Points").
- Save parsed data to the `nba_box_scores` table with the corresponding `game_date`.

### 3. Match Bets to Box Scores
1. Query unresolved bets (`result=''`) from the `betting_data` table where:
   - `event_time` matches the specified date.
2. For each bet:
   - Match `event_teams` to `teams` in `nba_box_scores`.
   - Parse the `description` field to extract:
     - Player or team name (e.g., "Brandon Clarke").
     - Condition (e.g., "Under 6.5").
   - Search the `nba_box_scores` table for:
     - `game_date='2025-01-04'`
     - `teams='Memphis Grizzlies vs Golden State Warriors'`
     - `player_name='Brandon Clarke'`
     - `stat_category='Rebounds'`
3. Compare the `stat_value` with the condition in `description`:
   - If the condition is met, set `result='Win'`.
   - If the condition is not met, set `result='Loss'`.

### 4. Handle Unmatched Bets
- If no match or insufficient data is found:
  - Set `result='PEND MANUAL'`.
  - Log these bets for manual review.

---

## Challenges and Considerations

### 1. Handling Custom Dates
- Ensure input date validation (e.g., "YYYY-MM-DD").
- Handle edge cases where box scores are unavailable for the given date.

### 2. Standardizing Names
- Handle variations in player names (e.g., "B. Clarke" vs "Brandon Clarke").
- Use a mapping or fuzzy matching function for consistency.

### 3. Parsing Descriptions
- Accurately extract conditions (e.g., "Under 6.5") from varied bet descriptions.

### 4. Handling Missing Data
- Bets marked as `PEND MANUAL` will require manual review.
- Log unresolved bets for easier troubleshooting.

---

## Tech Stack

### Python
- **Web Scraping**: `requests` or `selenium`.
- **Database Operations**: `sqlite3`.
- **Date Parsing**: `datetime` for flexible date handling.
- **Text Parsing**: `re` or `fuzzywuzzy` for fuzzy matching.

### Database
- SQLite (`betting_data.db`).

---

## Next Steps

1. Update the scraper to accept a specific date as input and populate the `nba_box_scores` table.
2. Implement a result-matching script to process unresolved bets for the specified date.
3. Test the workflow with past data to ensure flexibility and accuracy.
4. Add logging for unresolved bets and manual review cases.
