#!/bin/bash

# Create necessary directories if they don't exist
mkdir -p web/backend/app

# Start the backend
echo "Starting Flask backend on port 8080..."
cd web/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Check if app/__init__.py exists, if not create it
if [ ! -f "app/__init__.py" ]; then
  echo "Creating app/__init__.py..."
  mkdir -p app
  cat > app/__init__.py << 'EOF'
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app
EOF
fi

# Check if app/routes.py exists, if not create it
if [ ! -f "app/routes.py" ]; then
  echo "Creating app/routes.py..."
  cat > app/routes.py << 'EOF'
from flask import Blueprint, jsonify, request

api_bp = Blueprint('api', __name__)

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "API is running"})

@api_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    # In a real app, you would validate credentials here
    return jsonify({
        "user": {
            "id": 1,
            "email": data.get('email', 'test@example.com'),
            "plan": "free",
            "createdAt": "2023-01-01T00:00:00Z",
            "stats": {
                "totalChats": 5,
                "totalMessages": 25,
                "parlayCalculations": 3
            }
        },
        "token": "test-token-12345"
    })

@api_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    # In a real app, you would create a new user here
    return jsonify({
        "user": {
            "id": 1,
            "email": data.get('email', 'test@example.com'),
            "plan": "free",
            "createdAt": "2023-01-01T00:00:00Z",
            "stats": {
                "totalChats": 0,
                "totalMessages": 0,
                "parlayCalculations": 0
            }
        },
        "token": "test-token-12345"
    })

@api_bp.route('/chat/send', methods=['POST'])
def send_message():
    data = request.get_json()
    # In a real app, you would process the message and get a response from the chatbot
    return jsonify({
        "response": f"This is a test response to: {data.get('message', '')}",
        "session_id": data.get('session_id', 'test-session'),
        "recommendation_count": 1,
        "is_violation": False,
        "is_timed_out": False
    })

@api_bp.route('/parlay/calculate', methods=['POST'])
def calculate_parlay():
    data = request.get_json()
    # In a real app, you would calculate parlay odds here
    bets = data.get('bets', [])
    # Log the bets for debugging purposes
    print(f"Received bets: {bets}")
    return jsonify({
        "result": {
            "decimal_odds": 4.5,
            "american_odds": 350,
            "implied_probability": 0.22,
            "true_probability": 0.20,
            "ev_percent": 10.0,
            "kelly_fraction": 0.05,
            "edge": 2.0,
            "correlated_warning": False
        },
        "parsed_bets": [
            {
                "description": "Lakers -5.5",
                "odds": -110,
                "win_probability": 52.4,
                "ev_percent": 5.0
            },
            {
                "description": "Chiefs ML",
                "odds": 150,
                "win_probability": 40.0,
                "ev_percent": 5.0
            }
        ]
    })

@api_bp.route('/user/change-password', methods=['POST'])
def change_password():
    # In a real app, you would validate the current password and update to the new one
    return jsonify({"success": True, "message": "Password changed successfully"})

@api_bp.route('/user/upgrade-account', methods=['POST'])
def upgrade_account():
    # In a real app, you would process payment and upgrade the user's plan
    return jsonify({
        "success": True,
        "user": {
            "id": 1,
            "email": "test@example.com",
            "plan": "premium",
            "createdAt": "2023-01-01T00:00:00Z",
            "stats": {
                "totalChats": 5,
                "totalMessages": 25,
                "parlayCalculations": 3
            }
        }
    })

@api_bp.route('/user/delete-account', methods=['DELETE'])
def delete_account():
    # In a real app, you would delete the user's account and data
    return jsonify({"success": True, "message": "Account deleted successfully"})
EOF
fi

# Run the Flask app
python run.py &
BACKEND_PID=$!

# Start the frontend
echo "Starting React frontend on port 3080..."
cd ../frontend

# Check if node_modules exists, if not run npm install
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

npm start &
FRONTEND_PID=$!

# Function to handle script termination
cleanup() {
  echo "Shutting down servers..."
  kill $BACKEND_PID
  kill $FRONTEND_PID
  exit
}

# Set up trap to catch termination signals
trap cleanup SIGINT SIGTERM

# Keep the script running
echo "Development servers are running. Press Ctrl+C to stop."
wait 