#routes/subjects.py
from flask import Blueprint, request, jsonify
from app import db
from models.subject import Subject
from models.teacher import Teacher

subjects_bp = Blueprint('subjects', __name__)

def serialize_subject(s):
    return {
        "id": str(s.id),
        "school_id": str(s.school_id) if s.school_id else None,
        "class_id": str(s.class_id) if s.class_id else None,
        "teacher_id": str(s.teacher_id) if s.teacher_id else None,
        "name": s.name,
        "code": s.code,
        "description": s.description,
        "is_active": s.is_active,
    }

@subjects_bp.route('/', methods=['GET'])
    """
    List all subjects with filtering
    """
    school_id = request.args.get('school_id')
    class_id = request.args.get('class_id')
    teacher_id = request.args.get('teacher_id')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    search = request.args.get('search')
    
    query = Subject.query
    
    if school_id:
        query = query.filter_by(school_id=school_id)
    
    if class_id:
        query = query.filter_by(class_id=class_id)
    
    if teacher_id:
        query = query.filter_by(teacher_id=teacher_id)
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            db.or_(
                Subject.name.ilike(f'%{search}%'),
                Subject.code.ilike(f'%{search}%'),
                Subject.description.ilike(f'%{search}%')
            )
        )
    
    query = query.order_by(Subject.name)
    
    subjects = query.all()
    
    # Include teacher details
    subjects_data = []
    for subject in subjects:
        subject_dict = serialize_subject(subject)
        
        # Get teacher details if teacher exists
        if subject.teacher_id:
            teacher = Teacher.query.get(subject.teacher_id)
            if teacher:
                subject_dict['teacher'] = {
                    'id': teacher.id,
                    'full_name': teacher.full_name,
                    'email': teacher.email,
                    'teacher_code': teacher.teacher_code
                }
        
        subjects_data.append(subject_dict)
    
    return jsonify({
        "success": True,
        "data": subjects_data,
        "count": len(subjects_data)
    }), 200

@subjects_bp.route('/class/<class_id>/with_teachers', methods=['GET'])
def subjects_with_teachers(class_id):
    """
    Get subjects of a class with teacher info
    """
    subjects = Subject.query.filter_by(class_id=class_id).all()
    
    data = []
    for s in subjects:
        teacher = None
        if s.teacher_id:
            teacher = Teacher.query.get(s.teacher_id)
        
        data.append({
            "id": str(s.id),
            "name": s.name,
            "code": s.code,
            "description": s.description,
            "teacher": {
                "id": str(teacher.id),
                "first_name": teacher.first_name,
                "last_name": teacher.last_name,
                "full_name": teacher.full_name
            } if teacher else None
        })
    
    return jsonify({
        "success": True,
        "data": data
    }), 200

@subjects_bp.route('/', methods=['POST'])
def create_subject():
    """
    Create new subject
    """
    data = request.get_json() or {}
    
    required = ["name", "class_id", "teacher_id", "school_id"]
    for field in required:
        if field not in data:
            return jsonify({
                "success": False,
                "message": f"{field} is required"
            }), 400
    
    subject = Subject(
        name=data["name"],
        code=data.get("code"),
        description=data.get("description"),
        class_id=data["class_id"],
        teacher_id=data["teacher_id"],
        school_id=data["school_id"],
        is_active=data.get("is_active", True)
    )
    
    try:
        db.session.add(subject)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "data": serialize_subject(subject)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Database error",
            "details": str(e)
        }), 500

@subjects_bp.route('/<subject_id>', methods=['GET'])
def get_subject(subject_id):
    """
    Get specific subject details
    """
    subject = Subject.query.get(subject_id)
    
    if not subject:
        return jsonify({
            "success": False,
            "message": "Subject not found"
        }), 404
    
    subject_data = serialize_subject(subject)
    
    # Get teacher details
    if subject.teacher_id:
        teacher = Teacher.query.get(subject.teacher_id)
        if teacher:
            subject_data['teacher'] = {
                'id': teacher.id,
                'full_name': teacher.full_name,
                'email': teacher.email
            }
    
    return jsonify({
        "success": True,
        "data": subject_data
    }), 200

@subjects_bp.route('/<subject_id>', methods=['PUT'])
def update_subject(subject_id):
    """
    Update subject information
    """
    subject = Subject.query.get(subject_id)
    
    if not subject:
        return jsonify({
            "success": False,
            "message": "Subject not found"
        }), 404
    
    data = request.get_json() or {}
    
    # Update fields
    updatable_fields = ['name', 'code', 'description', 'teacher_id', 'is_active']
    for field in updatable_fields:
        if field in data:
            setattr(subject, field, data[field])
    
    try:
        db.session.commit()
        return jsonify({
            "success": True,
            "data": serialize_subject(subject)
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Database error",
            "details": str(e)
        }), 500

@subjects_bp.route('/<subject_id>/ca-structure', methods=['GET'])
def get_ca_structure(subject_id):
    """
    Get CA structure for subject
    """
    subject = Subject.query.get(subject_id)
    
    if not subject:
        return jsonify({
            "success": False,
            "message": "Subject not found"
        }), 404
    
    # Get school for academic config
    from models.school import School
    school = School.query.get(subject.school_id)
    
    if not school:
        return jsonify({
            "success": False,
            "message": "School not found"
        }), 404
    
    return jsonify({
        "success": True,
        "data": {
            "subject_id": subject_id,
            "subject_name": subject.name,
            "ca_structure": subject.get_effective_ca_structure(school) if hasattr(subject, 'get_effective_ca_structure') else None,
            "has_override": subject.ca_structure_override is not None,
            "override": subject.ca_structure_override,
            "school_default": school.academic_config.get('ca_structure') if school.academic_config else None
        }
    }), 200