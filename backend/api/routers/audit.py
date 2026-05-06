"""Audit router."""
from datetime import date as Date
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.api.schemas import AuditLog
from backend.services.audit_service import AuditService

router = APIRouter()


@router.get('')
def list_logs(
    limit: int = 100,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    from_date: Optional[Date] = None,
    to_date: Optional[Date] = None,
):
    # Cap limit 5000 - tranh client xin limit=999999 keo het bang audit_logs
    # ve UI lam crash hoac chiem RAM
    if limit < 1:
        limit = 100
    elif limit > 5000:
        limit = 5000
    return AuditService.get_all(limit=limit, user_id=user_id, action=action,
                                 from_date=from_date, to_date=to_date)


@router.post('')
def log(req: AuditLog):
    AuditService.log(
        req.action, user_id=req.user_id, username=req.username, role=req.role,
        target_type=req.target_type, target_id=req.target_id,
        description=req.description, ip_address=req.ip_address
    )
    return {'status': 'logged'}


@router.delete('/purge')
def purge_old(days: int = 90):
    # Min 7 ngay de tranh accident wipe het log (vd admin go nham days=0
    # se delete WHERE created_at < CURRENT_DATE -> xoa toan bo log truoc hom nay)
    if days < 7:
        raise HTTPException(
            status_code=400,
            detail=f'Số ngày tối thiểu để purge là 7 (truyền: {days}). Tránh xoá log mới.'
        )
    AuditService.purge_old(days=days)
    return {'status': 'purged'}
