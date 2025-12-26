"""
Subject Model for Echo Platform
Represents a subject taught by a teacher to a class
"""
from datetime import datetime
import uuid
from app import db
from sqlalchemy.orm import validates


class Subject(db.Model):
    __tablename__ = 'subjects'

    # =====================
    # CORE IDENTIFIERS
    # =====================
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id = db.Column(db.String(36), db.ForeignKey('schools.id'), nullable=False)

    class_id = db.Column(db.String(36), db.ForeignKey('classes.id'), nullable=False)
    teacher_id = db.Column(db.String(36), db.ForeignKey('teachers.id'), nullable=False)

    # =====================
    # SUBJECT DETAILS
    # =====================
    name = db.Column(db.String(100), nullable=False)   # Mathematics, English
    code = db.Column(db.String(20), nullable=True)     # MTH101, ENG-JSS2
    description = db.Column(db.Text, nullable=True)

    # =====================
    # GRADING CONFIG (inherits from school by default)
    # =====================
    ca_structure_override = db.Column(db.JSON, nullable=True)
    grading_scale_override = db.Column(db.JSON, nullable=True)

    # =====================
    # STATUS
    # =====================
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # =====================
    # RELATIONSHIPS - FIXED: REMOVE DUPLICATE
    # =====================
    # DELETE THIS LINE:
    # teacher = db.relationship("Teacher", backref="subjects")
    
    # Keep this commented out:
    """gradebooks = db.relationship(
        'GradeBook',
        backref='subject',
        lazy=True,
        cascade='all, delete-orphan'
    )"""

    # =====================
    # VALIDATION
    # =====================
    @validates('name')
    def validate_name(self, key, value):
        if not value or len(value.strip()) < 2:
            raise ValueError("Subject name must be at least 2 characters")
        return value.strip()

    # =====================
    # BUSINESS LOGIC
    # =====================
    def get_effective_ca_structure(self, school):
        if self.ca_structure_override:
            return self.ca_structure_override
        return school.academic_config.get('ca_structure')

    def get_effective_grading_scale(self, school):
        if self.grading_scale_override:
            return self.grading_scale_override
        return school.academic_config.get('overall_grade_thresholds')

    # =====================
    # SERIALIZATION
    # =====================
    def to_dict(self):
        return {
            'id': self.id,
            'school_id': self.school_id,
            'class_id': self.class_id,
            'teacher_id': self.teacher_id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f"<Subject {self.name} ({self.class_id})>"