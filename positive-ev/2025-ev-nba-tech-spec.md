# Technical Specifications: NBA Box Score Storage and Result Resolution

---

## Objective
Enhance the betting data pipeline by:
1. Storing NBA box scores daily in the same SQLite database (`betting_data.db`) but in a separate table.
2. Adding support for team scores (overall and by quarter) and assigning players to their respective teams.
3. Allowing the script to accept a specific date as input to process missed or redo days.
4. Comparing unresolved bets from the `betting_data` table with stored box score data to determine results.
5. Setting the result to `PEND MANUAL` if a bet cannot be resolved for a given day.

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
    team TEXT,
    player_name TEXT,
    stat_category TEXT,
    stat_value REAL
);
```

- **Fields**:
  - `game_date`: Date of the game (e.g., "2025-01-04").
  - `teams`: Full matchup (e.g., "Denver Nuggets vs San Antonio Spurs").
  - `team`: Individual team name (e.g., "Denver Nuggets").
  - `player_name`: Name of the player (if applicable).
  - `stat_category`: Statistic category (e.g., "Points", "Rebounds", "Q1 Points").
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
  - **Team stats**:
    - Overall score for the game.
    - Scores by quarter (`Q1`, `Q2`, `Q3`, `Q4`).
  - **Player stats**:
    - Rebounds, Points, Assists, etc.
    - Assign players to their respective teams.
- Save parsed data to the `nba_box_scores` table with the corresponding `game_date`.

### 3. Match Bets to Box Scores
1. Query unresolved bets (`result=''`) from the `betting_data` table where:
   - `event_time` matches the specified date.
2. For each bet:
   - Match `event_teams` to `teams` in `nba_box_scores`.
   - Parse the `description` field to extract:
     - Player or team name (e.g., "Brandon Clarke" or "Denver Nuggets").
     - Condition (e.g., "Under 6.5").
   - Search the `nba_box_scores` table for:
     - `game_date='2025-01-04'`
     - `teams='Memphis Grizzlies vs Golden State Warriors'`
     - `team='Denver Nuggets'` or `player_name='Brandon Clarke'`
     - `stat_category` matching the bet type (e.g., "Points", "Q1 Points").
3. Compare the `stat_value` with the condition in `description`:
   - If the condition is met, set `result='Win'`.
   - If the condition is not met, set `result='Loss'`.

### 4. Handle Unmatched Bets
- If no match or insufficient data is found:
  - Set `result='PEND MANUAL'`.
  - Log these bets for manual review.

---

## Matching Logic

### Input: Example Bet
```json
{
    "bet_id": "6e930eb26ee241e499a3bbcbf2eb74cf",
    "event_teams": "Memphis Grizzlies vs Golden State Warriors",
    "description": "Jaren Jackson Jr. Under 7.5",
    "bet_type": "Player Rebounds",
    "event_time": "2025-01-04"
}
```

### Steps
1. **Match Teams**:
   - Match `event_teams` from `betting_data` with `teams` in `nba_box_scores`.

2. **Extract Condition**:
   - Parse `description` to identify:
     - **Player Name**: Extract "Jaren Jackson Jr.".
     - **Condition**: Extract "Under 7.5".

3. **Query Box Scores**:
   - Search `nba_box_scores` for:
     - `game_date='2025-01-04'`
     - `teams='Memphis Grizzlies vs Golden State Warriors'`
     - `player_name='Jaren Jackson Jr.'`
     - `stat_category='Rebounds'`

4. **Determine Result**:
   - If `stat_value < 7.5`: Update `result='Win'`.
   - If `stat_value >= 7.5`: Update `result='Loss'`.

5. **Handle Missing Data**:
   - If no matching box score is found, update `result='PEND MANUAL'`.

---

## Challenges and Considerations

### 1. Team-Level Props
- Include quarter-specific scores (e.g., `Q1 Points`) to handle team-level bets.

### 2. Assigning Players to Teams
- Ensure consistency between player names and teams (e.g., "Brandon Clarke" belongs to "Memphis Grizzlies").

### 3. Handling Missing Data
- Bets marked as `PEND MANUAL` will require manual review.
- Log unresolved bets for easier troubleshooting.

### 4. Standardizing Names
- Handle variations like "J. Jackson Jr." vs "Jaren Jackson Jr." using fuzzy matching.

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
2. Ensure the scraper captures team-level scores by quarter and player-level stats.
3. Implement a result-matching script to process unresolved bets for the specified date.
4. Test the workflow with historical data to ensure flexibility and accuracy.
5. Add logging for unresolved bets and manual review cases.
