from .base import User


class Student(User):
    """Hoc vien - co them MSV, ngay sinh, gioi tinh, dia chi"""

    def __init__(self, id, username, full_name, msv,
                 ngaysinh=None, gioitinh=None, diachi=None,
                 email=None, sdt=None, is_active=True):
        super().__init__(id, username, 'student', full_name,
                         email, sdt, is_active)
        self._msv = msv
        self._ngaysinh = ngaysinh
        self._gioitinh = gioitinh
        self._diachi = diachi

    @property
    def msv(self): return self._msv

    @property
    def ngaysinh(self): return self._ngaysinh

    @property
    def gioitinh(self): return self._gioitinh

    @property
    def diachi(self): return self._diachi

    def get_display_role(self):
        return 'Học viên'
