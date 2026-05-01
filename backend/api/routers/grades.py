"""Grades router."""
from fastapi import APIRouter

from backend.api.schemas import GradeSave
from backend.services.grade_service import GradeService

router = APIRouter()


@router.get('/student/{hv_id}')
def by_student(hv_id: int):
    return GradeService.get_grades_by_student(hv_id)


@router.get('/student/{hv_id}/gpa')
def gpa(hv_id: int):
    return GradeService.get_gpa_stats(hv_id)


@router.get('/class/{lop_id}')
def by_class(lop_id: str):
    return GradeService.get_grades_by_class(lop_id)


@router.get('/teacher/{gv_id}/rating')
def teacher_rating(gv_id: int):
    return GradeService.get_teacher_avg_rating(gv_id)


@router.post('')
def save(req: GradeSave):
    GradeService.save_grade(req.hv_id, req.lop_id, req.diem_qt, req.diem_thi, req.gv_id)
    return {'status': 'saved'}
