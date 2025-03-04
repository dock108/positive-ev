import os
import uuid
import datetime
import sqlite3
import openai
from flask import Blueprint, request, jsonify, g
from typing import List, Dict, Any

from .auth import token_required, generate_token, hash_password, verify_password
from .db import get_db, init_db, DATABASE_PATH
from .chatbot_wrapper import process_query

api_bp = Blueprint('api', __name__)

# Initialize OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize database
try:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    init_db()
    print(f"Database initialized at {DATABASE_PATH}")
except Exception as e:
    print(f"Error initializing database: {e}")

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "API is running"})

@api_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '')
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Verify password
    if not verify_password(user['password_hash'], password):
        conn.close()
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Generate token
    token = generate_token(user['id'])
    
    conn.close()
    
    return jsonify({
        "user": {
            "id": user['id'],
            "email": user['email'],
            "plan": user['plan'],
            "createdAt": user['created_at'],
            "stats": {
                "totalChats": 5,
                "totalMessages": 25,
                "parlayCalculations": 3
            }
        },
        "token": token
    })

@api_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email', '')
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    # Validate email format
    if '@' not in email or '.' not in email:
        return jsonify({"error": "Invalid email format"}), 400
    
    # Validate password strength
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    # Hash password
    hashed_password = hash_password(password)
    
    # Create user in the database
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, plan) VALUES (?, ?, ?)",
            (email, hashed_password, "free")
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Email already exists"}), 400
    
    # Generate token
    token = generate_token(user_id)
    
    conn.close()
    
    return jsonify({
        "user": {
            "id": user_id,
            "email": email,
            "plan": "free",
            "createdAt": datetime.datetime.now().isoformat(),
            "stats": {
                "totalChats": 0,
                "totalMessages": 0,
                "parlayCalculations": 0
            }
        },
        "token": token
    })

def save_chat_message(user_id: int, session_id: str, message: str, role: str) -> int:
    """Save a chat message to the database."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO chat_history (user_id, session_id, message, role) VALUES (?, ?, ?, ?)",
        (user_id, session_id, message, role)
    )
    
    conn.commit()
    message_id = cursor.lastrowid
    conn.close()
    
    return message_id

def get_chat_history(user_id: int, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get chat history for a user and session."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM chat_history WHERE user_id = ? AND session_id = ? ORDER BY timestamp ASC LIMIT ?",
        (user_id, session_id, limit)
    )
    
    history = []
    for row in cursor.fetchall():
        history.append({
            "id": str(uuid.uuid4()),
            "text": row['message'],
            "sender": "user" if row['role'] == 'user' else "bot",
            "timestamp": row['timestamp']
        })
    
    conn.close()
    return history

def track_recommendation_usage(user_id: int) -> int:
    """Track recommendation usage for a user."""
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.date.today().isoformat()
    
    # Check current usage
    cursor.execute(
        "SELECT recommendation_count FROM user_usage WHERE user_id = ? AND date = ?",
        (user_id, today)
    )
    
    row = cursor.fetchone()
    if row:
        count = row['recommendation_count'] + 1
        cursor.execute(
            "UPDATE user_usage SET recommendation_count = ? WHERE user_id = ? AND date = ?",
            (count, user_id, today)
        )
    else:
        count = 1
        cursor.execute(
            "INSERT INTO user_usage (user_id, date, recommendation_count) VALUES (?, ?, ?)",
            (user_id, today, count)
        )
    
    conn.commit()
    conn.close()
    
    return count

def get_user_plan(user_id: int) -> str:
    """Get the plan for a user."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT plan FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return row['plan']
    return "free"

def get_recommendation_count(user_id: int) -> int:
    """Get the recommendation count for a user today."""
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.date.today().isoformat()
    
    cursor.execute(
        "SELECT recommendation_count FROM user_usage WHERE user_id = ? AND date = ?",
        (user_id, today)
    )
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row['recommendation_count']
    return 0

def contains_recommendation_request(message: str) -> bool:
    """Check if a message contains a recommendation request."""
    message = message.lower()
    keywords = [
        "best bet", "top bet", "recommend", "suggestion", "what should i bet",
        "good bet", "profitable bet", "winning bet", "sure bet", "lock"
    ]
    
    for keyword in keywords:
        if keyword in message:
            return True
    
    return False

