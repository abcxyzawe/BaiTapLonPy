"""Registrations + payments router."""
from fastapi import APIRouter, HTTPException

from backend.api.schemas import PaymentRequest, RegisterRequest
from backend.services.registration_service import RegistrationService

router = APIRouter()


@router.get('')
def list_registrations(limit: int = 100):
    return RegistrationService.get_all_registrations(limit=limit)


@router.get('/pending')
def pending_payments():
    return RegistrationService.get_pending_payments()


@router.get('/revenue/today')
def revenue_today():
    return {'total': RegistrationService.get_total_revenue_today()}


@router.get('/{reg_id}')
def get_registration(reg_id: int):
    row = RegistrationService.get_registration(reg_id)
    if not row:
        raise HTTPException(status_code=404, detail=f'Đăng ký id={reg_id} không tồn tại')
    return row


@router.post('')
def register(req: RegisterRequest):
    try:
        reg_id = RegistrationService.register_student(req.hv_id, req.lop_id, req.nv_id)
    except ValueError as e:
        # ValueError = validation lop khong ton tai / dot da closed -> tra 400 voi msg ro rang
        raise HTTPException(status_code=400, detail=str(e))
    return {'reg_id': reg_id}


@router.post('/{reg_id}/payment')
def confirm_payment(reg_id: int, req: PaymentRequest):
    try:
        RegistrationService.confirm_payment(
            reg_id, req.so_tien, req.hinh_thuc, req.nv_id, ghi_chu=req.ghi_chu
        )
    except ValueError as e:
        # ValueError = reg khong ton tai / da paid / cancelled / completed
        raise HTTPException(status_code=400, detail=str(e))
    return {'status': 'paid'}


@router.delete('/{reg_id}')
def cancel(reg_id: int):
    try:
        affected = RegistrationService.cancel_registration(reg_id)
    except ValueError as e:
        # Reg da completed/cancelled -> 400 voi msg ro rang
        raise HTTPException(status_code=400, detail=str(e))
    if not affected:
        raise HTTPException(status_code=404, detail=f'Đăng ký id={reg_id} không tồn tại')
    return {'status': 'cancelled'}
