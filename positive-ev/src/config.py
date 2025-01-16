from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import os
import logging

# Set up logging
if not os.path.exists("logs"):
    os.makedirs("logs")
logging.basicConfig(
    filename="logs/login.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

try:
    # Set up Chrome options with a dedicated user profile
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-data-dir={os.path.expanduser('~/Library/Application Support/Google/Chrome/ScraperProfile')}")  # Save profile

    # Initialize WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Navigate to the OddsJam login page
    login_url = "https://oddsjam.com/login"
    driver.get(login_url)
    logging.info("Navigated to OddsJam login page.")

    # Enter email
    email_input = WebDriverWait(driver, 10).until(
        lambda d: d.find_element(By.XPATH, "//input[@type='email']")
    )
    email_input.send_keys("mike.fuscoletti@gmail.com")  # Replace with your email
    email_input.send_keys(Keys.RETURN)
    logging.info("Entered email and submitted.")

    # Prompt user to finish entering the code manually
    print("Enter the verification code manually in the browser and complete the login process.")
    input("Once you're logged in, type 'y' and hit Enter to continue: ")  # Wait for user confirmation

    # Save a screenshot for verification
    driver.save_screenshot("logs/login_success.png")
    logging.info("Login complete. Profile saved for future use.")

except Exception as e:
    logging.error(f"An error occurred during login: {e}", exc_info=True)
    if 'driver' in locals():
        driver.save_screenshot("logs/login_error.png")
finally:
    if 'driver' in locals():
        driver.quit()
    logging.info("Browser closed.")
