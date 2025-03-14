from http.server import BaseHTTPRequestHandler
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
    from src.config import setup_logging, CHROME_PROFILE, IS_VERCEL
    from src.run_pipeline import run_pipeline
    # Import the new Vercel-specific Chrome profile setup
    from api.setup_chrome_profile_vercel import download_and_setup_chrome_profile
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# Initialize logger
logger = setup_logging(os.path.join(project_root, "logs", "vercel_api.log"), "vercel_api")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests to run the pipeline."""
        start_time = datetime.now()
        
        # Set response headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {"status": "processing", "message": "Pipeline started"}
        
        try:
            logger.info("API endpoint triggered - starting pipeline")
            logger.info(f"Using Chrome profile at: {CHROME_PROFILE}")
            logger.info(f"Running on Vercel: {IS_VERCEL}")
            
            # Step 1: Set up Chrome profile using the new method
            logger.info("Setting up Chrome profile")
            if not download_and_setup_chrome_profile():
                error_msg = "Failed to set up Chrome profile"
                logger.error(error_msg)
                response = {
                    "status": "error", 
                    "message": error_msg
                }
                self.wfile.write(json.dumps(response).encode())
                return
                
            logger.info("Chrome profile set up successfully")
            
            # Step 2: Run the pipeline
            logger.info("Running pipeline (scrape + grade)")
            success = run_pipeline(scrape=True, grade=True, full_grade=False, setup_chrome=False)
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            response["duration"] = f"{duration:.2f} seconds"
            response["status"] = "success" if success else "error"
            response["message"] = "Pipeline completed successfully" if success else "Pipeline failed"
            logger.info(f"Pipeline completed in {duration:.2f} seconds with status: {response['status']}")
            
        except Exception as e:
            logger.error(f"Error running pipeline: {str(e)}")
            logger.error(traceback.format_exc())
            response = {
                "status": "error", 
                "message": str(e),
                "traceback": traceback.format_exc()
            }
        
        # Send response
        self.wfile.write(json.dumps(response).encode())
        return 