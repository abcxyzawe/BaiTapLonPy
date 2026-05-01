"""Schedules router."""
from datetime import date as Date

from fastapi import APIRouter

from backend.api.schemas import ScheduleCreate
from backend.services.schedule_service import ScheduleService

router = APIRouter()


@router.get('/today')
def today():
    return ScheduleService.get_today()


@router.get('/week')
def by_week(start: Date):
    return ScheduleService.get_by_week(start)


@router.get('/student/{hv_id}/week')
def for_student_week(hv_id: int, start: Date):
    return ScheduleService.get_for_student_week(hv_id, start)


@router.get('/teacher/{gv_id}/week')
def for_teacher_week(gv_id: int, start: Date):
    return ScheduleService.get_for_teacher_week(gv_id, start)


@router.get('/class/{lop_id}')
def for_class(lop_id: str):
    return ScheduleService.get_for_class(lop_id)


@router.post('')
def create(req: ScheduleCreate):
    ScheduleService.create(
        req.lop_id, req.ngay, req.gio_bat_dau, req.gio_ket_thuc,
        phong=req.phong, buoi_so=req.buoi_so, noi_dung=req.noi_dung,
        thu=req.thu, trang_thai=req.trang_thai
    )
    return {'status': 'created'}
