"""Audit router."""
from datetime import date as Date
from typing import Optional

from fastapi import APIRouter

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
    AuditService.purge_old(days=days)
    return {'status': 'purged'}
