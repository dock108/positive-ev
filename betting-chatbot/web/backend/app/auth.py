from flask import request, jsonify, current_app, g
from functools import wraps
import jwt
import datetime
from .db import get_db

def generate_token(user_id):
    """Generate a JWT token for the user."""
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
        'iat': datetime.datetime.utcnow()
    }
    
    token = jwt.encode(
        payload,
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    
    return token

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
        except Exception as e:
            return jsonify({'message': f'Authentication error: {str(e)}'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def hash_password(password):
    """Simple password hashing for demo purposes.
    In production, use a proper password hashing library like bcrypt."""
    return f"hashed_{password}"

def verify_password(hashed_password, password):
    """Simple password verification for demo purposes.
    In production, use a proper password hashing library like bcrypt."""
    return hashed_password == f"hashed_{password}" 