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
    from src.setup_chrome_profile import setup_chrome_profile
    from src.run_pipeline import run_pipeline
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
            
            # Step 1: Verify Chrome profile
            logger.info("Verifying Chrome profile")
            if not os.path.exists(CHROME_PROFILE):
                error_msg = f"Chrome profile directory does not exist: {CHROME_PROFILE}"
                logger.error(error_msg)
                logger.error("The Chrome profile must be manually copied during deployment")
                logger.error(f"Current directory contents: {os.listdir(project_root)}")
                
                response = {
                    "status": "error", 
                    "message": error_msg,
                    "project_root": project_root,
                    "directory_contents": os.listdir(project_root)
                }
                self.wfile.write(json.dumps(response).encode())
                return
                
            # Log Chrome profile contents
            logger.info(f"Chrome profile exists at: {CHROME_PROFILE}")
            try:
                profile_contents = os.listdir(CHROME_PROFILE)
                logger.info(f"Chrome profile contents: {profile_contents}")
            except Exception as e:
                logger.error(f"Error listing Chrome profile contents: {str(e)}")
                
            # Verify Chrome profile setup
            if not setup_chrome_profile():
                error_msg = "Failed to verify Chrome profile"
                logger.error(error_msg)
                response = {
                    "status": "error", 
                    "message": error_msg
                }
                self.wfile.write(json.dumps(response).encode())
                return
                
            logger.info("Chrome profile verified successfully")
            
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