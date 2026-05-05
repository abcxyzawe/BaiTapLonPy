"""Notifications router."""
from fastapi import APIRouter, HTTPException

from backend.api.schemas import NotificationSend
from backend.services.notification_service import NotificationService

router = APIRouter()


@router.get('')
def list_all():
    return NotificationService.get_all()


@router.get('/recent')
def recent(limit: int = 10):
    return NotificationService.get_recent(limit=limit)


@router.get('/student/{hv_id}')
def for_student(hv_id: int):
    return NotificationService.get_for_student(hv_id)


@router.get('/teacher/{gv_id}')
def sent_by_teacher(gv_id: int, limit: int = 10):
    return NotificationService.get_sent_by_teacher(gv_id, limit=limit)


@router.post('')
def send(req: NotificationSend):
    NotificationService.send(req.tu_id, req.tieu_de, req.noi_dung,
                             den_lop=req.den_lop, den_hv_id=req.den_hv_id,
                             loai=req.loai)
    return {'status': 'sent'}


@router.delete('/{notif_id}')
def delete(notif_id: int):
    affected = NotificationService.delete(notif_id)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Thông báo id={notif_id} không tồn tại')
    return {'status': 'deleted'}
