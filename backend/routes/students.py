from flask import Blueprint, request, jsonify
from app import db
from models.student import Student
from models.school import School
from models.class_model import Class

students_bp = Blueprint('students', __name__)

@students_bp.route('', methods=['GET'])
def get_students():
    """
    Get all students with filtering
    """
    school_id = request.args.get('school_id')
    class_id = request.args.get('class_id')
    gender = request.args.get('gender')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    search = request.args.get('search')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 30, type=int)
    
    query = Student.query
    
    if school_id:
        query = query.filter_by(school_id=school_id)
    
    if class_id:
        query = query.filter_by(class_id=class_id)
    
    if gender:
        query = query.filter_by(gender=gender.lower())
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            db.or_(
                Student.first_name.ilike(f'%{search}%'),
                Student.last_name.ilike(f'%{search}%'),
                Student.student_code.ilike(f'%{search}%'),
                Student.admission_number.ilike(f'%{search}%'),
                Student.guardian_name.ilike(f'%{search}%'),
                Student.guardian_phone.ilike(f'%{search}%')
            )
        )
    
    query = query.order_by(Student.date_joined_platform.desc())
    
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Include class details
    students_data = []
    for student in paginated.items:
        student_dict = student.to_dict()
        
        if student.class_id:
            class_data = Class.query.get(student.class_id)
            if class_data:
                student_dict['class_details'] = class_data.to_dict()
        
        students_data.append(student_dict)
    
    return jsonify({
        'students': students_data,
        'total': paginated.total,
        'page': paginated.page,
        'per_page': paginated.per_page,
        'pages': paginated.pages
    })

@students_bp.route('/<student_id>', methods=['GET'])
def get_student(student_id):
    """
    Get specific student details
    """
    student = Student.query.get(student_id)
    
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    student_data = student.to_dict()
    
    # Get class details
    if student.class_id:
        class_data = Class.query.get(student.class_id)
        if class_data:
            student_data['class_details'] = class_data.to_dict()
            
            # Get form teacher
            if class_data.form_teacher_id:
                from models.teacher import Teacher
                teacher = Teacher.query.get(class_data.form_teacher_id)
                if teacher:
                    student_data['form_teacher'] = teacher.to_dict()
    
    # Get subjects for student's class
    from models.subject import Subject
    subjects = Subject.query.filter_by(
        class_id=student.class_id,
        is_active=True
    ).all()
    
    student_data['subjects'] = [subject.to_dict() for subject in subjects]
    
    return jsonify(student_data)

@students_bp.route('', methods=['POST'])
def create_student():
    """
    Create new student
    """
    data = request.get_json()
    
    required_fields = ['school_id', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check school exists and can add students
    school = School.query.get(data['school_id'])
    if not school:
        return jsonify({'error': 'School not found'}), 404
    
    if not school.can_add_student():
        return jsonify({'error': 'School has reached student limit'}), 400
    
    # Validate class if provided
    if data.get('class_id'):
        class_data = Class.query.filter_by(
            id=data['class_id'],
            school_id=data['school_id']
        ).first()
        
        if not class_data:
            return jsonify({'error': 'Class not found or belongs to different school'}), 404
    
    try:
        # Generate student code
        student_code = f"STU{school.id[:4].upper()}{str(school.student_count + 1).zfill(3)}"
        
        # Create student
        student = Student(
            school_id=data['school_id'],
            student_code=student_code,
            admission_number=data.get('admission_number'),
            first_name=data['first_name'],
            last_name=data['last_name'],
            other_names=data.get('other_names'),
            gender=data.get('gender'),
            email=data.get('email'),
            phone=data.get('phone'),
            guardian_name=data.get('guardian_name'),
            guardian_phone=data.get('guardian_phone'),
            guardian_email=data.get('guardian_email'),
            guardian_relationship=data.get('guardian_relationship'),
            class_id=data.get('class_id')
        )
        
        # Update school counter
        school.student_count += 1
        
        db.session.add(student)
        db.session.commit()
        
        return jsonify({
            'message': 'Student created successfully',
            'student': student.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@students_bp.route('/<student_id>', methods=['PUT'])
def update_student(student_id):
    """
    Update student information
    """
    student = Student.query.get(student_id)
    
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    updatable_fields = [
        'first_name', 'last_name', 'other_names',
        'gender', 'email', 'phone', 'admission_number',
        'guardian_name', 'guardian_phone', 'guardian_email',
        'guardian_relationship', 'class_id', 'is_active'
    ]
    
    for field in updatable_fields:
        if field in data:
            setattr(student, field, data[field])
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Student updated successfully',
            'student': student.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@students_bp.route('/<student_id>/transfer', methods=['POST'])
def transfer_student(student_id):
    """
    Transfer student to another class
    """
    student = Student.query.get(student_id)
    
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    data = request.get_json()
    
    if not data.get('new_class_id'):
        return jsonify({'error': 'new_class_id is required'}), 400
    
    # Check new class exists and belongs to same school
    new_class = Class.query.filter_by(
        id=data['new_class_id'],
        school_id=student.school_id
    ).first()
    
    if not new_class:
        return jsonify({'error': 'Class not found or belongs to different school'}), 404
    
    old_class_id = student.class_id
    student.class_id = data['new_class_id']
    
    try:
        db.session.commit()
        
        # Log transfer
        transfer_log = {
            'student_id': student_id,
            'old_class_id': old_class_id,
            'new_class_id': data['new_class_id'],
            'transferred_at': db.func.now().isoformat(),
            'transferred_by': 'system'  # Should be current user ID
        }
        
        return jsonify({
            'message': 'Student transferred successfully',
            'student': student.to_dict(),
            'transfer_log': transfer_log
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@students_bp.route('/import', methods=['POST'])
def import_students():
    """
    Bulk import students from CSV/Excel
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    school_id = request.form.get('school_id')
    
    if not school_id:
        return jsonify({'error': 'school_id is required'}), 400
    
    school = School.query.get(school_id)
    if not school:
        return jsonify({'error': 'School not found'}), 404
    
    # In a real implementation, parse CSV/Excel file
    # This is a simplified version
    
    data = request.get_json() if request.is_json else None
    
    if not data or not isinstance(data, list):
        return jsonify({'error': 'Invalid data format. Expected array of students.'}), 400
    
    results = {
        'successful': [],
        'failed': []
    }
    
    for i, student_data in enumerate(data):
        try:
            # Generate student code
            student_code = f"STU{school.id[:4].upper()}{str(school.student_count + 1 + i).zfill(3)}"
            
            student = Student(
                school_id=school_id,
                student_code=student_code,
                first_name=student_data.get('first_name', ''),
                last_name=student_data.get('last_name', ''),
                gender=student_data.get('gender'),
                guardian_name=student_data.get('guardian_name'),
                guardian_phone=student_data.get('guardian_phone'),
                class_id=student_data.get('class_id')
            )
            
            db.session.add(student)
            results['successful'].append(student_data)
            
        except Exception as e:
            results['failed'].append({
                'data': student_data,
                'error': str(e)
            })
    
    # Update school counter
    school.student_count += len(results['successful'])
    
    try:
        db.session.commit()
        return jsonify({
            'message': f'Import completed: {len(results["successful"])} successful, {len(results["failed"])} failed',
            'results': results
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500