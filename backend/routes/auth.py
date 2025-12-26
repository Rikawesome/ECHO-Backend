from flask import Blueprint, request, jsonify
from app import db
from models.user import User
import re

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
    Login existing user
    """
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active():
        return jsonify({'error': 'Account is not active. Please contact administrator.'}), 403
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'token': 'jwt_token_placeholder'
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