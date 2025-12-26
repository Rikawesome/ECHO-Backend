
#routes/users.py
from flask import Blueprint, request, jsonify
from app import db
from models.user import User
from models.school import School

users_bp = Blueprint('users', __name__)

# -------------------------------
# GET ALL USERS
# -------------------------------
@users_bp.route('/', methods=['GET'])
@users_bp.route('', methods=['GET'])
def get_users():
    """
    Get all users with filtering
    """
    school_id = request.args.get('school_id')
    role = request.args.get('role')
    status = request.args.get('status')
    search = request.args.get('search')
    
    query = User.query
    
    if school_id:
        query = query.filter_by(school_id=school_id)
    
    if role:
        query = query.filter_by(role=role)
    
    if status:
        query = query.filter_by(status=status)
    
    if search:
        query = query.filter(
            db.or_(
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    
    users = query.order_by(User.created_at.desc()).all()
    
    return jsonify({
        "success": True,
        "count": len(users),
        "data": [
            {
                "id": u.id,
                "school_id": u.school_id,
                "role": u.role,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "phone": u.phone,
                "status": u.status,
                "verified_at": u.verified_at.isoformat() if u.verified_at else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "full_name": f"{u.first_name} {u.last_name}"
            }
            for u in users
        ]
    }), 200

# -------------------------------
# GET SINGLE USER
# -------------------------------
@users_bp.route("/<user_id>", methods=["GET"])
def get_user(user_id):
    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        # Get school details if school exists
        school_data = None
        if user.school_id:
            school = School.query.get(user.school_id)
            if school:
                school_data = {
                    'id': school.id,
                    'name': school.name,
                    'slug': school.slug
                }

        return jsonify({
            "success": True,
            "data": {
                "id": user.id,
                "school_id": user.school_id,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone": user.phone,
                "status": user.status,
                "verified_at": user.verified_at.isoformat() if user.verified_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "full_name": f"{user.first_name} {user.last_name}",
                "school": school_data
            }
        }), 200

    except Exception as e:
        print("❌ USER GET ERROR:", e)
        return jsonify({
            "success": False,
            "message": "Failed to fetch user"
        }), 500

# -------------------------------
# CREATE USER (TEMP / DEV)
# -------------------------------
@users_bp.route("/", methods=["POST"])
@users_bp.route("", methods=["POST"])
def create_user():
    try:
        data = request.get_json()

        if not data.get("email"):
            return jsonify({
                "success": False,
                "message": "Email is required"
            }), 400
        
        if not data.get("password"):
            return jsonify({
                "success": False,
                "message": "Password is required"
            }), 400

        # Check if email exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({
                "success": False,
                "message": "Email already registered"
            }), 400

        user = User(
            school_id=data.get("school_id"),
            email=data["email"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            phone=data.get("phone"),
            role=data.get("role", "teacher"),
            status=data.get("status", "pending")
        )
        
        # Set password
        user.set_password(data["password"])
        
        # Activate if status is active
        if data.get("status") == "active":
            user.activate()

        db.session.add(user)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "User created successfully",
            "user_id": user.id,
            "user": user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print("❌ USER CREATE ERROR:", e)
        return jsonify({
            "success": False,
            "message": "Failed to create user"
        }), 500

# -------------------------------
# UPDATE USER
# -------------------------------
@users_bp.route("/<user_id>", methods=["PUT"])
def update_user(user_id):
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        data = request.get_json()
        
        # Update fields
        updatable_fields = ['first_name', 'last_name', 'phone', 'role', 'status']
        for field in updatable_fields:
            if field in data:
                setattr(user, field, data[field])
        
        # Update email if provided and not duplicate
        if 'email' in data and data['email'] != user.email:
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != user.id:
                return jsonify({
                    "success": False,
                    "message": "Email already in use by another user"
                }), 400
            user.email = data['email']
        
        # Update password if provided
        if 'password' in data:
            user.set_password(data['password'])
        
        # Update status
        if 'status' in data:
            if data['status'] == 'active' and not user.verified_at:
                user.activate()
            elif data['status'] == 'suspended':
                user.suspend()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "User updated successfully",
            "user": user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print("❌ USER UPDATE ERROR:", e)
        return jsonify({
            "success": False,
            "message": "Failed to update user"
        }), 500

# -------------------------------
# DELETE USER
# -------------------------------
@users_bp.route("/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "User deleted successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print("❌ USER DELETE ERROR:", e)
        return jsonify({
            "success": False,
            "message": "Failed to delete user"
        }), 500

# -------------------------------
# VERIFY/ACTIVATE USER (Admin endpoint)
# -------------------------------
@users_bp.route("/<user_id>/verify", methods=["POST"])
def verify_user(user_id):
    """
    Admin endpoint to verify/activate user
    """
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({
            "success": False,
            "message": "User not found"
        }), 404
    
    if user.status == 'active':
        return jsonify({
            "success": False,
            "message": "User already active"
        }), 400
    
    user.activate()
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "User activated successfully",
        "user": user.to_dict()
    }), 200