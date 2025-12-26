"""
User Model for Echo Platform
Handles authentication, role-based access, and school association
"""
from datetime import datetime
from app import db
from sqlalchemy.orm import validates, relationship
from sqlalchemy import Column, String, Boolean, DateTime, JSON
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = db.Column(db.String(36), db.ForeignKey('schools.id'), nullable=True)
    role = db.Column(db.String(20), nullable=False)
    
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    
    password_hash = db.Column(db.String(128), nullable=False)
    
    # ----------------- NEW/UPDATED FIELDS -----------------
    status = db.Column(db.String(20), default='pending')  # pending, active, suspended
    registration_code_used = db.Column(db.String(50), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    
    profile_data = db.Column(JSON, default={})
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ----------------- RELATIONSHIPS -----------------
    school = relationship('School', backref='users')

    # ----------------- VALIDATIONS -----------------
    @validates('role')
    def validate_role(self, key, role):
        valid_roles = ['user','owner', 'admin', 'teacher', 'student', 'parent']
        if role not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return role

    @validates('email')
    def validate_email(self, key, email):
        if not email or '@' not in email:
            raise ValueError('Invalid email')
        return email.lower()

    # ----------------- PASSWORD METHODS -----------------
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ----------------- STATUS METHODS -----------------
    def activate(self):
        self.status = 'active'
        self.verified_at = datetime.utcnow()

    def suspend(self):
        self.status = 'suspended'

    def is_active(self):
        return self.status == 'active'

    def is_pending(self):
        return self.status == 'pending'

    # ----------------- SERIALIZATION -----------------
    def to_dict(self):
        return {
            'id': self.id,
            'school_id': self.school_id,
            'role': self.role,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'status': self.status,
            'registration_code_used': self.registration_code_used,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'profile_data': self.profile_data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'full_name': f"{self.first_name} {self.last_name}"
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
