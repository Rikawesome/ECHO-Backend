from flask import Blueprint, request, jsonify
from app import db
from models.class_model import Class
from models.school import School
from models.teacher import Teacher
from models.student import Student
from models.subject import Subject

classes_bp = Blueprint('classes', __name__)

@classes_bp.route('/', methods=['GET'])
def get_classes():
    """
    Get all classes with filtering
    """
    school_id = request.args.get('school_id')
    level = request.args.get('level')
    stream = request.args.get('stream')
    academic_session = request.args.get('academic_session')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Class.query
    
    if school_id:
        query = query.filter_by(school_id=school_id)
    
    if level:
        query = query.filter_by(level=level)
    
    if stream:
        query = query.filter_by(stream=stream)
    
    if academic_session:
        query = query.filter_by(academic_session=academic_session)
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    query = query.order_by(Class.level, Class.stream, Class.academic_session)
    
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Include additional details
    classes_data = []
    for class_obj in paginated.items:
        class_dict = class_obj.to_dict()
        
        # Get form teacher details
        if class_obj.form_teacher_id:
            teacher = Teacher.query.get(class_obj.form_teacher_id)
            if teacher:
                class_dict['form_teacher'] = teacher.to_dict()
        
        # Get student count
        student_count = Student.query.filter_by(
            class_id=class_obj.id,
            is_active=True
        ).count()
        class_dict['student_count'] = student_count
        
        # Get subject count
        subject_count = Subject.query.filter_by(
            class_id=class_obj.id,
            is_active=True
        ).count()
        class_dict['subject_count'] = subject_count
        
        classes_data.append(class_dict)
    
    return jsonify({
        'classes': classes_data,
        'total': paginated.total,
        'page': paginated.page,
        'per_page': paginated.per_page,
        'pages': paginated.pages
    })

@classes_bp.route('/<class_id>', methods=['GET'])
def get_class(class_id):
    """
    Get specific class with detailed information
    """
    class_obj = Class.query.get(class_id)
    
    if not class_obj:
        return jsonify({'error': 'Class not found'}), 404
    
    class_data = class_obj.to_dict()
    
    # Get form teacher details
    if class_obj.form_teacher_id:
        teacher = Teacher.query.get(class_obj.form_teacher_id)
        if teacher:
            class_data['form_teacher'] = teacher.to_dict()
    
    # Get students
    students = Student.query.filter_by(
        class_id=class_id,
        is_active=True
    ).all()
    class_data['students'] = [student.to_dict() for student in students]
    
    # Get subjects
    subjects = Subject.query.filter_by(
        class_id=class_id,
        is_active=True
    ).all()
    
    subjects_data = []
    for subject in subjects:
        subject_dict = subject.to_dict()
        
        # Get teacher details for each subject
        if subject.teacher_id:
            teacher = Teacher.query.get(subject.teacher_id)
            if teacher:
                subject_dict['teacher'] = teacher.to_dict()
        
        subjects_data.append(subject_dict)
    
    class_data['subjects'] = subjects_data
    
    return jsonify(class_data)

