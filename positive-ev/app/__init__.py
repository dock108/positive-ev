# Empty file to make the directory a Python package 

from flask import Flask
from flask_caching import Cache
from app.config import BaseConfig
from app.db_utils import init_db

# Initialize extensions
cache = Cache()

def create_app(config_class=BaseConfig):
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions
    cache.init_app(app)

    with app.app_context():
        # Initialize database tables if they don't exist
        init_db()

        # Register blueprints
        from app.main import bp as main_bp
        app.register_blueprint(main_bp)

        from app.scraper import bp as scraper_bp
        app.register_blueprint(scraper_bp)
        
        from app.admin import bp as admin_bp
        app.register_blueprint(admin_bp)

        # Register error handlers
        @app.errorhandler(404)
        def not_found_error(error):
            return {'error': 'Resource not found'}, 404

        @app.errorhandler(500)
        def internal_error(error):
            return {'error': 'Internal server error'}, 500

    return app

# Import models to ensure they are registered with SQLAlchemy
# from app import models  # noqa: E402 