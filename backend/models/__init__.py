# models/__init__.py
from .school import School
from .user import User
from .teacher import Teacher
from .student import Student
from .class_model import Class
from .subject import Subject

__all__ = ['School', 'User', 'Teacher', 'Student', 'Class', 'Subject']