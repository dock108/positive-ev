# This file imports and exposes api_bp from routes.py
# Using a separate file to avoid circular imports

from app.routes import api_bp

__all__ = ['api_bp'] 