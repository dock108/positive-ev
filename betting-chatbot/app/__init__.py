import os
from flask import Flask
from flask_cors import CORS
import logging

from app.database.db import get_db, close_db
from app.routes.chat import chat_bp
from app.routes.auth import auth_bp
from app.routes.parlay import parlay_bp

def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    
    # Enable CORS
    CORS(app)
    
    # Configure app
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-for-development-only'),
        DATABASE=os.path.join(app.instance_path, 'chatbot.db'),
    )
    
    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass
    
    # Register database functions
    app.teardown_appcontext(close_db)
    
    # Register blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(parlay_bp)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint."""
        return {'status': 'ok'}
    
    return app
