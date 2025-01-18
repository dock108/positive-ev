from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
import logging
import time

# Set up logging
if not os.path.exists("logs"):
    os.makedirs("logs")
logging.basicConfig(
    filename="logs/analysis.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def fetch_oddsjam_page():
    """
    Fetch and save the OddsJam Positive EV page for analysis.
    """
    try:
        # Set up Chrome options with the saved profile
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"user-data-dir={os.path.expanduser('~/Library/Application Support/Google/Chrome/ScraperProfile')}")  # Use the saved profile

        # Initialize WebDriver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # Navigate to OddsJam Positive EV page
        url = "https://oddsjam.com/betting-tools/positive-ev"
        driver.get(url)
        logging.info("Navigated to OddsJam Positive EV page.")

        # Wait for 10 seconds to ensure the page fully loads
        logging.info("Waiting for 10 seconds to allow the page to fully load...")
        time.sleep(10)

        # Save the page source for analysis
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "oddsjam_positive_ev.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logging.info(f"Page source saved to {output_file}")

        # Save a screenshot for debugging
        screenshot_file = os.path.join("logs", "analysis_page_screenshot.png")
        driver.save_screenshot(screenshot_file)
        logging.info(f"Screenshot saved to {screenshot_file}")

    except Exception as e:
        logging.error(f"An error occurred while fetching the OddsJam page: {e}", exc_info=True)
        if 'driver' in locals():
            driver.save_screenshot("logs/analysis_error_screenshot.png")  # Capture screenshot for debugging
    finally:
        if 'driver' in locals():
            driver.quit()
        logging.info("Browser closed.")

if __name__ == "__main__":
    fetch_oddsjam_page()
