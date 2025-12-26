from flask import Blueprint, jsonify, request
from app import db
from models.school import School
from models.class_model import Class
import re

utils_bp = Blueprint('utils', __name__)

@utils_bp.route('/school-slug-available', methods=['GET'])
def check_school_slug():
    """
    Check if school slug is available
    """
    slug = request.args.get('slug')
    
    if not slug:
        return jsonify({'error': 'slug parameter is required'}), 400
    
    # Clean slug
    clean_slug = re.sub(r'[^a-z0-9]+', '-', slug.lower()).strip('-')
    clean_slug = re.sub(r'-+', '-', clean_slug)
    
    # Check availability
    existing = School.query.filter_by(slug=clean_slug).first()
    
    return jsonify({
        'requested_slug': slug,
        'clean_slug': clean_slug,
        'available': not existing,
        'existing_school': existing.name if existing else None
    })

@utils_bp.route('/generate-class-display-name', methods=['GET'])
def generate_class_display_name():
    """
    Generate class display name from level and stream
    """
    level = request.args.get('level')
    stream = request.args.get('stream')
    
    if not level:
        return jsonify({'error': 'level parameter is required'}), 400
    
    display_name = Class.build_display_name(level, stream)
    
    return jsonify({
        'level': level,
        'stream': stream,
        'display_name': display_name
    })

@utils_bp.route('/search', methods=['GET'])
def global_search():
    """
    Global search across schools, teachers, students
    """
    query = request.args.get('q')
    school_id = request.args.get('school_id')
    
    if not query or len(query) < 2:
        return jsonify({'error': 'Search query must be at least 2 characters'}), 400
    
    results = {}
    
    # Search schools
    school_query = School.query.filter(
        db.or_(
            School.name.ilike(f'%{query}%'),
            School.slug.ilike(f'%{query}%'),
            School.contact_email.ilike(f'%{query}%')
        )
    ).limit(10)
    
    if school_id:
        school_query = school_query.filter_by(id=school_id)
    
    results['schools'] = [school.to_dict() for school in school_query.all()]
    
    # Search teachers
    from models.teacher import Teacher
    teacher_query = Teacher.query.filter(
        db.or_(
            Teacher.first_name.ilike(f'%{query}%'),
            Teacher.last_name.ilike(f'%{query}%'),
            Teacher.teacher_code.ilike(f'%{query}%'),
            Teacher.email.ilike(f'%{query}%')
        )
    ).limit(20)
    
    if school_id:
        teacher_query = teacher_query.filter_by(school_id=school_id)
    
    results['teachers'] = [teacher.to_dict() for teacher in teacher_query.all()]
    
    # Search students
    from models.student import Student
    student_query = Student.query.filter(
        db.or_(
            Student.first_name.ilike(f'%{query}%'),
            Student.last_name.ilike(f'%{query}%'),
            Student.student_code.ilike(f'%{query}%'),
            Student.admission_number.ilike(f'%{query}%')
        )
    ).limit(20)
    
    if school_id:
        student_query = student_query.filter_by(school_id=school_id)
    
    results['students'] = [student.to_dict() for student in student_query.all()]
    
    # Count total results
    total_results = sum(len(results[key]) for key in results)
    
    return jsonify({
        'query': query,
        'total_results': total_results,
        'results': results
    })

@utils_bp.route('/states', methods=['GET'])
def get_nigerian_states():
    """
    Get list of Nigerian states for dropdowns
    """
    states = [
        'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa',
        'Benue', 'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti',
        'Enugu', 'Federal Capital Territory', 'Gombe', 'Imo', 'Jigawa',
        'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara', 'Lagos',
        'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau',
        'Rivers', 'Sokoto', 'Taraba', 'Yobe', 'Zamfara'
    ]
    
    return jsonify({
        'country': 'Nigeria',
        'states': states,
        'count': len(states)
    })

@utils_bp.route('/school-types', methods=['GET'])
def get_school_types():
    """
    Get valid school types
    """
    return jsonify({
        'school_types': ['primary', 'junior', 'senior', 'combined'],
        'descriptions': {
            'primary': 'Primary school only (Basic 1-6)',
            'junior': 'Junior secondary school only (JSS 1-3)',
            'senior': 'Senior secondary school only (SSS 1-3)',
            'combined': 'Combined primary and secondary'
        }
    })