"""
Compatibility module for Vercel API routes.
This file redirects to the vercel_handler.py implementation.
"""

# Import handler directly to make it available at the module level
from .vercel_handler import handler

# This ensures the handler is used and not flagged as unused
__all__ = ['handler'] 