"""Auth router: login + change password."""
from fastapi import APIRouter, HTTPException

from backend.api.schemas import ChangePasswordRequest, LoginRequest, LoginResponse
from backend.services.auth_service import AuthService

router = APIRouter()


@router.post('/login', response_model=LoginResponse)
def login(req: LoginRequest):
    """Authenticate user. Tra ve user_id + role + role-specific data."""
    user = AuthService.login(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail='Sai tai khoan hoac mat khau')
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
def change_password(req: ChangePasswordRequest):
    """Doi mat khau (hash sha256 ben service)."""
    AuthService.change_password(req.user_id, req.new_password)
    return {'status': 'ok'}
