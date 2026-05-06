"""Pydantic schemas - validate request body / shape response.
Optional fields = client co the omit, server tu fill default hoac null.
"""
from datetime import date, time
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

# Enum values khop voi DB CHECK constraint (schema.sql)
AttendanceStatus = Literal['present', 'absent', 'late', 'excused']
NotificationType = Literal['info', 'warning', 'urgent']
SemesterStatus = Literal['open', 'closed', 'upcoming']
ClassStatus = Literal['open', 'full', 'closed']
ScheduleStatus = Literal['scheduled', 'completed', 'cancelled', 'postponed']
RegistrationStatus = Literal['pending_payment', 'paid', 'cancelled', 'completed']
CurriculumLoai = Literal['Bat buoc', 'Tu chon', 'Dai cuong']  # khop CHECK schema.sql


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
    # min=6 dong bo voi frontend validate_password() (toi thieu 6 ky tu).
    # Truoc =4 -> attacker bypass FE validate co the doi sang mat khau yeu 4-char
    new_password: str = Field(..., min_length=6, max_length=100)


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
    den_hv_id: Optional[int] = Field(None, gt=0)  # Gui rieng 1 HV
    loai: NotificationType = 'info'


# ===== Users (Student/Teacher/Employee) =====
class StudentCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
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
    password: str = Field(..., min_length=6, max_length=100)
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
    password: str = Field(..., min_length=6, max_length=100)
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
    # Truoc thieu max_length -> attacker co the gui chuoi 1MB qua API. Dong nhat
    # voi EmployeeCreate.phong_ban (max=50) va TeacherUpdate.khoa (max=50)
    phong_ban: Optional[str] = Field(None, max_length=50)


class ReviewSubmit(BaseModel):
    hv_id: int = Field(..., gt=0)
    gv_id: int = Field(..., gt=0)
    lop_id: str = Field(..., min_length=1, max_length=30)
    diem: int = Field(..., ge=1, le=5)  # 1-5 sao
    nhan_xet: Optional[str] = Field(None, max_length=2000)


# ===== Semesters =====
class SemesterCreate(BaseModel):
    sem_id: str = Field(..., min_length=3, max_length=20)
    ten: str = Field(..., min_length=2, max_length=50)
    nam_hoc: str = Field(..., min_length=4, max_length=20)
    bat_dau: date
    ket_thuc: date
    trang_thai: SemesterStatus = 'closed'  # open | closed | upcoming - khop CHECK constraint DB

    @model_validator(mode='after')
    def _check_date_order(self):
        # bat_dau < ket_thuc, tranh tao HK kieu '2025-09-01 -> 2025-08-01'
        if self.bat_dau and self.ket_thuc and self.bat_dau >= self.ket_thuc:
            raise ValueError('Ngày bắt đầu phải nhỏ hơn ngày kết thúc')
        return self


class SemesterStatusUpdate(BaseModel):
    trang_thai: SemesterStatus  # open | closed | upcoming


# ===== Curriculum =====
class CurriculumCreate(BaseModel):
    ma_mon: str = Field(..., min_length=1, max_length=20)
    tin_chi: int = Field(..., ge=1, le=10)
    # Truoc plain str max=20 -> client co the gui 'Khac' -> BE accept nhung
    # DB CHECK reject (Bat buoc/Tu chon/Dai cuong) -> 400 vi pham CHECK
    loai: CurriculumLoai
    hoc_ky_de_nghi: Optional[str] = Field(None, max_length=30)
    mon_tien_quyet: Optional[str] = Field(None, max_length=200)
    nganh: str = Field('CNTT', max_length=50)
    ghi_chu: Optional[str] = Field(None, max_length=500)


class CurriculumUpdate(BaseModel):
    ma_mon: Optional[str] = Field(None, min_length=1, max_length=20)
    tin_chi: Optional[int] = Field(None, ge=1, le=10)
    loai: Optional[CurriculumLoai] = None
    hoc_ky_de_nghi: Optional[str] = Field(None, max_length=30)
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
    trang_thai: ScheduleStatus = 'scheduled'  # scheduled|completed|cancelled|postponed

    @model_validator(mode='after')
    def _check_time_order(self):
        # Check gio_bat_dau < gio_ket_thuc - tranh DB CHECK violation con xa
        # va cho user error message ro hon ('Gio bat dau phai truoc gio ket thuc')
        if self.gio_bat_dau and self.gio_ket_thuc and self.gio_bat_dau >= self.gio_ket_thuc:
            raise ValueError('Giờ bắt đầu phải nhỏ hơn giờ kết thúc')
        return self


