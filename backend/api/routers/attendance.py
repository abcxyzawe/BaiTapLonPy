"""Attendance router."""
from typing import Optional

from fastapi import APIRouter

from backend.api.schemas import AttendanceMark
from backend.services.attendance_service import AttendanceService

router = APIRouter()


@router.get('/schedule/{schedule_id}')
def for_schedule(schedule_id: int):
    return AttendanceService.get_for_schedule(schedule_id)


@router.get('/student/{hv_id}')
def for_student(hv_id: int, lop_id: Optional[str] = None):
    return AttendanceService.get_for_student(hv_id, lop_id=lop_id)


@router.get('/rate/{hv_id}/{lop_id}')
def attendance_rate(hv_id: int, lop_id: str):
    return {'rate': AttendanceService.attendance_rate(hv_id, lop_id)}


@router.get('/class/{lop_id}/summary')
def class_summary(lop_id: str):
    """Summary diem danh tat ca HV trong lop - dung de tinh CC hang loat."""
    return AttendanceService.class_summary(lop_id)


@router.post('')
def mark(req: AttendanceMark):
    AttendanceService.mark(
        req.schedule_id, req.hv_id, req.trang_thai,
        gio_vao=req.gio_vao, recorded_by=req.recorded_by, ghi_chu=req.ghi_chu
    )
    return {'status': 'marked'}
