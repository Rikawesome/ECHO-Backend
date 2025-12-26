"""
School Model for Echo Platform
Core entity representing educational institutions
"""
from datetime import datetime, timedelta
from app import db
from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, JSON
from sqlalchemy.orm import relationship, validates
import random
import string
import re
import uuid

class School(db.Model):
    """
    School Model - Tiered data structure for Nigerian schools
    """
    __tablename__ = 'schools'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ============ TIER 1: CORE IDENTITY ============
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    school_type = db.Column(db.String(50), nullable=False)  # 'primary', 'junior', 'senior', 'combined'
    
    # School personality
    motto = db.Column(db.String(300), nullable=True)
    vision = db.Column(db.Text, nullable=True)
    mission = db.Column(db.Text, nullable=True)
    
    # Contact information
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    contact_whatsapp = db.Column(db.String(20), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    
    # Location
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True, default='Lagos')
    country = db.Column(db.String(100), default='Nigeria')
    
    # ============ AUTO-GENERATED REGISTRATION CODES ============
    teacher_registration_code = db.Column(db.String(50), unique=True, nullable=False)
    student_registration_code = db.Column(db.String(50), unique=True, nullable=False)
    codes_generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ============ TIER 2: OPERATIONAL DETAILS (Optional JSON) ============
    operational_details = db.Column(JSON, nullable=True, default=None)
    
    # ============ TIER 3: CONFIGURATION (Gradual Setup) ============
    academic_config = db.Column(JSON, nullable=True, default=None)
    subscription_config = db.Column(JSON, nullable=True, default=None)
    
    # ============ STATUS & SETUP TRACKING ============
    setup_completed = db.Column(db.Boolean, default=False)
    setup_stage = db.Column(db.String(20), default='basic')
    # Stages: basic → contact → academic → grading → subscription → complete
    
    subscription_status = db.Column(db.String(20), default='trial')
    # Statuses: trial, active, past_due, cancelled, expired
    
    trial_ends_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # ============ DENORMALIZED COUNTERS (For Performance) ============
    student_count = db.Column(db.Integer, default=0)
    teacher_count = db.Column(db.Integer, default=0)
    
    # ============ RELATIONSHIPS ============
    #users = relationship('User', backref='school', lazy=True, cascade='all, delete-orphan')
    # Payments relationship will be added when Payment model is created
    # payments = relationship('Payment', backref='school', lazy=True)
    
    # ============ VALIDATION METHODS ============
    @validates('slug')
    def validate_slug(self, key, slug):
        """Ensure slug is URL-friendly"""
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return slug
    
    @validates('contact_email')
    def validate_email(self, key, email):
        """Validate email format if provided"""
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValueError('Invalid email format')
        return email
    
    @validates('school_type')
    def validate_school_type(self, key, school_type):
        """Ensure valid school type"""
        valid_types = ['primary', 'junior', 'senior', 'combined']
        if school_type not in valid_types:
            raise ValueError(f'School type must be one of: {", ".join(valid_types)}')
        return school_type
    
    @validates('subscription_status')
    def validate_subscription_status(self, key, status):
        """Ensure valid subscription status"""
        valid_statuses = ['trial', 'active', 'past_due', 'cancelled', 'expired']
        if status not in valid_statuses:
            raise ValueError(f'Subscription status must be one of: {", ".join(valid_statuses)}')
        return status
    
    # ============ INITIALIZATION ============
    def __init__(self, **kwargs):
        """Initialize school with auto-generated codes"""
        super().__init__(**kwargs)
        
        # Auto-generate registration codes
        if not self.teacher_registration_code:
            self.teacher_registration_code = self._generate_registration_code('teacher')
        
        if not self.student_registration_code:
            self.student_registration_code = self._generate_registration_code('student')
        
        # Set trial period (30 days)
        if not self.trial_ends_at and self.subscription_status == 'trial':
            self.trial_ends_at = datetime.utcnow() + timedelta(days=30)
        
        # Set default academic config based on school type
        if not self.academic_config:
            self.academic_config = self._get_default_academic_config()
        
        # Set default subscription config for trial
        if not self.subscription_config:
            self.subscription_config = self._get_default_subscription_config()
    
    # ============ PRIVATE METHODS ============
    def _generate_registration_code(self, user_type='student'):
        """Generate unique registration code: TCH/STU-SCH123-ABC789"""
        # Get school identifier (first 3 letters of name or 'SCH')
        if self.name:
            school_code = self.name[:3].upper().replace(' ', '')
            if len(school_code) < 3:
                school_code = school_code.ljust(3, 'X')
        else:
            school_code = 'SCH'
        
        # Generate random parts
        random_numbers = ''.join(random.choices(string.digits, k=3))
        random_letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        
        # Determine prefix
        prefix = 'TCH' if user_type.lower() == 'teacher' else 'STU'
        
        return f"{prefix}-{school_code}{random_numbers}-{random_letters}"
    
    def _get_default_academic_config(self):
        """Get default academic config based on school type"""
        base_config = {
            'session': f"{datetime.now().year}/{datetime.now().year + 1}",
            'current_term': 1,
            'setup_completed': False
        }
        
        if self.school_type == 'primary':
            return {
                **base_config,
                'grading_system': 'primary_scale',
                'ca_structure': 'basic_primary',
                'enable_overall_grades': False
            }
        elif self.school_type == 'junior':
            return {
                **base_config,
                'grading_system': 'junior_scale',
                'ca_structure': 'standard_30',
                'enable_overall_grades': True,
                'overall_grade_thresholds': {
                    'A+': {'min': 80, 'max': 100, 'remark': 'Excellent'},
                    'A': {'min': 70, 'max': 79, 'remark': 'Very Good'},
                    'B+': {'min': 65, 'max': 69, 'remark': 'Good Plus'},
                    'B': {'min': 60, 'max': 64, 'remark': 'Good'},
                    'C+': {'min': 55, 'max': 59, 'remark': 'Credit Plus'},
                    'C': {'min': 50, 'max': 54, 'remark': 'Credit'},
                    'D': {'min': 45, 'max': 49, 'remark': 'Pass'},
                    'E': {'min': 40, 'max': 44, 'remark': 'Fair'},
                    'F': {'min': 0, 'max': 39, 'remark': 'Fail'}
                }
            }
        elif self.school_type in ['senior', 'combined']:
            return {
                **base_config,
                'grading_system': 'waec',
                'ca_structure': 'standard_30',
                'enable_overall_grades': True,
                'overall_grade_thresholds': {
                    'A+': {'min': 80, 'max': 100, 'remark': 'Excellent'},
                    'A': {'min': 70, 'max': 79, 'remark': 'Very Good'},
                    'B+': {'min': 65, 'max': 69, 'remark': 'Good Plus'},
                    'B': {'min': 60, 'max': 64, 'remark': 'Good'},
                    'C+': {'min': 55, 'max': 59, 'remark': 'Credit Plus'},
                    'C': {'min': 50, 'max': 54, 'remark': 'Credit'},
                    'D': {'min': 45, 'max': 49, 'remark': 'Pass'},
                    'E': {'min': 40, 'max': 44, 'remark': 'Fair'},
                    'F': {'min': 0, 'max': 39, 'remark': 'Fail'}
                }
            }
        
        return base_config
    
    def _get_default_subscription_config(self):
        """Get default subscription config for trial"""
        return {
            'plan': 'trial',
            'price': 0.0,
            'currency': 'NGN',
            'trial_days': 30,
            'features': {
                'max_students': 50,
                'max_teachers': 10,
                'allowed_features': ['basic_grading', 'attendance', 'parent_portal']
            },
            'limits_reached': False
        }
    
    # ============ PUBLIC METHODS ============
    def update_academic_config(self, updates):
        """Update academic configuration"""
        if not self.academic_config:
            self.academic_config = self._get_default_academic_config()
        
        self.academic_config.update(updates)
        self._check_setup_completion()
        return self
    
    def update_subscription_config(self, updates):
        """Update subscription configuration"""
        if not self.subscription_config:
            self.subscription_config = self._get_default_subscription_config()
        
        self.subscription_config.update(updates)
        return self
    
    def add_operational_detail(self, category, data):
        """Add operational details (facilities, etc.)"""
        if not self.operational_details:
            self.operational_details = {}
        
        if category not in self.operational_details:
            self.operational_details[category] = {}
        
        self.operational_details[category].update(data)
        return self
    
    def get_contact_channels(self):
        """Get all active contact channels"""
        channels = []
        if self.contact_phone:
            channels.append({
                'type': 'phone',
                'value': self.contact_phone,
                'label': 'Phone'
            })
        if self.contact_whatsapp:
            channels.append({
                'type': 'whatsapp',
                'value': self.contact_whatsapp,
                'label': 'WhatsApp'
            })
        if self.contact_email:
            channels.append({
                'type': 'email',
                'value': self.contact_email,
                'label': 'Email'
            })
        if self.website:
            channels.append({
                'type': 'website',
                'value': self.website,
                'label': 'Website'
            })
        return channels
    
    def is_trial_expired(self):
        """Check if trial period has expired"""
        if self.subscription_status != 'trial' or not self.trial_ends_at:
            return False
        return datetime.utcnow() > self.trial_ends_at
    
    def can_add_student(self):
        """Check if school can add more students based on plan"""
        if not self.subscription_config:
            return True  # Default during trial
        
        max_students = self.subscription_config.get('features', {}).get('max_students', 50)
        return self.student_count < max_students
    
    def can_add_teacher(self):
        """Check if school can add more teachers based on plan"""
        if not self.subscription_config:
            return True  # Default during trial
        
        max_teachers = self.subscription_config.get('features', {}).get('max_teachers', 10)
        return self.teacher_count < max_teachers
    
    def update_setup_stage(self, stage):
        """Update setup progression stage"""
        valid_stages = ['basic', 'contact', 'academic', 'grading', 'subscription', 'complete']
        if stage in valid_stages:
            self.setup_stage = stage
            if stage == 'complete':
                self.setup_completed = True
        return self
    
    def _check_setup_completion(self):
        """Check if school setup is complete"""
        required_for_completion = [
            self.name,
            self.school_type,
            self.academic_config and 'grading_system' in self.academic_config,
            self.academic_config and 'ca_structure' in self.academic_config,
            self.subscription_config and 'plan' in self.subscription_config
        ]
        
        if all(required_for_completion):
            self.setup_completed = True
            self.setup_stage = 'complete'
    
    # ============ SERIALIZATION ============
    def to_dict(self):
        """Convert to dictionary for API responses"""
        # Create base dict manually since we're not using BaseModel
        base_dict = {
            'id': self.id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'name': self.name,
            'slug': self.slug,
            'school_type': self.school_type,
            'motto': self.motto,
            'vision': self.vision,
            'mission': self.mission,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'contact_whatsapp': self.contact_whatsapp,
            'website': self.website,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'teacher_registration_code': self.teacher_registration_code,
            'student_registration_code': self.student_registration_code,
            'codes_generated_at': self.codes_generated_at.isoformat() if self.codes_generated_at else None,
            'operational_details': self.operational_details,
            'academic_config': self.academic_config,
            'subscription_config': self.subscription_config,
            'setup_completed': self.setup_completed,
            'setup_stage': self.setup_stage,
            'subscription_status': self.subscription_status,
            'trial_ends_at': self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            'is_active': self.is_active,
            'student_count': self.student_count,
            'teacher_count': self.teacher_count
        }
        
        # Add calculated fields
        base_dict.update({
            'contact_channels': self.get_contact_channels(),
            'is_trial_expired': self.is_trial_expired(),
            'can_add_student': self.can_add_student(),
            'can_add_teacher': self.can_add_teacher(),
            'days_remaining_in_trial': self._get_trial_days_remaining(),
            'setup_progress': self._get_setup_progress()
        })
        
        return base_dict
    
    def _get_trial_days_remaining(self):
        """Get days remaining in trial"""
        if self.subscription_status != 'trial' or not self.trial_ends_at:
            return 0
        
        remaining = (self.trial_ends_at - datetime.utcnow()).days
        return max(0, remaining)
    
    def _get_setup_progress(self):
        """Calculate setup completion percentage"""
        stages = ['basic', 'contact', 'academic', 'grading', 'subscription', 'complete']
        stage_weights = {
            'basic': 20,
            'contact': 40,
            'academic': 60,
            'grading': 80,
            'subscription': 95,
            'complete': 100
        }
        
        return stage_weights.get(self.setup_stage, 0)
    
    # ============ REPRESENTATION ============
    def __repr__(self):
        return f'<School {self.name} ({self.slug})>'