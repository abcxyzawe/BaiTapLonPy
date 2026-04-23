from .base import User


class Teacher(User):
    """Giang vien - co ma GV, hoc vi, khoa, chuyen nganh, tham nien"""

    def __init__(self, id, username, full_name, ma_gv,
                 hoc_vi=None, khoa=None, chuyen_nganh=None,
                 tham_nien=0, email=None, sdt=None, is_active=True):
        super().__init__(id, username, 'teacher', full_name,
                         email, sdt, is_active)
        self._ma_gv = ma_gv
        self._hoc_vi = hoc_vi
        self._khoa = khoa
        self._chuyen_nganh = chuyen_nganh
        self._tham_nien = tham_nien

    @property
    def ma_gv(self): return self._ma_gv

    @property
    def hoc_vi(self): return self._hoc_vi

    @property
    def khoa(self): return self._khoa

    @property
    def chuyen_nganh(self): return self._chuyen_nganh

    @property
    def tham_nien(self): return self._tham_nien

    def get_display_role(self):
        return 'Giảng viên'
