"""api_client.py - HTTP client wrapper goi REST API server.

Drop-in replacement cho `from backend.services.X import X` truoc day.
Moi class co interface giong service - method signature giu nguyen
nen frontend code thay doi minimal:

    # Truoc:
    from backend.services.auth_service import AuthService
    user = AuthService.login(u, p)

    # Sau:
    from api_client import AuthService
    user = AuthService.login(u, p)

Config URL qua env var EAUT_API_URL (default http://localhost:8000)
"""
import os
from datetime import date, time
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter

API_URL = os.environ.get('EAUT_API_URL', 'http://localhost:8000').rstrip('/')
# Tuple (connect_timeout, read_timeout) - connect short de fail som khi API down,
# read longer cho query nang
TIMEOUT = (3, 10)

# Session voi keep-alive + connection pool - giam latency moi request
# Truoc day moi call mo socket moi (3-way handshake) -> lag UI khi switch page
# Voi Session: reuse TCP connection, ~10-20x nhanh hon cho cac call lien tiep
_session = requests.Session()
_adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=0)
_session.mount('http://', _adapter)
_session.mount('https://', _adapter)


# ===== HTTP helpers =====
def _get(path: str, **params) -> Any:
    r = _session.get(API_URL + path, params=_clean(params), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _post(path: str, json: Optional[dict] = None) -> Any:
    r = _session.post(API_URL + path, json=_serialize(json or {}), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _put(path: str, json: Optional[dict] = None) -> Any:
    r = _session.put(API_URL + path, json=_serialize(json or {}), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _patch(path: str, json: Optional[dict] = None) -> Any:
    r = _session.patch(API_URL + path, json=_serialize(json or {}), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _delete(path: str, **params) -> Any:
    r = _session.delete(API_URL + path, params=_clean(params), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _clean(d: dict) -> dict:
    """Loai bo None khoi query params."""
    return {k: _to_iso(v) for k, v in d.items() if v is not None}


def _serialize(d: dict) -> dict:
    """Convert date/time -> ISO string (JSON khong serialize duoc native)."""
    return {k: _to_iso(v) for k, v in d.items()}


def _to_iso(v):
    if isinstance(v, (date, time)):
        return v.isoformat()
    return v


def is_alive() -> bool:
    """Check API server reachable. Dung session de reuse TCP connection."""
    try:
        r = _session.get(API_URL + '/health', timeout=2)
        return r.status_code == 200 and r.json().get('db') == 'connected'
    except Exception:
        return False


# ===== _ApiUser shim - mimic Entity interface (cho AuthService.login) =====
class _ApiUser:
    """Wrap dict tra ve tu /auth/login thanh object co attribute access
    de frontend code goi user.id, user.full_name... khong can sua."""

    def __init__(self, data: dict):
        self._d = data
        self.__class__.__name__ = data.get('role', 'User').capitalize()
        # Top-level
        self.id = data.get('user_id')
        self.username = data.get('username')
        self.role = data.get('role')
        self.full_name = data.get('full_name', '')
        self.name = self.full_name  # alias frontend hay dung
        # initials: tinh tu full_name (vd "Nguyen Duc Thien" -> "NT")
        self.initials = self._compute_initials(self.full_name)
        # Default rong cho cac attr role-specific de tranh AttributeError
        for attr in ('msv', 'ma_gv', 'ma_nv', 'khoa', 'hoc_vi', 'chuc_vu',
                     'phong_ban', 'email', 'sdt', 'diachi', 'ngaysinh',
                     'gioitinh', 'tham_nien', 'lop'):
            setattr(self, attr, '')
        # Override bang role_data thuc te
        for k, v in (data.get('role_data') or {}).items():
            setattr(self, k, v)

    @staticmethod
    def _compute_initials(name: str) -> str:
        """Tinh viet tat tu ten - "Nguyen Duc Thien" -> "NT"."""
        if not name:
            return '?'
        parts = name.strip().split()
        if len(parts) == 1:
            return parts[0][:2].upper()
        # Lay chu cai dau cua HO va TEN
        return (parts[0][0] + parts[-1][0]).upper()

    def __getitem__(self, k):
        # Frontend doi khi dung user['id'] thay vi user.id
        if k in ('id', 'user_id'):
            return self.id
        if hasattr(self, k):
            return getattr(self, k)
        return self._d.get(k) or self._d.get('role_data', {}).get(k)

    def get(self, k, default=None):
        try:
            v = self[k]
            return v if v is not None and v != '' else default
        except Exception:
            return default


# ============================================================
# SERVICE WRAPPERS - moi class co interface giong service goc
# ============================================================

class AuthService:
    @staticmethod
    def login(username, password):
        try:
            data = _post('/auth/login', {'username': username, 'password': password})
            return _ApiUser(data)
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                return None
            raise

    @staticmethod
    def change_password(user_id, new_password):
        return _put('/auth/password', {'user_id': user_id, 'new_password': new_password})


class CourseService:
    @staticmethod
    def get_all_courses(): return _get('/courses')

    @staticmethod
    def get_course(ma_mon): return _get(f'/courses/{ma_mon}')

    @staticmethod
    def get_all_classes(): return _get('/classes')

    @staticmethod
    def get_class(ma_lop): return _get(f'/classes/{ma_lop}')

    @staticmethod
    def get_classes_by_teacher(gv_id): return _get(f'/classes/teacher/{gv_id}')

    @staticmethod
    def get_classes_by_student(hv_id): return _get(f'/classes/student/{hv_id}')

    @staticmethod
    def get_students_in_class(ma_lop): return _get(f'/classes/{ma_lop}/students')

    @staticmethod
    def get_students_by_teacher(gv_id, lop_filter=None):
        return _get(f'/teachers/{gv_id}/students', lop=lop_filter)

    @staticmethod
    def create_course(ma_mon, ten_mon, mo_ta=''):
        return _post('/courses', {'ma_mon': ma_mon, 'ten_mon': ten_mon, 'mo_ta': mo_ta})

    @staticmethod
    def update_course(ma_mon, ten_mon=None, mo_ta=None):
        return _put(f'/courses/{ma_mon}', {'ten_mon': ten_mon, 'mo_ta': mo_ta})

    @staticmethod
    def delete_course(ma_mon): return _delete(f'/courses/{ma_mon}')

    @staticmethod
    def create_class(ma_lop, ma_mon, gv_id=None, lich='', phong='', siso_max=40,
                     gia=0, semester_id=None, siso_hien_tai=0, so_buoi=24):
        return _post('/classes', {
            'ma_lop': ma_lop, 'ma_mon': ma_mon, 'gv_id': gv_id, 'lich': lich,
            'phong': phong, 'siso_max': siso_max, 'gia': gia,
            'semester_id': semester_id, 'siso_hien_tai': siso_hien_tai, 'so_buoi': so_buoi
        })

    @staticmethod
    def update_class(ma_lop, **fields):
        return _put(f'/classes/{ma_lop}', fields)

    @staticmethod
    def delete_class(ma_lop): return _delete(f'/classes/{ma_lop}')

    @staticmethod
    def update_class_price(ma_lop, gia):
        return _patch(f'/classes/{ma_lop}/price', {'gia': gia})

    @staticmethod
    def get_teachers_list(): return _get('/teachers/list')


class RegistrationService:
    @staticmethod
    def register_student(hv_id, lop_id, nv_id):
        r = _post('/registrations', {'hv_id': hv_id, 'lop_id': lop_id, 'nv_id': nv_id})
        return r.get('reg_id')

    @staticmethod
    def get_all_registrations(limit=100): return _get('/registrations', limit=limit)

    @staticmethod
    def get_pending_payments(): return _get('/registrations/pending')

    @staticmethod
    def confirm_payment(reg_id, so_tien, hinh_thuc, nv_id, ghi_chu=None):
        return _post(f'/registrations/{reg_id}/payment', {
            'so_tien': so_tien, 'hinh_thuc': hinh_thuc, 'nv_id': nv_id, 'ghi_chu': ghi_chu
        })

    @staticmethod
    def cancel_registration(reg_id): return _delete(f'/registrations/{reg_id}')

    @staticmethod
    def get_registration(reg_id): return _get(f'/registrations/{reg_id}')

    @staticmethod
    def get_total_revenue_today():
        return _get('/registrations/revenue/today').get('total', 0)


class GradeService:
    @staticmethod
    def get_grades_by_student(hv_id): return _get(f'/grades/student/{hv_id}')

    @staticmethod
    def get_grades_by_class(lop_id): return _get(f'/grades/class/{lop_id}')

    @staticmethod
    def save_grade(hv_id, lop_id, diem_qt, diem_thi, gv_id):
        return _post('/grades', {'hv_id': hv_id, 'lop_id': lop_id,
                                  'diem_qt': diem_qt, 'diem_thi': diem_thi, 'gv_id': gv_id})

    @staticmethod
    def get_gpa_stats(hv_id): return _get(f'/grades/student/{hv_id}/gpa')

    @staticmethod
    def get_teacher_avg_rating(gv_id): return _get(f'/grades/teacher/{gv_id}/rating')


class NotificationService:
    @staticmethod
    def get_all(): return _get('/notifications')

    @staticmethod
    def get_for_student(hv_id): return _get(f'/notifications/student/{hv_id}')

    @staticmethod
    def get_sent_by_teacher(gv_id, limit=10):
        return _get(f'/notifications/teacher/{gv_id}', limit=limit)

    @staticmethod
    def send(tu_id, tieu_de, noi_dung, den_lop=None, den_hv_id=None, loai='info'):
        """Gui notification:
        - den_lop=X: tat ca HV cua lop X
        - den_hv_id=N: 1 HV cu the (qua user_id)
        - Khong truyen 2: broadcast tat ca
        """
        return _post('/notifications', {
            'tu_id': tu_id, 'tieu_de': tieu_de, 'noi_dung': noi_dung,
            'den_lop': den_lop, 'den_hv_id': den_hv_id, 'loai': loai
        })

    @staticmethod
    def get_recent(limit=10): return _get('/notifications/recent', limit=limit)

    @staticmethod
    def delete(notif_id): return _delete(f'/notifications/{notif_id}')


class StudentService:
    @staticmethod
    def get_all(): return _get('/students')

    @staticmethod
    def get_by_msv(msv): return _get(f'/students/{msv}')

    @staticmethod
    def create(username, password, full_name, msv, email=None, sdt=None,
               ngaysinh=None, gioitinh=None, diachi=None):
        r = _post('/students', {
            'username': username, 'password': password, 'full_name': full_name, 'msv': msv,
            'email': email, 'sdt': sdt, 'ngaysinh': ngaysinh,
            'gioitinh': gioitinh, 'diachi': diachi
        })
        return r.get('user_id')

    @staticmethod
    def bulk_create(students_list):
        """Bulk import. students_list = list of dict {username,password,full_name,msv,...}.
        Tra ve {success, failed, total}."""
        return _post('/students/bulk', students_list)

    @staticmethod
    def update(user_id, **fields):
        return _put(f'/students/{user_id}', fields)

    @staticmethod
    def delete(user_id): return _delete(f'/students/{user_id}')


class TeacherService:
    @staticmethod
    def get_all(): return _get('/teachers')

    @staticmethod
    def get_for_review(): return _get('/teachers/for-review')

    @staticmethod
    def get_by_code(ma_gv): return _get(f'/teachers/by-code/{ma_gv}')

    @staticmethod
    def create(username, password, full_name, ma_gv, email=None, sdt=None,
               hoc_vi=None, khoa=None, chuyen_nganh=None, tham_nien=0):
        r = _post('/teachers', {
            'username': username, 'password': password, 'full_name': full_name, 'ma_gv': ma_gv,
            'email': email, 'sdt': sdt, 'hoc_vi': hoc_vi, 'khoa': khoa,
            'chuyen_nganh': chuyen_nganh, 'tham_nien': tham_nien
        })
        return r.get('user_id')

    @staticmethod
    def update(user_id, **fields):
        return _put(f'/teachers/{user_id}', fields)

    @staticmethod
    def delete(user_id): return _delete(f'/teachers/{user_id}')


class EmployeeService:
    @staticmethod
    def get_all(): return _get('/employees')

    @staticmethod
    def get_by_code(ma_nv): return _get(f'/employees/by-code/{ma_nv}')

    @staticmethod
    def create(username, password, full_name, ma_nv, email=None, sdt=None,
               chuc_vu=None, phong_ban=None, ngay_vao_lam=None):
        r = _post('/employees', {
            'username': username, 'password': password, 'full_name': full_name, 'ma_nv': ma_nv,
            'email': email, 'sdt': sdt, 'chuc_vu': chuc_vu,
            'phong_ban': phong_ban, 'ngay_vao_lam': ngay_vao_lam
        })
        return r.get('user_id')

    @staticmethod
    def update(user_id, **fields):
        return _put(f'/employees/{user_id}', fields)

    @staticmethod
    def delete(user_id): return _delete(f'/employees/{user_id}')


class ReviewService:
    @staticmethod
    def submit_review(hv_id, gv_id, lop_id, diem, nhan_xet=None):
        return _post('/reviews', {'hv_id': hv_id, 'gv_id': gv_id, 'lop_id': lop_id,
                                   'diem': diem, 'nhan_xet': nhan_xet})


class StatsService:
    @staticmethod
    def admin_overview(): return _get('/stats/admin/overview')

    @staticmethod
    def stats_by_semester(semester_id): return _get(f'/stats/semester/{semester_id}')

    @staticmethod
    def top_classes(limit=5): return _get('/stats/top-classes', limit=limit)

    @staticmethod
    def recent_activity(limit=5): return _get('/stats/recent-activity', limit=limit)

    @staticmethod
    def by_course(): return _get('/stats/by-course')

    @staticmethod
    def class_enrollment(): return _get('/stats/class-enrollment')

    @staticmethod
    def employee_today(emp_id): return _get(f'/stats/employee/{emp_id}/today')

    @staticmethod
    def employee_revenue_report(emp_id, from_date, to_date):
        """Bao cao doanh thu chi tiet cho NV trong khoang [from_date, to_date]."""
        return _get(f'/stats/employee/{emp_id}/revenue-report',
                    from_date=from_date, to_date=to_date)

    @staticmethod
    def recent_pending_registrations(limit=5):
        return _get('/stats/pending-registrations', limit=limit)

    @staticmethod
    def teacher_overview(gv_id): return _get(f'/stats/teacher/{gv_id}/overview')


class SemesterService:
    @staticmethod
    def get_all(): return _get('/semesters')

    @staticmethod
    def get_current(): return _get('/semesters/current')

    @staticmethod
    def get(sem_id): return _get(f'/semesters/{sem_id}')

    @staticmethod
    def create(sem_id, ten, nam_hoc, bat_dau, ket_thuc, trang_thai='closed'):
        return _post('/semesters', {
            'sem_id': sem_id, 'ten': ten, 'nam_hoc': nam_hoc,
            'bat_dau': bat_dau, 'ket_thuc': ket_thuc, 'trang_thai': trang_thai
        })

    @staticmethod
    def set_status(sem_id, trang_thai):
        return _patch(f'/semesters/{sem_id}/status', {'trang_thai': trang_thai})

    @staticmethod
    def delete(sem_id): return _delete(f'/semesters/{sem_id}')


class CurriculumService:
    @staticmethod
    def get_all(nganh=None): return _get('/curriculum', nganh=nganh)

    @staticmethod
    def get(cur_id): return _get(f'/curriculum/{cur_id}')

    @staticmethod
    def create(ma_mon, tin_chi, loai, hoc_ky_de_nghi=None, mon_tien_quyet=None,
               nganh='CNTT', ghi_chu=None):
        r = _post('/curriculum', {
            'ma_mon': ma_mon, 'tin_chi': tin_chi, 'loai': loai,
            'hoc_ky_de_nghi': hoc_ky_de_nghi, 'mon_tien_quyet': mon_tien_quyet,
            'nganh': nganh, 'ghi_chu': ghi_chu
        })
        return r.get('cur_id')

    @staticmethod
    def update(cur_id, **fields):
        return _put(f'/curriculum/{cur_id}', fields)

    @staticmethod
    def delete(cur_id): return _delete(f'/curriculum/{cur_id}')

    @staticmethod
    def get_prerequisites(ma_mon, nganh='CNTT'):
        return _get(f'/curriculum/prerequisites/{ma_mon}', nganh=nganh).get('prerequisites', [])

    @staticmethod
    def check_prerequisites_for_student(hv_id, ma_mon, nganh='CNTT'):
        return _get(f'/curriculum/check/{hv_id}/{ma_mon}', nganh=nganh)

    @staticmethod
    def get_progress_for_student(hv_id, nganh='CNTT'):
        return _get(f'/curriculum/progress/{hv_id}', nganh=nganh)


class ScheduleService:
    @staticmethod
    def get_by_week(week_start): return _get('/schedules/week', start=week_start)

    @staticmethod
    def get_for_student_week(hv_id, week_start):
        return _get(f'/schedules/student/{hv_id}/week', start=week_start)

    @staticmethod
    def nearest_week_for_student(hv_id, ref_date):
        """Tra QDate Monday cua tuan gan nhat co lich. None neu khong co."""
        r = _get(f'/schedules/student/{hv_id}/nearest-week', ref=ref_date)
        return r.get('monday') if r else None

    @staticmethod
    def get_for_teacher_week(gv_id, week_start):
        return _get(f'/schedules/teacher/{gv_id}/week', start=week_start)

    @staticmethod
    def nearest_week_for_teacher(gv_id, ref_date):
        r = _get(f'/schedules/teacher/{gv_id}/nearest-week', ref=ref_date)
        return r.get('monday') if r else None

    @staticmethod
    def get_today(): return _get('/schedules/today')

    @staticmethod
    def get_for_class(lop_id): return _get(f'/schedules/class/{lop_id}')

    @staticmethod
    def create(lop_id, ngay, gio_bat_dau, gio_ket_thuc, phong=None, buoi_so=None,
               noi_dung=None, thu=None, trang_thai='scheduled'):
        return _post('/schedules', {
            'lop_id': lop_id, 'ngay': ngay, 'gio_bat_dau': gio_bat_dau,
            'gio_ket_thuc': gio_ket_thuc, 'phong': phong, 'buoi_so': buoi_so,
            'noi_dung': noi_dung, 'thu': thu, 'trang_thai': trang_thai
        })

    @staticmethod
    def delete(sched_id): return _delete(f'/schedules/{sched_id}')

    @staticmethod
    def get(sched_id): return _get(f'/schedules/{sched_id}')

    @staticmethod
    def create_batch(lop_id, days_of_week, start_date, num_weeks,
                     gio_bat_dau, gio_ket_thuc, phong=None,
                     start_buoi_so=1, noi_dung=None):
        """Bulk tao buoi hoc theo pattern T2/T5 cho N tuan."""
        return _post('/schedules/batch', {
            'lop_id': lop_id, 'days_of_week': days_of_week,
            'start_date': start_date, 'num_weeks': num_weeks,
            'gio_bat_dau': gio_bat_dau, 'gio_ket_thuc': gio_ket_thuc,
            'phong': phong, 'start_buoi_so': start_buoi_so,
            'noi_dung': noi_dung,
        })

    @staticmethod
    def get_all_for_student(hv_id, from_date=None, to_date=None):
        """Tat ca buoi hoc cua HV (dung cho ICS export). Default 6 thang truoc + sau."""
        params = {}
        if from_date: params['from_date'] = from_date
        if to_date: params['to_date'] = to_date
        return _get(f'/schedules/student/{hv_id}/all', **params)

    @staticmethod
    def get_all_for_teacher(gv_id, from_date=None, to_date=None):
        """Tat ca buoi day cua GV."""
        params = {}
        if from_date: params['from_date'] = from_date
        if to_date: params['to_date'] = to_date
        return _get(f'/schedules/teacher/{gv_id}/all', **params)

    @staticmethod
    def check_conflict(ngay, gio_bat_dau, gio_ket_thuc, phong=None,
                       lop_id=None, gv_id=None, exclude_id=None):
        """Check trung lich: cung phong hoac cung lop hoac cung GV + overlap gio.
        Tra ve {'conflicts': list, 'count': int}."""
        payload = {
            'ngay': ngay, 'gio_bat_dau': gio_bat_dau, 'gio_ket_thuc': gio_ket_thuc,
            'phong': phong, 'lop_id': lop_id, 'gv_id': gv_id,
            'exclude_id': exclude_id,
        }
        # Strip None values
        payload = {k: v for k, v in payload.items() if v is not None}
        return _post('/schedules/check-conflict', payload)

    @staticmethod
    def update(sched_id, **fields):
        # Backend yeu cau lop_id (Pydantic schema) - dummy de pass validation, server ignore
        if 'lop_id' not in fields:
            fields['lop_id'] = '_'
        # ngay/gio fields can be ISO string
        return _put(f'/schedules/{sched_id}', fields)


class ExamService:
    @staticmethod
    def get_all(semester_id=None): return _get('/exams', semester_id=semester_id)

    @staticmethod
    def get_for_student(hv_id, semester_id=None):
        return _get(f'/exams/student/{hv_id}', semester_id=semester_id)

    @staticmethod
    def get_for_class(lop_id): return _get(f'/exams/class/{lop_id}')

    @staticmethod
    def get_for_teacher(gv_id):
        return _get(f'/exams/teacher/{gv_id}')

    @staticmethod
    def create(lop_id, ngay_thi, ca_thi, phong=None, hinh_thuc='Tu luan', semester_id=None,
               gio_bat_dau=None, gio_ket_thuc=None, so_cau=None, thoi_gian_phut=90):
        return _post('/exams', {
            'lop_id': lop_id, 'ngay_thi': ngay_thi, 'ca_thi': ca_thi, 'phong': phong,
            'hinh_thuc': hinh_thuc, 'semester_id': semester_id,
            'gio_bat_dau': gio_bat_dau, 'gio_ket_thuc': gio_ket_thuc,
            'so_cau': so_cau, 'thoi_gian_phut': thoi_gian_phut
        })

    @staticmethod
    def delete(exam_id): return _delete(f'/exams/{exam_id}')


class AttendanceService:
    @staticmethod
    def get_for_schedule(schedule_id): return _get(f'/attendance/schedule/{schedule_id}')

    @staticmethod
    def get_for_student(hv_id, lop_id=None):
        return _get(f'/attendance/student/{hv_id}', lop_id=lop_id)

    @staticmethod
    def mark(schedule_id, hv_id, trang_thai, gio_vao=None, recorded_by=None, ghi_chu=None):
        return _post('/attendance', {
            'schedule_id': schedule_id, 'hv_id': hv_id, 'trang_thai': trang_thai,
            'gio_vao': gio_vao, 'recorded_by': recorded_by, 'ghi_chu': ghi_chu
        })

    @staticmethod
    def attendance_rate(hv_id, lop_id):
        return _get(f'/attendance/rate/{hv_id}/{lop_id}').get('rate', 0.0)

    @staticmethod
    def class_summary(lop_id):
        """Tra ve list [{msv, present_cnt, total, rate}, ...] cho tat ca HV trong lop."""
        return _get(f'/attendance/class/{lop_id}/summary')


class AuditService:
    @staticmethod
    def get_all(limit=100, user_id=None, action=None, from_date=None, to_date=None):
        return _get('/audit', limit=limit, user_id=user_id, action=action,
                    from_date=from_date, to_date=to_date)

    @staticmethod
    def log(action, user_id=None, username=None, role=None, target_type=None,
            target_id=None, description=None, ip_address=None):
        return _post('/audit', {
            'action': action, 'user_id': user_id, 'username': username, 'role': role,
            'target_type': target_type, 'target_id': target_id,
            'description': description, 'ip_address': ip_address
        })

    @staticmethod
    def purge_old(days=90): return _delete('/audit/purge', days=days)


class AssignmentService:
    """Bai tap GV giao + HV nop + GV cham."""

    # GV
    @staticmethod
    def create(lop_id, gv_id, tieu_de, mo_ta='', han_nop=None, diem_toi_da=10,
               file_path=None):
        return _post('/assignments', {
            'lop_id': lop_id, 'gv_id': gv_id,
            'tieu_de': tieu_de, 'mo_ta': mo_ta,
            'file_path': file_path,
            'han_nop': han_nop.isoformat() if han_nop else None,
            'diem_toi_da': diem_toi_da,
        })

    @staticmethod
    def upload_file(local_path):
        """GV upload file dinh kem TRUOC khi tao bai. Tra ve dict
        {file_path, size, filename}. Local_path la duong dan tuyet doi tren may GV.

        Goi truc tiep multipart/form-data qua requests session (khong qua _post
        vi _post chi support JSON body)."""
        with open(local_path, 'rb') as f:
            files = {'file': (os.path.basename(local_path), f)}
            r = _session.post(API_URL + '/assignments/upload-file',
                              files=files, timeout=(3, 60))  # read timeout 60s cho file lon
        r.raise_for_status()
        return r.json()

    @staticmethod
    def download_file(file_path, dest_path):
        """Tai file dinh kem ve local. file_path = relative tu uploads/.
        dest_path = absolute path luu file."""
        with _session.get(API_URL + f'/assignments/file/{file_path}',
                          stream=True, timeout=(3, 60)) as r:
            r.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(1024 * 64):
                    if chunk:
                        f.write(chunk)
        return dest_path

    @staticmethod
    def update(asg_id, **fields):
        # han_nop -> isoformat string for API
        if 'han_nop' in fields and fields['han_nop'] is not None:
            try:
                fields['han_nop'] = fields['han_nop'].isoformat()
            except AttributeError:
                pass
        return _put(f'/assignments/{asg_id}', {k: v for k, v in fields.items() if v is not None})

    @staticmethod
    def delete(asg_id):
        return _delete(f'/assignments/{asg_id}')

    @staticmethod
    def get(asg_id):
        return _get(f'/assignments/{asg_id}')

    @staticmethod
    def get_by_teacher(gv_id):
        return _get(f'/assignments/teacher/{gv_id}')

    @staticmethod
    def get_submissions(asg_id):
        return _get(f'/assignments/{asg_id}/submissions')

    # HV
    @staticmethod
    def get_by_class(lop_id):
        return _get(f'/assignments/class/{lop_id}')

    @staticmethod
    def get_my_submission(asg_id, hv_id):
        return _get(f'/assignments/{asg_id}/submission/{hv_id}')

    @staticmethod
    def get_pending(hv_id):
        return _get(f'/assignments/student/{hv_id}/pending')

    @staticmethod
    def submit(assignment_id, hv_id, noi_dung, file_url=None):
        return _post('/submissions', {
            'assignment_id': assignment_id, 'hv_id': hv_id,
            'noi_dung': noi_dung, 'file_url': file_url,
        })

    @staticmethod
    def get_history(hv_id):
        return _get(f'/submissions/student/{hv_id}')

    @staticmethod
    def grade(sub_id, diem, nhan_xet=''):
        return _post(f'/submissions/{sub_id}/grade', {
            'diem': diem, 'nhan_xet': nhan_xet
        })
