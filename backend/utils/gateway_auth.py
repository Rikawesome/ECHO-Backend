# utils/gateway_auth.py
"""
Gateway Authentication Helper
Handles authentication in BOTH development and production modes:
1. Production: Reads x-user-id header from Trecks' API Gateway
2. Development: Allows user_id in request body or query params
"""
from flask import request
from models.user import User


def get_user_from_gateway():
    """
    Extract user from Trecks' gateway headers.
    Works for BOTH development and production.
    
    Returns:
        User object if found, None otherwise
    """
    # Method 1: Production - Read from Trecks' gateway headers
    user_id = request.headers.get('x-user-id')
    
    if user_id:
        user = User.query.get(user_id)
        if user:
            return user
    
    # Method 2: Development - Allow user_id in JSON body
    if request.is_json:
        user_id = request.json.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user:
                return user
    
    # Method 3: Development - Allow user_id as query parameter
    user_id = request.args.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return user
    
    # Method 4: Development - Special header for testing
    user_id = request.headers.get('X-Test-User-Id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return user
    
    return None


def require_auth(f):
    """
    Decorator to require authentication.
    
    Usage:
    @schools_bp.route('', methods=['POST'])
    @require_auth
    def create_school():
        user = get_user_from_gateway()  # Will always return a user
        # ... your logic
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_user_from_gateway()
        if not user:
            return {
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }, 401
        return f(*args, **kwargs)
    return decorated_function


def require_role(*allowed_roles):
    """
    Decorator to require specific user role(s).
    
    Usage:
    @schools_bp.route('', methods=['POST'])
    @require_role('owner', 'admin')
    def create_school():
        # Only owners or admins can access this
        # ... your logic
    """
    from functools import wraps
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_user_from_gateway()
            if not user:
                return {
                    'success': False,
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }, 401
            
            if user.role not in allowed_roles:
                return {
                    'success': False,
                    'error': f'Role {user.role} not allowed. Required: {allowed_roles}',
                    'code': 'PERMISSION_DENIED'
                }, 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_current_user_or_fail():
    """
    Get current user or return error response immediately.
    
    Returns:
        (user, None) if user found
        (None, error_response) if user not found
    """
    user = get_user_from_gateway()
    if not user:
        return None, ({
            'success': False,
            'error': 'Authentication required',
            'code': 'AUTH_REQUIRED'
        }, 401)
    return user, None


# Optional: JWT decoding if you want to verify tokens yourself
def decode_gateway_token():
    """
    OPTIONAL: Decode JWT token from Authorization header.
    Only needed if you want to verify tokens in Python too.
    """
    import jwt
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    try:
        # Trecks' JWT secret
        payload = jwt.decode(
            token, 
            'echo-secret-key-change-in-production',
            algorithms=['HS256'],
            options={'verify_exp': False}  # Trecks already verified
        )
        return payload
    except jwt.InvalidTokenError:
        return None