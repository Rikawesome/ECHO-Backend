# routes/auth.py - COMPLETE FIXED VERSION
import re
import jwt
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from app import db
from models.user import User

auth_bp = Blueprint('auth', __name__)

# ================= BASIC USER REGISTRATION =================
@auth_bp.route('/register', methods=['POST'])
def register_user():
    """
    Register a basic user account (no school yet)
    """
    data = request.get_json()
    
    # Required fields
    required = ['email', 'password', 'first_name', 'last_name']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Validate email
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data['email']):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Check if email exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    try:
        # Create BASIC user (no school, no role)
        user = User(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            role='user',  # Default role until they join a school
            status='active'  # Auto-activate for now
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User registered successfully. Please join or create a school.',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'has_school': False,
                'school_id': None
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ================= LOGIN =================
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login existing user - FIXED VERSION WITH REAL JWT TOKENS
    """
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active():
        return jsonify({'error': 'Account is not active. Please contact administrator.'}), 403
    
    # ✅✅✅ FIXED: Generate REAL JWT Token (NOT placeholder)
    # Create token payload with user info
    token_payload = {
        'user_id': str(user.id),
        'email': user.email,
        'role': user.role,
        'school_id': str(user.school_id) if user.school_id else None,
        'exp': datetime.utcnow() + timedelta(days=1)  # Token expires in 1 day
    }
    
    # Get secret key from environment
    # First try Flask config, then environment variable
    secret_key = current_app.config.get('SECRET_KEY')
    if not secret_key:
        # Fallback to environment variable
        import os
        secret_key = os.environ.get('SECRET_KEY')
        
    # If still no secret key, use a temporary one (for testing)
    if not secret_key:
        secret_key = 'temporary-secret-key-for-testing-only'
        print("⚠️ WARNING: Using temporary secret key. Set SECRET_KEY in production!")
    
    # Generate the actual JWT token
    try:
        token = jwt.encode(token_payload, secret_key, algorithm='HS256')
        # If token is bytes (older PyJWT), convert to string
        if not isinstance(token, str):
            token = token.decode('utf-8')
    except Exception as e:
        print(f"❌ JWT generation error: {e}")
        return jsonify({'error': 'Authentication error'}), 500
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'token': token  # ✅✅✅ REAL JWT token (NOT placeholder)
    })

# ================= TEST ENDPOINT =================
@auth_bp.route('/test', methods=['GET'])
def test_auth():
    """
    Test endpoint to verify auth routes are working
    """
    return jsonify({
        'message': 'Auth routes are working!',
        'endpoints': [
            'POST /auth/register',
            'POST /auth/login'
        ]
    })