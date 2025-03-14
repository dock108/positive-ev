"""
Compatibility module for Vercel API routes.
This file redirects to the index.py implementation.
"""

import os
import sys
import json
import traceback
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import the necessary modules
try:
    from src.config import setup_logging, CHROME_PROFILE, LOGS_DIR
    from src.run_pipeline import run_pipeline
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# Initialize logger
logger = setup_logging(os.path.join(LOGS_DIR, "vercel_api.log"), "vercel_api")

def handler(request, context):
    try:
        start_time = datetime.now()
        logger.info(f"Received request: {request.method} {request.url}")

        # Check Chrome profile
        if os.path.exists(CHROME_PROFILE):
            logger.info(f"Chrome profile directory exists: {CHROME_PROFILE}")
            try:
                profile_contents = os.listdir(CHROME_PROFILE)
                logger.info(f"Chrome profile contents: {profile_contents}")
            except Exception as e:
                logger.error(f"Error listing Chrome profile contents: {str(e)}")
        else:
            logger.error(f"Chrome profile directory does not exist: {CHROME_PROFILE}")
            return {
                "statusCode": 500,
                "body": json.dumps({"status": "error", "message": "Chrome profile not found"})
            }

        # Run the pipeline
        success = run_pipeline(scrape=True, grade=True, full_grade=False, setup_chrome=True)

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        # Return response
        if success:
            logger.info(f"Pipeline completed successfully in {duration:.2f} seconds")
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "success", "message": f"Pipeline completed successfully in {duration:.2f} seconds"})
            }
        else:
            logger.error(f"Pipeline failed after {duration:.2f} seconds")
            return {
                "statusCode": 500,
                "body": json.dumps({"status": "error", "message": "Pipeline execution failed"})
            }
    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "error", "message": str(e)})
        }

# Export the handler function for Vercel serverless functions
__all__ = ['handler'] 