class ScheduleBatchCreate(BaseModel):
    """Tao nhieu buoi hoc theo pattern (vd T2/T5 cho 12 tuan)."""
    lop_id: str = Field(..., min_length=1, max_length=30)
    days_of_week: list[int] = Field(..., min_length=1, max_length=7)  # 2=T2..8=CN
    start_date: date  # Tuan dau tien (lay Monday cua tuan nay)
    num_weeks: int = Field(..., ge=1, le=52)
    gio_bat_dau: time
    gio_ket_thuc: time
    phong: Optional[str] = Field(None, max_length=20)
    start_buoi_so: int = Field(1, ge=1, le=200)
    noi_dung: Optional[str] = Field(None, max_length=500)

    @model_validator(mode='after')
    def _check_time_order(self):
        if self.gio_bat_dau and self.gio_ket_thuc and self.gio_bat_dau >= self.gio_ket_thuc:
            raise ValueError('Giờ bắt đầu phải nhỏ hơn giờ kết thúc')
        return self

    @model_validator(mode='after')
    def _check_days_range(self):
        # Service chap nhan 0-6 (Mon=0) hoac 2-8 (T2=2..CN=8). Truoc khong validate
        # -> client gui [100] -> service normalize -> days_norm=[] -> tra count=0
        # khong loi nhung khong tao gi (UX confusing)
        for d in self.days_of_week:
            if not (0 <= d <= 6 or 2 <= d <= 8):
                raise ValueError(
                    f'days_of_week phải trong 0-6 (Mon=0..Sun=6) hoặc 2-8 (T2=2..CN=8), nhận: {d}'
                )
        return self


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

    @model_validator(mode='after')
    def _check_time_order(self):
        # Cho exam: 2 truong optional - chi check khi ca 2 deu co
        if self.gio_bat_dau and self.gio_ket_thuc and self.gio_bat_dau >= self.gio_ket_thuc:
            raise ValueError('Giờ bắt đầu phải nhỏ hơn giờ kết thúc')
        return self


# ===== Attendance =====
class AttendanceMark(BaseModel):
    schedule_id: int = Field(..., gt=0)
    hv_id: int = Field(..., gt=0)
    trang_thai: AttendanceStatus  # present|absent|late|excused
    gio_vao: Optional[time] = None
    recorded_by: Optional[int] = Field(None, gt=0)
    ghi_chu: Optional[str] = Field(None, max_length=500)


# ===== Audit =====
class AuditLog(BaseModel):
    action: str = Field(..., min_length=1, max_length=50)
    user_id: Optional[int] = Field(None, gt=0)
    username: Optional[str] = Field(None, max_length=50)
    role: Optional[str] = Field(None, max_length=20)
    target_type: Optional[str] = Field(None, max_length=50)
    target_id: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    ip_address: Optional[str] = Field(None, max_length=45)  # IPv6 max length


# ===== Assignments =====
from datetime import datetime as _dt


class AssignmentCreate(BaseModel):
    lop_id: str = Field(..., min_length=1, max_length=30)
    gv_id: int = Field(..., gt=0)
    tieu_de: str = Field(..., min_length=1, max_length=200)
    mo_ta: Optional[str] = Field(None, max_length=5000)
    han_nop: Optional[_dt] = None
    diem_toi_da: float = Field(10, gt=0, le=100)


class AssignmentUpdate(BaseModel):
    tieu_de: Optional[str] = Field(None, min_length=1, max_length=200)
    mo_ta: Optional[str] = Field(None, max_length=5000)
    han_nop: Optional[_dt] = None
    diem_toi_da: Optional[float] = Field(None, gt=0, le=100)


class SubmissionCreate(BaseModel):
    assignment_id: int = Field(..., gt=0)
    hv_id: int = Field(..., gt=0)
    noi_dung: str = Field('', max_length=10000)
    file_url: Optional[str] = Field(None, max_length=500)


class SubmissionGrade(BaseModel):
    diem: float = Field(..., ge=0, le=100)
    nhan_xet: Optional[str] = Field('', max_length=2000)
