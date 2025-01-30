import os
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Ensure logs directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Set up logging
logging.basicConfig(
    filename="logs/debug.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def setup_driver():
    """Initialize ChromeDriver with debugging options."""
    try:
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--remote-debugging-port=9222")

        # Try using a saved profile (comment out if it causes crashes)
        profile_path = os.path.expanduser("~/Library/Application Support/Google/Chrome/ScraperProfile")
        options.add_argument(f"user-data-dir={profile_path}")

        # Set ChromeDriver logging
        service = Service(ChromeDriverManager().install())
        service.log_path = "logs/chromedriver.log"
        service.start()

        driver = webdriver.Chrome(service=service, options=options)
        logging.info("ChromeDriver initialized successfully.")
        return driver

    except Exception as e:
        logging.error(f"Failed to initialize ChromeDriver: {e}", exc_info=True)
        raise

def check_driver_crash(driver):
    """Check if ChromeDriver process is running."""
    try:
        driver.execute_script("return navigator.userAgent;")
        logging.info("ChromeDriver is running fine.")
    except Exception as e:
        logging.critical("ChromeDriver seems to have crashed!", exc_info=True)
        driver.save_screenshot("logs/chrome_crash.png")
        raise

def login_to_oddsjam(driver):
    """Automate login to OddsJam with debugging."""
    try:
        login_url = "https://oddsjam.com/login"
        driver.get(login_url)
        logging.info(f"Navigated to {login_url}")

        # Check if login page loaded
        time.sleep(2)
        check_driver_crash(driver)

        # Take a screenshot before attempting login
        driver.save_screenshot("logs/login_page.png")

        # Enter email
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
        )
        email_input.send_keys("mike.fuscoletti@gmail.com")
        email_input.send_keys(Keys.RETURN)
        logging.info("Entered email and submitted.")

        # Check if the page transitioned to the verification step
        time.sleep(2)
        check_driver_crash(driver)

        # Prompt user to manually enter verification code
        print("Enter the verification code manually in the browser and complete the login process.")
        input("Once you're logged in, type 'y' and hit Enter to continue: ")

        # Final verification
        driver.save_screenshot("logs/login_success.png")
        logging.info("Login successful. Profile saved.")

    except Exception as e:
        logging.error(f"Login failed: {e}", exc_info=True)
        driver.save_screenshot("logs/login_error.png")
        raise

if __name__ == "__main__":
    driver = None
    try:
        driver = setup_driver()
        login_to_oddsjam(driver)

    except Exception as e:
        logging.critical(f"Fatal script error: {e}", exc_info=True)

    finally:
        if driver:
            driver.quit()
            logging.info("ChromeDriver closed.")
