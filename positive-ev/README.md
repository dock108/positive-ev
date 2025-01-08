# Positive-EV Betting Data Pipeline

Welcome to the **Positive-EV** folder within the **Mega Plan** repository! This is the foundation of our automated pipeline for analyzing positive expected value (EV) betting opportunities. The goal is to collect, store, and process betting data, including results, in a structured way to identify long-term profitable strategies.

---

## Overview

The **Positive-EV Betting Data Pipeline** automates the following:
1. **Data Collection**:
   - Scrapes positive EV opportunities from betting tools (e.g., OddsJam).
   - Captures NBA box scores and stores results for detailed analysis.
2. **Data Storage**:
   - Organizes betting opportunities and box scores in a robust SQLite database.
3. **Results Processing**:
   - Matches unresolved bets with NBA box scores to determine outcomes.
   - Flags unresolved bets as `PEND MANUAL` for further review.
4. **Future Expansion**:
   - Scales to other sports, leagues, and advanced modeling strategies.

---

## Features

### 🔍 **Betting Data Collection**
- Scrapes **positive EV bets** every 10 minutes.
- Captures data points like:
  - Timestamp
  - EV Percent
  - Event Teams
  - Bet Type
  - Win Probability
  - Sportsbook and Odds

### 🏀 **NBA Box Score Integration**
- Scrapes **daily NBA box scores** to match and resolve bets.
- Stores:
  - Player-level stats (e.g., Points, Rebounds)
  - Team-level stats, including scores by quarter.

### 🛠 **Result Matching**
- Matches unresolved bets to box scores.
- Automatically updates results to `Win`, `Loss`, or `PEND MANUAL`.

### 📊 **Scalability**
- Built with scalability in mind for:
  - Adding new sports or leagues.
  - Enhancing with predictive modeling (e.g., Random Forest, Bayesian models).

---

## Folder Structure

```plaintext
positive-ev/
│
├── README.md            # This file
├── .gitignore           # Git ignore file to exclude data
├── betting_data.db      # SQLite database storing bets and results
├── backups/             # Daily backups of the database
├── logs/                # Log files for monitoring
├── scripts/             # Core Python scripts
│   ├── scrape_ev.py     # Scrapes positive EV opportunities
│   ├── scrape_boxscores.py # Scrapes NBA box scores
│   ├── resolve_results.py  # Matches bets with results
│   └── utils.py         # Helper functions (e.g., database operations)
└── reports/             # Output reports for unresolved bets
```

---

## .gitignore Configuration

To ensure that all data files are excluded from version control, we've set up a `.gitignore` file with the following content:

```plaintext
# Ignore database files
betting_data.db

# Ignore backup files
backups/

# Ignore log files
logs/

# Ignore reports
reports/

# Ignore any other data files
*.data
```

This configuration ensures that all data files, including databases, backups, logs, and reports, are excluded from the repository. Users are expected to generate or collect their own data when using this project.

---

## Database Design

### Betting Data Table: `betting_data`
| Field            | Type    | Description                               |
|------------------|---------|-------------------------------------------|
| `id`             | INTEGER | Primary key                               |
| `bet_id`         | TEXT    | Unique identifier for the bet             |
| `timestamp`      | TEXT    | When the bet was recorded                 |
| `ev_percent`     | TEXT    | Expected Value percentage                 |
| `event_time`     | TEXT    | Scheduled time of the event               |
| `event_teams`    | TEXT    | Teams involved in the event               |
| `sport_league`   | TEXT    | Sport and league                          |
| `bet_type`       | TEXT    | Type of bet (e.g., Player Points)         |
| `description`    | TEXT    | Detailed description of the bet           |
| `odds`           | TEXT    | American odds                             |
| `sportsbook`     | TEXT    | Sportsbook offering the odds              |
| `bet_size`       | TEXT    | Suggested bet size                        |
| `win_probability`| TEXT    | Implied win probability                   |
| `result`         | TEXT    | Outcome: `Win`, `Loss`, or `PEND MANUAL`  |

### NBA Box Scores Table: `nba_box_scores`
| Field           | Type    | Description                               |
|-----------------|---------|-------------------------------------------|
| `id`            | INTEGER | Primary key                               |
| `game_date`     | TEXT    | Date of the game                          |
| `teams`         | TEXT    | Full matchup (e.g., Nuggets vs Spurs)     |
| `team`          | TEXT    | Individual team name                      |
| `player_name`   | TEXT    | Name of the player (if applicable)        |
| `stat_category` | TEXT    | Statistic category (e.g., Points)         |
| `stat_value`    | REAL    | Value of the statistic                    |

---

## Usage

### Prerequisites
1. Python 3.9+ installed.
2. Required Python libraries:
   ```bash
   pip install selenium beautifulsoup4 sqlite3 requests
   ```
3. ChromeDriver installed for Selenium scraping.

### Running Scripts
1. **Scrape Positive EV Bets**:
   ```bash
   python scripts/scrape_ev.py
   ```
2. **Scrape NBA Box Scores** (for a specific date):
   ```bash
   python scripts/scrape_boxscores.py --date YYYY-MM-DD
   ```
3. **Resolve Results**:
   ```bash
   python scripts/resolve_results.py
   ```

---

## Key Limitations
1. **Manual Review**:
   - Bets with insufficient or missing data are flagged as `PEND MANUAL`.
2. **Supported Sports**:
   - Currently focused on NBA; additional sports require scraper expansion.
3. **Scaling**:
   - Scrapers may need optimization for larger datasets.

---

## Future Roadmap

### Leveraging Betting Limits Near Game Time

An initial observation is that betting limits often increase as the event approaches, allowing bettors to place larger wagers closer to game time. This is because sportsbooks adjust their limits based on the amount of information and confidence they have in their odds, which tends to increase as more bets are placed and the event nears. [Source](https://www.actionnetwork.com/education/limits)

### Proof of Concept: AI/ML-Driven Bet Timing Alerts

To capitalize on the observation that betting limits often increase as the event approaches, the first proof of concept (POC) will focus on developing an alert system that uses AI/ML to determine optimal bet timing. The system will:

- **Analyze**:
  - Current time relative to game time.
  - Current EV of the bet.
  - Historical data on betting limits and volume.

- **Alert**:
  - Notify when it's advantageous to place a bet, considering potential increases in betting limits and EV stability or improvement as game time approaches.

This approach aims to maximize the amount that can be wagered on positive EV opportunities, especially for accounts with betting limits, by strategically timing bets to coincide with higher permissible volumes closer to game time.

### Implementing a Time-Based Value Scale

To effectively assess and act upon betting opportunities as game time approaches, we propose implementing a time-based value scale. This scale categorizes the proximity to game time into specific bands, each assigned a value from 1 to 5. The proposed bands are:

- **Value 5**: Within 20 minutes of game time
- **Value 4**: Within 40 minutes of game time
- **Value 3**: Within 120 minutes (2 hours) of game time
- **Value 2**: Within 480 minutes (8 hours) of game time
- **Value 1**: More than 480 minutes before game time

This scale allows for a structured approach to evaluating betting opportunities, considering the typical increase in betting limits as the event nears. By assigning values based on time proximity, bettors can prioritize wagers that are closer to game time, potentially taking advantage of higher limits and more accurate information.

**Note**: This time-based value scale is an initial framework and may be adjusted based on empirical data and further analysis. The goal is to create a systematic method for evaluating betting opportunities relative to game time, enhancing decision-making processes in the betting strategy.
