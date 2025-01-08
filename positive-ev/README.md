# Positive-EV Betting Data Pipeline: Mega Plan

Welcome to the **Positive-EV** folder within the **Mega Plan** repository! This initiative is designed to help build a sustainable, data-driven betting strategy. The ultimate goal? **Quit your day job** by leveraging disciplined betting techniques, maximizing +EV opportunities, and strategically managing limited sportsbook accounts (in bet amount, not the number of accounts).

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

## Key Concepts: Quit Your Day Job Plan

This project focuses on overcoming the challenges of sportsbook-imposed bet amount limits by strategically timing bets and leveraging pre-game volume boosts to place larger stakes. Key guidelines include:

1. **Bet Timing and Limits**:
   - **Initial Hypothesis**: Betting limits increase closer to game time, enabling larger wagers on +EV opportunities.
   - Strategic timing can take advantage of sportsbooks’ higher limits near game time due to increased betting volume and confidence in their odds.

2. **Value Scale**:
   A bell curve value scale prioritizes bets closer to game time:
   | Minutes to Event Range | Value |
   |-------------------------|-------|
   | **20–40 minutes**       | 5     |
   | **40–120 minutes**      | 4     |
   | **0–20 minutes**        | 3     |
   | **120–480 minutes**     | 2     |
   | **480+ minutes**        | 1     |

3. **Manual Arbitrage**:
   - While not scalable, manual arbitrage provides consistent, risk-free cash flow, allowing for more aggressive +EV bets over time.

4. **Diversify Accounts**:
   - Avoid concentrating activity in a single sportsbook. Spread action across multiple accounts to mitigate risk and maximize opportunities.

5. **Sustainable Withdrawals**:
   - Withdraw primarily from betting exchanges to preserve major accounts like **DraftKings** and **FanDuel** for larger +EV opportunities.

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

## Supporting Documentation

For initial project goals and exploratory data analysis, refer to:
- ```[initial_eda.md](./docs/initial_eda.md)```: Supporting data and results.

---

## Folder Structure

```plaintext
positive-ev/
│
├── README.md            # Project overview and details
├── initial_eda.md       # Initial exploratory data analysis details
├── .gitignore           # Exclude sensitive or unnecessary files from version control
│
├── data/                # Stores input data files (excluded by .gitignore)
│   ├── oddsjam-bet-tracker.csv   # Example data file
│   └── other-data-files.csv      # Placeholder for additional data files
│
├── backups/             # Backup SQLite databases (excluded by .gitignore)
│   ├── betting_data_MMDDYY.db    # Daily backups
│   └── …                         # Older backups for archival purposes
│
├── logs/                # Log files for monitoring and debugging (excluded by .gitignore)
│   ├── scraping.log             # Log file for the scraper
│   └── …                        # Additional logs as needed
│
├── src/                 # Source code for the project
│   ├── scraper.py              # Core script for scraping positive EV opportunities
│   ├── bet_results_eda.py      # EDA script for bet results analysis
│   ├── resolve_results.py      # Match bets with outcomes and update results
│   ├── scrape_boxscores.py     # Scraper for NBA box scores
│   └── utils.py                # Helper functions (e.g., database operations)
│
└── reports/             # Generated reports for analysis
    ├── unresolved_bets.md     # Report on unresolved bets requiring manual review
    └── other_reports.md       # Placeholder for additional reports
```

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

## Next Steps

1. **Model Development**:
   - Build predictive models incorporating timing and EV patterns.
2. **Integration**:
   - Expand to new sports and implement ML-driven bet timing alerts.
3. **Refinements**:
   - Fine-tune scraping efficiency and add visualization dashboards.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.
