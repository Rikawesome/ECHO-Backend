"""
Class Model for Echo Platform
Represents a class (level + stream) for a specific academic session
"""

from datetime import datetime
import uuid
from app import db
from sqlalchemy.orm import validates
from sqlalchemy import UniqueConstraint


class Class(db.Model):
    __tablename__ = 'classes'

    # ============ CORE IDENTIFIERS ============
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = db.Column(db.String(36), db.ForeignKey('schools.id'), nullable=False)

    # ============ CLASS IDENTITY ============
    level = db.Column(db.String(50), nullable=False)
    # Examples: JSS 1, SS 2, Primary 5, Basic 4

    stream = db.Column(db.String(50), nullable=True)
    # Examples: A, B, Gold, Science

    display_name = db.Column(db.String(100), nullable=False)
    # Example: "JSS 1 A"

    academic_session = db.Column(db.String(20), nullable=False)
    # Example: 2024/2025

    # ============ FORM TEACHER ============
    form_teacher_id = db.Column(
        db.String(36),
        db.ForeignKey('teachers.id'),
        nullable=True
    )

    # ============ STATUS ============
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # ============ CONSTRAINTS ============
    __table_args__ = (
        UniqueConstraint(
            'school_id',
            'display_name',
            'academic_session',
            name='uq_class_per_school_per_session'
        ),
    )

    # ============ VALIDATION ============
    @validates('level')
    def validate_level(self, key, value):
        if not value:
            raise ValueError("Class level is required")
        return value.strip()

    @validates('academic_session')
    def validate_session(self, key, value):
        if '/' not in value:
            raise ValueError("Academic session must be in format YYYY/YYYY")
        return value

    # ============ HELPERS ============
    @staticmethod
    def build_display_name(level, stream=None):
        if stream:
            return f"{level} {stream}"
        return level

    def to_dict(self):
        return {
            'id': self.id,
            'school_id': self.school_id,
            'level': self.level,
            'stream': self.stream,
            'display_name': self.display_name,
            'academic_session': self.academic_session,
            'form_teacher_id': self.form_teacher_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f'<Class {self.display_name} ({self.academic_session})>'
