from flask import Blueprint, request, jsonify, current_app
from app.database.db import get_db
import jwt
import datetime
import uuid
import hashlib
import re

# Create blueprint
auth_bp = Blueprint('auth', __name__)

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_email(email):
    """Check if email is valid."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Request body:
    {
        "email": "user@example.com",
        "password": "password123"
    }
    
    Response:
    {
        "message": "User registered successfully",
        "user_id": 1
    }
    """
    data = request.get_json()
    
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password are required'}), 400
    
    email = data['email']
    password = data['password']
    
    # Validate email
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Validate password
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    # Hash password
    password_hash = hash_password(password)
    
    # Check if user already exists
    db = get_db()
    cursor = db.execute('SELECT id FROM users WHERE email = ?', (email,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        return jsonify({'error': 'Email already registered'}), 409
    
    # Insert new user
    cursor = db.execute(
        'INSERT INTO users (email, password_hash) VALUES (?, ?)',
        (email, password_hash)
    )
    db.commit()
    
    return jsonify({
        'message': 'User registered successfully',
        'user_id': cursor.lastrowid
    }), 201

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """
    Login a user.
    
    Request body:
    {
        "email": "user@example.com",
        "password": "password123"
    }
    
    Response:
    {
        "token": "jwt-token",
        "user": {
            "id": 1,
            "email": "user@example.com",
            "plan": "free"
        }
    }
    """
    data = request.get_json()
    
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password are required'}), 400
    
    email = data['email']
    password = data['password']
    
    # Hash password
    password_hash = hash_password(password)
    
    # Check credentials
    db = get_db()
    cursor = db.execute(
        'SELECT id, email, plan FROM users WHERE email = ? AND password_hash = ?',
        (email, password_hash)
    )
    user = cursor.fetchone()
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Generate token
    token = jwt.encode(
        {
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        },
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    
    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'plan': user['plan']
        }
    })

@auth_bp.route('/api/auth/upgrade', methods=['POST'])
def upgrade_plan():
    """
    Upgrade a user's plan to premium.
    In a real app, this would handle payment processing.
    
    Request body:
    {
        "user_id": 1,
        "payment_token": "payment-token"
    }
    
    Response:
    {
        "message": "Plan upgraded successfully",
        "plan": "premium"
    }
    """
    data = request.get_json()
    
    if not data or 'user_id' not in data or 'payment_token' not in data:
        return jsonify({'error': 'User ID and payment token are required'}), 400
    
    user_id = data['user_id']
    payment_token = data['payment_token']
    
    # In a real app, process payment here
    # For now, just update the user's plan
    
    db = get_db()
    db.execute(
        'UPDATE users SET plan = "premium" WHERE id = ?',
        (user_id,)
    )
    db.commit()
    
    return jsonify({
        'message': 'Plan upgraded successfully',
        'plan': 'premium'
    })
