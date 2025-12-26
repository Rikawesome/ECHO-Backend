from flask import Blueprint, request, jsonify
from app import db
from models.teacher import Teacher
from models.user import User
from models.school import School
import uuid

teachers_bp = Blueprint('teachers', __name__)

@teachers_bp.route('/', methods=['GET'])
def get_teachers():
    """
    Get all teachers with filtering
    """
    school_id = request.args.get('school_id')
    role = request.args.get('role')
    status = request.args.get('status')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    search = request.args.get('search')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Teacher.query
    
    if school_id:
        query = query.filter_by(school_id=school_id)
    
    if role:
        query = query.filter_by(role=role)
    
    if status:
        query = query.filter_by(employment_status=status)
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            db.or_(
                Teacher.first_name.ilike(f'%{search}%'),
                Teacher.last_name.ilike(f'%{search}%'),
                Teacher.email.ilike(f'%{search}%'),
                Teacher.teacher_code.ilike(f'%{search}%'),
                Teacher.staff_number.ilike(f'%{search}%')
            )
        )
    
    query = query.order_by(Teacher.date_joined_platform.desc())
    
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'teachers': [teacher.to_dict() for teacher in paginated.items],
        'total': paginated.total,
        'page': paginated.page,
        'per_page': paginated.per_page,
        'pages': paginated.pages
    })

@teachers_bp.route('/<teacher_id>', methods=['GET'])
def get_teacher(teacher_id):
    """
    Get specific teacher details
    """
    teacher = Teacher.query.get(teacher_id)
    
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404
    
    teacher_data = teacher.to_dict()
    
    # Get associated user account
    user = User.query.get(teacher_id)
    if user:
        teacher_data['user_account'] = {
            'email': user.email,
            'status': user.status,
            'verified_at': user.verified_at.isoformat() if user.verified_at else None
        }
    
    # Get classes taught by this teacher
    from models.class_model import Class
    classes = Class.query.filter_by(form_teacher_id=teacher_id).all()
    teacher_data['form_teacher_of'] = [cls.to_dict() for cls in classes]
    
    # Get subjects taught
    from models.subject import Subject
    subjects = Subject.query.filter_by(teacher_id=teacher_id).all()
    teacher_data['subjects_taught'] = [subject.to_dict() for subject in subjects]
    
    return jsonify(teacher_data)

@teachers_bp.route('', methods=['POST'])
def create_teacher():
    """
    Create new teacher (admin only)
    """
    data = request.get_json()
    
    required_fields = ['school_id', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check school exists and can add teachers
    school = School.query.get(data['school_id'])
    if not school:
        return jsonify({'error': 'School not found'}), 404
    
    if not school.can_add_teacher():
        return jsonify({'error': 'School has reached teacher limit'}), 400
    
    try:
        # Generate teacher code
        teacher_code = f"TCH{school.id[:4].upper()}{str(school.teacher_count + 1).zfill(3)}"
        
        # Create teacher
        teacher = Teacher(
            school_id=data['school_id'],
            teacher_code=teacher_code,
            staff_number=data.get('staff_number'),
            first_name=data['first_name'],
            last_name=data['last_name'],
            other_names=data.get('other_names'),
            gender=data.get('gender'),
            email=data.get('email'),
            phone=data.get('phone'),
            role=data.get('role', 'teacher'),
            employment_status=data.get('employment_status', 'active')
        )
        
        # Create user account if email provided
        if data.get('email'):
            user = User(
                id=teacher.id,  # Same ID
                school_id=data['school_id'],
                role='teacher',
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                phone=data.get('phone'),
                status='active'
            )
            # Generate temporary password
            temp_password = str(uuid.uuid4())[:8]
            user.set_password(temp_password)
            user.activate()
            
            db.session.add(user)
            teacher_data['temporary_password'] = temp_password
        
        # Update school counter
        school.teacher_count += 1
        
        db.session.add(teacher)
        db.session.commit()
        
        teacher_data = teacher.to_dict()
        
        return jsonify({
            'message': 'Teacher created successfully',
            'teacher': teacher_data
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@teachers_bp.route('/<teacher_id>', methods=['PUT'])
def update_teacher(teacher_id):
    """
    Update teacher information
    """
    teacher = Teacher.query.get(teacher_id)
    
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    updatable_fields = [
        'first_name', 'last_name', 'other_names',
        'gender', 'email', 'phone', 'role',
        'employment_status', 'staff_number'
    ]
    
    for field in updatable_fields:
        if field in data:
            setattr(teacher, field, data[field])
    
    # Update user account if email changed
    if 'email' in data:
        user = User.query.get(teacher_id)
        if user:
            user.email = data['email']
    
    # Update is_active based on employment_status
    if 'employment_status' in data:
        teacher.is_active = (data['employment_status'] == 'active')
        
        # Also update user status
        user = User.query.get(teacher_id)
        if user:
            if data['employment_status'] in ['active', 'resigned', 'retired']:
                user.status = 'active'
            else:
                user.status = 'suspended'
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Teacher updated successfully',
            'teacher': teacher.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@teachers_bp.route('/<teacher_id>/subjects', methods=['GET'])
def get_teacher_subjects(teacher_id):
    """
    Get all subjects taught by teacher
    """
    from models.subject import Subject
    from models.class_model import Class
    
    subjects = Subject.query.filter_by(
        teacher_id=teacher_id,
        is_active=True
    ).all()
    
    result = []
    for subject in subjects:
        subject_data = subject.to_dict()
        
        # Get class details
        class_data = Class.query.get(subject.class_id)
        if class_data:
            subject_data['class_details'] = class_data.to_dict()
        
        result.append(subject_data)
    
    return jsonify(result)

@teachers_bp.route('/<teacher_id>/activate', methods=['POST'])
def activate_teacher(teacher_id):
    """
    Activate teacher account
    """
    teacher = Teacher.query.get(teacher_id)
    
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404
    
    teacher.employment_status = 'active'
    teacher.is_active = True
    
    # Activate user account
    user = User.query.get(teacher_id)
    if user:
        user.activate()
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Teacher activated successfully',
            'teacher': teacher.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500