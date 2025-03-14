# Add project root to Python path first
import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now we can import the rest
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from src.run_pipeline import run_pipeline

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Run the pipeline
            success = run_pipeline(scrape=True, grade=True)
            
            # Set response headers
            self.send_response(200 if success else 500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Send response
            response = {
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Pipeline completed successfully" if success else "Pipeline failed"
            }
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "success": False,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
            self.wfile.write(json.dumps(response).encode()) 