"""Schedules router."""
from datetime import date as Date

from fastapi import APIRouter, HTTPException

from backend.api.schemas import ScheduleCreate, ScheduleBatchCreate
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


@router.get('/student/{hv_id}/nearest-week')
def nearest_week_student(hv_id: int, ref: Date):
    """Tra ve Monday cua tuan gan ref nhat ma HV co lich. None neu khong co buoi nao."""
    monday = ScheduleService.nearest_week_for_student(hv_id, ref)
    return {'monday': monday.isoformat() if monday else None}


@router.get('/teacher/{gv_id}/week')
def for_teacher_week(gv_id: int, start: Date):
    return ScheduleService.get_for_teacher_week(gv_id, start)


@router.get('/teacher/{gv_id}/nearest-week')
def nearest_week_teacher(gv_id: int, ref: Date):
    monday = ScheduleService.nearest_week_for_teacher(gv_id, ref)
    return {'monday': monday.isoformat() if monday else None}


@router.get('/class/{lop_id}')
def for_class(lop_id: str):
    return ScheduleService.get_for_class(lop_id)


@router.post('')
def create(req: ScheduleCreate):
    sid = ScheduleService.create(
        req.lop_id, req.ngay, req.gio_bat_dau, req.gio_ket_thuc,
        phong=req.phong, buoi_so=req.buoi_so, noi_dung=req.noi_dung,
        thu=req.thu, trang_thai=req.trang_thai,
        meeting_url=req.meeting_url
    )
    return {'id': sid, 'status': 'created'}


@router.post('/batch')
def create_batch(req: ScheduleBatchCreate):
    """Bulk tao buoi hoc theo pattern: cac thu trong tuan, lap N tuan."""
    ids = ScheduleService.create_batch(
        lop_id=req.lop_id, days_of_week=req.days_of_week,
        start_date=req.start_date, num_weeks=req.num_weeks,
        gio_bat_dau=req.gio_bat_dau, gio_ket_thuc=req.gio_ket_thuc,
        phong=req.phong, start_buoi_so=req.start_buoi_so,
        noi_dung=req.noi_dung
    )
    return {'created_ids': ids, 'count': len(ids), 'status': 'ok'}


@router.delete('/{sched_id}')
def delete_schedule(sched_id: int):
    if not ScheduleService.delete(sched_id):
        raise HTTPException(status_code=404, detail=f'Buoi hoc id={sched_id} khong ton tai')
    return {'status': 'deleted'}


@router.get('/{sched_id}')
def get_schedule(sched_id: int):
    row = ScheduleService.get_by_id(sched_id)
    if not row:
        raise HTTPException(status_code=404, detail=f'Buoi hoc id={sched_id} khong ton tai')
    return row


@router.put('/{sched_id}')
def update_schedule(sched_id: int, req: ScheduleCreate):
    """Update buoi hoc. Reuse ScheduleCreate schema (lop_id se bi ignore - khong cho doi lop)."""
    fields = req.model_dump(exclude_unset=True)
    fields.pop('lop_id', None)  # khong cho doi lop_id
    if not ScheduleService.update(sched_id, **fields):
        raise HTTPException(status_code=404, detail=f'Khong cap nhat duoc id={sched_id}')
    return {'status': 'ok'}


@router.get('/student/{hv_id}/all')
def get_all_for_student(hv_id: int, from_date: Date = None, to_date: Date = None):
    """Tat ca buoi hoc cua HV trong khoang ngay (default 6 thang truoc + sau)."""
    return ScheduleService.get_all_for_student(hv_id, from_date, to_date)


@router.get('/teacher/{gv_id}/all')
def get_all_for_teacher(gv_id: int, from_date: Date = None, to_date: Date = None):
    """Tat ca buoi day cua GV trong khoang ngay."""
    return ScheduleService.get_all_for_teacher(gv_id, from_date, to_date)


@router.post('/check-conflict')
def check_conflict(payload: dict):
    """Check trung lich. Body: {ngay, gio_bat_dau, gio_ket_thuc, phong?, lop_id?, gv_id?, exclude_id?}.
    Tra ve list cac buoi conflict (cung phong/lop/GV + overlap thoi gian)."""
    from datetime import date as Date, time as Time
    try:
        ngay = Date.fromisoformat(payload['ngay'])
        gio_bd = Time.fromisoformat(payload['gio_bat_dau'])
        gio_kt = Time.fromisoformat(payload['gio_ket_thuc'])
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f'Tham so sai: {e}')
    rows = ScheduleService.check_conflicts(
        ngay, gio_bd, gio_kt,
        phong=payload.get('phong'),
        lop_id=payload.get('lop_id'),
        gv_id=payload.get('gv_id'),
        exclude_id=payload.get('exclude_id'),
    )
    return {'conflicts': rows, 'count': len(rows)}
