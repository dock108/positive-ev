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

This Proof of Concept (POC) builds on initial exploratory evidence gathered by analyzing bets placed over the last 30 days. The analysis revealed a strong correlation between bet amounts and proximity to game time. Specifically, sportsbooks appeared to allow larger wager amounts closer to the start of the game, likely due to increased betting volume and confidence in their odds.

The POC will focus on leveraging this observation to enhance betting strategies by developing an alert system that uses AI/ML to determine optimal bet timing. The system will:

- **Analyze**:
  - Current time relative to game time.
  - Current EV of the bet.
  - Historical data on betting limits and volume trends.

- **Alert**:
  - Notify when it’s most advantageous to place a bet, factoring in potential increases in betting limits and the stability or improvement of EV as game time approaches.

By strategically timing bets, the system aims to optimize the amount wagered on positive EV opportunities, maximizing profitability while accounting for potential limitations from sportsbooks.

### Implementing a Time-Based Value Scale

To effectively assess and act upon betting opportunities as game time approaches, a time-based value scale will be implemented. This scale categorizes the proximity to game time into specific bands, each assigned a value from 1 to 5. The proposed bands are:

- **Value 5**: Within 20 minutes of game time
- **Value 4**: Within 40 minutes of game time
- **Value 3**: Within 120 minutes (2 hours) of game time
- **Value 2**: Within 480 minutes (8 hours) of game time
- **Value 1**: More than 480 minutes before game time

This structured scale prioritizes bets as game time approaches, enabling bettors to capitalize on higher limits and more stable EV opportunities. Additionally, the time-based value scale provides a systematic approach to evaluating and ranking betting opportunities, aligning with the broader goal of long-term profitability.

**Note**: This initial framework may be refined with further empirical data and machine learning models. The goal is to systematically exploit patterns in sportsbook behavior to maximize betting efficiency and returns.

### Daily Strategy: Prioritizing Exchange Withdrawals and Manual Arbitrage for Cash Flow

To maintain account longevity, sustain profitability, and enable larger bets on +EV opportunities, a strategic approach to withdrawals and manual arbitrage is essential. By combining disciplined withdrawal habits with the manual effort of arbitrage betting, bettors can achieve a more stable cash flow while avoiding unnecessary limitations from sportsbooks.

---

### Why This Matters:
- **Sportsbook Monitoring**: Frequent or large withdrawals from major sportsbooks like **DraftKings** or **FanDuel** can raise red flags and result in account restrictions.
- **Guaranteed Cash Flow**: Manual arbitrage betting ensures consistent profitability by locking in guaranteed returns across multiple books, enabling a reliable source of funds for further +EV bets.
- **Exchanges Are Safer**: Betting exchanges are less likely to impose restrictions, making them ideal for withdrawals and larger transactions.

---

### Key Guidelines:

#### **1. Focus on Scaling and Sustaining Accounts:**
- Prioritize keeping funds in major sportsbooks like **DraftKings** and **FanDuel** to maintain their viability for high-limit bets.
- Use these accounts to maximize opportunities for +EV betting without drawing attention to withdrawal behavior.

#### **2. Use Exchanges for Withdrawals:**
- Withdraw profits primarily from betting exchanges, where restrictions are less likely.
- Reinvest these funds into other sportsbooks or accounts to maintain flexibility and liquidity.

#### **3. Leverage Manual Arbitrage for Guaranteed Cash Flow:**
- **Why Arbitrage?**
  - Arbitrage (arb) betting locks in guaranteed profits by exploiting price discrepancies between sportsbooks and exchanges.
  - While not as scalable as +EV betting, arbitrage can provide consistent cash flow to fund more significant opportunities.
- **Challenges of Arbitrage:**
  - Requires **patience** and **manual timing effort** to find and execute profitable opportunities.
  - Involves quick decisions and simultaneous bets across multiple books.
- **Benefit of Arbitrage:**
  - Provides a steady, risk-free income stream that enables you to bet more aggressively on +EV opportunities.

#### **4. Spread Action Across Accounts:**
- Avoid concentrating large betting or withdrawal activity in a single sportsbook account.
- Diversify betting activity across multiple sportsbooks to reduce the risk of account limitations.

#### **5. Balance Between Arbitrage and +EV Bets:**
- Allocate time and effort strategically between guaranteed arbitrage profits and long-term +EV betting strategies.
- Arbitrage provides the cash flow foundation, while +EV bets generate larger potential profits over time.

---

### Managing Manual Effort:
1. **Tools for Timing:**
   - Use alerts and tracking systems to identify arbitrage opportunities efficiently.
   - Maintain a detailed log of arb bets to track profits and time investment.

2. **Patience is Key:**
   - Manual arbitrage betting requires discipline and focus but can yield consistent returns.
   - Commit to a dedicated schedule for spotting and executing arb bets, even when the process feels tedious.

3. **Scaling with Cash Flow:**
   - By generating steady cash flow from manual arbitrage, you can reinvest profits into higher-limit +EV opportunities.
   - This approach creates a feedback loop that amplifies overall profitability while managing risks.

---

### Conclusion:
Balancing the manual effort of arbitrage with disciplined withdrawal habits is critical for long-term success. While manual arbitrage requires patience and timing, it ensures consistent cash flow, allowing for more aggressive +EV betting. Prioritizing exchanges for withdrawals further protects sportsbook accounts, enabling sustainable scaling and profitability over time.