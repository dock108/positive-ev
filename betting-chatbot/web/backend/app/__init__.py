import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Set secret key for JWT
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-for-development-only')
    
    # Import and register blueprints
    # Import directly from routes.py, not from the routes package
    from app.routes import api_bp  # This is importing from routes.py
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register admin blueprint
    from app.admin import admin_bp
    app.register_blueprint(admin_bp)
    
    return app 