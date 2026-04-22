from abc import ABC, abstractmethod


class User(ABC):
    """base abstract class cho moi nguoi dung trong he thong.
    su dung ke thua + encapsulation (private attr, property getter)
    """

    def __init__(self, id, username, role, full_name, email=None, sdt=None, is_active=True):
        self._id = id
        self._username = username
        self._role = role
        self._full_name = full_name
        self._email = email
        self._sdt = sdt
        self._is_active = is_active

    # ---- encapsulation: expose qua property ----
    @property
    def id(self): return self._id

    @property
    def username(self): return self._username

    @property
    def role(self): return self._role

    @property
    def full_name(self): return self._full_name

    @property
    def email(self): return self._email

    @property
    def sdt(self): return self._sdt

    @property
    def is_active(self): return self._is_active

    @property
    def initials(self) -> str:
        """lay 2 chu cai dau tu ho ten de hien avatar. vd: 'Dao Viet Quang Huy' -> 'QH'"""
        parts = self._full_name.strip().split()
        if len(parts) >= 2:
            return (parts[-2][0] + parts[-1][0]).upper()
        if parts:
            return parts[0][:2].upper()
        return 'NA'

    # ---- polymorphism: moi role override ----
    @abstractmethod
    def get_display_role(self) -> str:
        """ten role hien thi cho user"""
        raise NotImplementedError

    def __repr__(self):
        return f'<{self.__class__.__name__} {self._username} ({self._full_name})>'


# ===== Hoc vien =====
class Student(User):
    def __init__(self, id, username, full_name, msv, ngaysinh=None, gioitinh=None,
                 diachi=None, email=None, sdt=None, is_active=True):
        super().__init__(id, username, 'student', full_name, email, sdt, is_active)
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

    def get_display_role(self): return 'Học viên'


# ===== Giang vien =====
class Teacher(User):
    def __init__(self, id, username, full_name, ma_gv, hoc_vi=None, khoa=None,
                 chuyen_nganh=None, tham_nien=0, email=None, sdt=None, is_active=True):
        super().__init__(id, username, 'teacher', full_name, email, sdt, is_active)
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

    def get_display_role(self): return 'Giảng viên'


# ===== Nhan vien =====
class Employee(User):
    def __init__(self, id, username, full_name, ma_nv, chuc_vu=None, phong_ban=None,
                 ngay_vao_lam=None, email=None, sdt=None, is_active=True):
        super().__init__(id, username, 'employee', full_name, email, sdt, is_active)
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

    def get_display_role(self): return 'Nhân viên'


# ===== Quan tri vien =====
class Admin(User):
    def __init__(self, id, username, full_name, ma_admin='AD001',
                 email=None, sdt=None, is_active=True):
        super().__init__(id, username, 'admin', full_name, email, sdt, is_active)
        self._ma_admin = ma_admin

    @property
    def ma_admin(self): return self._ma_admin

    def get_display_role(self): return 'Quản trị viên'
