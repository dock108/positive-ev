from flask import Blueprint, request, jsonify, current_app, g
import uuid
from app.chatbot.core import ChatbotCore
from app.database.db import get_db
import jwt
from functools import wraps
import datetime

# Create blueprint
chat_bp = Blueprint('chat', __name__)

# Initialize chatbot
chatbot = ChatbotCore()

def token_required(f):
    """Decorator to require JWT token for authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check if token is in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            # Decode token
            data = jwt.decode(
                token, 
                current_app.config['SECRET_KEY'], 
                algorithms=['HS256']
            )
            
            # Get user from database
            db = get_db()
            cursor = db.execute('SELECT * FROM users WHERE id = ?', (data['user_id'],))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'message': 'User not found!'}), 401
            
            # Store user in g for access in route
            g.user = dict(user)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

@chat_bp.route('/api/chat', methods=['POST'])
@token_required
def chat():
    """
    Chat API endpoint.
    
    Request body:
    {
        "message": "User message here",
        "session_id": "optional-session-id"
    }
    
    Response:
    {
        "response": "Chatbot response",
        "session_id": "session-id",
        "recommendation_count": 0,
        "is_violation": false,
        "is_timed_out": false
    }
    """
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400
    
    user_id = g.user['id']
    message = data['message']
    
    # Get or create session ID
    session_id = data.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Process message with chatbot
    result = chatbot.process_query(user_id, session_id, message)
    
    # Return response
    return jsonify({
        'response': result['text'],
        'session_id': session_id,
        'recommendation_count': result['recommendation_count'],
        'is_violation': result['is_violation'],
        'is_timed_out': result['is_timed_out']
    })

@chat_bp.route('/api/chat/history', methods=['GET'])
@token_required
def get_history():
    """
    Get chat history for a session.
    
    Query parameters:
    - session_id: Required session ID
    - limit: Optional limit of messages to return (default 25)
    
    Response:
    {
        "history": [
            {
                "role": "user",
                "message": "User message",
                "timestamp": "2023-01-01T12:00:00"
            },
            {
                "role": "assistant",
                "message": "Assistant response",
                "timestamp": "2023-01-01T12:00:01"
            }
        ]
    }
    """
    session_id = request.args.get('session_id')
    limit = request.args.get('limit', 25, type=int)
    
    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400
    
    user_id = g.user['id']
    
    # Get chat history from database
    db = get_db()
    cursor = db.execute(
        """
        SELECT role, message, timestamp 
        FROM chat_history 
        WHERE user_id = ? AND session_id = ? 
        ORDER BY timestamp ASC
        LIMIT ?
        """,
        (user_id, session_id, limit)
    )
    
    history = []
    for row in cursor:
        history.append({
            'role': row['role'],
            'message': row['message'],
            'timestamp': row['timestamp']
        })
    
    return jsonify({'history': history})
