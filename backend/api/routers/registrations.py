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
    return RegistrationService.get_registration(reg_id)


@router.post('')
def register(req: RegisterRequest):
    reg_id = RegistrationService.register_student(req.hv_id, req.lop_id, req.nv_id)
    return {'reg_id': reg_id}


@router.post('/{reg_id}/payment')
def confirm_payment(reg_id: int, req: PaymentRequest):
    RegistrationService.confirm_payment(
        reg_id, req.so_tien, req.hinh_thuc, req.nv_id, ghi_chu=req.ghi_chu
    )
    return {'status': 'paid'}


@router.delete('/{reg_id}')
def cancel(reg_id: int):
    affected = RegistrationService.cancel_registration(reg_id)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Đăng ký id={reg_id} không tồn tại')
    return {'status': 'cancelled'}
