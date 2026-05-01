"""Stats router - 9 endpoint dashboard."""
from fastapi import APIRouter

from backend.services.stats_service import StatsService

router = APIRouter()


@router.get('/admin/overview')
def admin_overview():
    return StatsService.admin_overview()


@router.get('/semester/{semester_id}')
def by_semester(semester_id: str):
    return StatsService.stats_by_semester(semester_id)


@router.get('/top-classes')
def top_classes(limit: int = 5):
    return StatsService.top_classes(limit=limit)


@router.get('/recent-activity')
def recent_activity(limit: int = 5):
    return StatsService.recent_activity(limit=limit)


@router.get('/by-course')
def by_course():
    return StatsService.by_course()


@router.get('/class-enrollment')
def class_enrollment():
    return StatsService.class_enrollment()


@router.get('/employee/{emp_id}/today')
def employee_today(emp_id: int):
    return StatsService.employee_today(emp_id)


@router.get('/pending-registrations')
def pending_regs(limit: int = 5):
    return StatsService.recent_pending_registrations(limit=limit)


@router.get('/teacher/{gv_id}/overview')
def teacher_overview(gv_id: int):
    return StatsService.teacher_overview(gv_id)