@classes_bp.route('/', methods=['POST'])
def create_class():
    """
    Create new class
    """
    data = request.get_json()
    
    required_fields = ['school_id', 'level', 'academic_session']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check school exists
    school = School.query.get(data['school_id'])
    if not school:
        return jsonify({'error': 'School not found'}), 404
    
    # Build display name
    display_name = Class.build_display_name(
        data['level'],
        data.get('stream')
    )
    
    # Check for duplicate class
    existing = Class.query.filter_by(
        school_id=data['school_id'],
        display_name=display_name,
        academic_session=data['academic_session']
    ).first()
    
    if existing:
        return jsonify({'error': 'Class already exists for this session'}), 409
    
    # Validate form teacher if provided
    if data.get('form_teacher_id'):
        teacher = Teacher.query.filter_by(
            id=data['form_teacher_id'],
            school_id=data['school_id']
        ).first()
        
        if not teacher:
            return jsonify({'error': 'Teacher not found or belongs to different school'}), 404
    
    try:
        class_obj = Class(
            school_id=data['school_id'],
            level=data['level'],
            stream=data.get('stream'),
            display_name=display_name,
            academic_session=data['academic_session'],
            form_teacher_id=data.get('form_teacher_id'),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(class_obj)
        db.session.commit()
        
        return jsonify({
            'message': 'Class created successfully',
            'class': class_obj.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@classes_bp.route('/<class_id>', methods=['PUT'])
def update_class(class_id):
    """
    Update class information
    """
    class_obj = Class.query.get(class_id)
    
    if not class_obj:
        return jsonify({'error': 'Class not found'}), 404
    
    data = request.get_json()
    
    # Rebuild display name if level or stream changed
    level = data.get('level', class_obj.level)
    stream = data.get('stream', class_obj.stream)
    
    new_display_name = Class.build_display_name(level, stream)
    
    # Check for duplicates with new display name
    if new_display_name != class_obj.display_name or data.get('academic_session'):
        existing = Class.query.filter(
            Class.id != class_id,
            Class.school_id == class_obj.school_id,
            Class.display_name == new_display_name,
            Class.academic_session == data.get('academic_session', class_obj.academic_session)
        ).first()
        
        if existing:
            return jsonify({'error': 'Class with this name already exists for this session'}), 409
    
    # Update fields
    if 'level' in data:
        class_obj.level = data['level']
    
    if 'stream' in data:
        class_obj.stream = data['stream']
    
    if 'academic_session' in data:
        class_obj.academic_session = data['academic_session']
    
    class_obj.display_name = new_display_name
    
    if 'form_teacher_id' in data:
        # Validate teacher belongs to same school
        if data['form_teacher_id']:
            teacher = Teacher.query.filter_by(
                id=data['form_teacher_id'],
                school_id=class_obj.school_id
            ).first()
            
            if not teacher:
                return jsonify({'error': 'Teacher not found or belongs to different school'}), 404
        
        class_obj.form_teacher_id = data['form_teacher_id']
    
    if 'is_active' in data:
        class_obj.is_active = data['is_active']
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Class updated successfully',
            'class': class_obj.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@classes_bp.route('/<class_id>/students', methods=['GET'])
def get_class_students(class_id):
    """
    Get all students in a class
    """
    class_obj = Class.query.get(class_id)
    
    if not class_obj:
        return jsonify({'error': 'Class not found'}), 404
    
    students = Student.query.filter_by(
        class_id=class_id,
        is_active=True
    ).order_by(Student.last_name, Student.first_name).all()
    
    return jsonify([student.to_dict() for student in students])

@classes_bp.route('/<class_id>/subjects', methods=['GET'])
def get_class_subjects(class_id):
    """
    Get all subjects in a class
    """
    class_obj = Class.query.get(class_id)
    
    if not class_obj:
        return jsonify({'error': 'Class not found'}), 404
    
    subjects = Subject.query.filter_by(
        class_id=class_id,
        is_active=True
    ).order_by(Subject.name).all()
    
    subjects_data = []
    for subject in subjects:
        subject_dict = subject.to_dict()
        
        # Get teacher details
        if subject.teacher_id:
            teacher = Teacher.query.get(subject.teacher_id)
            if teacher:
                subject_dict['teacher'] = teacher.to_dict()
        
        subjects_data.append(subject_dict)
    
    return jsonify(subjects_data)

@classes_bp.route('/<class_id>/assign-form-teacher', methods=['POST'])
def assign_form_teacher(class_id):
    """
    Assign form teacher to class
    """
    class_obj = Class.query.get(class_id)
    
    if not class_obj:
        return jsonify({'error': 'Class not found'}), 404
    
    data = request.get_json()
    
    if not data.get('teacher_id'):
        return jsonify({'error': 'teacher_id is required'}), 400
    
    # Validate teacher belongs to same school
    teacher = Teacher.query.filter_by(
        id=data['teacher_id'],
        school_id=class_obj.school_id
    ).first()
    
    if not teacher:
        return jsonify({'error': 'Teacher not found or belongs to different school'}), 404
    
    class_obj.form_teacher_id = data['teacher_id']
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Form teacher assigned successfully',
            'class': class_obj.to_dict(),
            'teacher': teacher.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500