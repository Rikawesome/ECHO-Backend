"""
Teacher Model for Echo Platform
Represents teaching staff within a school
"""

from datetime import datetime
import uuid
from app import db
from sqlalchemy.orm import validates
from sqlalchemy import UniqueConstraint


class Teacher(db.Model):
    __tablename__ = 'teachers'

    # ============ CORE IDENTIFIERS ============
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = db.Column(db.String(36), db.ForeignKey('schools.id'), nullable=False)

    # System-generated identifier (used internally + UI)
    teacher_code = db.Column(db.String(30), unique=True, nullable=False)

    # Optional school-specific number
    staff_number = db.Column(db.String(50), nullable=True)

    # ============ BIO DATA ============
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    other_names = db.Column(db.String(100), nullable=True)

    gender = db.Column(db.String(10), nullable=True)

    # ============ CONTACT ============
    email = db.Column(db.String(120), nullable=True, index=True)
    phone = db.Column(db.String(20), nullable=True)

    # ============ ROLE & STATUS ============
    role = db.Column(
        db.String(20),
        default='teacher'
    )
    # teacher | admin | head_teacher

    employment_status = db.Column(
        db.String(20),
        default='active'
    )
    # active | resigned | suspended | retired

    is_active = db.Column(db.Boolean, default=True)

    # ============ PLATFORM TRACKING ============
    date_joined_platform = db.Column(db.DateTime, default=datetime.utcnow)

    # ============ RELATIONSHIPS ============
    # Subject.teacher_id -> Teacher.id
    subjects = db.relationship('Subject', backref='teacher', lazy=True)
    # This creates a 'teacher' attribute on Subject objects

    # Class.form_teacher_id -> Teacher.id (defined in Class model)

    # ============ CONSTRAINTS ============
    __table_args__ = (
        UniqueConstraint(
            'school_id',
            'staff_number',
            name='uq_teacher_staff_number_per_school'
        ),
    )

    # ============ VALIDATION ============
    @validates('employment_status')
    def validate_status(self, key, value):
        allowed = ['active', 'resigned', 'suspended', 'retired']
        if value not in allowed:
            raise ValueError(f'Invalid employment status: {value}')
        return value

    @validates('role')
    def validate_role(self, key, value):
        allowed = ['teacher', 'admin', 'head_teacher']
        if value not in allowed:
            raise ValueError(f'Invalid role: {value}')
        return value

    # ============ HELPERS ============
    @property
    def full_name(self):
        parts = [self.first_name, self.last_name]
        if self.other_names:
            parts.append(self.other_names)
        return " ".join(parts)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_code': self.teacher_code,
            'staff_number': self.staff_number,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'employment_status': self.employment_status,
            'date_joined_platform': self.date_joined_platform.isoformat(),
            'is_active': self.is_active
        }

    def __repr__(self):
        return f'<Teacher {self.full_name} ({self.teacher_code})>'