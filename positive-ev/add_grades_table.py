from app import create_app, db
from app.models import BetGrade

app = create_app()

with app.app_context():
    # Create just the bet_grades table
    BetGrade.__table__.create(db.engine)
    print("Bet grades table created successfully.") 