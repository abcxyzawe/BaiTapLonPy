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
ClassStatus = Literal['open', 'full', 'closed']


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
    user_id: int = Field(..., gt=0)
    new_password: str = Field(..., min_length=4, max_length=100)


# ===== Courses =====
class CourseCreate(BaseModel):
    ma_mon: str = Field(..., min_length=1, max_length=20)
    ten_mon: str = Field(..., min_length=1, max_length=100)
    mo_ta: str = Field('', max_length=2000)


class CourseUpdate(BaseModel):
    ten_mon: Optional[str] = Field(None, min_length=1, max_length=100)
    mo_ta: Optional[str] = Field(None, max_length=2000)


class ClassCreate(BaseModel):
    ma_lop: str = Field(..., min_length=1, max_length=30)
    ma_mon: str = Field(..., min_length=1, max_length=20)
    gv_id: Optional[int] = None
    lich: str = Field('', max_length=100)
    phong: str = Field('', max_length=20)
    siso_max: int = Field(40, ge=1, le=500)
    gia: int = Field(0, ge=0, le=100_000_000)
    semester_id: Optional[str] = Field(None, max_length=20)
    siso_hien_tai: int = Field(0, ge=0, le=500)
    so_buoi: int = Field(24, ge=1, le=200)


class ClassUpdate(BaseModel):
    ma_mon: Optional[str] = Field(None, min_length=1, max_length=20)
    gv_id: Optional[int] = None
    lich: Optional[str] = Field(None, max_length=100)
    phong: Optional[str] = Field(None, max_length=20)
    siso_max: Optional[int] = Field(None, ge=1, le=500)
    siso_hien_tai: Optional[int] = Field(None, ge=0, le=500)
    gia: Optional[int] = Field(None, ge=0, le=100_000_000)
    semester_id: Optional[str] = Field(None, max_length=20)
    so_buoi: Optional[int] = Field(None, ge=1, le=200)
    trang_thai: Optional[ClassStatus] = None


class ClassPriceUpdate(BaseModel):
    gia: int = Field(..., ge=0, le=100_000_000)


# ===== Registrations =====
class RegisterRequest(BaseModel):
    hv_id: int = Field(..., gt=0)
    lop_id: str = Field(..., min_length=1, max_length=30)
    nv_id: int = Field(..., gt=0)


class PaymentRequest(BaseModel):
    so_tien: int = Field(..., gt=0, le=100_000_000)
    hinh_thuc: str = Field(..., min_length=1, max_length=50)
    nv_id: int = Field(..., gt=0)
    ghi_chu: Optional[str] = Field(None, max_length=500)


# ===== Grades =====
class GradeSave(BaseModel):
    hv_id: int = Field(..., gt=0)
    lop_id: str = Field(..., min_length=1, max_length=30)
    diem_qt: float = Field(..., ge=0, le=10)
    diem_thi: float = Field(..., ge=0, le=10)
    gv_id: int = Field(..., gt=0)


# ===== Notifications =====
class NotificationSend(BaseModel):
    tu_id: int = Field(..., gt=0)
    tieu_de: str = Field(..., min_length=1, max_length=200)
    noi_dung: str = Field(..., min_length=1, max_length=5000)
    den_lop: Optional[str] = Field(None, max_length=30)
    loai: NotificationType = 'info'


# ===== Users (Student/Teacher/Employee) =====
class StudentCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    msv: str = Field(..., min_length=3, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    sdt: Optional[str] = Field(None, max_length=20)
    ngaysinh: Optional[date] = None
    gioitinh: Optional[str] = Field(None, max_length=10)
    diachi: Optional[str] = Field(None, max_length=200)


class StudentUpdate(BaseModel):
    email: Optional[str] = Field(None, max_length=100)
    sdt: Optional[str] = Field(None, max_length=20)
    diachi: Optional[str] = Field(None, max_length=200)
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)


class TeacherCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    ma_gv: str = Field(..., min_length=3, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    sdt: Optional[str] = Field(None, max_length=20)
    hoc_vi: Optional[str] = Field(None, max_length=50)
    khoa: Optional[str] = Field(None, max_length=50)
    chuyen_nganh: Optional[str] = Field(None, max_length=100)
    tham_nien: int = Field(0, ge=0, le=60)


class TeacherUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    sdt: Optional[str] = Field(None, max_length=20)
    hoc_vi: Optional[str] = Field(None, max_length=50)
    khoa: Optional[str] = Field(None, max_length=50)
    chuyen_nganh: Optional[str] = Field(None, max_length=100)
    tham_nien: Optional[int] = Field(None, ge=0, le=60)


class EmployeeCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    ma_nv: str = Field(..., min_length=3, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    sdt: Optional[str] = Field(None, max_length=20)
    chuc_vu: Optional[str] = Field(None, max_length=50)
    phong_ban: Optional[str] = Field(None, max_length=50)
    ngay_vao_lam: Optional[date] = None


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    sdt: Optional[str] = Field(None, max_length=20)
    chuc_vu: Optional[str] = Field(None, max_length=50)
    phong_ban: Optional[str] = None


class ReviewSubmit(BaseModel):
    hv_id: int
    gv_id: int
    lop_id: str
    diem: int
    nhan_xet: Optional[str] = None


# ===== Semesters =====
class SemesterCreate(BaseModel):
    sem_id: str = Field(..., min_length=3, max_length=20)
    ten: str = Field(..., min_length=2, max_length=50)
    nam_hoc: str = Field(..., min_length=4, max_length=20)
    bat_dau: date
    ket_thuc: date
    trang_thai: str = Field('closed', max_length=20)


class SemesterStatusUpdate(BaseModel):
    trang_thai: SemesterStatus  # open | closed | upcoming


# ===== Curriculum =====
class CurriculumCreate(BaseModel):
    ma_mon: str = Field(..., min_length=1, max_length=20)
    tin_chi: int = Field(..., ge=1, le=10)
    loai: str = Field(..., min_length=1, max_length=20)
    hoc_ky_de_nghi: Optional[str] = Field(None, max_length=10)
    mon_tien_quyet: Optional[str] = Field(None, max_length=200)
    nganh: str = Field('CNTT', max_length=50)
    ghi_chu: Optional[str] = Field(None, max_length=500)


class CurriculumUpdate(BaseModel):
    ma_mon: Optional[str] = Field(None, min_length=1, max_length=20)
    tin_chi: Optional[int] = Field(None, ge=1, le=10)
    loai: Optional[str] = Field(None, min_length=1, max_length=20)
    hoc_ky_de_nghi: Optional[str] = Field(None, max_length=10)
    mon_tien_quyet: Optional[str] = Field(None, max_length=200)
    nganh: Optional[str] = Field(None, max_length=50)
    ghi_chu: Optional[str] = Field(None, max_length=500)


# ===== Schedules =====
class ScheduleCreate(BaseModel):
    lop_id: str = Field(..., min_length=1, max_length=30)
    ngay: date
    gio_bat_dau: time
    gio_ket_thuc: time
    phong: Optional[str] = Field(None, max_length=20)
    buoi_so: Optional[int] = Field(None, ge=1, le=200)
    noi_dung: Optional[str] = Field(None, max_length=500)
    thu: Optional[int] = Field(None, ge=2, le=8)
    trang_thai: str = Field('scheduled', max_length=20)


# ===== Exams =====
class ExamCreate(BaseModel):
    lop_id: str = Field(..., min_length=1, max_length=30)
    ngay_thi: date
    ca_thi: str = Field(..., min_length=1, max_length=50)
    phong: Optional[str] = Field(None, max_length=20)
    hinh_thuc: str = Field('Tu luan', max_length=20)
    semester_id: Optional[str] = Field(None, max_length=20)
    gio_bat_dau: Optional[time] = None
    gio_ket_thuc: Optional[time] = None
    so_cau: Optional[int] = Field(None, ge=1, le=500)
    thoi_gian_phut: int = Field(90, ge=15, le=300)


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
