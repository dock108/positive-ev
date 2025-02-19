import os
import sys
import logging
from datetime import datetime

# Add the app directory to the Python path
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(app_dir))

from app.scripts.grade_calculator import calculate_grades
from app.config import BaseConfig

def setup_logging():
    """Configure logging for the grade calculator."""
    log_file = os.path.join(BaseConfig.LOGS_DIR, 'grade_calculator.log')
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)

def main():
    """Main function to run the grade calculator."""
    setup_logging()
    
    try:
        logging.info("Starting grade calculator job")
        start_time = datetime.now()
        
        calculate_grades()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logging.info(f"Grade calculator job completed successfully in {duration:.2f} seconds")
        
    except Exception as e:
        logging.error(f"Error running grade calculator: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 