"""Package chua cac class User + 4 role con ke thua.

Moi class 1 file rieng de de maintain. Import nhu sau:

    from backend.models.user import User, Student, Teacher, Employee, Admin

hoac import tung class rieng:

    from backend.models.user.student import Student
"""
from .base import User
from .student import Student
from .teacher import Teacher
from .employee import Employee
from .admin import Admin

__all__ = ['User', 'Student', 'Teacher', 'Employee', 'Admin']
