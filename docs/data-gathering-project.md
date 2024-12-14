Here’s a complete, GitHub-ready Project Plan for automating data capture from OddsJam, tailored to handle login requirements and dynamic page changes:

# **OddsJam Data Capture Automation**

---

## **Project Overview**

This project aims to automate the collection of arbitrage betting data from OddsJam. The system will:
1. **Log in** to OddsJam and navigate to the Arbitrage Betting page.
2. **Monitor the odds table** for changes and save updated data to a local file.
3. Enable further **parsing and analysis** of the collected data for modeling and decision-making.

---

## **Goals**

1. Automate the login process to access the odds data.  
2. Monitor and capture real-time changes in the arbitrage table.  
3. Save table data in a structured format (CSV or JSON) for further use.  
4. Lay the foundation for future integration with machine learning models.

---

## **Technical Requirements**

### **Tools and Libraries**
- **Python**: For scripting and automation.
  - `selenium` for browser automation.
  - `pickle` for managing cookies.
  - `pandas` for data parsing and storage.
- **ChromeDriver**: To interact with Chrome.
- **Git**: For version control.

---

## **Project Workflow**

### **Step 1: Environment Setup**

1. **Install Dependencies**  
   - Install Python packages:
     ```bash
     pip install selenium pandas
     ```
   - Download and install ChromeDriver (compatible with your Chrome version):
     [ChromeDriver Download](https://chromedriver.chromium.org/downloads).

2. **Project Structure**
   - Set up a folder structure:
     ```
     oddsjam-data-capture/
     ├── main.py            # Main script
     ├── credentials.json   # Stores login credentials
     ├── cookies.pkl        # Cookies file for session persistence
     ├── data/              # Directory for saved data files
     ├── requirements.txt   # List of dependencies
     └── README.md          # Documentation
     ```

---

### **Step 2: Automate Login**

1. **Save Login Credentials**
   - Create a `credentials.json` file:
     ```json
     {
       "email": "your_email@example.com",
       "password": "your_password"
     }
     ```

2. **Write the Login Script**
   - Automate login using Selenium:
     ```python
     from selenium import webdriver
     from selenium.webdriver.common.by import By
     from selenium.webdriver.common.keys import Keys
     import json
     import pickle

     # Load credentials
     with open("credentials.json", "r") as file:
         credentials = json.load(file)

     # Set up Selenium WebDriver
     driver = webdriver.Chrome()
     driver.get("https://oddsjam.com/login")

     # Log in to OddsJam
     email_field = driver.find_element(By.NAME, "email")
     email_field.send_keys(credentials["email"])

     password_field = driver.find_element(By.NAME, "password")
     password_field.send_keys(credentials["password"])
     password_field.send_keys(Keys.RETURN)

     # Save cookies for session persistence
     with open("cookies.pkl", "wb") as file:
         pickle.dump(driver.get_cookies(), file)
     ```

---

### **Step 3: Navigate and Capture Data**

1. **Reuse Cookies for Subsequent Logins**
   - Load cookies to bypass repeated logins:
     ```python
     # Load cookies
     with open("cookies.pkl", "rb") as file:
         cookies = pickle.load(file)

     driver.get("https://oddsjam.com/betting-tools/arbitrage")
     for cookie in cookies:
         driver.add_cookie(cookie)
     driver.refresh()
     ```

2. **Monitor and Save Table Changes**
   - Continuously check for updates in the odds table:
     ```python
     import time

     old_table = None
     while True:
         table = driver.find_element(By.CSS_SELECTOR, "div.table-class")  # Update selector
         current_table = table.get_attribute("outerHTML")

         if current_table != old_table:  # Detect changes
             with open("data/latest_table.html", "w") as file:
                 file.write(current_table)  # Save updated table locally
             old_table = current_table

         time.sleep(5)  # Check every 5 seconds
     ```

---

### **Step 4: Parse and Store Data**

1. **Extract Relevant Fields**
   - Use Python to parse the saved table and extract key details:
     ```python
     from bs4 import BeautifulSoup
     import pandas as pd

     # Load saved table
     with open("data/latest_table.html", "r") as file:
         html_content = file.read()

     # Parse with BeautifulSoup
     soup = BeautifulSoup(html_content, "html.parser")
     rows = soup.select("tr")  # Update selector for table rows

     # Extract data
     data = []
     for row in rows:
         cells = row.find_all("td")
         data.append([cell.text.strip() for cell in cells])

     # Save to CSV
     df = pd.DataFrame(data, columns=["Column1", "Column2", "Column3"])  # Update column names
     df.to_csv("data/latest_table.csv", index=False)
     ```

---

### **Step 5: Validation and Testing**

1. **Test the Script**
   - Run the script during active betting hours to ensure it:
     - Logs in successfully.
     - Detects table changes in real time.
     - Saves complete and accurate data.

2. **Debug Issues**
   - Check for stale cookies, incorrect selectors, or session timeouts.

---

## **Next Steps**

1. **Improve Automation**
   - Optimize table monitoring by reducing redundant saves.
   - Add error handling for network or selector issues.

2. **Integrate with Machine Learning**
   - Use the collected data to train models for ranking +EV opportunities.

3. **Build Real-Time Alerts**
   - Notify via email or messaging apps (e.g., Discord) when new opportunities arise.

---

## **The Big Picture**

This project automates data collection from OddsJam, enabling consistent and accurate tracking of arbitrage opportunities. By capturing dynamic changes and storing structured data, it provides a foundation for advanced analysis and modeling.

---

## **How to Run the Project**

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/oddsjam-data-capture.git
```
	2.	Install dependencies:
```bash
pip install -r requirements.txt
```

	3.	Run the script:
```bash
python main.py
```
