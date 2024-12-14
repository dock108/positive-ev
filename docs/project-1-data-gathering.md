# **OddsJam Positive EV Data Gathering Project Plan**

---

## **Project Overview**

This project automates the collection of **Positive EV (+EV) betting data** from OddsJam's `/positive-ev` page. The system will:
1. **Log in** to OddsJam using email/password or Google authentication.
2. **Monitor the +EV table** for updates, including all betting lines (mainlines and player props).
3. **Save the data** locally in a structured format for further analysis.
4. **Automate results tracking** using game outcomes and detailed player statistics from box scores.
5. Lay the foundation for future **machine learning integrations**.

---

## **Key Challenges and Considerations**

1. **Authentication**:
   - The `/login` page supports multiple login methods, including Google.
   - If using the Google login, additional steps (e.g., handling redirects or tokens) may be required.

2. **Dynamic Content**:
   - The `/positive-ev` page content is dynamically rendered via JavaScript, so a headless browser (e.g., Selenium or Puppeteer) is required to extract data.

3. **Comprehensive Data Tracking**:
   - Mainlines (moneylines, spreads, totals) are easier to track, but player props require fetching detailed game stats (e.g., box scores).

4. **Scalability**:
   - The system needs to handle an increasing volume of betting lines and sports over time.

---

## **Goals**

1. Automate login to OddsJam (supporting email/password or Google authentication).
2. Continuously monitor and save +EV betting data.
3. Automate results tracking for mainlines and player props using box scores or detailed statistics.
4. Save structured data in a database or CSV format for further analysis.
5. Build a scalable foundation for future machine learning and analytics.

---

## **Technical Requirements**

### **Tools and Libraries**
- **Python**:
  - `selenium` for browser automation.
  - `requests` for API calls.
  - `pandas` for data parsing and storage.
  - `beautifulsoup4` for HTML parsing.
- **Sports Data API**:
  - Examples: [SportsDataIO](https://sportsdata.io), [API-FOOTBALL](https://rapidapi.com/api-sports/api/api-football).
- **Database**:
  - SQLite (initial) or PostgreSQL (for scalability).
- **ChromeDriver**: To enable Selenium to interact with the OddsJam interface.

---

## **Workflow**

### **Step 1: Automate Login**

#### **Email/Password Login**

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pickle
import time

# Set up WebDriver
driver = webdriver.Chrome()
driver.get("https://oddsjam.com/login")

# Enter credentials
email = driver.find_element(By.NAME, "email")
email.send_keys("your_email@example.com")

password = driver.find_element(By.NAME, "password")
password.send_keys("your_password")
password.send_keys(Keys.RETURN)

# Save session cookies
time.sleep(5)
with open("cookies.pkl", "wb") as file:
    pickle.dump(driver.get_cookies(), file)
```

#### **Reuse Saved Cookies**

```python
with open("cookies.pkl", "rb") as file:
    cookies = pickle.load(file)
for cookie in cookies:
    driver.add_cookie(cookie)
driver.refresh()
```

#### **Google Login (If Required)**

- **Considerations**:
  - Automating Google login can be more complex due to OAuth flows.
  - Workarounds:
    - Perform the Google login manually once and save the session cookies.
    - Use browser profiles to preserve login sessions across runs.

---

### **Step 2: Capture +EV Data**

1. **Navigate to the +EV Page**:
   - Once logged in, navigate to `https://oddsjam.com/positive-ev`.

2. **Locate the +EV Table**:
   - Use Selenium to locate the dynamically rendered odds table:

   ```python
   table = driver.find_element(By.CSS_SELECTOR, "div.table-class")  # Update selector
   ```

3. **Monitor for Changes**:
   - Compare the current table state with the previous state to detect updates:

   ```python
   old_table = None
   while True:
       current_table = table.get_attribute("outerHTML")
       if current_table != old_table:
           with open("data/latest_table.html", "w") as file:
               file.write(current_table)
           old_table = current_table
       time.sleep(10)  # Check every 10 seconds
   ```

4. **Save Data in CSV Format**:
   - Parse the saved table with `BeautifulSoup` to extract key details (event, market, line, odds, book).

   ```python
   from bs4 import BeautifulSoup
   import pandas as pd

   with open("data/latest_table.html", "r") as file:
       soup = BeautifulSoup(file.read(), "html.parser")

   rows = soup.select("tr")  # Update selector for rows
   data = []
   for row in rows:
       cells = row.find_all("td")
       data.append([cell.text.strip() for cell in cells])

   df = pd.DataFrame(data, columns=["Event", "Market", "Line", "Odds", "Book"])
   df.to_csv("data/positive_ev.csv", index=False)
   ```

---

### **Step 3: Automate Results Tracking**

1. **Fetch Game Outcomes**:

   ```python
   import requests

   API_URL = "https://api.sportsdata.io/v4/nba/scores/json/BoxScores"
   API_KEY = "your_api_key"

   def get_box_scores(date):
       response = requests.get(f"{API_URL}/{date}", headers={"Ocp-Apim-Subscription-Key": API_KEY})
       return response.json()
   ```

2. **Match Bets to Outcomes**:

   ```python
   def match_results(bets, box_scores):
       for bet in bets:
           for game in box_scores:
               if bet["event"] in game["Teams"]:
                   # Check player stats or final scores
                   bet["result"] = "Win" if some_condition else "Loss"
       return bets
   ```

3. **Save Results**:
   - Append results to the original CSV or save to a new file:

   ```python
   pd.DataFrame(bets).to_csv("results/matched_results.csv", index=False)
   ```

---

### **Step 4: Scale to All Betting Lines**

1. **Start with Mainlines**:
   - Focus on moneylines, spreads, and totals.

2. **Add Support for Player Props**:
   - Use box scores to validate bets on player stats (e.g., points, rebounds, assists).

3. **Handle Edge Cases**:
   - Bets voided due to player scratches or game cancellations.

---

## **Limitations**

1. **Authentication**:
   - Automating Google login is challenging; using saved cookies is recommended.

2. **Data Availability**:
   - Accurate results for player props depend on the quality of box score data from the API.

3. **Scalability**:
   - High-frequency updates may require database integration instead of CSV files.

---

## **Next Steps**

1. Implement and validate data collection from the `/positive-ev` page.  
2. Automate results tracking using API data for mainlines and player props.  
3. Expand to additional sports or betting markets as needed.

---

## **The Big Picture**

This project automates the data collection and results tracking workflow for +EV betting. It sets the foundation for advanced analytics, modeling, and scaling across betting markets.
