#!/usr/bin/env python3
"""
Pipeline script to run the entire betting data workflow:
1. Scrape new betting data
2. Calculate grades for new bets

This script can be scheduled to run periodically to keep the database updated.
"""

import os
import sys
import traceback
from datetime import datetime
import json

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import from new consolidated modules
try:
    # Try relative imports (when used as a module)
    from .config import setup_logging
    from .scraper import main as run_scraper
    from .grade_calculator import main as run_grade_calculator
except ImportError:
    # Fall back to absolute imports (when run directly)
    from src.config import setup_logging
    from src.scraper import main as run_scraper
    from src.grade_calculator import main as run_grade_calculator

# Initialize logger
logger = setup_logging(os.path.join(project_root, "logs", "pipeline.log"), "pipeline")

def run_pipeline(scrape=True, grade=True, full_grade=False, setup_chrome=False):
    """
    Run the complete data pipeline.
    
    Args:
        scrape: Whether to run the scraper
        grade: Whether to run the grade calculator
        full_grade: Whether to run the grade calculator in full mode
        setup_chrome: Whether to set up Chrome profile before running (for direct execution)
    """
    start_time = datetime.now()
    logger.info("Starting betting data pipeline")
    
    try:
        # Step 0: Set up Chrome profile if requested (when run directly)
        if setup_chrome and scrape:
            logger.info("Setting up Chrome profile")
            try:
                from src.setup_chrome_profile import setup_chrome_profile
                from src.config import CHROME_PROFILE
                
                logger.info(f"Using Chrome profile at: {CHROME_PROFILE}")
                
                if os.path.exists(CHROME_PROFILE):
                    logger.info(f"Chrome profile directory exists: {CHROME_PROFILE}")
                    try:
                        profile_contents = os.listdir(CHROME_PROFILE)
                        logger.info(f"Chrome profile contents: {profile_contents}")
                    except Exception as e:
                        logger.error(f"Error listing Chrome profile contents: {str(e)}")
                else:
                    logger.error(f"Chrome profile directory does not exist: {CHROME_PROFILE}")
                    logger.error("The Chrome profile must be manually copied during deployment")
                    return False
                
                if setup_chrome_profile():
                    logger.info("Successfully verified Chrome profile")
                else:
                    logger.error("Failed to verify Chrome profile")
                    return False
            except ImportError as e:
                logger.error(f"Error importing Chrome profile setup modules: {e}")
                return False
        
        # Step 1: Run the scraper to get new betting data
        if scrape:
            logger.info("Step 1: Running scraper to collect new betting data")
            scraper_start = datetime.now()
            run_scraper()
            scraper_duration = (datetime.now() - scraper_start).total_seconds()
            logger.info(f"Scraper completed in {scraper_duration:.2f} seconds")
        else:
            logger.info("Skipping scraper step")
        
        # Step 2: Run the grade calculator to grade new bets
        if grade:
            logger.info("Step 2: Running grade calculator")
            
            # Set full mode argument if requested
            original_argv = sys.argv.copy()
            if full_grade:
                logger.info("Running grade calculator in FULL mode")
                sys.argv = [sys.argv[0], "--full"]
            else:
                # Reset sys.argv to avoid passing any arguments
                sys.argv = [sys.argv[0]]
                
            grade_start = datetime.now()
            run_grade_calculator()
            grade_duration = (datetime.now() - grade_start).total_seconds()
            logger.info(f"Grade calculator completed in {grade_duration:.2f} seconds")
            
            # Restore original argv
            sys.argv = original_argv
        else:
            logger.info("Skipping grade calculator step")
        
        # Pipeline completed successfully
        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Pipeline completed successfully in {total_duration:.2f} seconds")
        return True
        
    except Exception as e:
        logger.error(f"Error in pipeline: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Parse command line arguments and run the pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the betting data pipeline")
    parser.add_argument("--no-scrape", action="store_true", help="Skip the scraper step")
    parser.add_argument("--no-grade", action="store_true", help="Skip the grade calculator step")
    parser.add_argument("--full-grade", action="store_true", help="Run grade calculator in full mode")
    parser.add_argument("--setup-chrome", action="store_true", help="Set up Chrome profile before running")
    
    args = parser.parse_args()
    
    # Run the pipeline with the specified options
    success = run_pipeline(
        scrape=not args.no_scrape,
        grade=not args.no_grade,
        full_grade=args.full_grade,
        setup_chrome=args.setup_chrome
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

# For Vercel serverless function
def handler(event, context):
    """Handler for serverless function execution."""
    try:
        # Run the pipeline
        success = run_pipeline(scrape=True, grade=True, full_grade=False, setup_chrome=True)
        
        # Return response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success" if success else "error",
                "message": "Pipeline completed successfully" if success else "Pipeline failed"
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "message": str(e)
            })
        }

if __name__ == "__main__":
    main() 