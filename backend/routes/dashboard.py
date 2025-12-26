from flask import Blueprint, jsonify, request
from app import db
from models.school import School
from models.user import User
from models.student import Student
from models.teacher import Teacher
from models.class_model import Class
from models.subject import Subject
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/overview/<school_id>', methods=['GET'])
def school_overview(school_id):
    """
    Get school dashboard overview
    """
    school = School.query.get(school_id)
    
    if not school:
        return jsonify({'error': 'School not found'}), 404
    
    # Basic counts
    total_students = Student.query.filter_by(school_id=school_id).count()
    active_students = Student.query.filter_by(school_id=school_id, is_active=True).count()
    
    total_teachers = Teacher.query.filter_by(school_id=school_id).count()
    active_teachers = Teacher.query.filter_by(school_id=school_id, is_active=True).count()
    
    total_classes = Class.query.filter_by(school_id=school_id).count()
    active_classes = Class.query.filter_by(school_id=school_id, is_active=True).count()
    
    total_subjects = Subject.query.filter_by(school_id=school_id).count()
    
    # Recent registrations (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    new_students = Student.query.filter(
        Student.school_id == school_id,
        Student.date_joined_platform >= thirty_days_ago
    ).count()
    
    new_teachers = Teacher.query.filter(
        Teacher.school_id == school_id,
        Teacher.date_joined_platform >= thirty_days_ago
    ).count()
    
    return jsonify({
        'school_id': school_id,
        'school_name': school.name,
        'summary': {
            'students': {
                'total': total_students,
                'active': active_students,
                'new_last_30_days': new_students,
                'inactive': total_students - active_students
            },
            'teachers': {
                'total': total_teachers,
                'active': active_teachers,
                'new_last_30_days': new_teachers,
                'inactive': total_teachers - active_teachers
            },
            'classes': {
                'total': total_classes,
                'active': active_classes
            },
            'subjects': {
                'total': total_subjects
            }
        },
        'subscription': {
            'status': school.subscription_status,
            'trial_ends_at': school.trial_ends_at.isoformat() if school.trial_ends_at else None,
            'days_remaining': school._get_trial_days_remaining() if hasattr(school, '_get_trial_days_remaining') else 0
        }
    })

@dashboard_bp.route('/teacher/<teacher_id>', methods=['GET'])
def teacher_dashboard(teacher_id):
    """
    Get teacher-specific dashboard
    """
    teacher = Teacher.query.get(teacher_id)
    
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404
    
    # Classes where teacher is form teacher
    form_teacher_classes = Class.query.filter_by(
        form_teacher_id=teacher_id,
        is_active=True
    ).all()
    
    # Subjects taught by teacher
    subjects = Subject.query.filter_by(
        teacher_id=teacher_id,
        is_active=True
    ).all()
    
    # Count students across all subjects
    total_students = 0
    for subject in subjects:
        class_students = Student.query.filter_by(
            class_id=subject.class_id,
            is_active=True
        ).count()
        total_students += class_students
    
    return jsonify({
        'teacher_id': teacher_id,
        'teacher_name': teacher.full_name,
        'summary': {
            'form_teacher_of': len(form_teacher_classes),
            'subjects_taught': len(subjects),
            'total_students': total_students,
            'active_status': teacher.is_active
        },
        'details': {
            'form_teacher_classes': [cls.to_dict() for cls in form_teacher_classes],
            'subjects': [subject.to_dict() for subject in subjects]
        }
    })