"""Pydantic schemas - validate request body / shape response.
Optional fields = client co the omit, server tu fill default hoac null.
"""
from datetime import date, time
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# Enum values khop voi DB CHECK constraint (schema.sql)
AttendanceStatus = Literal['present', 'absent', 'late', 'excused']
NotificationType = Literal['info', 'warning', 'urgent']
SemesterStatus = Literal['open', 'closed', 'upcoming']


# ===== Auth =====
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user_id: int
    username: str
    role: str
    full_name: str
    role_data: dict[str, Any] = Field(default_factory=dict)  # student/teacher/employee/admin specific


class ChangePasswordRequest(BaseModel):
    user_id: int
    new_password: str


# ===== Courses =====
class CourseCreate(BaseModel):
    ma_mon: str
    ten_mon: str
    mo_ta: str = ''


class CourseUpdate(BaseModel):
    ten_mon: Optional[str] = None
    mo_ta: Optional[str] = None


class ClassCreate(BaseModel):
    ma_lop: str
    ma_mon: str
    gv_id: Optional[int] = None
    lich: str = ''
    phong: str = ''
    siso_max: int = 40
    gia: int = 0
    semester_id: Optional[str] = None
    siso_hien_tai: int = 0
    so_buoi: int = 24


class ClassUpdate(BaseModel):
    ma_mon: Optional[str] = None
    gv_id: Optional[int] = None
    lich: Optional[str] = None
    phong: Optional[str] = None
    siso_max: Optional[int] = None
    siso_hien_tai: Optional[int] = None
    gia: Optional[int] = None
    semester_id: Optional[str] = None
    so_buoi: Optional[int] = None
    trang_thai: Optional[str] = None


class ClassPriceUpdate(BaseModel):
    gia: int


# ===== Registrations =====
class RegisterRequest(BaseModel):
    hv_id: int
    lop_id: str
    nv_id: int


class PaymentRequest(BaseModel):
    so_tien: int
    hinh_thuc: str
    nv_id: int
    ghi_chu: Optional[str] = None


# ===== Grades =====
class GradeSave(BaseModel):
    hv_id: int
    lop_id: str
    diem_qt: float
    diem_thi: float
    gv_id: int


# ===== Notifications =====
class NotificationSend(BaseModel):
    tu_id: int
    tieu_de: str
    noi_dung: str
    den_lop: Optional[str] = None
    loai: NotificationType = 'info'


# ===== Users (Student/Teacher/Employee) =====
class StudentCreate(BaseModel):
    username: str
    password: str
    full_name: str
    msv: str
    email: Optional[str] = None
    sdt: Optional[str] = None
    ngaysinh: Optional[date] = None
    gioitinh: Optional[str] = None
    diachi: Optional[str] = None


class StudentUpdate(BaseModel):
    email: Optional[str] = None
    sdt: Optional[str] = None
    diachi: Optional[str] = None
    full_name: Optional[str] = None


class TeacherCreate(BaseModel):
    username: str
    password: str
    full_name: str
    ma_gv: str
    email: Optional[str] = None
    sdt: Optional[str] = None
    hoc_vi: Optional[str] = None
    khoa: Optional[str] = None
    chuyen_nganh: Optional[str] = None
    tham_nien: int = 0


class TeacherUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    sdt: Optional[str] = None
    hoc_vi: Optional[str] = None
    khoa: Optional[str] = None
    chuyen_nganh: Optional[str] = None
    tham_nien: Optional[int] = None


class EmployeeCreate(BaseModel):
    username: str
    password: str
    full_name: str
    ma_nv: str
    email: Optional[str] = None
    sdt: Optional[str] = None
    chuc_vu: Optional[str] = None
    phong_ban: Optional[str] = None
    ngay_vao_lam: Optional[date] = None


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    sdt: Optional[str] = None
    chuc_vu: Optional[str] = None
    phong_ban: Optional[str] = None


class ReviewSubmit(BaseModel):
    hv_id: int
    gv_id: int
    lop_id: str
    diem: int
    nhan_xet: Optional[str] = None


# ===== Semesters =====
class SemesterCreate(BaseModel):
    sem_id: str
    ten: str
    nam_hoc: str
    bat_dau: date
    ket_thuc: date
    trang_thai: str = 'closed'


class SemesterStatusUpdate(BaseModel):
    trang_thai: SemesterStatus  # open | closed | upcoming


# ===== Curriculum =====
class CurriculumCreate(BaseModel):
    ma_mon: str
    tin_chi: int
    loai: str
    hoc_ky_de_nghi: Optional[str] = None
    mon_tien_quyet: Optional[str] = None
    nganh: str = 'CNTT'
    ghi_chu: Optional[str] = None


class CurriculumUpdate(BaseModel):
    ma_mon: Optional[str] = None
    tin_chi: Optional[int] = None
    loai: Optional[str] = None
    hoc_ky_de_nghi: Optional[str] = None
    mon_tien_quyet: Optional[str] = None
    nganh: Optional[str] = None
    ghi_chu: Optional[str] = None


# ===== Schedules =====
class ScheduleCreate(BaseModel):
    lop_id: str
    ngay: date
    gio_bat_dau: time
    gio_ket_thuc: time
    phong: Optional[str] = None
    buoi_so: Optional[int] = None
    noi_dung: Optional[str] = None
    thu: Optional[int] = None
    trang_thai: str = 'scheduled'


# ===== Exams =====
class ExamCreate(BaseModel):
    lop_id: str
    ngay_thi: date
    ca_thi: str
    phong: Optional[str] = None
    hinh_thuc: str = 'Tu luan'
    semester_id: Optional[str] = None
    gio_bat_dau: Optional[time] = None
    gio_ket_thuc: Optional[time] = None
    so_cau: Optional[int] = None
    thoi_gian_phut: int = 90


# ===== Attendance =====
class AttendanceMark(BaseModel):
    schedule_id: int
    hv_id: int
    trang_thai: AttendanceStatus  # present|absent|late|excused
    gio_vao: Optional[time] = None
    recorded_by: Optional[int] = None
    ghi_chu: Optional[str] = None


# ===== Audit =====
class AuditLog(BaseModel):
    action: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