@api_bp.route('/chat/send', methods=['POST'])
@token_required
def send_message():
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
    
    message = data.get('message')
    session_id = data.get('session_id', str(uuid.uuid4()))
    
    # Get user_id from the authenticated user
    user_id = g.user['id']
    
    # Process the query using our chatbot wrapper
    try:
        result = process_query(user_id, session_id, message)
        
        # Return the response
        return jsonify({
            "response": result["response"],
            "session_id": result["session_id"],
            "recommendation_count": result.get("recommendation_count", 0),
            "is_violation": "violation" in result,
            "is_timed_out": "timeout" in result
        })
    except Exception as e:
        print(f"Error processing query with chatbot wrapper: {e}")
        
        # Fallback to the original implementation if chatbot wrapper fails
        # Save user message to database
        save_chat_message(user_id, session_id, message, 'user')
        
        # Check if user is on free plan and has reached the limit
        plan = get_user_plan(user_id)
        recommendation_count = get_recommendation_count(user_id)
        is_recommendation = contains_recommendation_request(message)
        
        # Check if this is a recommendation request and user is on free plan
        if is_recommendation and plan == 'free':
            if recommendation_count >= 3:
                response = "You've reached your daily limit of 3 recommendations. Please upgrade to premium for unlimited recommendations."
                save_chat_message(user_id, session_id, response, 'assistant')
                return jsonify({
                    "response": response,
                    "session_id": session_id,
                    "recommendation_count": recommendation_count,
                    "is_violation": False,
                    "is_timed_out": False
                })
            else:
                # Increment recommendation count
                recommendation_count = track_recommendation_usage(user_id)
        
        # Get chat history for context
        history = get_chat_history(user_id, session_id)
        
        # Format history for OpenAI
        messages = [
            {"role": "system", "content": """
            You are an AI sports betting assistant that helps users make informed betting decisions.
            
            Your primary goal is to provide thoughtful analysis and insights about sports betting opportunities.
            
            Guidelines:
            1. You can discuss betting strategies, odds analysis, and specific bets when asked.
            2. You should NEVER directly list the "top bets" or "best bets" when asked. Instead, guide users to think about specific sports, teams, or bet types they're interested in.
            3. For free users, you can provide up to 3 specific bet recommendations per day.
            4. Always explain the reasoning behind your recommendations, including EV (Expected Value) considerations.
            5. If users try to circumvent the recommendation limit, politely redirect them to more general betting advice.
            6. When discussing parlays, explain both the appeal and the mathematical disadvantages.
            """}
        ]
        
        # Add history messages
        for msg in history:
            role = "user" if msg["sender"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["text"]})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            # Call OpenAI API
            if os.getenv("OPENAI_API_KEY"):
                client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=500,
                    temperature=0.7
                )
                bot_response = response.choices[0].message.content
            else:
                # Fallback if no API key
                bot_response = f"This is a test response to: {message}"
                if is_recommendation:
                    bot_response = "Here's my analysis for your betting question: I recommend looking at the recent performance trends and injury reports before placing this bet. The odds suggest there might be value, but always consider the implied probability versus your own assessment."
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            bot_response = "I'm having trouble processing your request right now. Please try again later."
        
        # Save bot response to database
        save_chat_message(user_id, session_id, bot_response, 'assistant')
        
        return jsonify({
            "response": bot_response,
            "session_id": session_id,
            "recommendation_count": recommendation_count,
            "is_violation": False,
            "is_timed_out": False
        })

@api_bp.route('/chat/history', methods=['GET'])
@token_required
def get_chat_history_endpoint():
    session_id = request.args.get('session_id', '')
    
    # Get user_id from the authenticated user
    user_id = g.user['id']
    
    # Get chat history
    messages = get_chat_history(user_id, session_id, limit=50)
    recommendation_count = get_recommendation_count(user_id)
    
    return jsonify({
        "messages": messages,
        "recommendation_count": recommendation_count
    })

@api_bp.route('/parlay/calculate', methods=['POST'])
@token_required
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
@token_required
def change_password():
    data = request.get_json()
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not current_password or not new_password:
        return jsonify({"error": "Current password and new password are required"}), 400
    
    # Validate password strength
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400
    
    # Get user from g
    user = g.user
    
    # Verify current password
    if not verify_password(user['password_hash'], current_password):
        return jsonify({"error": "Current password is incorrect"}), 401
    
    # Hash new password
    hashed_password = hash_password(new_password)
    
    # Update password in database
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hashed_password, user['id'])
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Password changed successfully"})

@api_bp.route('/user/upgrade-account', methods=['POST'])
@token_required
def upgrade_account():
    # Get user_id from the authenticated user
    user_id = g.user['id']
    
    # Update user plan in database
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET plan = 'premium' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({
        "success": True,
        "user": {
            "id": user_id,
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
@token_required
def delete_account():
    # Get user from g
    user = g.user
    
    # Delete user data from database
    conn = get_db()
    cursor = conn.cursor()
    
    # Delete chat history
    cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user['id'],))
    
    # Delete user usage
    cursor.execute("DELETE FROM user_usage WHERE user_id = ?", (user['id'],))
    
    # Delete user
    cursor.execute("DELETE FROM users WHERE id = ?", (user['id'],))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Account deleted successfully"}) 