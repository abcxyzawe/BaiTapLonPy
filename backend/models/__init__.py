"""Package chua tat ca domain model cua he thong.

Bao gom:
  - Entity (abstract base cho moi entity)
  - User hierarchy: User, Student, Teacher, Employee, Admin (trong sub-package user/)
  - Entity concrete: Course, Semester, Klass, Curriculum, Registration,
                     Payment, Grade, Notification, Review, Schedule,
                     ExamSchedule, Attendance, AuditLog

Import thuong dung:
    from backend.models import Student, Teacher, Klass, Registration
"""
from .entity import Entity

# User hierarchy (re-export tu sub-package)
from .user import User, Student, Teacher, Employee, Admin

# Cac entity khac
from .course import Course
from .semester import Semester
from .klass import Klass
from .curriculum import Curriculum
from .registration import Registration
from .payment import Payment
from .grade import Grade
from .notification import Notification
from .review import Review
from .schedule import Schedule
from .exam_schedule import ExamSchedule
from .attendance import Attendance
from .audit_log import AuditLog

__all__ = [
    'Entity',
    'User', 'Student', 'Teacher', 'Employee', 'Admin',
    'Course', 'Semester', 'Klass', 'Curriculum',
    'Registration', 'Payment', 'Grade',
    'Notification', 'Review',
    'Schedule', 'ExamSchedule', 'Attendance',
    'AuditLog',
]
