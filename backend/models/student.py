"""
Student Model for Echo Platform
Represents enrolled learners within a school
"""

from datetime import datetime
import uuid
from app import db
from sqlalchemy.orm import validates
from sqlalchemy import UniqueConstraint


class Student(db.Model):
    __tablename__ = 'students'

    # ============ CORE IDENTIFIERS ============
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = db.Column(db.String(36), db.ForeignKey('schools.id'), nullable=False)

    # System-generated student code (used instead of admission number)
    student_code = db.Column(db.String(30), unique=True, nullable=False)

    # Optional school admission number
    admission_number = db.Column(db.String(50), nullable=True)

    # ============ BIO DATA ============
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    other_names = db.Column(db.String(100), nullable=True)

    gender = db.Column(db.String(10), nullable=True)

    # ============ CONTACT (STUDENT) ============
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)

    # ============ GUARDIAN / PARENT ============
    guardian_name = db.Column(db.String(150), nullable=True)
    guardian_phone = db.Column(db.String(20), nullable=True)
    guardian_email = db.Column(db.String(120), nullable=True)
    guardian_relationship = db.Column(db.String(50), nullable=True)
    # e.g. Father, Mother, Guardian

    # ============ ACADEMIC ============
    class_id = db.Column(
        db.String(36),
        db.ForeignKey('classes.id'),
        nullable=True
    )  # Current class only

    # ============ PLATFORM TRACKING ============
    date_joined_platform = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # ============ RELATIONSHIPS ============
    """gradebooks = db.relationship(
        'GradeBook',
        backref='student',
        lazy=True,
        cascade='all, delete-orphan'
    )"""

    # Optional student timetable snapshot
    timetable = db.Column(db.JSON, default=None)

    # ============ CONSTRAINTS ============
    __table_args__ = (
        UniqueConstraint(
            'school_id',
            'admission_number',
            name='uq_student_admission_number_per_school'
        ),
    )

    # ============ VALIDATION ============
    @validates('gender')
    def validate_gender(self, key, value):
        if value and value.lower() not in ['male', 'female']:
            raise ValueError('Gender must be male or female')
        return value.lower() if value else value

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
            'student_code': self.student_code,
            'admission_number': self.admission_number,
            'full_name': self.full_name,
            'gender': self.gender,
            'email': self.email,
            'phone': self.phone,
            'guardian': {
                'name': self.guardian_name,
                'phone': self.guardian_phone,
                'email': self.guardian_email,
                'relationship': self.guardian_relationship
            },
            'class_id': self.class_id,
            'date_joined_platform': self.date_joined_platform.isoformat(),
            'is_active': self.is_active
        }

    def __repr__(self):
        return f'<Student {self.full_name} ({self.student_code})>'
