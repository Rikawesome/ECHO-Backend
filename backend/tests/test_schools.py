#!/usr/bin/env python
"""
Tests for School Model
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pytest
from app import create_app
from models.school import School
from models.base import db

class TestSchoolModel:
    """Test cases for School model"""
    
    @pytest.fixture(scope='function')
    def app(self):
        """Create test app"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()
    
    def test_school_creation(self, app):
        """Test basic school creation"""
        with app.app_context():
            school = School(
                name='Test Academy',
                slug='test-academy',
                school_type='secondary',
                motto='Education for All',
                contact_phone='08012345678'
            )
            
            db.session.add(school)
            db.session.commit()
            
            assert school.id is not None
            assert school.teacher_registration_code is not None
            assert school.student_registration_code is not None
            assert school.subscription_status == 'trial'
            assert school.setup_completed == False
    
    def test_registration_code_format(self, app):
        """Test registration code generation"""
        with app.app_context():
            school = School(
                name='Premium Hills',
                slug='premium-hills',
                school_type='secondary'
            )
            
            # Check teacher code format
            assert school.teacher_registration_code.startswith('TCH-')
            assert len(school.teacher_registration_code) == 16  # TCH-PRE123-ABC789
            
            # Check student code format
            assert school.student_registration_code.startswith('STU-')
            assert len(school.student_registration_code) == 16
    
    def test_academic_config_defaults(self, app):
        """Test default academic config based on school type"""
        with app.app_context():
            # Test primary school
            primary = School(
                name='Primary Test',
                slug='primary-test',
                school_type='primary'
            )
            assert primary.academic_config['grading_system'] == 'primary_scale'
            assert primary.academic_config['enable_overall_grades'] == False
            
            # Test secondary school
            secondary = School(
                name='Secondary Test',
                slug='secondary-test',
                school_type='senior'
            )
            assert secondary.academic_config['grading_system'] == 'waec'
            assert secondary.academic_config['enable_overall_grades'] == True
    
    def test_trial_expiration(self, app):
        """Test trial expiration logic"""
        with app.app_context():
            school = School(
                name='Trial School',
                slug='trial-school',
                school_type='secondary'
            )
            
            # Set trial to end yesterday
            school.trial_ends_at = datetime.utcnow() - timedelta(days=1)
            
            assert school.is_trial_expired() == True
            
            # Set trial to end tomorrow
            school.trial_ends_at = datetime.utcnow() + timedelta(days=1)
            
            assert school.is_trial_expired() == False
    
    def test_contact_channels(self, app):
        """Test contact channels collection"""
        with app.app_context():
            school = School(
                name='Contact School',
                slug='contact-school',
                school_type='secondary',
                contact_phone='08011111111',
                contact_whatsapp='08022222222',
                contact_email='test@school.edu.ng',
                website='school.edu.ng'
            )
            
            channels = school.get_contact_channels()
            
            assert len(channels) == 4
            channel_types = [c['type'] for c in channels]
            assert 'phone' in channel_types
            assert 'whatsapp' in channel_types
            assert 'email' in channel_types
            assert 'website' in channel_types
    
    def test_operational_details(self, app):
        """Test adding operational details"""
        with app.app_context():
            school = School(
                name='Ops School',
                slug='ops-school',
                school_type='secondary'
            )
            
            # Initially should be None
            assert school.operational_details is None
            
            # Add boarding details
            school.add_operational_detail('boarding', {
                'has_boarding': True,
                'capacity': 200
            })
            
            assert school.operational_details is not None
            assert school.operational_details['boarding']['has_boarding'] == True
            assert school.operational_details['boarding']['capacity'] == 200
            
            # Add facilities
            school.add_operational_detail('facilities', {
                'has_lab': True,
                'has_library': True
            })
            
            assert 'facilities' in school.operational_details
    
    def test_setup_progression(self, app):
        """Test setup stage progression"""
        with app.app_context():
            school = School(
                name='Setup School',
                slug='setup-school',
                school_type='secondary'
            )
            
            assert school.setup_stage == 'basic'
            assert school.setup_completed == False
            
            # Update stage
            school.update_setup_stage('academic')
            assert school.setup_stage == 'academic'
            
            # Complete setup
            school.update_setup_stage('complete')
            assert school.setup_stage == 'complete'
            assert school.setup_completed == True
    
    def test_plan_limits(self, app):
        """Test student/teacher limits based on plan"""
        with app.app_context():
            school = School(
                name='Limit School',
                slug='limit-school',
                school_type='secondary'
            )
            
            # During trial
            assert school.can_add_student() == True
            assert school.can_add_teacher() == True
            
            # Simulate reaching limits
            school.student_count = 49
            school.teacher_count = 9
            assert school.can_add_student() == True
            assert school.can_add_teacher() == True
            
            school.student_count = 50
            school.teacher_count = 10
            assert school.can_add_student() == False
            assert school.can_add_teacher() == False

if __name__ == '__main__':
    # Run tests directly
    pytest.main([__file__, '-v'])