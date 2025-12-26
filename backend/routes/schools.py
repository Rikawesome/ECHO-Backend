from flask import Blueprint, request, jsonify
from app import db
from models.school import School
from models.user import User
from models.student import Student
from models.class_model import Class
import re

schools_bp = Blueprint('schools', __name__)

# ============ CREATE SCHOOL ============
@schools_bp.route('/', methods=['POST'])
def create_school():
    """
    Create a new school
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Required fields
        if not data.get('name'):
            return jsonify({'error': 'School name is required'}), 400
        
        if not data.get('school_type'):
            return jsonify({'error': 'School type is required'}), 400
        
        # Validate school type
        valid_types = ['primary', 'junior', 'senior', 'combined']
        if data['school_type'] not in valid_types:
            return jsonify({
                'error': f'School type must be one of: {", ".join(valid_types)}'
            }), 400
        
        # Generate slug if not provided
        if 'slug' not in data:
            slug = data['name'].lower()
            slug = re.sub(r'[^a-z0-9]+', '-', slug)
            slug = re.sub(r'^-|-$', '', slug)
            data['slug'] = slug
        
        # Check if slug already exists
        existing = School.query.filter_by(slug=data['slug']).first()
        if existing:
            return jsonify({'error': 'School with this slug already exists'}), 409
        
        # Create school
        school = School(**data)
        db.session.add(school)
        db.session.commit()
        
        return jsonify({
            'message': 'School created successfully',
            'school': school.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============ GET ALL SCHOOLS ============
@schools_bp.route('/', methods=['GET'])
def get_schools():
    """
    Get all schools (with filtering)
    """
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Filtering
    school_type = request.args.get('type')
    state = request.args.get('state')
    city = request.args.get('city')
    search = request.args.get('search')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    query = School.query
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    if school_type:
        query = query.filter_by(school_type=school_type)
    
    if state:
        query = query.filter_by(state=state)
    
    if city:
        query = query.filter_by(city=city)
    
    if search:
        query = query.filter(
            db.or_(
                School.name.ilike(f'%{search}%'),
                School.slug.ilike(f'%{search}%'),
                School.contact_email.ilike(f'%{search}%')
            )
        )
    
    # Order by creation date
    query = query.order_by(School.created_at.desc())
    
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'schools': [school.to_dict() for school in paginated.items],
        'total': paginated.total,
        'page': paginated.page,
        'per_page': paginated.per_page,
        'pages': paginated.pages
    })

# ============ GET SINGLE SCHOOL ============
@schools_bp.route('/<school_id>', methods=['GET'])
def get_school(school_id):
    """
    Get specific school details
    """
    school = School.query.get(school_id)
    
    if not school:
        return jsonify({'error': 'School not found'}), 404
    
    return jsonify(school.to_dict())

# ============ UPDATE SCHOOL ============
@schools_bp.route('/<school_id>', methods=['PUT'])
def update_school(school_id):
    """
    Update school information
    """
    school = School.query.get(school_id)
    
    if not school:
        return jsonify({'error': 'School not found'}), 404
    
    data = request.get_json()
    
    # Update basic fields
    updatable_fields = [
        'motto', 'vision', 'mission',
        'contact_email', 'contact_phone', 'contact_whatsapp',
        'website', 'address', 'city', 'state', 'country'
    ]
    
    for field in updatable_fields:
        if field in data:
            setattr(school, field, data[field])
    
    # Update academic config
    if 'academic_config' in data:
        school.update_academic_config(data['academic_config'])
    
    # Update operational details
    if 'operational_details' in data:
        for category, details in data['operational_details'].items():
            school.add_operational_detail(category, details)
    
    # Update subscription config
    if 'subscription_config' in data:
        school.update_subscription_config(data['subscription_config'])
    
    # Update setup stage
    if 'setup_stage' in data:
        school.update_setup_stage(data['setup_stage'])
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'School updated successfully',
            'school': school.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============ GET SCHOOL STATS ============
@schools_bp.route('/<school_id>/stats', methods=['GET'])
def get_school_stats(school_id):
    """
    Get school statistics
    """
    school = School.query.get(school_id)
    
    if not school:
        return jsonify({'error': 'School not found'}), 404
    
    # Get user counts by role
    user_counts = db.session.query(
        User.role,
        db.func.count(User.id).label('count')
    ).filter_by(
        school_id=school_id,
        status='active'
    ).group_by(User.role).all()
    
    role_counts = {role: count for role, count in user_counts}
    
    # Get student stats
    active_students = Student.query.filter_by(
        school_id=school_id,
        is_active=True
    ).count()
    
    class_count = Class.query.filter_by(
        school_id=school_id,
        is_active=True
    ).count()
    
    return jsonify({
        'school_id': school_id,
        'student_count': school.student_count,
        'active_students': active_students,
        'teacher_count': school.teacher_count,
        'class_count': class_count,
        'role_distribution': role_counts,
        'subscription_status': school.subscription_status,
        'trial_days_remaining': school._get_trial_days_remaining(),
        'setup_progress': school._get_setup_progress()
    })

# ============ REGENERATE CODES ============
@schools_bp.route('/<school_id>/regenerate-codes', methods=['POST'])
def regenerate_codes(school_id):
    """
    Regenerate teacher/student registration codes
    """
    school = School.query.get(school_id)
    
    if not school:
        return jsonify({'error': 'School not found'}), 404
    
    # Regenerate codes
    school.teacher_registration_code = school._generate_registration_code('teacher')
    school.student_registration_code = school._generate_registration_code('student')
    school.codes_generated_at = db.func.now()
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Registration codes regenerated',
            'teacher_code': school.teacher_registration_code,
            'student_code': school.student_registration_code,
            'generated_at': school.codes_generated_at.isoformat()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============ JOIN SCHOOL ============
@schools_bp.route('/join', methods=['POST'])
def join_school():
    """
    Join a school using registration code
    """
    data = request.get_json()
    
    required = ['user_id', 'registration_code', 'role_type']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Validate role type
    if data['role_type'] not in ['teacher', 'student']:
        return jsonify({'error': 'role_type must be "teacher" or "student"'}), 400
    
    # Get user
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Find school by registration code
    if data['role_type'] == 'teacher':
        school = School.query.filter_by(
            teacher_registration_code=data['registration_code']
        ).first()
    else:
        school = School.query.filter_by(
            student_registration_code=data['registration_code']
        ).first()
    
    if not school:
        return jsonify({'error': 'Invalid registration code'}), 404
    
    # Check if user can join this school
    if user.school_id:
        return jsonify({'error': 'User already belongs to a school'}), 400
    
    try:
        # Update user with school and role
        user.school_id = school.id
        user.role = data['role_type']
        
        # Create Teacher/Student record
        if data['role_type'] == 'teacher':
            from models.teacher import Teacher
            teacher_code = f"TCH{school.id[:4].upper()}{str(school.teacher_count + 1).zfill(3)}"
            teacher = Teacher(
                id=user.id,  # Same ID as user
                school_id=school.id,
                teacher_code=teacher_code,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email
            )
            school.teacher_count += 1
            db.session.add(teacher)
        else:
            from models.student import Student
            student_code = f"STU{school.id[:4].upper()}{str(school.student_count + 1).zfill(3)}"
            student = Student(
                school_id=school.id,
                student_code=student_code,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email
            )
            school.student_count += 1
            db.session.add(student)
        
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully joined {school.name} as {data["role_type"]}',
            'school': school.to_dict(),
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============ CREATE AND JOIN SCHOOL ============
@schools_bp.route('/create-and-join', methods=['POST'])
def create_and_join_school():
    """
    Create a school and join as owner
    """
    data = request.get_json()
    
    required = ['user_id', 'school_name', 'school_type']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.school_id:
        return jsonify({'error': 'User already belongs to a school'}), 400
    
    try:
        # Create slug
        slug = re.sub(r'[^a-z0-9]+', '-', data['school_name'].lower()).strip('-')
        slug = re.sub(r'-+', '-', slug)
        
        # Check if slug exists
        counter = 1
        original_slug = slug
        while School.query.filter_by(slug=slug).first():
            slug = f"{original_slug}-{counter}"
            counter += 1
        
        # Create school
        school = School(
            name=data['school_name'],
            slug=slug,
            school_type=data['school_type'],
            contact_email=user.email
        )
        
        # Generate registration codes
        school.teacher_registration_code = school._generate_registration_code('teacher')
        school.student_registration_code = school._generate_registration_code('student')
        
        db.session.add(school)
        db.session.flush()  # Get school ID
        
        # Update user as owner
        user.school_id = school.id
        user.role = 'owner'
        
        db.session.commit()
        
        return jsonify({
            'message': 'School created successfully',
            'school': school.to_dict(),
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500