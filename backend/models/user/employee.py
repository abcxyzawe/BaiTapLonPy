from .base import User


class Employee(User):
    """Nhan vien - co ma NV, chuc vu, phong ban, ngay vao lam"""

    def __init__(self, id, username, full_name, ma_nv,
                 chuc_vu=None, phong_ban=None, ngay_vao_lam=None,
                 email=None, sdt=None, is_active=True):
        super().__init__(id, username, 'employee', full_name,
                         email, sdt, is_active)
        self._ma_nv = ma_nv
        self._chuc_vu = chuc_vu
        self._phong_ban = phong_ban
        self._ngay_vao_lam = ngay_vao_lam

    @property
    def ma_nv(self): return self._ma_nv

    @property
    def chuc_vu(self): return self._chuc_vu

    @property
    def phong_ban(self): return self._phong_ban

    @property
    def ngay_vao_lam(self): return self._ngay_vao_lam

    def get_display_role(self):
        return 'Nhân viên'
