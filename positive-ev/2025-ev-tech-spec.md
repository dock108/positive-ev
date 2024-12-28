# **Technical Specifications: Phase 1 - Web Scraping and Data Automation**

---

## **1. Overview**

This document outlines the technical details for automating data collection by periodically scraping web pages (e.g., OddsJam's Positive EV page) using Selenium and storing the results. Additionally, the system will fetch game results through APIs or web scraping, focusing on one sport (e.g., basketball or soccer) to refine the workflow during the MVP phase.

---

## **2. Functional Components**

### **2.1 Data Sources**
- **Odds Data**:
  - Scrape pages displaying +EV betting opportunities, including markets like moneylines, spreads, totals, and player props.
  - Extract relevant odds and metadata.
- **Game Results**:
  - Retrieve results via APIs (e.g., SportsDataIO, API-Football) or web scraping box scores from sports websites.

### **2.2 Data Collection**
- **Frequency**: Scrape odds every 1-5 minutes, depending on market activity.
- **Key Data Points**:
  - Game/Event Details: Teams, players, start time, market type.
  - Odds: Values for each market and sportsbook.
  - Timestamps: To track line movements and stale data.

---

## **3. Architecture Design**

### **3.1 Workflow**

1. **Odds Data Scraping**:
   - Use Selenium to load and capture the webpage.
   - Extract odds and relevant metadata into structured formats (e.g., JSON or CSV).
2. **Results Retrieval**:
   - Use APIs or scrape box scores for corresponding game outcomes.
   - Match scraped odds to game results for validation and analysis.
3. **Storage**:
   - Save data in SQLite or CSV for initial storage.
   - Include metadata for easy filtering and analysis.

---

## **4. Technical Implementation**

### **4.1 Odds Data Scraping with Selenium**

#### **Key Libraries**
- `selenium`: Automates browser interactions.
- `beautifulsoup4`: Parses HTML for data extraction.
- `pandas`: Stores and manipulates scraped data.
- `logging`: Tracks script execution and errors.

#### **Sample Code: Scrape +EV Odds**
REPLACEWITHTRIPLETICKpython
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging

# Set up logging
logging.basicConfig(filename="scraping.log", level=logging.INFO)

# Configure Selenium
driver = webdriver.Chrome()

# Open OddsJam +EV page
url = "https://oddsjam.com/positive-ev"
driver.get(url)
time.sleep(5)  # Allow page to load

# Extract odds table
page_source = driver.page_source
soup = BeautifulSoup(page_source, "html.parser")

# Parse table
def parse_odds_table(soup):
    rows = soup.select("tr")  # Update selector based on page structure
    data = []
    for row in rows:
        cells = row.find_all("td")
        if cells:
            data.append([cell.text.strip() for cell in cells])
    return pd.DataFrame(data, columns=["Event", "Market", "Odds", "Sportsbook", "Timestamp"])

# Save to CSV
odds_data = parse_odds_table(soup)
odds_data.to_csv("data/odds_data.csv", mode="a", index=False, header=False)

# Close browser
driver.quit()
REPLACEWITHTRIPLETICK

---

### **4.2 Results Retrieval**

#### **Option 1: API Integration**
- Use sports APIs to fetch game results (e.g., API-Football for soccer, SportsDataIO for basketball).
- Match scraped odds to API results using event details (e.g., team names, start time).

**Example API Workflow**:
REPLACEWITHTRIPLETICKpython
import requests

def fetch_game_results(api_url, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch results: {response.status_code}")
        return None

# Example usage
api_url = "https://api.sportsdata.io/v4/soccer/scores/json/GamesByDate/2024-12-13"
api_key = "YOUR_API_KEY"
results = fetch_game_results(api_url, api_key)
REPLACEWITHTRIPLETICK

#### **Option 2: Web Scraping Box Scores**
- Scrape sports websites for game results, focusing on:
  - Team stats and player props.
  - Final scores for mainline bets.

**Example Box Score Scraping**:
REPLACEWITHTRIPLETICKpython
def scrape_box_scores(url):
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    # Update selector logic based on page structure
    scores = soup.select("div.box-score")
    return [{"team": score.find("team-name").text, "score": score.find("score").text} for score in scores]
REPLACEWITHTRIPLETICK

---

### **4.3 Database Design**

#### **Odds Table**
- `event_id`: Unique identifier for the game/event.
- `team_1`: First team/player.
- `team_2`: Second team/player.
- `market`: Market type (e.g., moneyline, spread, prop).
- `odds`: Numeric odds value.
- `timestamp`: Time of scraping.

#### **Results Table**
- `event_id`: Matches the odds table.
- `team_1_score`: Final score for the first team.
- `team_2_score`: Final score for the second team.
- `player_stats`: JSON or structured data for player props.
- `result_time`: Time of result recording.

---

## **5. Data Validation**

### **5.1 Validation Rules**
1. **Completeness**:
   - Ensure key fields (e.g., event_id, odds, timestamp) are populated.
2. **Consistency**:
   - Verify that scraped odds align with known market types.
3. **Staleness**:
   - Remove odds entries older than 12 hours if they haven’t been validated.

#### **Validation Script**
REPLACEWITHTRIPLETICKpython
def validate_data(df):
    valid_data = df.dropna(subset=["event_id", "odds", "timestamp"])
    fresh_data = valid_data[valid_data["timestamp"] > time.time() - 43200]  # Last 12 hours
    return fresh_data
REPLACEWITHTRIPLETICK

---

## **6. Monitoring and Maintenance**

1. **Error Logging**:
   - Log failed scrapes, invalid data, and API errors for review.
2. **Performance Tracking**:
   - Monitor script runtime and data quality metrics (e.g., completeness rate).
3. **Alerting**:
   - Notify for critical failures, such as webpage structure changes.

---

## **7. Success Metrics**

1. **Data Collection**:
   - Successfully scrape and store odds for at least 5,000 events during MVP.
2. **Data Accuracy**:
   - Achieve at least 95% accuracy in matching odds to game results.
3. **System Uptime**:
   - Ensure 99% uptime for scraping and data retrieval processes.

---

## **8. Scalability Considerations**

1. **Expand Scope**:
   - Add additional sports or markets as scraping logic matures.
2. **Database Migration**:
   - Transition from SQLite to a more scalable solution (e.g., PostgreSQL).
3. **Real-Time Updates**:
   - Implement WebSocket scraping for near-instant data updates.

---

This approach ensures a robust, scalable pipeline for odds scraping and results retrieval while maintaining flexibility for future expansions. Let me know if you'd like to refine or expand any specific sections!
