from flask import Blueprint

bp = Blueprint('scraper', __name__)

from app.scraper import routes 