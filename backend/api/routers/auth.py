"""Auth router: login + change password."""
from fastapi import APIRouter, HTTPException, Request

from backend.api.schemas import ChangePasswordRequest, LoginRequest, LoginResponse
from backend.services.audit_service import AuditService
from backend.services.auth_service import AuthService

router = APIRouter()


@router.post('/login', response_model=LoginResponse)
def login(req: LoginRequest, request: Request = None):
    """Authenticate user. Tra ve user_id + role + role-specific data.
    Log audit cho ca login thanh cong va that bai (truoc khong log -> audit
    log thieu data dang nhap, kho debug + khong audit security)."""
    ip = request.client.host if (request and request.client) else None
    user = AuthService.login(req.username, req.password)
    if not user:
        # Log login_failed (user_id=None vi khong xac dinh duoc)
        try:
            AuditService.log_login(user_id=None, username=req.username,
                                    role=None, success=False, ip=ip)
        except Exception:
            pass  # audit fail khong duoc lam fail login flow
        raise HTTPException(status_code=401, detail='Sai tai khoan hoac mat khau')
    # Log login success
    try:
        AuditService.log_login(user_id=user.id, username=user.username,
                                role=user.__class__.__name__.lower(),
                                success=True, ip=ip)
    except Exception:
        pass
    # AuthService.login tra Entity object - serialize ve dict
    role_data = {}
    role = user.__class__.__name__.lower()  # Student/Teacher/Employee/Admin
    # Lay them attribute role-specific (an toan, fallback rong)
    for attr in ('msv', 'ma_gv', 'ma_nv', 'khoa', 'hoc_vi', 'chuc_vu', 'phong_ban',
                 'email', 'sdt', 'diachi', 'ngaysinh', 'gioitinh', 'tham_nien'):
        val = getattr(user, attr, None)
        if val is not None:
            role_data[attr] = val if not hasattr(val, 'isoformat') else val.isoformat()
    return LoginResponse(
        user_id=user.id,
        username=user.username,
        role=role,
        full_name=getattr(user, 'full_name', '') or getattr(user, 'name', ''),
        role_data=role_data,
    )


@router.put('/password')
def change_password(req: ChangePasswordRequest, request: Request = None):
    """Doi mat khau (hash sha256 ben service). Log audit de track ai doi
    mat khau khi nao - quan trong cho security investigation."""
    ip = request.client.host if (request and request.client) else None
    affected = AuthService.change_password(req.user_id, req.new_password)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Tài khoản user_id={req.user_id} không tồn tại')
    try:
        AuditService.log(
            action='change_password', user_id=req.user_id,
            target_type='users', target_id=str(req.user_id),
            description='Đổi mật khẩu', ip_address=ip
        )
    except Exception:
        pass  # audit fail khong duoc fail action chinh
    return {'status': 'ok'}
