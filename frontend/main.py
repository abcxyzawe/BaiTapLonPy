import sys, os
# them root vao path de import backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtGui import QPixmap, QIcon, QColor, QFont
from PyQt5.QtCore import Qt, QDate
from theme_helper import (load_theme, setup_sidebar_icons, setup_stat_icons,
                          apply_eaut_overrides, COLORS, SIDEBAR_ACTIVE, SIDEBAR_NORMAL)

# Goi REST API server (backend/api) qua HTTP client wrapper
# DB_AVAILABLE = True ngay khi api_client import OK. Tung call rieng se
# tu xu ly loi khi server tam thoi down. KHONG cache 1 lan luc startup
# (truoc day cache False -> moi action sau bi 'Khong luu duoc' du API up).
DB_AVAILABLE = False
try:
    from api_client import (AuthService, CourseService, RegistrationService, GradeService,
                            NotificationService, StudentService, TeacherService,
                            EmployeeService, ReviewService, StatsService,
                            SemesterService, CurriculumService, ScheduleService,
                            ExamService, AttendanceService, AuditService, is_alive)
    # Class shim cho code cu - frontend doi khi dung db.fetch_one truc tiep
    # (deprecated path - cac call nay da duoc thay bang API tuong ung)
    class _ApiDb:
        @staticmethod
        def fetch_one(sql, params=None):
            print(f'[WARN] db.fetch_one called from frontend - bypass API: {sql[:50]}')
            return None
        @staticmethod
        def fetch_all(sql, params=None):
            print(f'[WARN] db.fetch_all called from frontend - bypass API: {sql[:50]}')
            return []
        @staticmethod
        def execute(sql, params=None):
            print(f'[WARN] db.execute called from frontend - bypass API: {sql[:50]}')
        @staticmethod
        def execute_returning(sql, params=None):
            print(f'[WARN] db.execute_returning called from frontend - bypass API: {sql[:50]}')
            return None
    db = _ApiDb()

    DB_AVAILABLE = True  # Co api_client = co the goi API. Loi tam thoi xu ly tai cho.
    # 1 lan check optional cho user biet trang thai luc startup
    if is_alive():
        print('[API] Ket noi REST API server OK')
    else:
        print('[API] CANH BAO: API server chua chay - cac action se loi cho den khi server len')
        print('      Hay chay: uvicorn backend.api.main:app --port 8000')
except Exception as _e:
    print(f'[API] Khong load duoc api_client ({_e}) - frontend chay che do offline')


# ===== Cache layer cho courses/classes =====
# Load 1 lan luc startup, refresh sau admin CRUD.
# Khong dung mock hardcode - lay tu API thuc.

def _load_app_data():
    """Goi sau khi import api_client thanh cong de prefetch cache."""
    if not DB_AVAILABLE:
        return
    try:
        _load_courses_cache()
        _load_classes_cache()
        print(f'[CACHE] Loaded {len(MOCK_COURSES)} courses + {len(MOCK_CLASSES)} classes')
    except Exception as e:
        print(f'[CACHE] Loi prefetch: {e}')


# ===== helpers popup =====
def _style_msgbox(box):
    """Apply Segoe UI + kich co hop ly cho QMessageBox"""
    box.setFont(QFont('Segoe UI', 10))
    box.setStyleSheet(
        'QMessageBox { font-family: "Segoe UI"; background: white; } '
        'QMessageBox QLabel { font-family: "Segoe UI"; font-size: 13px; color: #1a1a2e; min-width: 280px; padding: 6px; } '
        'QMessageBox QPushButton { font-family: "Segoe UI"; font-size: 12px; min-width: 84px; min-height: 28px; padding: 6px 16px; }'
    )


def fmt_date(value, fmt='%d/%m/%Y', default='—'):
    """Format date/datetime/ISO string thanh dd/mm/yyyy.
    API tra ve ISO string (do JSON), nen luc parse can detect string."""
    if not value:
        return default
    if isinstance(value, str):
        try:
            from datetime import datetime
            # Thu parse ISO format (2025-12-31 hoac 2025-12-31T10:00:00)
            value = datetime.fromisoformat(value.split('T')[0] if 'T' in value else value)
        except Exception:
            return value  # tra ve string nguyen ban neu parse fail
    try:
        return value.strftime(fmt)
    except Exception:
        return str(value)


def msg_info(parent, title, text):
    box = QtWidgets.QMessageBox(parent)
    box.setIcon(QtWidgets.QMessageBox.Information)
    box.setWindowTitle(title)
    box.setText(text)
    _style_msgbox(box)
    box.exec_()


def msg_warn(parent, title, text):
    box = QtWidgets.QMessageBox(parent)
    box.setIcon(QtWidgets.QMessageBox.Warning)
    box.setWindowTitle(title)
    box.setText(text)
    _style_msgbox(box)
    box.exec_()


def msg_confirm(parent, title, text):
    box = QtWidgets.QMessageBox(parent)
    box.setIcon(QtWidgets.QMessageBox.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    box.setDefaultButton(QtWidgets.QMessageBox.No)
    # doi chu nut sang tieng Viet
    box.button(QtWidgets.QMessageBox.Yes).setText('Đồng ý')
    box.button(QtWidgets.QMessageBox.No).setText('Huỷ')
    _style_msgbox(box)
    return box.exec_() == QtWidgets.QMessageBox.Yes


def msg_input(parent, title, label, default=''):
    dlg = QtWidgets.QInputDialog(parent)
    dlg.setFont(QFont('Segoe UI', 10))
    dlg.setStyleSheet(
        'QInputDialog { font-family: "Segoe UI"; background: white; } '
        'QLabel { font-size: 13px; color: #1a1a2e; } '
        'QLineEdit { font-size: 13px; min-height: 28px; padding: 6px 10px; '
        '  border: 1px solid #d2d6dc; border-radius: 6px; } '
        'QPushButton { font-size: 12px; min-width: 84px; min-height: 28px; }'
    )
    dlg.setWindowTitle(title)
    dlg.setLabelText(label)
    dlg.setTextValue(default)
    dlg.setOkButtonText('Đồng ý')
    dlg.setCancelButtonText('Huỷ')
    if dlg.exec_() == QtWidgets.QDialog.Accepted:
        return dlg.textValue().strip()
    return None


def norm(s):
    """bo dau + lower cho search"""
    if not s:
        return ''
    import unicodedata
    s = unicodedata.normalize('NFD', str(s))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower().replace('đ', 'd').replace('Đ', 'd')


def table_filter(tbl, keyword, cols=None):
    """an row khong match keyword - check cac cot cho phep"""
    kw = norm(keyword)
    if cols is None:
        cols = range(tbl.columnCount())
    for r in range(tbl.rowCount()):
        show = not kw
        if kw:
            for c in cols:
                it = tbl.item(r, c)
                if it and kw in norm(it.text()):
                    show = True
                    break
        tbl.setRowHidden(r, not show)


class _GradeEditorDelegate(QtWidgets.QStyledItemDelegate):
    """delegate cho o nhap diem - phong to editor ra ngoai cell de de nhin"""
    def createEditor(self, parent, option, index):
        ed = QtWidgets.QLineEdit(parent)
        ed.setFont(QFont('Segoe UI', 13, QFont.Bold))
        ed.setStyleSheet(
            'QLineEdit { background: white; color: #1a1a2e; '
            'border: 2px solid #002060; border-radius: 4px; '
            'padding: 6px 10px; }'
        )
        ed.setAlignment(Qt.AlignCenter)
        return ed

    def updateEditorGeometry(self, editor, option, index):
        # phong editor ra 140x44 de de go
        rect = option.rect
        w = max(rect.width() + 20, 140)
        h = max(rect.height() + 8, 44)
        x = rect.x() - (w - rect.width()) // 2
        y = rect.y() - (h - rect.height()) // 2
        editor.setGeometry(x, y, w, h)


def style_dialog(dlg):
    """Apply font Segoe UI + stylesheet chung cho moi QDialog.
    Fix loi font tieng Viet + input bi cat chu."""
    dlg.setFont(QFont('Segoe UI', 10))
    dlg.setStyleSheet(
        'QDialog { background: white; font-family: "Segoe UI"; } '
        'QLabel { font-family: "Segoe UI"; font-size: 12px; color: #1a1a2e; background: transparent; } '
        'QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox { '
        '  font-family: "Segoe UI"; font-size: 13px; '
        '  min-height: 28px; padding: 6px 10px; '
        '  border: 1px solid #d2d6dc; border-radius: 6px; '
        '  background: white; color: #1a1a2e; } '
        'QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: #002060; } '
        'QLineEdit[readOnly="true"] { background: #f7fafc; color: #718096; } '
        'QPushButton { font-family: "Segoe UI"; font-size: 12px; min-height: 30px; padding: 6px 16px; } '
        'QDialogButtonBox QPushButton { min-width: 88px; } '
        'QFormLayout { spacing: 12px; }'
    )


def show_detail_dialog(parent, title, fields, avatar_text=None, subtitle=None):
    """Dialog chi tiet co header navy + avatar + danh sach field dep"""
    # mau EAUT tu module-level COLORS
    navy = '#002060'
    navy_hover = '#1a3a6c'
    text_dark = '#1a1a2e'
    text_mid = '#4a5568'
    text_light = '#718096'
    border = '#d2d6dc'

    dlg = QtWidgets.QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setFixedSize(440, 540)
    dlg.setFont(QFont('Segoe UI', 10))
    dlg.setStyleSheet('QDialog { background: white; font-family: "Segoe UI"; }')

    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    # header navy voi avatar
    header = QtWidgets.QFrame()
    header.setFixedHeight(140)
    header.setStyleSheet(f'QFrame {{ background: {navy}; border: none; }}')
    hv = QtWidgets.QVBoxLayout(header)
    hv.setContentsMargins(20, 22, 20, 18)
    hv.setSpacing(6)
    hv.setAlignment(Qt.AlignCenter)

    if avatar_text:
        av = QtWidgets.QLabel(avatar_text[:2].upper())
        av.setFixedSize(56, 56)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet('QLabel { background: rgba(255,255,255,0.18); '
                         'border-radius: 28px; color: white; '
                         'font-size: 18px; font-weight: bold; }')
        wrap = QtWidgets.QHBoxLayout()
        wrap.setAlignment(Qt.AlignCenter)
        wrap.addWidget(av)
        hv.addLayout(wrap)

    lbl_title = QtWidgets.QLabel(title)
    lbl_title.setAlignment(Qt.AlignCenter)
    lbl_title.setStyleSheet('color: white; font-size: 15px; font-weight: bold; background: transparent;')
    hv.addWidget(lbl_title)

    if subtitle:
        lbl_sub = QtWidgets.QLabel(subtitle)
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet('color: rgba(255,255,255,0.75); font-size: 11px; background: transparent;')
        hv.addWidget(lbl_sub)

    lay.addWidget(header)

    # body voi cac field
    body = QtWidgets.QScrollArea()
    body.setWidgetResizable(True)
    body.setStyleSheet('QScrollArea { border: none; background: white; }')
    inner = QtWidgets.QWidget()
    form = QtWidgets.QVBoxLayout(inner)
    form.setContentsMargins(28, 22, 28, 22)
    form.setSpacing(14)

    for label, val in fields:
        row = QtWidgets.QFrame()
        row.setStyleSheet(f'QFrame {{ border: none; border-bottom: 1px solid #edf2f7; background: transparent; }}')
        rl = QtWidgets.QVBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 10)
        rl.setSpacing(4)
        lbl_k = QtWidgets.QLabel(str(label))
        lbl_k.setFont(QFont('Segoe UI', 8, QFont.Bold))
        lbl_k.setStyleSheet(f'color: {text_light}; background: transparent; border: none; '
                            f'letter-spacing: 0.5px;')
        lbl_v = QtWidgets.QLabel(str(val) if val is not None and val != '' else '—')
        lbl_v.setFont(QFont('Segoe UI', 11, QFont.Medium if hasattr(QFont, 'Medium') else QFont.Normal))
        lbl_v.setStyleSheet(f'color: {text_dark}; background: transparent; border: none;')
        lbl_v.setWordWrap(True)
        rl.addWidget(lbl_k)
        rl.addWidget(lbl_v)
        form.addWidget(row)

    form.addStretch()
    body.setWidget(inner)
    lay.addWidget(body, 1)

    # footer nut dong
    footer = QtWidgets.QFrame()
    footer.setFixedHeight(60)
    footer.setStyleSheet(f'QFrame {{ background: #f7fafc; border-top: 1px solid {border}; }}')
    fl = QtWidgets.QHBoxLayout(footer)
    fl.setContentsMargins(20, 10, 20, 10)
    fl.setAlignment(Qt.AlignRight)
    btn = QtWidgets.QPushButton('Đóng')
    btn.setFixedSize(110, 36)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f'QPushButton {{ background: {navy}; color: white; border: none; '
                      f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                      f'QPushButton:hover {{ background: {navy_hover}; }}')
    btn.clicked.connect(dlg.accept)
    fl.addWidget(btn)
    lay.addWidget(footer)

    dlg.exec_()


def toggle_max_window(win):
    """Toggle phong to / thu nho cua so"""
    if win.isMaximized():
        win.showNormal()
    else:
        win.showMaximized()


def add_maximize_button(sidebar, win):
    """Them nut phong to/thu nho o goc tren ben phai cua sidebar"""
    btn = QtWidgets.QPushButton('⛶', sidebar)
    btn.setGeometry(195, 20, 24, 24)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setToolTip('Phóng to / Thu nhỏ cửa sổ')
    btn.setStyleSheet(
        'QPushButton { background: transparent; border: none; '
        'font-size: 18px; color: #4a5568; font-weight: bold; } '
        'QPushButton:hover { background: #edf2f7; border-radius: 4px; color: #002060; }'
    )
    btn.clicked.connect(lambda: toggle_max_window(win))
    return btn


def widen_search(page, txt_name, new_width, shift_after=None):
    """noi rong o tim kiem va day widget ben phai neu can"""
    txt = page.findChild(QtWidgets.QLineEdit, txt_name)
    if not txt:
        return
    g = txt.geometry()
    if g.width() >= new_width:
        return
    diff = new_width - g.width()
    txt.setGeometry(g.x(), g.y(), new_width, g.height())
    # day cac combo/button ben phai sang
    if shift_after:
        for nm in shift_after:
            w = page.findChild(QtWidgets.QWidget, nm)
            if w:
                gw = w.geometry()
                if gw.x() > g.x():
                    w.setGeometry(gw.x() + diff, gw.y(), gw.width(), gw.height())


def export_table_csv(parent, tbl, default_name='export.csv', title='Xuất file'):
    """ghi bang ra CSV, hoi nguoi dung chon noi luu"""
    import csv
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent, title,
        os.path.join(os.path.expanduser('~'), 'Desktop', default_name),
        'CSV UTF-8 (*.csv)'
    )
    if not path:
        return False
    try:
        # dung utf-8-sig de Excel hieu tieng Viet
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            wr = csv.writer(f)
            headers = []
            for c in range(tbl.columnCount()):
                h = tbl.horizontalHeaderItem(c)
                headers.append(h.text() if h else f'Col{c}')
            wr.writerow(headers)
            for r in range(tbl.rowCount()):
                if tbl.isRowHidden(r):
                    continue
                row = []
                for c in range(tbl.columnCount()):
                    it = tbl.item(r, c)
                    row.append(it.text() if it else '')
                wr.writerow(row)
        msg_info(parent, 'Thành công', f'Đã xuất file:\n{path}')
        return True
    except Exception as e:
        msg_warn(parent, 'Lỗi', f'Không xuất được file:\n{e}')
        return False

BASE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(BASE, 'ui')
RES = os.path.join(BASE, 'resources')
ICONS = os.path.join(RES, 'icons')

# Current user placeholder - duoc fill sau khi login tu API.
# 4 dict tuong ung 4 role, sidebar/profile binding default truoc khi co data that.
# Sau login, _sync_current_from_user(user) overwrite cac field tu /auth/login response.
CURRENT_USER = {
    'username': '', 'password': '', 'role': 'Học viên',
    'name': '', 'msv': '', 'lop': '',
    'khoa': '', 'ngaysinh': '', 'gioitinh': '',
    'nienkhoa': '', 'hedt': '',
    'email': '', 'sdt': '',
    'diachi': '', 'initials': '?',
}

CURRENT_ADMIN = {
    'username': '', 'password': '',
    'name': '', 'role': 'Quản trị viên', 'initials': 'AD',
}

CURRENT_TEACHER = {
    'username': '', 'password': '', 'role': 'Giảng viên',
    'id': '', 'name': '', 'initials': '?',
    'khoa': '', 'hocvi': '',
    'email': '', 'sdt': '',
}

CURRENT_EMPLOYEE = {
    'username': '', 'password': '', 'role': 'Nhân viên',
    'id': '', 'name': '', 'initials': '?',
    'chucvu': '',
    'email': '', 'sdt': '',
}

# Backward-compat aliases - de tranh break code cu chua sua het
MOCK_USER = CURRENT_USER
MOCK_ADMIN = CURRENT_ADMIN
MOCK_TEACHER = CURRENT_TEACHER
MOCK_EMPLOYEE = CURRENT_EMPLOYEE

# Cache classes/courses tu API - thay vi hardcode mock data
# Lazy-loaded boi _load_courses_cache() / _load_classes_cache()
# Empty list = chua load hoac API loi -> UI hien empty state
MOCK_COURSES = []  # alias backward compat - actually populated tu API
MOCK_CLASSES = []  # alias backward compat - actually populated tu API


def _load_courses_cache():
    """Load courses tu API. Cache vao MOCK_COURSES de cac code cu reuse.
    Tra ve list of (ma_mon, ten_mon)."""
    global MOCK_COURSES
    if MOCK_COURSES:
        return MOCK_COURSES
    try:
        rows = CourseService.get_all_courses() or []
        MOCK_COURSES = [(r['ma_mon'], r.get('ten_mon', '')) for r in rows]
    except Exception as e:
        print(f'[CACHE] Load courses loi: {e}')
        MOCK_COURSES = []
    return MOCK_COURSES


def _load_classes_cache():
    """Load classes tu API. Cache vao MOCK_CLASSES.
    Format: list of (ma_lop, ma_mon, ten_mon, ten_gv, lich, phong, smax, scur, gia)."""
    global MOCK_CLASSES
    if MOCK_CLASSES:
        return MOCK_CLASSES
    try:
        rows = CourseService.get_all_classes() or []
        MOCK_CLASSES = [(
            r.get('ma_lop', ''), r.get('ma_mon', ''), r.get('ten_mon', ''),
            r.get('ten_gv', '') or '', r.get('lich', '') or '',
            r.get('phong', '') or '',
            int(r.get('siso_max') or 40),
            int(r.get('siso_hien_tai') or 0),
            int(r.get('gia') or 0),
        ) for r in rows]
    except Exception as e:
        print(f'[CACHE] Load classes loi: {e}')
        MOCK_CLASSES = []
    return MOCK_CLASSES


def _refresh_cache():
    """Force refresh cache - goi sau khi admin them/sua/xoa."""
    global MOCK_COURSES, MOCK_CLASSES
    MOCK_COURSES = []
    MOCK_CLASSES = []
    _load_courses_cache()
    _load_classes_cache()


# STUDENT pages
PAGES = [
    ('btnHome', 'dashboard_student.ui'),
    ('btnSchedule', 'schedule.ui'),
    ('btnExam', 'exam_schedule.ui'),
    ('btnGrades', 'grades.ui'),
    ('btnReview', 'teacher_review.ui'),
    ('btnNotice', 'notifications.ui'),
    ('btnProfile', 'profile.ui'),
]

MENU_ITEMS = [
    ('btnHome', 'iconHome', 'home', 'Trang chủ'),
    ('btnSchedule', 'iconSchedule', 'calendar', 'Lịch học'),
    ('btnExam', 'iconExam', 'clipboard', 'Lịch thi'),
    ('btnGrades', 'iconGrades', 'bar-chart', 'Xem điểm'),
    ('btnReview', 'iconReview', 'star', 'Đánh giá giảng viên'),
    ('btnNotice', 'iconNotice', 'bell', 'Thông báo'),
    ('btnProfile', 'iconProfile', 'user', 'Thông tin cá nhân'),
]

# TEACHER pages
TEACHER_PAGES = [
    ('btnTeaDash', 'teacher_dashboard.ui'),
    ('btnTeaSchedule', 'schedule.ui'),
    ('btnTeaClasses', 'teacher_classes.ui'),
    ('btnTeaStudents', 'teacher_students.ui'),
    ('btnTeaAttend', 'teacher_attendance.ui'),
    ('btnTeaNotice', 'teacher_notice.ui'),
    ('btnTeaGrades', 'teacher_grades.ui'),
    ('btnTeaProfile', 'profile.ui'),
]

TEACHER_MENU = [
    ('btnTeaDash', 'iconTeaDash', 'home', 'Tổng quan'),
    ('btnTeaSchedule', 'iconTeaSchedule', 'calendar', 'Lịch dạy'),
    ('btnTeaClasses', 'iconTeaClasses', 'layers', 'Lớp của tôi'),
    ('btnTeaStudents', 'iconTeaStudents', 'users', 'Học viên'),
    ('btnTeaAttend', 'iconTeaAttend', 'check-circle', 'Điểm danh'),
    ('btnTeaNotice', 'iconTeaNotice', 'bell', 'Gửi thông báo'),
    ('btnTeaGrades', 'iconTeaGrades', 'edit', 'Nhập điểm'),
    ('btnTeaProfile', 'iconTeaProfile', 'user', 'Thông tin cá nhân'),
]

# EMPLOYEE pages
EMPLOYEE_PAGES = [
    ('btnEmpDash', 'employee_dashboard.ui'),
    ('btnEmpRegister', 'employee_register.ui'),
    ('btnEmpRegList', 'employee_registrations.ui'),
    ('btnEmpPay', 'employee_payment.ui'),
    ('btnEmpClasses', 'employee_classes.ui'),
    ('btnEmpProfile', 'profile.ui'),
]

EMPLOYEE_MENU = [
    ('btnEmpDash', 'iconEmpDash', 'home', 'Tổng quan'),
    ('btnEmpRegister', 'iconEmpRegister', 'edit', 'Đăng ký cho HV'),
    ('btnEmpRegList', 'iconEmpRegList', 'file-text', 'DS đăng ký'),
    ('btnEmpPay', 'iconEmpPay', 'credit-card', 'Thu học phí'),
    ('btnEmpClasses', 'iconEmpClasses', 'layers', 'Quản lý lớp'),
    ('btnEmpProfile', 'iconEmpProfile', 'user', 'Thông tin cá nhân'),
]

# ADMIN pages
ADMIN_PAGES = [
    ('btnAdminDash', 'admin_dashboard.ui'),
    ('btnAdminCourse', 'admin_courses.ui'),
    ('btnAdminClasses', 'admin_classes.ui'),
    ('btnAdminStudent', 'admin_students.ui'),
    ('btnAdminTeacher', 'admin_teachers.ui'),
    ('btnAdminEmployee', 'admin_employees.ui'),
    ('btnAdminSemester', 'admin_semester.ui'),
    ('btnAdminCurriculum', 'admin_curriculum.ui'),
    ('btnAdminAudit', 'admin_audit.ui'),
    ('btnAdminStats', 'admin_stats.ui'),
]

ADMIN_MENU = [
    ('btnAdminDash', 'iconAdminDash', 'grid', 'Tổng quan'),
    ('btnAdminCourse', 'iconAdminCourse', 'database', 'Quản lý môn học'),
    ('btnAdminClasses', 'iconAdminClasses', 'layers', 'Quản lý lớp'),
    ('btnAdminStudent', 'iconAdminStudent', 'users', 'Quản lý học viên'),
    ('btnAdminTeacher', 'iconAdminTeacher', 'user-check', 'Quản lý giảng viên'),
    ('btnAdminEmployee', 'iconAdminEmployee', 'briefcase', 'Quản lý nhân viên'),
    ('btnAdminSemester', 'iconAdminSemester', 'sliders', 'Quản lý học kỳ'),
    ('btnAdminCurriculum', 'iconAdminCurriculum', 'file-text', 'Khung chương trình'),
    ('btnAdminAudit', 'iconAdminAudit', 'shield', 'Nhật ký hệ thống'),
    ('btnAdminStats', 'iconAdminStats', 'pie-chart', 'Thống kê'),
]


class MainWindow(QtWidgets.QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.setObjectName('MainWindow')
        self.setWindowTitle('EAUT - Hệ thống Đăng ký Khóa học')
        self.setMinimumSize(1100, 700)
        self.resize(1100, 700)
        self.setWindowIcon(QIcon(os.path.join(RES, 'logo.png')))

        # layout chinh
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # sidebar
        self.sidebar = self._build_sidebar()
        layout.addWidget(self.sidebar)

        # stacked widget
        self.stack = QtWidgets.QStackedWidget()
        layout.addWidget(self.stack)

        # load tung trang
        self.page_widgets = []
        self.pages_filled = [False] * len(PAGES)
        for btn_name, ui_file in PAGES:
            page = self._load_page(ui_file)
            self.page_widgets.append(page)
            self.stack.addWidget(page)

        # hien trang dau tien
        self._switch_page(0)
        self._fill_dashboard()
        self.pages_filled[0] = True

    def _build_sidebar(self):
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet('QFrame#sidebar { background: #ffffff; border-right: 1px solid #d2d6dc; }')

        # logo
        self.lblSidebarLogo = QtWidgets.QLabel(sidebar)
        self.lblSidebarLogo.setGeometry(20, 20, 42, 42)
        self.lblSidebarLogo.setScaledContents(True)
        logo_path = os.path.join(RES, 'logo.png')
        if os.path.exists(logo_path):
            self.lblSidebarLogo.setPixmap(QPixmap(logo_path).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # ten truong
        self.lblSidebarSchool = QtWidgets.QLabel('EAUT', sidebar)
        self.lblSidebarSchool.setGeometry(68, 20, 150, 20)
        self.lblSidebarSchool.setStyleSheet(f'color: {COLORS["navy"]}; font-size: 13px; font-weight: bold; background: transparent;')

        self.lblSidebarSub = QtWidgets.QLabel('Đăng ký khóa học', sidebar)
        self.lblSidebarSub.setGeometry(68, 40, 120, 16)
        self.lblSidebarSub.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 11px; background: transparent;')
        # Nut phong to/thu nho cua so
        add_maximize_button(sidebar, self)

        # duong ke
        sep = QtWidgets.QFrame(sidebar)
        sep.setGeometry(15, 74, 200, 1)
        sep.setStyleSheet(f'background: {COLORS["border"]};')

        # menu buttons
        y = 86
        for btn_name, icon_name, icon_file, label in MENU_ITEMS:
            btn = QtWidgets.QPushButton(label, sidebar)
            btn.setObjectName(btn_name)
            btn.setGeometry(10, y, 210, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(SIDEBAR_NORMAL)
            setattr(self, btn_name, btn)

            icon_lbl = QtWidgets.QLabel(sidebar)
            icon_lbl.setObjectName(icon_name)
            icon_lbl.setGeometry(20, y + 9, 16, 16)
            icon_lbl.setScaledContents(True)
            icon_lbl.setStyleSheet('background: transparent;')
            icon_path = os.path.join(ICONS, f'{icon_file}.png')
            if os.path.exists(icon_path):
                icon_lbl.setPixmap(QPixmap(icon_path).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            setattr(self, icon_name, icon_lbl)

            y += 38

        # connect sidebar buttons
        for i, (btn_name, _) in enumerate(PAGES):
            btn = getattr(self, btn_name)
            btn.clicked.connect(lambda checked, idx=i: self._on_nav(idx))

        # duong ke duoi
        sep2 = QtWidgets.QFrame(sidebar)
        sep2.setGeometry(15, 610, 200, 1)
        sep2.setStyleSheet(f'background: {COLORS["border"]};')

        # user info
        self.lblAvatar = QtWidgets.QLabel(MOCK_USER['initials'], sidebar)
        self.lblAvatar.setGeometry(15, 625, 38, 38)
        self.lblAvatar.setAlignment(Qt.AlignCenter)
        self.lblAvatar.setStyleSheet(f'background: {COLORS["active_bg"]}; border-radius: 19px; color: {COLORS["navy"]}; font-size: 13px; font-weight: bold;')

        self.lblStudentName = QtWidgets.QLabel(MOCK_USER['name'], sidebar)
        self.lblStudentName.setGeometry(60, 626, 135, 17)
        self.lblStudentName.setStyleSheet(f'color: {COLORS["text_dark"]}; font-size: 12px; font-weight: bold; background: transparent;')

        self.lblStudentId = QtWidgets.QLabel(f"MSV: {MOCK_USER['msv']}", sidebar)
        self.lblStudentId.setGeometry(60, 644, 110, 15)
        self.lblStudentId.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 10px; background: transparent;')

        # logout
        self.iconLogout = QtWidgets.QLabel(sidebar)
        self.iconLogout.setGeometry(191, 635, 18, 18)
        self.iconLogout.setScaledContents(True)
        self.iconLogout.setStyleSheet('background: transparent;')
        logout_path = os.path.join(ICONS, 'log-out.png')
        if os.path.exists(logout_path):
            self.iconLogout.setPixmap(QPixmap(logout_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.btnLogout = QtWidgets.QPushButton(sidebar)
        self.btnLogout.setGeometry(183, 627, 34, 34)
        self.btnLogout.setCursor(Qt.PointingHandCursor)
        self.btnLogout.setToolTip('Đăng xuất')
        self.btnLogout.setStyleSheet('QPushButton { background: transparent; border: none; } QPushButton:hover { background: #fce8e6; border-radius: 8px; }')
        self.btnLogout.clicked.connect(self._on_logout)

        return sidebar

    def _load_page(self, ui_file):
        """load .ui, tach contentArea ra"""
        temp = uic.loadUi(os.path.join(UI, ui_file))
        content = temp.findChild(QtWidgets.QFrame, 'contentArea')
        if content:
            content.setParent(None)
            # chuan hoa kich thuoc
            content.setFixedSize(870, 700)
            return content
        # fallback neu khong co contentArea
        return temp

    def _on_nav(self, index):
        self._switch_page(index)
        if not self.pages_filled[index]:
            fill_methods = [
                self._fill_dashboard, self._fill_schedule, self._fill_exam,
                self._fill_grades, self._fill_review,
                self._fill_notifications, self._fill_profile,
            ]
            if fill_methods[index]:
                fill_methods[index]()
            self.pages_filled[index] = True

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
        active_btn = PAGES[index][0]
        # highlight active
        for btn_name, _ in PAGES:
            btn = getattr(self, btn_name)
            icon = getattr(self, btn_name.replace('btn', 'icon'))
            if btn_name == active_btn:
                btn.setStyleSheet(SIDEBAR_ACTIVE)
                icon.raise_()
            else:
                btn.setStyleSheet(SIDEBAR_NORMAL)

    def _on_logout(self):
        self.close()
        self.app_ref.show_login()

    # === DATA FILL ===

    def _fill_dashboard(self):
        page = self.page_widgets[0]

        # stat icons
        for attr, icon_file in [('iconStat1Img', 'layers'), ('iconStat2Img', 'check-circle'), ('iconStat3Img', 'clock')]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setPixmap(QPixmap(os.path.join(ICONS, f'{icon_file}.png')).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # stat colors
        for attr, color in [('iconStat1', COLORS['navy']), ('iconStat2', COLORS['green']), ('iconStat3', COLORS['gold'])]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
                w.setStyleSheet(f'background: rgba({r},{g},{b},0.08); border-radius: 10px;')

        for attr, color in [('lblStatCourses', COLORS['navy']), ('lblStatCredits', COLORS['green']), ('lblStatRemaining', COLORS['gold'])]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setStyleSheet(f'color: {color}; font-size: 24px; font-weight: bold; background: transparent;')

        for attr in ['lblStatCoursesLabel', 'lblStatCreditsLabel', 'lblStatRemainingLabel']:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 12px; background: transparent;')

        # welcome
        w = page.findChild(QtWidgets.QLabel, 'lblWelcome')
        if w:
            w.setText(f"Xin chào, {MOCK_USER['name']}")

        # bang khoa hoc
        data = [
            ['IT001', 'Lập trình ứng dụng với Python', '3', 'Nguyễn Đức Thiện', 'T3 (7:00-9:30)', 'Đã xác nhận'],
            ['IT002', 'Cơ sở dữ liệu', '3', 'Lê Thị C', 'T5 (7:00-9:30)', 'Đã xác nhận'],
            ['IT003', 'Mạng máy tính', '3', 'Phạm Văn D', 'T6 (7:00-9:30)', 'Chờ duyệt'],
            ['MA001', 'Toán rời rạc', '3', 'Nguyễn Thị E', 'T2 (9:30-12:00)', 'Đã xác nhận'],
            ['EN001', 'Tiếng Anh 3', '3', 'Hoàng Văn F', 'T4 (13:00-15:30)', 'Đã xác nhận'],
        ]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCourses')
        if tbl:
            tbl.setRowCount(len(data))
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    if c == 5 and 'xác nhận' in val:
                        item.setForeground(QColor(COLORS['green']))
                    elif c == 5:
                        item.setForeground(QColor(COLORS['orange']))
                    tbl.setItem(r, c, item)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setColumnWidth(0, 60)
            tbl.setColumnWidth(1, 200)
            tbl.setColumnWidth(2, 50)
            tbl.setColumnWidth(3, 140)
            tbl.setColumnWidth(4, 125)
            tbl.verticalHeader().setVisible(False)

    def _fill_schedule(self):
        page = self.page_widgets[1]

        # dieu chinh kich thuoc schedule
        sf = page.findChild(QtWidgets.QFrame, 'scheduleFrame')
        if sf:
            sf.setGeometry(15, 68, 610, 618)
        cf = page.findChild(QtWidgets.QFrame, 'calendarFrame')
        if cf:
            cf.setGeometry(638, 68, 220, 230)
        lf = page.findChild(QtWidgets.QFrame, 'legendFrame')
        if lf:
            lf.setGeometry(638, 310, 220, 180)

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblSchedule')
        if not tbl:
            return

        hours = ['7:00','8:00','9:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00']
        tbl.setRowCount(len(hours))
        tbl.verticalHeader().setVisible(False)

        today = QDate.currentDate()
        monday = today.addDays(-(today.dayOfWeek() - 1))
        days_vn = ['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7']
        for i in range(6):
            d = monday.addDays(i)
            tbl.horizontalHeaderItem(i+1).setText(f'{d.toString("dd/MM/yyyy")}\n{days_vn[i]}')

        tbl.setColumnWidth(0, 45)
        for i in range(1, 7):
            tbl.setColumnWidth(i, 92)
        # font lon hon va row cao hon de doc lich hoc de hon
        for r in range(len(hours)):
            tbl.setRowHeight(r, 55)
            item = QtWidgets.QTableWidgetItem(hours[r])
            item.setTextAlignment(Qt.AlignRight | Qt.AlignTop)
            item.setForeground(QColor('#718096'))
            item.setFont(QFont('Segoe UI', 9))
            tbl.setItem(r, 0, item)

        for r in range(len(hours)):
            for c in range(1, 7):
                if not tbl.item(r, c) and not tbl.cellWidget(r, c):
                    tbl.setItem(r, c, QtWidgets.QTableWidgetItem(''))

        def mk_card(ten, ts, toa, phong, gv, color):
            f = QtWidgets.QFrame()
            f.setStyleSheet(f'QFrame {{ background: white; border: 1px solid #d2d6dc; border-radius: 4px; border-top: 3px solid {color}; margin: 1px; }}')
            vb = QtWidgets.QVBoxLayout(f)
            vb.setContentsMargins(5, 4, 5, 4)
            vb.setSpacing(2)
            for txt, st in [(ten, f'color: {color}; font-size: 11px; font-weight: bold; border: none;'),
                            (ts, 'color: #4a5568; font-size: 10px; border: none;'),
                            (f'Tòa {toa} - {phong}', 'color: #718096; font-size: 9px; border: none;'),
                            (gv, 'color: #4a5568; font-size: 9px; border: none;')]:
                l = QtWidgets.QLabel(txt)
                l.setStyleSheet(st)
                l.setWordWrap(True)
                vb.addWidget(l)
            vb.addStretch()
            return f

        # (row, span, col, ten, gio, toa nha, phong, giang vien, mau)
        sched = [
            (0, 3, 2, 'LT ứng dụng Python', '07:00-09:30', 'EAUT', 'P.107', 'Nguyễn Đức Thiện', '#c68a1e'),
            (0, 3, 4, 'LT ứng dụng Python', '07:00-09:30', 'EAUT', 'P.107', 'Nguyễn Đức Thiện', '#c68a1e'),
            (0, 3, 5, 'LT ứng dụng Python', '07:00-09:30', 'EAUT', 'P.107', 'Nguyễn Đức Thiện', '#c68a1e'),
            (6, 3, 1, 'TA CN CNPM', '13:00-15:30', 'EAUT', 'P.301', 'Ngô Thảo Anh', '#002060'),
            (6, 3, 3, 'CN phần mềm', '13:00-15:30', 'VNB', 'P.408', 'Lê Trung Thực', '#276749'),
            (6, 3, 5, 'TA CN CNPM', '13:00-15:30', 'EAUT', 'P.301', 'Ngô Thảo Anh', '#002060'),
            (9, 3, 2, 'KT đồ hoạ MT', '15:40-18:10', 'EAUT', 'P.105', 'Lê Mai Nam', '#c53030'),
            (9, 3, 4, 'KT đồ hoạ MT', '15:40-18:10', 'EAUT', 'P.105', 'Lê Mai Nam', '#c53030'),
            (9, 3, 5, 'KT đồ hoạ MT', '15:40-18:10', 'EAUT', 'P.105', 'Lê Mai Nam', '#c53030'),
        ]
        for rs, span, col, ten, ts, toa, phong, gv, color in sched:
            tbl.setCellWidget(rs, col, mk_card(ten, ts, toa, phong, gv, color))
            tbl.setSpan(rs, col, span, 1)

        # Wire calendar: click 1 ngay → cap nhat header tuan + popup ngay do
        cal = page.findChild(QtWidgets.QCalendarWidget, 'calendarWidget')
        if cal:
            def on_cal_clicked(qdate):
                # tinh ngay dau tuan (thu 2)
                mon = qdate.addDays(-(qdate.dayOfWeek() - 1))
                for i in range(6):
                    d = mon.addDays(i)
                    tbl.horizontalHeaderItem(i+1).setText(f'{d.toString("dd/MM/yyyy")}\n{days_vn[i]}')
                # hien popup ngay chon
                thu_vn = ['Chủ nhật', 'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7'][qdate.dayOfWeek() % 7]
                msg_info(self, 'Xem lịch',
                         f'{thu_vn}, ngày {qdate.toString("dd/MM/yyyy")}\n'
                         f'Tuần: {mon.toString("dd/MM")} → {mon.addDays(5).toString("dd/MM")}')
            cal.clicked.connect(on_cal_clicked)

    def _fill_exam(self):
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblExam')
        if not tbl:
            return
        data = [
            ['1', 'IT001', 'Lập trình Python', '20/06/2026', 'Ca 1 (07:30-09:00)', 'P.A301', ''],
            ['2', 'IT002', 'Cơ sở dữ liệu', '22/06/2026', 'Ca 2 (09:30-11:00)', 'P.B205', ''],
            ['3', 'MA001', 'Toán rời rạc', '24/06/2026', 'Ca 1 (07:30-09:00)', 'P.A102', 'Máy tính'],
            ['4', 'EN001', 'Tiếng Anh 3', '26/06/2026', 'Ca 3 (13:30-15:00)', 'P.C401', ''],
            ['5', 'IT003', 'Mạng máy tính', '28/06/2026', 'Ca 2 (09:30-11:00)', 'P.A205', 'Không tài liệu'],
        ]
        tbl.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, val in enumerate(row):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(val))
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, w in enumerate([30, 65, 140, 85, 135, 80]):
            tbl.setColumnWidth(c, w)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 40)

        cbo = page.findChild(QtWidgets.QComboBox, 'cboSemester')
        if cbo:
            cbo.currentIndexChanged.connect(lambda idx: self._filter_exam_sem(idx))

    def _filter_exam_sem(self, idx):
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblExam')
        if not tbl:
            return
        # idx 0 = tat ca, 1 = HK2 (3 dong dau), 2 = HK1 (2 dong cuoi)
        for r in range(tbl.rowCount()):
            if idx == 0:
                tbl.setRowHidden(r, False)
            elif idx == 1:
                tbl.setRowHidden(r, r >= 3)
            else:
                tbl.setRowHidden(r, r < 3)

    def _fill_grades(self):
        page = self.page_widgets[3]
        # lay tu DB truoc neu co
        self._student_grades_by_sem = {}
        if DB_AVAILABLE:
            try:
                hv_id = MOCK_USER.get('id')
                if hv_id:
                    rows = GradeService.get_grades_by_student(hv_id)
                    # group theo semester_id (tu lop)
                    from collections import defaultdict
                    by_sem = defaultdict(list)
                    for g in rows:
                        sem = db.fetch_one(
                            'SELECT semester_id FROM classes WHERE ma_lop = %s',
                            (g['lop_id'],)
                        )
                        sid = sem['semester_id'] if sem and sem.get('semester_id') else 'HK2-2526'
                        by_sem[sid].append([
                            g['ma_mon'], g['ten_mon'], '3',
                            f"{float(g['diem_qt']):.1f}" if g.get('diem_qt') else '',
                            f"{float(g['diem_thi']):.1f}" if g.get('diem_thi') else '',
                            f"{float(g['tong_ket']):.1f}" if g.get('tong_ket') else '',
                            g.get('xep_loai', '') or '',
                        ])
                    self._student_grades_by_sem = dict(by_sem)
            except Exception as e:
                print(f'[GRADES] DB loi: {e}')
        # khong co du lieu -> de trong, ham render se hien bang rong
        # them mot dong placeholder de bao "Chua co du lieu diem"
        if not self._student_grades_by_sem:
            print('[GRADES] khong co du lieu, hien empty state')
        self._render_student_grades(None)
        # neu khong co diem -> chen dong text "Chua co du lieu" vao bang
        if not self._student_grades_by_sem:
            tbl_g = page.findChild(QtWidgets.QTableWidget, 'tblGrades')
            if tbl_g:
                tbl_g.setRowCount(1)
                placeholder = QtWidgets.QTableWidgetItem('Chưa có dữ liệu điểm')
                placeholder.setTextAlignment(Qt.AlignCenter)
                placeholder.setForeground(QColor(COLORS['text_light']))
                fnt = QFont('Segoe UI', 10)
                fnt.setItalic(True)
                placeholder.setFont(fnt)
                tbl_g.setItem(0, 0, placeholder)
                tbl_g.setSpan(0, 0, 1, tbl_g.columnCount())
                tbl_g.setRowHeight(0, 60)

        # GPA stats tu DB
        if DB_AVAILABLE:
            try:
                hv_id = MOCK_USER.get('id')
                if hv_id:
                    stats = GradeService.get_gpa_stats(hv_id)
                    for attr, val, color in [
                        ('lblGpa', f'{stats.get("gpa", 0):.2f}', COLORS['navy']),
                        ('lblGpaSem', f'{stats.get("gpa", 0):.2f}', COLORS['green']),
                        ('lblTotalCredits', str(int(stats.get('so_lop', 0)) * 3), COLORS['gold'])
                    ]:
                        w = page.findChild(QtWidgets.QLabel, attr)
                        if w:
                            w.setText(val)
                            w.setStyleSheet(f'color: {color}; font-size: 22px; font-weight: bold; background: transparent;')
            except Exception as e:
                print(f'[GPA] loi: {e}')
        # GPA cards fallback - khong co data thi de '-'
        for attr, val, color in [('lblGpa', '-', COLORS['navy']),
                                 ('lblGpaSem', '-', COLORS['green']),
                                 ('lblTotalCredits', '-', COLORS['gold'])]:
            if DB_AVAILABLE:
                break
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setText(val)
                w.setStyleSheet(f'color: {color}; font-size: 22px; font-weight: bold; background: transparent;')
        # nut "Tien do CT" - dat ben trai cboSemester, khong de tran tieu de
        # bo nut "Xuat PDF" cu vi chua co tinh nang that
        header = page.findChild(QtWidgets.QFrame, 'headerBar')
        # don dep nut cu (neu co tu lan render truoc)
        if header:
            old = header.findChild(QtWidgets.QPushButton, 'btnExportPDF')
            if old:
                old.deleteLater()
        # thu nho cboSemester de co cho cho nut Tien do
        cbo_sem = page.findChild(QtWidgets.QComboBox, 'cboSemester')
        if cbo_sem:
            cbo_sem.setGeometry(660, 12, 195, 32)
        if header and not header.findChild(QtWidgets.QPushButton, 'btnProgressCT'):
            btn_prog = QtWidgets.QPushButton('Xem tiến độ CT', header)
            btn_prog.setObjectName('btnProgressCT')
            btn_prog.setGeometry(515, 14, 135, 28)
            btn_prog.setCursor(Qt.PointingHandCursor)
            btn_prog.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 4px; padding: 4px 12px; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
            btn_prog.show()
            btn_prog.clicked.connect(self._show_progress_dialog)
        # combo loc HK
        cbo = page.findChild(QtWidgets.QComboBox, 'cboSemester')
        if cbo:
            cbo.clear()
            cbo.addItems(['Tất cả học kỳ', 'HK2 - 2025-2026', 'HK1 - 2025-2026'])
            sem_map = {0: None, 1: 'HK2-2526', 2: 'HK1-2526'}
            cbo.currentIndexChanged.connect(lambda idx: self._render_student_grades(sem_map.get(idx)))

    def _render_student_grades(self, sem_id):
        """Render bang diem theo HK. sem_id=None = all"""
        page = self.page_widgets[3]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblGrades')
        if not tbl:
            return
        grade_colors = {'A+': COLORS['green'], 'A': COLORS['green'],
                        'B+': COLORS['navy'], 'B': COLORS['navy'],
                        'C+': COLORS['orange'], 'C': COLORS['orange'],
                        'D': COLORS['red'], 'F': COLORS['red']}
        # luy ke du lieu + them cot HK de phan biet
        all_rows = []
        sem_labels = {'HK2-2526': 'HK2 25-26', 'HK1-2526': 'HK1 25-26',
                      'HK2-2425': 'HK2 24-25', 'HK1-2425': 'HK1 24-25'}
        if sem_id and sem_id in self._student_grades_by_sem:
            for r in self._student_grades_by_sem[sem_id]:
                all_rows.append([sem_labels.get(sem_id, sem_id)] + r)
        else:
            for s_id, rows in self._student_grades_by_sem.items():
                for r in rows:
                    all_rows.append([sem_labels.get(s_id, s_id)] + r)

        tbl.setColumnCount(8)
        headers = ['Học kỳ', 'Mã môn', 'Tên môn', 'TC', 'Điểm QT', 'Điểm thi', 'Tổng kết', 'Xếp loại']
        for c, h in enumerate(headers):
            tbl.setHorizontalHeaderItem(c, QtWidgets.QTableWidgetItem(h))

        tbl.setRowCount(len(all_rows))
        for r, row in enumerate(all_rows):
            for c, val in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter if c != 2 else Qt.AlignLeft | Qt.AlignVCenter)
                # cot HK to dam mau navy
                if c == 0:
                    item.setForeground(QColor(COLORS['navy']))
                    item.setFont(QFont('Segoe UI', 10, QFont.Bold))
                elif c == 7:  # xep loai
                    item.setForeground(QColor(grade_colors.get(val, '#4a5568')))
                    item.setFont(QFont('Segoe UI', 11, QFont.Bold))
                elif c == 6:  # tong ket
                    try:
                        s = float(val)
                        item.setForeground(QColor(COLORS['green'] if s >= 8 else COLORS['navy'] if s >= 6.5 else COLORS['orange']))
                    except ValueError:
                        pass
                tbl.setItem(r, c, item)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, w in enumerate([95, 60, 170, 30, 70, 70, 75, 80]):
            tbl.setColumnWidth(c, w)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(all_rows)):
            tbl.setRowHeight(r, 40)

    def _fill_review(self):
        page = self.page_widgets[4]
        si = page.findChild(QtWidgets.QLabel, 'iconSearchReview')
        if si:
            si.setPixmap(QPixmap(os.path.join(ICONS, 'search.png')).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        data = [
            ['1', 'Nguyễn Đức Thiện', 'CNTT', '4.6', '32'],
            ['2', 'Lê Thị C', 'CNTT', '4.3', '28'],
            ['3', 'Phạm Văn D', 'CNTT', '4.1', '25'],
            ['4', 'Nguyễn Thị E', 'Toán', '4.8', '30'],
            ['5', 'Hoàng Văn F', 'Ngoại ngữ', '3.9', '18'],
            ['6', 'Nguyễn Văn G', 'CNTT', '4.5', '22'],
            ['7', 'Trần Thị H', 'CNTT', '4.2', '20'],
            ['8', 'Lê Văn K', 'CNTT', '4.0', '15'],
        ]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblReview')
        if tbl:
            tbl.setRowCount(len(data))
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter if c >= 3 else Qt.AlignLeft | Qt.AlignVCenter)
                    if c == 3:
                        score = float(val)
                        color = COLORS['green'] if score >= 4.5 else COLORS['navy'] if score >= 4.0 else COLORS['orange']
                        item.setForeground(QColor(color))
                        item.setFont(QFont('Segoe UI', 11, QFont.Bold))
                    tbl.setItem(r, c, item)
                btn = QtWidgets.QPushButton('Đánh giá')
                btn.setCursor(Qt.PointingHandCursor)
                btn.setFixedSize(82, 24)
                btn.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 5px; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
                w = QtWidgets.QWidget()
                hl = QtWidgets.QHBoxLayout(w)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setAlignment(Qt.AlignCenter)
                hl.addWidget(btn)
                tbl.setCellWidget(r, 5, w)
            for c, cw in enumerate([40, 195, 115, 80, 90, 120]):
                tbl.setColumnWidth(c, cw)
            tbl.horizontalHeader().setStretchLastSection(False)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 50)
            # connect nut danh gia
            for r, row in enumerate(data):
                w = tbl.cellWidget(r, 5)
                if w:
                    b = w.findChild(QtWidgets.QPushButton)
                    if b:
                        gv_name = row[1]
                        b.clicked.connect(lambda ch, gv=gv_name: self._open_review_dialog(gv))

        widen_search(page, 'txtSearchReview', 280, ['cboSubject', 'cboDept'])
        # search + filter
        txt_s = page.findChild(QtWidgets.QLineEdit, 'txtSearchReview')
        if txt_s:
            txt_s.textChanged.connect(lambda t: table_filter(tbl, t, cols=[1, 2]) if tbl else None)
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboDept')
        if cbo_d:
            cbo_d.currentIndexChanged.connect(lambda: self._apply_review_filter())
        cbo_s = page.findChild(QtWidgets.QComboBox, 'cboSubject')
        if cbo_s:
            cbo_s.currentIndexChanged.connect(lambda: self._apply_review_filter())

    def _apply_review_filter(self):
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblReview')
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboDept')
        if not tbl or not cbo_d:
            return
        dept_map = {0: None, 1: 'CNTT', 2: 'Toán', 3: 'Ngoại ngữ'}
        want = dept_map.get(cbo_d.currentIndex())
        for r in range(tbl.rowCount()):
            it = tbl.item(r, 2)
            if not want:
                tbl.setRowHidden(r, False)
            else:
                tbl.setRowHidden(r, it.text() != want if it else False)

    def _open_review_dialog(self, gv_name):
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Đánh giá giảng viên')
        dlg.setFixedSize(420, 320)
        lay = QtWidgets.QVBoxLayout(dlg)
        lay.addWidget(QtWidgets.QLabel(f'<b>Giảng viên:</b> {gv_name}'))
        lay.addWidget(QtWidgets.QLabel('Chấm điểm (1-5):'))
        sp = QtWidgets.QSpinBox(); sp.setRange(1, 5); sp.setValue(4)
        lay.addWidget(sp)
        lay.addWidget(QtWidgets.QLabel('Nhận xét:'))
        ta = QtWidgets.QTextEdit()
        lay.addWidget(ta)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        # ghi DB
        if DB_AVAILABLE:
            try:
                hv_id = MOCK_USER.get('id')
                gv_row = db.fetch_one(
                    "SELECT id FROM users WHERE full_name = %s AND role = 'teacher'",
                    (gv_name,)
                )
                if hv_id and gv_row:
                    # lay 1 lop bat ky ma HV + GV cung co
                    lop = db.fetch_one(
                        """SELECT r.lop_id FROM registrations r
                             JOIN classes c ON c.ma_lop = r.lop_id
                            WHERE r.hv_id = %s AND c.gv_id = %s LIMIT 1""",
                        (hv_id, gv_row['id'])
                    )
                    lop_id = lop['lop_id'] if lop else 'NA'
                    ReviewService.submit_review(hv_id, gv_row['id'], lop_id,
                                                sp.value(), ta.toPlainText().strip())
                    print(f'[REVIEW] da ghi DB: {sp.value()}/5 cho {gv_name}')
            except Exception as e:
                print(f'[REVIEW] loi: {e}')
        msg_info(self, 'Đánh giá', f'Đã gửi đánh giá {sp.value()}/5 cho {gv_name}')

    def _fill_notifications(self):
        page = self.page_widgets[5]
        # fix scroll - set minimum height cho scrollContent
        sc = page.findChild(QtWidgets.QWidget, 'scrollContent')
        if sc:
            sc.setMinimumHeight(760)

    def _fill_profile(self):
        page = self.page_widgets[6]
        u = MOCK_USER
        for attr, val in [('lblProfileName', u['name']), ('lblProfileRole', f"Học viên - Lớp {u['lop']}"),
                          ('lblProfileAvatar', u['initials']), ('valMaSV', u['msv']), ('valHoTen', u['name']),
                          ('valNgaySinh', u['ngaysinh']), ('valGioiTinh', u['gioitinh']), ('valLop', u['lop']),
                          ('valKhoa', u['khoa']), ('valNienKhoa', u['nienkhoa']), ('valHeDT', u['hedt'])]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setText(val)
        for attr, val in [('txtEmail', u['email']), ('txtPhone', u['sdt']), ('txtAddress', u['diachi'])]:
            w = page.findChild(QtWidgets.QLineEdit, attr)
            if w:
                w.setText(val)

        btn_save = page.findChild(QtWidgets.QPushButton, 'btnSave')
        if btn_save:
            btn_save.clicked.connect(self._save_profile)
        btn_cp = page.findChild(QtWidgets.QPushButton, 'btnChangePass')
        if btn_cp:
            btn_cp.clicked.connect(self._change_pass)

    def _save_profile(self):
        page = self.page_widgets[6]
        for attr, key in [('txtEmail', 'email'), ('txtPhone', 'sdt'), ('txtAddress', 'diachi')]:
            w = page.findChild(QtWidgets.QLineEdit, attr)
            if w:
                MOCK_USER[key] = w.text().strip()
        msg_info(self, 'Thành công', 'Đã lưu thông tin cá nhân.')

    def _show_progress_dialog(self):
        """Dialog hien tien do hoc khung CT cua HV - lien ket curriculum + grades"""
        if not (DB_AVAILABLE and CurriculumService):
            msg_warn(self, 'Chưa kết nối được hệ thống',
                     'Tính năng tiến độ chương trình hiện không khả dụng.\n'
                     'Vui lòng kiểm tra kết nối mạng và đăng nhập lại.')
            return
        hv_id = MOCK_USER.get('id')
        if not hv_id:
            msg_warn(self, 'Lỗi', 'Không tìm thấy ID học viên')
            return
        try:
            prog = CurriculumService.get_progress_for_student(hv_id, 'CNTT')
        except Exception as e:
            msg_warn(self, 'Lỗi', f'Không lấy được tiến độ học:\n{e}')
            return

        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Tiến độ học khung chương trình - Ngành CNTT')
        dlg.setFixedSize(720, 580)
        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)

        # Header tien do
        ty_le = prog['ty_le']
        color = COLORS['green'] if ty_le >= 70 else COLORS['gold'] if ty_le >= 30 else COLORS['orange']
        lbl_title = QtWidgets.QLabel(
            f'<b style="color:{COLORS["navy"]}; font-size:18px;">{MOCK_USER["name"]}</b>  '
            f'<span style="color:#718096;">({MOCK_USER.get("msv", "")})</span><br>'
            f'<span style="color:{color}; font-size:24px; font-weight:bold;">'
            f'  {prog["da_pass"]}/{prog["tong_mon"]} môn  ·  {ty_le}%</span>'
        )
        lay.addWidget(lbl_title)

        # Progress bar
        bar = QtWidgets.QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(ty_le))
        bar.setFormat(f'{ty_le}%')
        bar.setStyleSheet(
            f'QProgressBar {{ height: 20px; border-radius: 10px; background: #edf2f7; '
            f'text-align: center; font-weight: bold; }} '
            f'QProgressBar::chunk {{ background: {color}; border-radius: 10px; }}'
        )
        lay.addWidget(bar)

        # 4 stat box
        stats_frame = QtWidgets.QFrame()
        sl = QtWidgets.QHBoxLayout(stats_frame)
        sl.setSpacing(8)
        for label, val, c in [
            ('Đã đạt',    prog['da_pass'],  COLORS['green']),
            ('Đang học',  prog['dang_hoc'], COLORS['navy']),
            ('Phải học lại', prog['da_fail'], COLORS['red']),
            ('Chưa học',  prog['chua_hoc'], COLORS['text_light']),
        ]:
            box = QtWidgets.QFrame()
            box.setStyleSheet(f'QFrame {{ background: white; border: 1px solid #d2d6dc; border-radius: 8px; padding: 8px; }}')
            bl = QtWidgets.QVBoxLayout(box)
            bl.setContentsMargins(8, 6, 8, 6)
            l1 = QtWidgets.QLabel(str(val))
            l1.setStyleSheet(f'color: {c}; font-size: 22px; font-weight: bold; border: none;')
            l1.setAlignment(Qt.AlignCenter)
            l2 = QtWidgets.QLabel(label)
            l2.setStyleSheet('color: #718096; font-size: 11px; border: none;')
            l2.setAlignment(Qt.AlignCenter)
            bl.addWidget(l1); bl.addWidget(l2)
            sl.addWidget(box)
        lay.addWidget(stats_frame)

        # Bang chi tiet 14 mon
        tbl = QtWidgets.QTableWidget()
        tbl.setColumnCount(6)
        tbl.setHorizontalHeaderLabels(['Mã môn', 'Tên môn', 'TC', 'HK', 'Điểm', 'Trạng thái'])
        tbl.setRowCount(len(prog['chi_tiet']))
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        status_text = {
            'pass':        ('✓ Đạt',          COLORS['green']),
            'fail':        ('✗ Trượt',        COLORS['red']),
            'learning':    ('⏳ Đang học',     COLORS['navy']),
            'not_started': ('— Chưa học',     COLORS['text_light']),
        }
        for r, m in enumerate(prog['chi_tiet']):
            tbl.setItem(r, 0, QtWidgets.QTableWidgetItem(m['ma_mon']))
            tbl.setItem(r, 1, QtWidgets.QTableWidgetItem(m['ten_mon']))
            it_tc = QtWidgets.QTableWidgetItem(str(m['tin_chi']))
            it_tc.setTextAlignment(Qt.AlignCenter)
            tbl.setItem(r, 2, it_tc)
            it_hk = QtWidgets.QTableWidgetItem(m['hoc_ky'] or '—')
            it_hk.setTextAlignment(Qt.AlignCenter)
            tbl.setItem(r, 3, it_hk)
            it_diem = QtWidgets.QTableWidgetItem(f'{m["diem"]:.1f}' if m['diem'] is not None else '—')
            it_diem.setTextAlignment(Qt.AlignCenter)
            if m['diem'] is not None:
                it_diem.setForeground(QColor(COLORS['green'] if m['diem'] >= 5 else COLORS['red']))
            tbl.setItem(r, 4, it_diem)
            txt, c = status_text.get(m['trang_thai'], ('—', COLORS['text_mid']))
            it_st = QtWidgets.QTableWidgetItem(txt)
            it_st.setTextAlignment(Qt.AlignCenter)
            it_st.setForeground(QColor(c))
            it_st.setFont(QFont('Segoe UI', 10, QFont.Bold))
            tbl.setItem(r, 5, it_st)
            tbl.setRowHeight(r, 30)
        for c, w in enumerate([75, 230, 40, 50, 70, 130]):
            tbl.setColumnWidth(c, w)
        tbl.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(tbl, 1)

        # Note
        note = QtWidgets.QLabel(
            '<i style="color:#718096; font-size:11px;">'
            '💡 Tổng hợp từ <b>khung chương trình ngành CNTT</b> + bảng điểm cá nhân. '
            'Môn đạt = tổng kết ≥ 5.0</i>'
        )
        note.setWordWrap(True)
        lay.addWidget(note)

        # Close
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        btns.button(QtWidgets.QDialogButtonBox.Close).setText('Đóng')
        btns.rejected.connect(dlg.accept)
        lay.addWidget(btns)

        dlg.exec_()

    def _change_pass(self):
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Đổi mật khẩu')
        dlg.setFixedSize(380, 220)
        form = QtWidgets.QFormLayout(dlg)
        old = QtWidgets.QLineEdit(); old.setEchoMode(QtWidgets.QLineEdit.Password)
        new1 = QtWidgets.QLineEdit(); new1.setEchoMode(QtWidgets.QLineEdit.Password)
        new2 = QtWidgets.QLineEdit(); new2.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow('Mật khẩu cũ:', old)
        form.addRow('Mật khẩu mới:', new1)
        form.addRow('Nhập lại:', new2)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if old.text() != MOCK_USER['password']:
            msg_warn(self, 'Lỗi', 'Sai mật khẩu cũ')
            return
        if not new1.text() or new1.text() != new2.text():
            msg_warn(self, 'Lỗi', 'Mật khẩu mới không khớp')
            return
        MOCK_USER['password'] = new1.text()
        if DB_AVAILABLE and MOCK_USER.get('id'):
            try:
                AuthService.change_password(MOCK_USER['id'], new1.text())
                print('[AUTH] da doi mk trong DB')
            except Exception as e:
                print(f'[AUTH] loi doi mk: {e}')
        msg_info(self, 'Thành công', 'Đổi mật khẩu thành công')


class AdminWindow(QtWidgets.QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.setObjectName('MainWindow')
        self.setWindowTitle('EAUT - Quản trị hệ thống')
        self.setMinimumSize(1250, 720)
        self.resize(1250, 720)
        self.setWindowIcon(QIcon(os.path.join(RES, 'logo.png')))

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        layout.addWidget(self.sidebar)

        self.stack = QtWidgets.QStackedWidget()
        layout.addWidget(self.stack)

        self.page_widgets = []
        self.pages_filled = [False] * len(ADMIN_PAGES)
        for btn_name, ui_file in ADMIN_PAGES:
            page = self._load_page(ui_file)
            self.page_widgets.append(page)
            self.stack.addWidget(page)

        self._switch_page(0)
        self._fill_admin_dashboard()
        self.pages_filled[0] = True

    def _build_sidebar(self):
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet('QFrame#sidebar { background: #ffffff; border-right: 1px solid #d2d6dc; }')

        # logo
        lbl_logo = QtWidgets.QLabel(sidebar)
        lbl_logo.setGeometry(20, 20, 42, 42)
        lbl_logo.setScaledContents(True)
        logo_path = os.path.join(RES, 'logo.png')
        if os.path.exists(logo_path):
            lbl_logo.setPixmap(QPixmap(logo_path).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        lbl_school = QtWidgets.QLabel('EAUT', sidebar)
        lbl_school.setGeometry(68, 20, 150, 20)
        lbl_school.setStyleSheet(f'color: {COLORS["navy"]}; font-size: 13px; font-weight: bold; background: transparent;')

        lbl_sub = QtWidgets.QLabel('Quản trị hệ thống', sidebar)
        lbl_sub.setGeometry(68, 40, 120, 16)
        lbl_sub.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 11px; background: transparent;')
        add_maximize_button(sidebar, self)

        sep = QtWidgets.QFrame(sidebar)
        sep.setGeometry(15, 74, 200, 1)
        sep.setStyleSheet(f'background: {COLORS["border"]};')

        y = 86
        for btn_name, icon_name, icon_file, label in ADMIN_MENU:
            btn = QtWidgets.QPushButton(label, sidebar)
            btn.setObjectName(btn_name)
            btn.setGeometry(10, y, 210, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(SIDEBAR_NORMAL)
            setattr(self, btn_name, btn)

            icon_lbl = QtWidgets.QLabel(sidebar)
            icon_lbl.setObjectName(icon_name)
            icon_lbl.setGeometry(20, y + 9, 16, 16)
            icon_lbl.setScaledContents(True)
            icon_lbl.setStyleSheet('background: transparent;')
            icon_path = os.path.join(ICONS, f'{icon_file}.png')
            if os.path.exists(icon_path):
                icon_lbl.setPixmap(QPixmap(icon_path).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            setattr(self, icon_name, icon_lbl)
            y += 38

        for i, (btn_name, _) in enumerate(ADMIN_PAGES):
            btn = getattr(self, btn_name)
            btn.clicked.connect(lambda checked, idx=i: self._on_nav(idx))

        sep2 = QtWidgets.QFrame(sidebar)
        sep2.setGeometry(15, 610, 200, 1)
        sep2.setStyleSheet(f'background: {COLORS["border"]};')

        lbl_av = QtWidgets.QLabel('AD', sidebar)
        lbl_av.setGeometry(15, 625, 38, 38)
        lbl_av.setAlignment(Qt.AlignCenter)
        lbl_av.setStyleSheet(f'background: {COLORS["active_bg"]}; border-radius: 19px; color: {COLORS["navy"]}; font-size: 13px; font-weight: bold;')

        lbl_name = QtWidgets.QLabel('Admin', sidebar)
        lbl_name.setGeometry(60, 626, 110, 17)
        lbl_name.setStyleSheet(f'color: {COLORS["text_dark"]}; font-size: 12px; font-weight: bold; background: transparent;')

        lbl_role = QtWidgets.QLabel('Quản trị viên', sidebar)
        lbl_role.setGeometry(60, 644, 110, 15)
        lbl_role.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 10px; background: transparent;')

        icon_lo = QtWidgets.QLabel(sidebar)
        icon_lo.setGeometry(191, 635, 18, 18)
        icon_lo.setScaledContents(True)
        icon_lo.setStyleSheet('background: transparent;')
        lo_path = os.path.join(ICONS, 'log-out.png')
        if os.path.exists(lo_path):
            icon_lo.setPixmap(QPixmap(lo_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        btn_lo = QtWidgets.QPushButton(sidebar)
        btn_lo.setGeometry(183, 627, 34, 34)
        btn_lo.setCursor(Qt.PointingHandCursor)
        btn_lo.setToolTip('Đăng xuất')
        btn_lo.setStyleSheet('QPushButton { background: transparent; border: none; } QPushButton:hover { background: #fce8e6; border-radius: 8px; }')
        btn_lo.clicked.connect(self._on_logout)

        return sidebar

    def _load_page(self, ui_file):
        temp = uic.loadUi(os.path.join(UI, ui_file))
        content = temp.findChild(QtWidgets.QFrame, 'contentArea')
        if content:
            content.setParent(None)
            content.setFixedSize(1020, 720)
            return content
        return temp

    def _on_nav(self, index):
        self._switch_page(index)
        if not self.pages_filled[index]:
            fill = [self._fill_admin_dashboard, self._fill_admin_courses,
                    self._fill_admin_classes, self._fill_admin_students,
                    self._fill_admin_teachers, self._fill_admin_employees,
                    self._fill_admin_semester, self._fill_admin_curriculum,
                    self._fill_admin_audit, self._fill_admin_stats]
            fill[index]()
            self.pages_filled[index] = True

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
        active = ADMIN_PAGES[index][0]
        for btn_name, _ in ADMIN_PAGES:
            btn = getattr(self, btn_name)
            icon = getattr(self, btn_name.replace('btn', 'icon'))
            if btn_name == active:
                btn.setStyleSheet(SIDEBAR_ACTIVE)
                icon.raise_()
            else:
                btn.setStyleSheet(SIDEBAR_NORMAL)

    def _on_logout(self):
        self.close()
        self.app_ref.show_login()

    # === ADMIN DATA FILL ===

    def _make_progress_bar(self, value, max_val, width=None):
        pct = int(value / max_val * 100) if max_val else 0
        color = COLORS['red'] if pct >= 90 else COLORS['gold'] if pct >= 60 else COLORS['green']
        pb = QtWidgets.QProgressBar()
        pb.setValue(pct)
        pb.setTextVisible(True)
        pb.setFormat(f'{value}/{max_val}')
        pb.setMinimumHeight(22)
        if width:
            pb.setMinimumWidth(width)
        pb.setStyleSheet(f'QProgressBar {{ background: #edf2f7; border: none; border-radius: 4px; font-size: 11px; color: white; }} QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}')
        return pb

    def _make_badge(self, text, color):
        lbl = QtWidgets.QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setMinimumWidth(70)
        lbl.setFixedHeight(24)
        lbl.setStyleSheet(f'background: {color}; color: white; border-radius: 4px; padding: 3px 12px; font-size: 11px; font-weight: bold;')
        w = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(w)
        hl.setContentsMargins(4, 4, 4, 4)
        hl.addWidget(lbl)
        hl.addStretch()
        return w

    def _fill_admin_dashboard(self):
        page = self.page_widgets[0]
        # 4 stat card o tren cung - lay tu /stats/admin/overview
        stat_card_data = None
        if DB_AVAILABLE:
            try:
                stat_card_data = StatsService.admin_overview()
            except Exception as e:
                print(f'[STATS] admin_overview loi: {e}')
        if stat_card_data:
            for lbl_name, key in [('lblStat1', 'total_students'),
                                   ('lblStat2', 'total_classes'),
                                   ('lblStat3', 'total_registrations'),
                                   ('lblStat4', 'current_semester')]:
                w = page.findChild(QtWidgets.QLabel, lbl_name)
                if w:
                    val = stat_card_data.get(key, '—')
                    w.setText(str(val) if val not in (None, '') else '—')

        # by dept - lay tu stats_by_semester(current)
        dept_rows = None
        if DB_AVAILABLE and stat_card_data:
            try:
                cur_sem = stat_card_data.get('current_semester')
                if cur_sem and cur_sem != '—':
                    sem_stats = StatsService.stats_by_semester(cur_sem)
                    dept_rows = sem_stats.get('dept', []) if sem_stats else []
            except Exception as e:
                print(f'[STATS] stats_by_semester loi: {e}')

        # lay du lieu that neu co DB, khong thi dung mock
        top_data = None
        recent_data = None
        if DB_AVAILABLE:
            try:
                rows = StatsService.top_classes(limit=5)
                top_data = [(r.get('ten_mon', r.get('ma_lop', '?')),
                             int(r.get('siso_hien_tai') or 0),
                             int(r.get('siso_max') or 40)) for r in rows]
            except Exception as e:
                print(f'[STATS] top_classes loi: {e}')
            try:
                acts = StatsService.recent_activity(limit=5)
                recent_data = []
                for a in acts:
                    t_str = 'Vừa xong' if not a.get('thoi_gian') else str(a['thoi_gian'])[:16]
                    color = COLORS['green'] if a.get('loai') == 'reg' else COLORS['gold']
                    recent_data.append((t_str, a.get('noi_dung', ''), color))
            except Exception as e:
                print(f'[STATS] recent loi: {e}')

        # top courses voi progress bar
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblTopCourses')
        if tbl:
            data = top_data if top_data else []
            tbl.setRowCount(len(data) if data else 1)
            if not data:
                # khong co du lieu -> 1 row "Chua co du lieu"
                ph = QtWidgets.QTableWidgetItem('Chưa có dữ liệu')
                ph.setTextAlignment(Qt.AlignCenter)
                ph.setForeground(QColor(COLORS['text_light']))
                tbl.setItem(0, 0, ph)
                tbl.setSpan(0, 0, 1, tbl.columnCount())
                tbl.setRowHeight(0, 50)
            else:
                for r, (name, cur, mx) in enumerate(data):
                    tbl.setItem(r, 0, QtWidgets.QTableWidgetItem(name))
                    item_ss = QtWidgets.QTableWidgetItem(f'{cur}/{mx}')
                    item_ss.setTextAlignment(Qt.AlignCenter)
                    tbl.setItem(r, 1, item_ss)
                    pct = int(cur / mx * 100) if mx else 0
                    item_pct = QtWidgets.QTableWidgetItem(f'{pct}%')
                    item_pct.setTextAlignment(Qt.AlignCenter)
                    color = COLORS['red'] if pct >= 90 else COLORS['gold'] if pct >= 60 else COLORS['green']
                    item_pct.setForeground(QColor(color))
                    item_pct.setFont(QFont('Segoe UI', 10, QFont.Bold))
                    tbl.setItem(r, 2, item_pct)
                for r in range(len(data)):
                    tbl.setRowHeight(r, 34)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setColumnWidth(0, 150)
            tbl.setColumnWidth(1, 55)
            tbl.verticalHeader().setVisible(False)

        # recent voi badge loai
        tbl2 = page.findChild(QtWidgets.QTableWidget, 'tblRecent')
        if tbl2:
            data = recent_data if recent_data else []
            tbl2.setRowCount(len(data) if data else 1)
            if not data:
                ph2 = QtWidgets.QTableWidgetItem('Chưa có dữ liệu')
                ph2.setTextAlignment(Qt.AlignCenter)
                ph2.setForeground(QColor(COLORS['text_light']))
                tbl2.setItem(0, 0, ph2)
                tbl2.setSpan(0, 0, 1, tbl2.columnCount())
                tbl2.setRowHeight(0, 50)
            else:
                for r, (time_str, content, color) in enumerate(data):
                    item_time = QtWidgets.QTableWidgetItem(time_str)
                    item_time.setForeground(QColor(COLORS['text_light']))
                    item_time.setFont(QFont('Segoe UI', 9))
                    tbl2.setItem(r, 0, item_time)
                    item_content = QtWidgets.QTableWidgetItem(content)
                    tbl2.setItem(r, 1, item_content)
                for r in range(len(data)):
                    tbl2.setRowHeight(r, 34)
            tbl2.horizontalHeader().setStretchLastSection(True)
            tbl2.setColumnWidth(0, 100)
            tbl2.verticalHeader().setVisible(False)

        # by dept - lay tu API stats_by_semester['dept']
        tbl3 = page.findChild(QtWidgets.QTableWidget, 'tblByDept')
        if tbl3:
            if dept_rows:
                data = [[r.get('khoa', '?'), str(r.get('so_hv', 0)), str(r.get('so_lop', 0))]
                        for r in dept_rows]
            else:
                data = []
            tbl3.setRowCount(len(data) if data else 1)
            if not data:
                ph = QtWidgets.QTableWidgetItem('Chưa có dữ liệu')
                ph.setTextAlignment(Qt.AlignCenter)
                ph.setForeground(QColor(COLORS['text_light']))
                tbl3.setItem(0, 0, ph)
                tbl3.setSpan(0, 0, 1, tbl3.columnCount())
                tbl3.setRowHeight(0, 50)
            else:
                for r, row in enumerate(data):
                    for c, val in enumerate(row):
                        item = QtWidgets.QTableWidgetItem(val)
                        item.setTextAlignment(Qt.AlignCenter if c > 0 else Qt.AlignLeft | Qt.AlignVCenter)
                        tbl3.setItem(r, c, item)
            tbl3.horizontalHeader().setStretchLastSection(True)
            for c, w in enumerate([200, 80, 80, 80]):
                tbl3.setColumnWidth(c, w)
            tbl3.verticalHeader().setVisible(False)

    def _fill_admin_courses(self):
        page = self.page_widgets[1]
        si = page.findChild(QtWidgets.QLabel, 'iconSearchCourse')
        if si:
            si.setPixmap(QPixmap(os.path.join(ICONS, 'search.png')).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        data = None
        if DB_AVAILABLE:
            try:
                courses = CourseService.get_all_courses()
                # 1 lan goi /classes de aggregate per ma_mon (tranh N+1)
                all_classes = CourseService.get_all_classes() or []
                agg_by_ma_mon = {}
                for cls in all_classes:
                    ma = cls.get('ma_mon')
                    if not ma:
                        continue
                    a = agg_by_ma_mon.setdefault(ma, {'cur': 0, 'mx': 0, 'n': 0, 'gv': set(), 'lich': set()})
                    a['cur'] += int(cls.get('siso_hien_tai') or 0)
                    a['mx'] += int(cls.get('siso_max') or 0)
                    a['n'] += 1
                    if cls.get('ten_gv'): a['gv'].add(cls['ten_gv'])
                    if cls.get('lich'): a['lich'].add(cls['lich'])
                data = []
                for c in courses:
                    a = agg_by_ma_mon.get(c['ma_mon'], {})
                    data.append([
                        c['ma_mon'], c['ten_mon'], '3',
                        ', '.join(sorted(a.get('gv', set()))) or '—',
                        ', '.join(sorted(a.get('lich', set()))) or '—',
                        a.get('cur', 0), a.get('mx', 40) or 40,
                    ])
            except Exception as e:
                print(f'[ADMIN_COURSES] API loi: {e}')
        if not data:
            data = []  # khong co data -> empty table
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdminCourses')
        if tbl:
            tbl.setRowCount(len(data))
            for r, row in enumerate(data):
                for c in range(5):
                    tbl.setItem(r, c, QtWidgets.QTableWidgetItem(str(row[c])))
                # si so = text mau
                cur, mx = row[5], row[6]
                pct = int(cur / mx * 100) if mx else 0
                item_ss = QtWidgets.QTableWidgetItem(f'{cur}/{mx}')
                item_ss.setTextAlignment(Qt.AlignCenter)
                color = COLORS['red'] if pct >= 90 else COLORS['gold'] if pct >= 60 else COLORS['green']
                item_ss.setForeground(QColor(color))
                tbl.setItem(r, 5, item_ss)
                btn_edit = QtWidgets.QPushButton('Sửa')
                btn_edit.setCursor(Qt.PointingHandCursor)
                btn_edit.setFixedSize(50, 24)
                btn_edit.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
                btn_del = QtWidgets.QPushButton('Xóa')
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setFixedSize(50, 24)
                btn_del.setStyleSheet(f'QPushButton {{ background: {COLORS["red"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
                w = QtWidgets.QWidget()
                hl = QtWidgets.QHBoxLayout(w)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setSpacing(6)
                hl.setAlignment(Qt.AlignCenter)
                hl.addWidget(btn_edit)
                hl.addWidget(btn_del)
                tbl.setCellWidget(r, 6, w)
            tbl.horizontalHeader().setStretchLastSection(True)
            for c, cw in enumerate([70, 180, 30, 140, 130, 110, 150]):
                tbl.setColumnWidth(c, cw)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)
            # wire edit/del each row
            for r, row in enumerate(data):
                w = tbl.cellWidget(r, 6)
                if w:
                    btns = w.findChildren(QtWidgets.QPushButton)
                    if len(btns) >= 2:
                        btns[0].clicked.connect(lambda ch, ma=row[0], nm=row[1]: self._admin_edit_course(ma, nm))
                        btns[1].clicked.connect(lambda ch, ma=row[0], nm=row[1], t=tbl: self._admin_del_row(t, ma, nm, 'môn học'))

        # Khong day btnSearchCourse vi no o sat mep phai roi - chi day combo + separator
        widen_search(page, 'txtSearchCourse', 300, ['sepFilter1', 'cboFilterDept'])
        # wire search / filter / add
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchCourse')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[0, 1, 3]))
        btn_s = page.findChild(QtWidgets.QPushButton, 'btnSearchCourse')
        if btn_s and txt:
            btn_s.clicked.connect(lambda: table_filter(tbl, txt.text(), cols=[0, 1, 3]))
        cbo = page.findChild(QtWidgets.QComboBox, 'cboFilterDept')
        if cbo:
            cbo.clear()
            cbo.addItems(['Tất cả khoa', 'Công nghệ thông tin (CNTT)', 'Toán', 'Ngoại ngữ'])
            cbo.currentIndexChanged.connect(lambda: self._admin_filter_courses())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddCourse')
        if btn_add:
            btn_add.clicked.connect(self._admin_add_course)

    def _admin_filter_courses(self):
        page = self.page_widgets[1]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdminCourses')
        cbo = page.findChild(QtWidgets.QComboBox, 'cboFilterDept')
        if not tbl or not cbo:
            return
        if cbo.currentIndex() == 0:
            for r in range(tbl.rowCount()):
                tbl.setRowHidden(r, False)
            return
        # map khoa -> prefix ma mon
        prefix_map = {1: 'IT', 2: 'MA', 3: 'EN'}
        prefix = prefix_map.get(cbo.currentIndex())
        for r in range(tbl.rowCount()):
            it = tbl.item(r, 0)
            show = prefix is None or (it and it.text().startswith(prefix))
            tbl.setRowHidden(r, not show)

    def _admin_add_course(self):
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Thêm môn học')
        dlg.setFixedSize(380, 260)
        form = QtWidgets.QFormLayout(dlg)
        txt_code = QtWidgets.QLineEdit()
        txt_name = QtWidgets.QLineEdit()
        txt_tc = QtWidgets.QLineEdit('3')
        txt_gv = QtWidgets.QLineEdit()
        form.addRow('Mã môn:', txt_code)
        form.addRow('Tên môn:', txt_name)
        form.addRow('Tín chỉ:', txt_tc)
        form.addRow('GV phụ trách:', txt_gv)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not txt_code.text().strip() or not txt_name.text().strip():
            msg_warn(self, 'Thiếu', 'Mã môn và tên môn không được trống')
            return
        tbl = self.page_widgets[1].findChild(QtWidgets.QTableWidget, 'tblAdminCourses')
        if tbl:
            r = tbl.rowCount()
            tbl.insertRow(r)
            new_code = txt_code.text().upper()
            new_name = txt_name.text()
            vals = [new_code, new_name, txt_tc.text() or '3', txt_gv.text() or '—', '—']
            for c, v in enumerate(vals):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(v))
            item_ss = QtWidgets.QTableWidgetItem('0/40')
            item_ss.setTextAlignment(Qt.AlignCenter)
            item_ss.setForeground(QColor(COLORS['green']))
            tbl.setItem(r, 5, item_ss)
            tbl.setRowHeight(r, 44)
            # them nut sua/xoa cho row moi (giong cac row cu)
            btn_edit = QtWidgets.QPushButton('Sửa')
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setFixedSize(50, 24)
            btn_edit.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
            btn_edit.clicked.connect(lambda ch, ma=new_code, nm=new_name: self._admin_edit_course(ma, nm))
            btn_del = QtWidgets.QPushButton('Xóa')
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setFixedSize(50, 24)
            btn_del.setStyleSheet(f'QPushButton {{ background: {COLORS["red"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
            btn_del.clicked.connect(lambda ch, ma=new_code, nm=new_name: self._admin_del_row(tbl, ma, nm, 'môn học'))
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(6); hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(btn_edit); hl.addWidget(btn_del)
            tbl.setCellWidget(r, 6, w)
        # them vao MOCK_COURSES
        MOCK_COURSES.append((txt_code.text().upper(), txt_name.text()))
        # ghi DB neu co
        if DB_AVAILABLE:
            try:
                CourseService.create_course(
                    ma_mon=txt_code.text().upper(),
                    ten_mon=txt_name.text(),
                    mo_ta=f'TC: {txt_tc.text() or 3}, GV: {txt_gv.text() or ""}'
                )
            except Exception as e:
                print(f'[ADM_ADD_COURSE] DB loi: {e}')
        msg_info(self, 'Thành công', f'Đã thêm môn {txt_code.text()} - {txt_name.text()}')

    def _admin_edit_course(self, ma, nm):
        tbl = self.page_widgets[1].findChild(QtWidgets.QTableWidget, 'tblAdminCourses')
        if not tbl:
            return
        target_row = -1
        for r in range(tbl.rowCount()):
            it = tbl.item(r, 0)
            if it and it.text() == ma:
                target_row = r
                break
        if target_row < 0:
            return

        dlg = QtWidgets.QDialog(self)

        style_dialog(dlg)
        dlg.setWindowTitle(f'Sửa môn học - {ma}')
        dlg.setFixedSize(400, 320)
        form = QtWidgets.QFormLayout(dlg)
        txt_code = QtWidgets.QLineEdit(tbl.item(target_row, 0).text() if tbl.item(target_row, 0) else ma)
        txt_name = QtWidgets.QLineEdit(tbl.item(target_row, 1).text() if tbl.item(target_row, 1) else nm)
        txt_tc = QtWidgets.QLineEdit(tbl.item(target_row, 2).text() if tbl.item(target_row, 2) else '3')
        txt_gv = QtWidgets.QLineEdit(tbl.item(target_row, 3).text() if tbl.item(target_row, 3) else '')
        txt_lich = QtWidgets.QLineEdit(tbl.item(target_row, 4).text() if tbl.item(target_row, 4) else '')
        form.addRow('Mã môn:', txt_code)
        form.addRow('Tên môn:', txt_name)
        form.addRow('Tín chỉ:', txt_tc)
        form.addRow('GV phụ trách:', txt_gv)
        form.addRow('Lịch học:', txt_lich)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not txt_code.text().strip() or not txt_name.text().strip():
            msg_warn(self, 'Thiếu', 'Mã và tên môn không được trống')
            return
        for c, w in enumerate([txt_code, txt_name, txt_tc, txt_gv, txt_lich]):
            tbl.setItem(target_row, c, QtWidgets.QTableWidgetItem(w.text()))
        msg_info(self, 'Đã cập nhật', f'Đã lưu thay đổi cho {txt_code.text()}')

    def _admin_del_row(self, tbl, ma, nm, loai):
        if not msg_confirm(self, 'Xác nhận xóa', f'Xóa {loai} {ma} - {nm}?'):
            return
        # ghi DB truoc khi xoa UI
        if DB_AVAILABLE:
            try:
                if loai == 'môn học':
                    CourseService.delete_course(ma)
                elif loai == 'lớp':
                    CourseService.delete_class(ma)
                elif loai == 'học viên':
                    # ma la MSV -> tim user_id
                    row = db.fetch_one('SELECT user_id FROM students WHERE msv = %s', (ma,))
                    if row: StudentService.delete(row['user_id'])
                elif loai == 'giảng viên':
                    row = db.fetch_one('SELECT user_id FROM teachers WHERE ma_gv = %s', (ma,))
                    if row: TeacherService.delete(row['user_id'])
                elif loai == 'nhân viên':
                    row = db.fetch_one('SELECT user_id FROM employees WHERE ma_nv = %s', (ma,))
                    if row: EmployeeService.delete(row['user_id'])
                elif loai == 'môn trong CT':
                    # ma la ma_mon, xoa row dau tien trung
                    if CurriculumService:
                        CurriculumService.delete(int(ma) if ma.isdigit() else 0)
            except Exception as e:
                print(f'[ADM_DEL] DB loi: {e}')
        for r in range(tbl.rowCount()):
            it = tbl.item(r, 0)
            if it and it.text() == ma:
                tbl.removeRow(r)
                break
        msg_info(self, 'Đã xóa', f'Đã xóa {loai}: {ma}')

    def _fill_admin_students(self):
        page = self.page_widgets[3]
        si = page.findChild(QtWidgets.QLabel, 'iconSearchStudent')
        if si:
            si.setPixmap(QPixmap(os.path.join(ICONS, 'search.png')).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # lay tu DB neu co, khong thi de empty
        data = None
        if DB_AVAILABLE:
            try:
                rows = StudentService.get_all()
                data = [[r['msv'], r['full_name'], r['cac_lop'] or '—',
                         '—', r.get('sdt') or '—', str(r.get('so_lop') or 0)]
                        for r in rows]
            except Exception as e:
                print(f'[STUDENT] loi: {e}')
        if not data:
            data = []
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdminStudents')
        if tbl:
            tbl.setRowCount(len(data))
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    tbl.setItem(r, c, QtWidgets.QTableWidgetItem(val))
                btn_detail = QtWidgets.QPushButton('Chi tiết')
                btn_detail.setCursor(Qt.PointingHandCursor)
                btn_detail.setFixedSize(62, 24)
                btn_detail.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
                btn_del = QtWidgets.QPushButton('Xóa')
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setFixedSize(50, 24)
                btn_del.setStyleSheet(f'QPushButton {{ background: {COLORS["red"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
                w = QtWidgets.QWidget()
                hl = QtWidgets.QHBoxLayout(w)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setSpacing(6)
                hl.setAlignment(Qt.AlignCenter)
                hl.addWidget(btn_detail)
                hl.addWidget(btn_del)
                tbl.setCellWidget(r, 6, w)
            tbl.horizontalHeader().setStretchLastSection(True)
            for c, cw in enumerate([75, 140, 100, 95, 90, 100, 150]):
                tbl.setColumnWidth(c, cw)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)
            # wire buttons
            for r, row in enumerate(data):
                w = tbl.cellWidget(r, 6)
                if w:
                    btns = w.findChildren(QtWidgets.QPushButton)
                    if len(btns) >= 2:
                        btns[0].clicked.connect(lambda ch, rd=row: show_detail_dialog(
                            self, 'Chi tiết học viên',
                            [('MSV', rd[0]), ('Họ tên', rd[1]), ('Lớp', rd[2]),
                             ('Khoa', rd[3]), ('Số điện thoại', rd[4]),
                             ('Số môn đăng ký', rd[5])],
                            avatar_text=rd[1].split()[-1] if rd[1] else '?', subtitle=rd[0]))
                        btns[1].clicked.connect(lambda ch, ma=row[0], nm=row[1], t=tbl: self._admin_del_row(t, ma, nm, 'học viên'))

        # btnSearchStudent o sat phai - khong day, chi day combo
        widen_search(page, 'txtSearchStudent', 300, ['cboFilterClass', 'cboFilterDeptSt'])
        # search / filter / add
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchStudent')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[0, 1]))
        btn_s = page.findChild(QtWidgets.QPushButton, 'btnSearchStudent')
        if btn_s and txt:
            btn_s.clicked.connect(lambda: table_filter(tbl, txt.text(), cols=[0, 1]))
        # mapping khoa -> lop (dung khi cascade)
        self._adm_lop_by_khoa = {
            'CNTT': ['CNTT-K20A', 'CNTT-K20B'],
            'Toán': ['TOAN-K20'],
            'Ngoại ngữ': ['NN-K20'],
        }
        # Khoa truoc (cha)
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboFilterDeptSt')
        if cbo_d:
            cbo_d.clear()
            cbo_d.addItems(['Tất cả khoa', 'CNTT', 'Toán', 'Ngoại ngữ'])
            cbo_d.currentIndexChanged.connect(self._adm_st_khoa_changed)
        # Lop sau (con) - mac dinh tat ca, doi khi khoa thay doi
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboFilterClass')
        if cbo_c:
            cbo_c.clear()
            cbo_c.addItem('Tất cả lớp')
            for lops in self._adm_lop_by_khoa.values():
                for lop in lops:
                    cbo_c.addItem(lop)
            cbo_c.currentIndexChanged.connect(lambda: self._admin_filter_students())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddStudent')
        if btn_add:
            btn_add.clicked.connect(self._admin_add_student)

    def _adm_st_khoa_changed(self, idx):
        """Khi chon khoa -> populate lai cbo lop voi cac lop cua khoa do"""
        page = self.page_widgets[3]
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboFilterDeptSt')
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboFilterClass')
        if not cbo_c or not cbo_d:
            return
        # block signal de tranh trigger filter 2 lan
        cbo_c.blockSignals(True)
        cbo_c.clear()
        cbo_c.addItem('Tất cả lớp')
        if idx == 0:
            # tat ca lop
            for lops in self._adm_lop_by_khoa.values():
                for lop in lops:
                    cbo_c.addItem(lop)
        else:
            khoa = cbo_d.currentText()
            for lop in self._adm_lop_by_khoa.get(khoa, []):
                cbo_c.addItem(lop)
        cbo_c.blockSignals(False)
        # filter ngay
        self._admin_filter_students()

    def _admin_filter_students(self):
        page = self.page_widgets[3]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdminStudents')
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboFilterClass')
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboFilterDeptSt')
        if not tbl:
            return
        lop_sel = cbo_c.currentText() if cbo_c and cbo_c.currentIndex() > 0 else None
        khoa_sel = cbo_d.currentText() if cbo_d and cbo_d.currentIndex() > 0 else None
        for r in range(tbl.rowCount()):
            it_lop = tbl.item(r, 2)
            it_khoa = tbl.item(r, 3)
            show = True
            if lop_sel and it_lop and lop_sel not in it_lop.text():
                show = False
            if khoa_sel and it_khoa and khoa_sel not in it_khoa.text():
                show = False
            tbl.setRowHidden(r, not show)

    def _admin_add_student(self):
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Thêm học viên')
        dlg.setFixedSize(380, 280)
        form = QtWidgets.QFormLayout(dlg)
        fields = [('MSV', 'msv'), ('Họ tên', 'ten'), ('Lớp', 'lop'), ('Khoa', 'khoa'), ('SDT', 'sdt')]
        widgets = {}
        for label, key in fields:
            w = QtWidgets.QLineEdit()
            form.addRow(label + ':', w)
            widgets[key] = w
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not widgets['msv'].text().strip() or not widgets['ten'].text().strip():
            msg_warn(self, 'Thiếu', 'MSV và họ tên không được trống')
            return
        tbl = self.page_widgets[3].findChild(QtWidgets.QTableWidget, 'tblAdminStudents')
        if tbl:
            r = tbl.rowCount()
            tbl.insertRow(r)
            vals = [widgets['msv'].text(), widgets['ten'].text(), widgets['lop'].text() or '—',
                    widgets['khoa'].text() or '—', widgets['sdt'].text() or '—', '0']
            for c, v in enumerate(vals):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(v))
            tbl.setRowHeight(r, 44)
        # ghi DB - tao user + student
        if DB_AVAILABLE:
            try:
                StudentService.create(
                    username=widgets['msv'].text().lower(),
                    password='passuser',   # default password
                    full_name=widgets['ten'].text(),
                    msv=widgets['msv'].text(),
                    sdt=widgets['sdt'].text() or None,
                )
            except Exception as e:
                print(f'[ADM_ADD_HV] DB loi: {e}')
                msg_warn(self, 'Lỗi', f'Đã hiển thị nhưng chưa lưu được vào hệ thống:\n{e}')
        msg_info(self, 'Thành công', f'Đã thêm học viên {widgets["msv"].text()}')

    def _fill_admin_semester(self):
        page = self.page_widgets[6]
        data = None
        if DB_AVAILABLE:
            try:
                if not SemesterService: raise RuntimeError("SemesterService chua co")
                rows = SemesterService.get_all()
                status_map = {'open': 'Đang mở', 'closed': 'Đã đóng', 'upcoming': 'Sắp tới'}
                data = [[s['id'], s['ten'], s['nam_hoc'],
                         fmt_date(s.get('bat_dau')),
                         fmt_date(s.get('ket_thuc')),
                         status_map.get(s['trang_thai'], s['trang_thai'])] for s in rows]
            except Exception as e:
                print(f'[ADM_SEM] DB loi: {e}')
        if not data:
            data = [
                ['HK2-2526', 'Học kỳ 2', '2025-2026', '01/01/2026', '30/06/2026', 'Đang mở'],
                ['HK1-2526', 'Học kỳ 1', '2025-2026', '01/08/2025', '31/12/2025', 'Đã đóng'],
                ['HK2-2425', 'Học kỳ 2', '2024-2025', '01/01/2025', '30/06/2025', 'Đã đóng'],
                ['HK1-2425', 'Học kỳ 1', '2024-2025', '01/08/2024', '31/12/2024', 'Đã đóng'],
            ]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblSemesters')
        if tbl:
            tbl.setRowCount(len(data))
            for r, row in enumerate(data):
                for c in range(5):
                    tbl.setItem(r, c, QtWidgets.QTableWidgetItem(row[c]))
                # status = text mau
                is_open = 'mở' in row[5]
                item_st = QtWidgets.QTableWidgetItem(row[5])
                item_st.setTextAlignment(Qt.AlignCenter)
                if is_open:
                    item_st.setForeground(QColor(COLORS['green']))
                else:
                    item_st.setForeground(QColor(COLORS['text_light']))
                tbl.setItem(r, 5, item_st)
                btn_toggle = QtWidgets.QPushButton('Đóng ĐK' if is_open else 'Mở ĐK')
                btn_toggle.setCursor(Qt.PointingHandCursor)
                btn_toggle.setFixedSize(72, 24)
                if is_open:
                    btn_toggle.setStyleSheet(f'QPushButton {{ background: white; color: {COLORS["orange"]}; border: 1px solid {COLORS["orange"]}; border-radius: 4px; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["orange"]}; color: white; }}')
                else:
                    btn_toggle.setStyleSheet(f'QPushButton {{ background: white; color: {COLORS["green"]}; border: 1px solid {COLORS["green"]}; border-radius: 4px; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["green"]}; color: white; }}')
                w = QtWidgets.QWidget()
                hl = QtWidgets.QHBoxLayout(w)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setAlignment(Qt.AlignCenter)
                hl.addWidget(btn_toggle)
                tbl.setCellWidget(r, 6, w)
            tbl.horizontalHeader().setStretchLastSection(True)
            for c, cw in enumerate([95, 90, 95, 105, 105, 95, 130]):
                tbl.setColumnWidth(c, cw)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)
            # wire toggle button
            for r, row in enumerate(data):
                w = tbl.cellWidget(r, 6)
                if w:
                    btn = w.findChild(QtWidgets.QPushButton)
                    if btn:
                        btn.clicked.connect(lambda ch, ma=row[0], b=btn: self._admin_toggle_sem(ma, b))

        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddSemester')
        if btn_add:
            btn_add.clicked.connect(self._admin_add_semester)

    def _admin_toggle_sem(self, ma, btn):
        current = btn.text()
        is_open = 'Đóng' in current
        new_state = 'mở' if not is_open else 'đóng'
        if not msg_confirm(self, 'Xác nhận', f'{"Đóng" if is_open else "Mở"} đăng ký cho {ma}?'):
            return
        # ghi DB
        if DB_AVAILABLE:
            try:
                if not SemesterService: raise RuntimeError("SemesterService chua co")
                SemesterService.set_status(ma, 'closed' if is_open else 'open')
            except Exception as e:
                print(f'[ADM_TOGGLE_SEM] DB loi: {e}')
        btn.setText('Mở ĐK' if is_open else 'Đóng ĐK')
        msg_info(self, 'Thành công', f'Đã {new_state} đăng ký cho {ma}')

    def _admin_add_semester(self):
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Thêm học kỳ')
        dlg.setFixedSize(360, 260)
        form = QtWidgets.QFormLayout(dlg)
        ma = QtWidgets.QLineEdit('HK?-????')
        ten = QtWidgets.QLineEdit('Học kỳ ?')
        nam = QtWidgets.QLineEdit('2026-2027')
        bd = QtWidgets.QLineEdit('01/08/2026')
        kt = QtWidgets.QLineEdit('31/12/2026')
        form.addRow('Mã HK:', ma)
        form.addRow('Tên HK:', ten)
        form.addRow('Năm học:', nam)
        form.addRow('Bắt đầu:', bd)
        form.addRow('Kết thúc:', kt)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        tbl = self.page_widgets[6].findChild(QtWidgets.QTableWidget, 'tblSemesters')
        if tbl:
            r = tbl.rowCount()
            tbl.insertRow(r)
            for c, v in enumerate([ma.text(), ten.text(), nam.text(), bd.text(), kt.text()]):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(v))
            st = QtWidgets.QTableWidgetItem('Đang mở')
            st.setTextAlignment(Qt.AlignCenter)
            st.setForeground(QColor(COLORS['green']))
            tbl.setItem(r, 5, st)
            tbl.setRowHeight(r, 44)
        # ghi DB
        if DB_AVAILABLE:
            try:
                from datetime import datetime
                def parse_dd_mm_yyyy(s):
                    return datetime.strptime(s.strip(), '%d/%m/%Y').date()
                if not SemesterService: raise RuntimeError("SemesterService chua co")
                SemesterService.create(
                    sem_id=ma.text(), ten=ten.text(), nam_hoc=nam.text(),
                    bat_dau=parse_dd_mm_yyyy(bd.text()),
                    ket_thuc=parse_dd_mm_yyyy(kt.text()),
                    trang_thai='open'
                )
            except Exception as e:
                print(f'[ADM_ADD_SEM] DB loi: {e}')
        msg_info(self, 'Thành công', f'Đã thêm học kỳ {ma.text()}')

    def _fill_admin_curriculum(self):
        page = self.page_widgets[7]
        si = page.findChild(QtWidgets.QLabel, 'iconSearchCurr')
        if si:
            si.setPixmap(QPixmap(os.path.join(ICONS, 'search.png')).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        data = None
        if DB_AVAILABLE:
            try:
                if not CurriculumService: raise RuntimeError("CurriculumService chua co")
                rows = CurriculumService.get_all()
                # convert 'Bat buoc' tu DB -> 'Bắt buộc' cho UI
                loai_map = {'Bat buoc': 'Bắt buộc', 'Tu chon': 'Tự chọn', 'Dai cuong': 'Đại cương'}
                data = []
                for i, c in enumerate(rows, start=1):
                    data.append([
                        str(i), c['ma_mon'], c.get('ten_mon', '') or '',
                        str(c.get('tin_chi', 3)),
                        loai_map.get(c.get('loai', ''), c.get('loai', '')),
                        c.get('hoc_ky_de_nghi', '') or '—',
                        c.get('mon_tien_quyet') or '—',
                    ])
            except Exception as e:
                print(f'[ADM_CURR] DB loi: {e}')
        if not data:
            data = [
                ['1', 'IT001', 'Nhập môn lập trình', '3', 'Bắt buộc', 'HK1', '—'],
                ['2', 'MA001', 'Giải tích 1', '3', 'Bắt buộc', 'HK1', '—'],
                ['3', 'EN001', 'Tiếng Anh 1', '3', 'Đại cương', 'HK1', '—'],
                ['4', 'IT002', 'Cấu trúc dữ liệu', '3', 'Bắt buộc', 'HK2', 'IT001'],
                ['5', 'MA002', 'Đại số tuyến tính', '3', 'Bắt buộc', 'HK2', '—'],
                ['6', 'IT003', 'Kỹ thuật lập trình', '3', 'Bắt buộc', 'HK3', 'IT002'],
                ['7', 'IT004', 'Cơ sở dữ liệu', '3', 'Bắt buộc', 'HK3', 'IT002'],
                ['8', 'IT005', 'Mạng máy tính', '3', 'Bắt buộc', 'HK4', '—'],
                ['9', 'IT006', 'Hệ điều hành', '3', 'Bắt buộc', 'HK4', 'IT003'],
                ['10', 'IT007', 'Công nghệ phần mềm', '3', 'Bắt buộc', 'HK5', 'IT003'],
                ['11', 'IT008', 'Trí tuệ nhân tạo', '3', 'Tự chọn', 'HK5', 'IT002, MA002'],
                ['12', 'IT009', 'Phát triển web', '3', 'Tự chọn', 'HK5', 'IT003'],
                ['13', 'IT010', 'An toàn thông tin', '3', 'Tự chọn', 'HK6', 'IT005'],
                ['14', 'IT011', 'Lập trình di động', '3', 'Tự chọn', 'HK6', 'IT003'],
            ]
        # tinh trang thai mo lop cho moi mon (de show "Đang mở X lớp")
        # query DB neu co, khong thi check trong MOCK_CLASSES
        ma_mon_count = {}
        if DB_AVAILABLE:
            try:
                rows = db.fetch_all('SELECT ma_mon, COUNT(*) AS n FROM classes GROUP BY ma_mon')
                ma_mon_count = {r['ma_mon']: r['n'] for r in rows}
            except Exception: pass
        if not ma_mon_count:
            for c in MOCK_CLASSES:
                ma_mon_count[c[1]] = ma_mon_count.get(c[1], 0) + 1

        # Stats summary tren cung trang
        n_total = len(data)
        n_bb = sum(1 for r in data if r[4] == 'Bắt buộc')
        n_tc = sum(1 for r in data if r[4] == 'Tự chọn')
        n_dc = sum(1 for r in data if r[4] == 'Đại cương')
        n_co_lop = sum(1 for r in data if ma_mon_count.get(r[1], 0) > 0)
        # tao label summary o headerBar (dynamic create)
        headerBar = page.findChild(QtWidgets.QFrame, 'headerBar')
        if headerBar:
            old = headerBar.findChild(QtWidgets.QLabel, 'lblCurrStats')
            if old:
                old.deleteLater()
            lbl_stats = QtWidgets.QLabel(headerBar)
            lbl_stats.setObjectName('lblCurrStats')
            lbl_stats.setGeometry(380, 18, 540, 22)
            lbl_stats.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 12px; background: transparent;')
            lbl_stats.setText(
                f'<b>{n_total}</b> môn  ·  '
                f'<span style="color:{COLORS["navy"]};"><b>{n_bb}</b> Bắt buộc</span>  '
                f'<span style="color:{COLORS["green"]};"><b>{n_tc}</b> Tự chọn</span>  '
                f'<span style="color:{COLORS["gold"]};"><b>{n_dc}</b> Đại cương</span>  ·  '
                f'<b>{n_co_lop}/{n_total}</b> môn đã mở lớp'
            )
            lbl_stats.show()

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCurriculum')
        if tbl:
            # them 1 cot 'Trang thai' truoc cot Thao tac → tong 9 cot
            tbl.setColumnCount(9)
            tbl.setHorizontalHeaderItem(7, QtWidgets.QTableWidgetItem('Trạng thái'))
            tbl.setHorizontalHeaderItem(8, QtWidgets.QTableWidgetItem('Thao tác'))
            tbl.setRowCount(len(data))
            type_colors = {'Bắt buộc': COLORS['navy'], 'Tự chọn': COLORS['green'], 'Đại cương': COLORS['gold']}
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter if c in (0, 3, 4, 5) else Qt.AlignLeft | Qt.AlignVCenter)
                    if c == 4:
                        item.setForeground(QColor(type_colors.get(val, COLORS['text_mid'])))
                    tbl.setItem(r, c, item)
                # cot 7: trang thai mo lop
                cnt = ma_mon_count.get(row[1], 0)
                if cnt > 0:
                    tt = QtWidgets.QTableWidgetItem(f'✓ {cnt} lớp')
                    tt.setForeground(QColor(COLORS['green']))
                else:
                    tt = QtWidgets.QTableWidgetItem('⚠ Chưa mở')
                    tt.setForeground(QColor(COLORS['orange']))
                tt.setTextAlignment(Qt.AlignCenter)
                tt.setFont(QFont('Segoe UI', 10, QFont.Bold))
                tbl.setItem(r, 7, tt)
                # cot 8: nut sua/xoa
                btn_edit = QtWidgets.QPushButton('Sửa')
                btn_edit.setCursor(Qt.PointingHandCursor)
                btn_edit.setFixedSize(50, 24)
                btn_edit.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
                btn_del = QtWidgets.QPushButton('Xóa')
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setFixedSize(50, 24)
                btn_del.setStyleSheet(f'QPushButton {{ background: {COLORS["red"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
                w = QtWidgets.QWidget()
                hl = QtWidgets.QHBoxLayout(w)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setSpacing(4)
                hl.setAlignment(Qt.AlignCenter)
                hl.addWidget(btn_edit)
                hl.addWidget(btn_del)
                tbl.setCellWidget(r, 8, w)
            # tang cot Hoc ky tu 48 -> 70 cho "Hoc ky X" hien thi du
            for c, cw in enumerate([32, 65, 150, 28, 90, 70, 95, 90, 130]):
                tbl.setColumnWidth(c, cw)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)
            # wire action
            for r, row in enumerate(data):
                w = tbl.cellWidget(r, 8)
                if w:
                    btns = w.findChildren(QtWidgets.QPushButton)
                    if len(btns) >= 2:
                        btns[0].clicked.connect(lambda ch, rr=r: self._admin_edit_curriculum(rr))
                        btns[1].clicked.connect(lambda ch, ma=row[1], nm=row[2], t=tbl: self._admin_del_row(t, ma, nm, 'môn trong CT'))

        # btnExportCurr o frame khac va o phai - khong day
        widen_search(page, 'txtSearchCurr', 280, ['cboNganh', 'cboLoai', 'cboHocKy'])
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchCurr')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[1, 2]))
        cbo_n = page.findChild(QtWidgets.QComboBox, 'cboNganh')
        if cbo_n:
            cbo_n.clear()
            cbo_n.addItems(['Tất cả ngành', 'CNTT', 'Toán', 'Ngoại ngữ'])
        cbo_l = page.findChild(QtWidgets.QComboBox, 'cboLoai')
        if cbo_l:
            cbo_l.clear()
            cbo_l.addItems(['Tất cả loại', 'Bắt buộc', 'Tự chọn', 'Đại cương'])
        cbo_h = page.findChild(QtWidgets.QComboBox, 'cboHocKy')
        if cbo_h:
            cbo_h.clear()
            cbo_h.addItems(['Tất cả học kỳ'] + [f'HK{i}' for i in range(1, 9)])
        for nm in ('cboNganh', 'cboLoai', 'cboHocKy'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda idx: self._admin_filter_curriculum())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddCurr')
        if btn_add:
            btn_add.clicked.connect(self._admin_add_curriculum)
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportCurr')
        if btn_exp:
            btn_exp.clicked.connect(lambda: export_table_csv(self, tbl, 'khung_chuong_trinh.csv', 'Xuất khung chương trình'))

    def _admin_edit_curriculum(self, row_idx):
        page = self.page_widgets[7]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCurriculum')
        if not tbl:
            return
        cur = [tbl.item(row_idx, c).text() if tbl.item(row_idx, c) else '' for c in range(7)]

        dlg = QtWidgets.QDialog(self)

        style_dialog(dlg)
        dlg.setWindowTitle('Sửa môn trong khung CT')
        dlg.setFixedSize(420, 400)
        form = QtWidgets.QFormLayout(dlg)
        txt_stt = QtWidgets.QLineEdit(cur[0]); txt_stt.setReadOnly(True)
        txt_stt.setStyleSheet('background: #f7fafc; color: #718096;')
        txt_code = QtWidgets.QLineEdit(cur[1])
        txt_name = QtWidgets.QLineEdit(cur[2])
        txt_tc = QtWidgets.QLineEdit(cur[3])
        cbo_loai = QtWidgets.QComboBox()
        cbo_loai.addItems(['Bắt buộc', 'Tự chọn', 'Đại cương'])
        if cur[4] in ['Bắt buộc', 'Tự chọn', 'Đại cương']:
            cbo_loai.setCurrentText(cur[4])
        cbo_hk = QtWidgets.QComboBox()
        cbo_hk.addItems(['HK1', 'HK2', 'HK3', 'HK4', 'HK5', 'HK6', 'HK7', 'HK8'])
        if cur[5] in [f'HK{i}' for i in range(1, 9)]:
            cbo_hk.setCurrentText(cur[5])
        txt_prereq = QtWidgets.QLineEdit(cur[6] if cur[6] != '—' else '')
        txt_prereq.setPlaceholderText('Để trống nếu không có, cách nhau bởi dấu phẩy')
        form.addRow('STT:', txt_stt)
        form.addRow('Mã môn:', txt_code)
        form.addRow('Tên môn:', txt_name)
        form.addRow('Tín chỉ:', txt_tc)
        form.addRow('Loại:', cbo_loai)
        form.addRow('Học kỳ:', cbo_hk)
        form.addRow('Môn tiên quyết:', txt_prereq)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not txt_code.text().strip() or not txt_name.text().strip():
            msg_warn(self, 'Thiếu', 'Mã môn và tên môn không được trống')
            return
        try:
            int(txt_tc.text())
        except ValueError:
            msg_warn(self, 'Sai dữ liệu', 'Tín chỉ phải là số')
            return
        type_colors = {'Bắt buộc': COLORS['navy'], 'Tự chọn': COLORS['green'], 'Đại cương': COLORS['gold']}
        new_vals = [cur[0], txt_code.text().upper(), txt_name.text(), txt_tc.text(),
                    cbo_loai.currentText(), cbo_hk.currentText(),
                    txt_prereq.text().strip() or '—']
        for c, v in enumerate(new_vals):
            it = QtWidgets.QTableWidgetItem(v)
            it.setTextAlignment(Qt.AlignCenter if c in (0, 3, 4, 5) else Qt.AlignLeft | Qt.AlignVCenter)
            if c == 4:
                it.setForeground(QColor(type_colors.get(v, COLORS['text_mid'])))
            tbl.setItem(row_idx, c, it)
        msg_info(self, 'Thành công', f'Đã cập nhật môn {txt_code.text()} - {txt_name.text()}')

    def _admin_add_curriculum(self):
        page = self.page_widgets[7]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCurriculum')
        if not tbl:
            return
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Thêm môn vào khung CT')
        dlg.setFixedSize(420, 380)
        form = QtWidgets.QFormLayout(dlg)
        txt_code = QtWidgets.QLineEdit()
        txt_name = QtWidgets.QLineEdit()
        txt_tc = QtWidgets.QLineEdit('3')
        cbo_loai = QtWidgets.QComboBox(); cbo_loai.addItems(['Bắt buộc', 'Tự chọn', 'Đại cương'])
        cbo_hk = QtWidgets.QComboBox(); cbo_hk.addItems([f'HK{i}' for i in range(1, 9)])
        txt_prereq = QtWidgets.QLineEdit()
        txt_prereq.setPlaceholderText('Để trống nếu không có')
        form.addRow('Mã môn:', txt_code)
        form.addRow('Tên môn:', txt_name)
        form.addRow('Tín chỉ:', txt_tc)
        form.addRow('Loại:', cbo_loai)
        form.addRow('Học kỳ:', cbo_hk)
        form.addRow('Môn tiên quyết:', txt_prereq)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not txt_code.text().strip() or not txt_name.text().strip():
            msg_warn(self, 'Thiếu', 'Mã và tên môn không được trống')
            return
        type_colors = {'Bắt buộc': COLORS['navy'], 'Tự chọn': COLORS['green'], 'Đại cương': COLORS['gold']}
        r = tbl.rowCount()
        tbl.insertRow(r)
        vals = [str(r + 1), txt_code.text().upper(), txt_name.text(), txt_tc.text(),
                cbo_loai.currentText(), cbo_hk.currentText(), txt_prereq.text().strip() or '—']
        for c, v in enumerate(vals):
            it = QtWidgets.QTableWidgetItem(v)
            it.setTextAlignment(Qt.AlignCenter if c in (0, 3, 4, 5) else Qt.AlignLeft | Qt.AlignVCenter)
            if c == 4:
                it.setForeground(QColor(type_colors.get(v, COLORS['text_mid'])))
            tbl.setItem(r, c, it)
        tbl.setRowHeight(r, 44)
        # ghi DB
        if DB_AVAILABLE:
            try:
                loai_map = {'Bắt buộc': 'Bat buoc', 'Tự chọn': 'Tu chon', 'Đại cương': 'Dai cuong'}
                if not CurriculumService: raise RuntimeError("CurriculumService chua co")
                CurriculumService.create(
                    ma_mon=txt_code.text().upper(),
                    tin_chi=int(txt_tc.text()),
                    loai=loai_map.get(cbo_loai.currentText(), 'Bat buoc'),
                    hoc_ky_de_nghi=cbo_hk.currentText(),
                    mon_tien_quyet=txt_prereq.text().strip() or None,
                    nganh='CNTT',
                )
            except Exception as e:
                print(f'[ADM_ADD_CURR] DB loi: {e}')
        msg_info(self, 'Thành công', f'Đã thêm môn {txt_code.text()}')

    def _admin_filter_curriculum(self):
        page = self.page_widgets[7]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCurriculum')
        if not tbl:
            return
        cbo_n = page.findChild(QtWidgets.QComboBox, 'cboNganh')
        cbo_l = page.findChild(QtWidgets.QComboBox, 'cboLoai')
        cbo_h = page.findChild(QtWidgets.QComboBox, 'cboHocKy')
        loai_sel = cbo_l.currentText() if cbo_l and cbo_l.currentIndex() > 0 else None
        hk_sel = cbo_h.currentText() if cbo_h and cbo_h.currentIndex() > 0 else None
        nganh_prefix = None
        if cbo_n and cbo_n.currentIndex() > 0:
            t = cbo_n.currentText()
            if 'CNTT' in t or 'thông tin' in t.lower():
                nganh_prefix = 'IT'
            elif 'Toán' in t:
                nganh_prefix = 'MA'
            elif 'Ngoại ngữ' in t or 'Anh' in t:
                nganh_prefix = 'EN'
        for r in range(tbl.rowCount()):
            show = True
            if nganh_prefix:
                it = tbl.item(r, 1)
                if it and not it.text().startswith(nganh_prefix):
                    show = False
            if loai_sel:
                it = tbl.item(r, 4)
                if it and loai_sel not in it.text():
                    show = False
            if hk_sel:
                it = tbl.item(r, 5)
                if it and it.text() != hk_sel:
                    show = False
            tbl.setRowHidden(r, not show)

    def _fill_admin_audit(self):
        page = self.page_widgets[8]
        si = page.findChild(QtWidgets.QLabel, 'iconSearchAudit')
        if si:
            si.setPixmap(QPixmap(os.path.join(ICONS, 'search.png')).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        data = None
        if DB_AVAILABLE:
            try:
                if not AuditService: raise RuntimeError("AuditService chua co")
                rows = AuditService.get_all(limit=50)
                role_map = {'admin': 'QTV', 'teacher': 'GV', 'employee': 'NV', 'student': 'SV'}
                data = []
                for l in rows:
                    ts = fmt_date(l.get('created_at'), fmt='%d/%m/%Y %H:%M:%S')
                    data.append([
                        ts, l.get('username') or '—',
                        role_map.get(l.get('role', ''), l.get('role', '') or '—'),
                        l.get('action', ''),
                        l.get('description') or '',
                        l.get('ip_address') or '—',
                    ])
            except Exception as e:
                print(f'[ADM_AUDIT] DB loi: {e}')
        if not data:
            data = [
                ['17/04/2026 08:12:34', 'admin', 'QTV', 'Đăng nhập', 'Đăng nhập thành công', '192.168.1.10'],
                ['17/04/2026 08:15:02', 'admin', 'QTV', 'Mở đăng ký', 'Mở đăng ký HK2-2526', '192.168.1.10'],
                ['17/04/2026 08:30:11', '2024001', 'SV', 'Đăng nhập', 'Đăng nhập thành công', '10.0.0.55'],
                ['17/04/2026 08:31:45', '2024001', 'SV', 'Đăng ký', 'Đăng ký IT004 - Trí tuệ nhân tạo', '10.0.0.55'],
                ['17/04/2026 08:32:10', '2024001', 'SV', 'Đăng ký', 'Đăng ký IT005 - Phát triển web', '10.0.0.55'],
                ['17/04/2026 08:45:30', '2024002', 'SV', 'Đăng nhập', 'Đăng nhập thành công', '10.0.0.87'],
                ['17/04/2026 08:46:12', '2024002', 'SV', 'Hủy ĐK', 'Hủy đăng ký MA002 - Xác suất TK', '10.0.0.87'],
                ['17/04/2026 09:00:05', '2024003', 'SV', 'Đăng nhập', 'Đăng nhập thất bại (sai MK)', '10.0.0.42'],
                ['17/04/2026 09:00:15', '2024003', 'SV', 'Đăng nhập', 'Đăng nhập thất bại (sai MK)', '10.0.0.42'],
                ['17/04/2026 09:00:25', '2024003', 'SV', 'Cảnh báo', 'Khóa tài khoản 15 phút (3 lần sai)', '10.0.0.42'],
                ['17/04/2026 09:15:30', 'admin', 'QTV', 'Cập nhật', 'Sửa sĩ số IT001 từ 35 → 40', '192.168.1.10'],
                ['17/04/2026 09:30:00', '2024010', 'SV', 'Thanh toán', 'Thanh toán 9,000,000 đ - HK2', '10.0.0.91'],
            ]
        action_colors = {
            'Đăng nhập': COLORS['green'], 'Đăng ký': COLORS['navy'],
            'Hủy ĐK': COLORS['orange'], 'Thanh toán': COLORS['gold'],
            'Cập nhật': COLORS['text_mid'], 'Mở đăng ký': COLORS['green'],
            'Cảnh báo': COLORS['red'],
        }
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAudit')
        if tbl:
            tbl.setRowCount(len(data))
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    if c == 0:
                        item.setForeground(QColor(COLORS['text_light']))
                        item.setFont(QFont('Segoe UI', 9))
                    elif c == 3:
                        color = action_colors.get(val, COLORS['text_mid'])
                        item.setForeground(QColor(color))
                    elif c == 5:
                        item.setForeground(QColor(COLORS['text_light']))
                    tbl.setItem(r, c, item)
            for c, cw in enumerate([135, 90, 50, 95, 260, 120]):
                tbl.setColumnWidth(c, cw)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 36)

        widen_search(page, 'txtSearchAudit', 260, ['cboAuditUser', 'cboAuditAction', 'cboAuditDate'])
        # search + filter
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchAudit')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[1, 3, 4]))
        cbo_u = page.findChild(QtWidgets.QComboBox, 'cboAuditUser')
        if cbo_u:
            cbo_u.clear()
            cbo_u.addItems(['Tất cả người dùng', 'admin', 'QTV', 'SV'])
        cbo_a = page.findChild(QtWidgets.QComboBox, 'cboAuditAction')
        if cbo_a:
            cbo_a.clear()
            cbo_a.addItems(['Tất cả hành động', 'Đăng nhập', 'Đăng ký', 'Hủy ĐK',
                            'Thanh toán', 'Cập nhật', 'Cảnh báo', 'Mở đăng ký'])
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboAuditDate')
        if cbo_d:
            cbo_d.clear()
            cbo_d.addItems(['Tất cả thời gian', 'Hôm nay (17/04)', '7 ngày qua', '30 ngày qua'])
        for nm in ('cboAuditUser', 'cboAuditAction', 'cboAuditDate'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda: self._admin_filter_audit())
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportAudit')
        if btn_exp:
            btn_exp.clicked.connect(lambda: export_table_csv(self, tbl, 'nhat_ky_he_thong.csv', 'Xuất nhật ký hệ thống'))

    def _admin_filter_audit(self):
        page = self.page_widgets[8]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAudit')
        if not tbl:
            return
        cbo_u = page.findChild(QtWidgets.QComboBox, 'cboAuditUser')
        cbo_a = page.findChild(QtWidgets.QComboBox, 'cboAuditAction')
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboAuditDate')
        user_sel = cbo_u.currentText() if cbo_u and cbo_u.currentIndex() > 0 else None
        action_sel = cbo_a.currentText() if cbo_a and cbo_a.currentIndex() > 0 else None
        date_sel = cbo_d.currentText() if cbo_d and cbo_d.currentIndex() > 0 else None
        for r in range(tbl.rowCount()):
            show = True
            if user_sel:
                it = tbl.item(r, 2)  # col 2 = role (QTV/SV/...)
                if it and user_sel not in it.text() and user_sel != 'Tất cả người dùng':
                    # match theo username (col 1) hoac role (col 2)
                    it1 = tbl.item(r, 1)
                    if not (it1 and user_sel.lower() in it1.text().lower()):
                        show = False
            if action_sel:
                it = tbl.item(r, 3)
                if it and action_sel not in it.text():
                    show = False
            if date_sel:
                it = tbl.item(r, 0)
                if it:
                    # date_sel co the la 'Hom nay', '7 ngay qua', '30 ngay qua', dd/mm/yyyy...
                    # don gian: hom nay = chua loc gi
                    if 'hôm nay' in date_sel.lower() or 'today' in date_sel.lower():
                        # giu lai nhung dong co ngay 17/04/2026 (mock)
                        show = show and '17/04/2026' in it.text()
            tbl.setRowHidden(r, not show)

    def _fill_admin_stats(self):
        self._render_admin_stats(0)
        page = self.page_widgets[9]
        cbo = page.findChild(QtWidgets.QComboBox, 'cboStatSemester')
        if cbo:
            cbo.currentIndexChanged.connect(self._render_admin_stats)

    def _render_admin_stats(self, idx):
        page = self.page_widgets[9]
        # du lieu khac nhau cho HK2 (idx=0, hien tai) vs HK1 (idx=1) va nam truoc (idx>=2)
        datasets = [
            # HK2 2025-2026 (hien tai): cao diem IT, nhieu lop full
            {
                'chart': [('Lập trình Python', 40, 40), ('CSDL', 35, 40),
                          ('Mạng MT', 18, 30), ('Toán rời rạc', 30, 40),
                          ('Tiếng Anh 3', 15, 35), ('Trí tuệ nhân tạo', 28, 40)],
                'dept': [['CNTT', '98', '63%'], ['Toán', '30', '19%'],
                         ['Ngoại ngữ', '18', '12%'], ['Khác', '10', '6%']],
                'class': [['CNTT-K20A', '35', '4.8', '504'], ['CNTT-K20B', '33', '4.5', '445'],
                          ['TOAN-K20', '30', '4.2', '378'], ['NN-K20', '28', '3.8', '319']],
            },
            # HK1 2025-2026: it hoc vien hon, tap trung toan / tieng anh
            {
                'chart': [('Lập trình Python', 32, 40), ('CSDL', 25, 40),
                          ('Mạng MT', 12, 30), ('Toán rời rạc', 38, 40),
                          ('Tiếng Anh 3', 30, 35), ('Trí tuệ nhân tạo', 18, 40)],
                'dept': [['CNTT', '62', '44%'], ['Toán', '45', '32%'],
                         ['Ngoại ngữ', '25', '18%'], ['Khác', '8', '6%']],
                'class': [['CNTT-K20A', '32', '4.5', '420'], ['CNTT-K20B', '29', '4.3', '378'],
                          ['TOAN-K20', '38', '4.6', '525'], ['NN-K20', '30', '4.1', '340']],
            },
            # HK2 2024-2025: nam truoc, it hoc vien
            {
                'chart': [('Lập trình Python', 28, 40), ('CSDL', 22, 40),
                          ('Mạng MT', 8, 30), ('Toán rời rạc', 25, 40),
                          ('Tiếng Anh 3', 20, 35), ('Trí tuệ nhân tạo', 15, 40)],
                'dept': [['CNTT', '48', '41%'], ['Toán', '32', '27%'],
                         ['Ngoại ngữ', '28', '24%'], ['Khác', '10', '8%']],
                'class': [['CNTT-K19A', '28', '4.3', '350'], ['CNTT-K19B', '26', '4.0', '310'],
                          ['TOAN-K19', '25', '4.2', '320'], ['NN-K19', '22', '3.9', '268']],
            },
        ]
        ds = datasets[min(idx, len(datasets) - 1)]

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblChartData')
        if tbl:
            data = ds['chart']
            tbl.setRowCount(len(data))
            for r, (name, cur, mx) in enumerate(data):
                tbl.setItem(r, 0, QtWidgets.QTableWidgetItem(name))
                tbl.setItem(r, 1, QtWidgets.QTableWidgetItem(str(cur)))
                tbl.setItem(r, 2, QtWidgets.QTableWidgetItem(str(mx)))
                pct = int(cur / mx * 100) if mx else 0
                item_pct = QtWidgets.QTableWidgetItem(f'{pct}%')
                item_pct.setTextAlignment(Qt.AlignCenter)
                color = COLORS['red'] if pct >= 90 else COLORS['gold'] if pct >= 60 else COLORS['green']
                item_pct.setForeground(QColor(color))
                item_pct.setFont(QFont('Segoe UI', 11, QFont.Bold))
                tbl.setItem(r, 3, item_pct)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setColumnWidth(0, 160)
            tbl.setColumnWidth(1, 60)
            tbl.setColumnWidth(2, 60)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 36)

        tbl2 = page.findChild(QtWidgets.QTableWidget, 'tblDeptStats')
        if tbl2:
            data = ds['dept']
            tbl2.setRowCount(len(data))
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    tbl2.setItem(r, c, QtWidgets.QTableWidgetItem(val))
            tbl2.horizontalHeader().setStretchLastSection(True)
            tbl2.setColumnWidth(0, 100)
            tbl2.setColumnWidth(1, 60)
            tbl2.verticalHeader().setVisible(False)

        tbl3 = page.findChild(QtWidgets.QTableWidget, 'tblClassStats')
        if tbl3:
            data = ds['class']
            tbl3.setRowCount(len(data))
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter if c > 0 else Qt.AlignLeft | Qt.AlignVCenter)
                    tbl3.setItem(r, c, item)
            tbl3.horizontalHeader().setStretchLastSection(True)
            for c, w in enumerate([200, 80, 120]):
                tbl3.setColumnWidth(c, w)
            tbl3.verticalHeader().setVisible(False)

        # update stat cards neu co
        totals = [sum(d[1] for d in ds['chart']), sum(int(d[1]) for d in ds['dept']), len(ds['class'])]
        for attr, val in [('lblStatTotalRegs', str(totals[0])),
                          ('lblStatTotalStudents', str(totals[1])),
                          ('lblStatTotalClasses', str(len(ds['chart'])))]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setText(val)

    def _fill_admin_classes(self):
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmClasses')
        if not tbl:
            return
        type_colors = {'Còn chỗ': COLORS['green'], 'Đầy': COLORS['red']}
        # lay tu DB neu co
        classes_src = []
        if DB_AVAILABLE:
            try:
                rows = CourseService.get_all_classes()
                for r_db in rows:
                    classes_src.append((
                        r_db['ma_lop'], r_db.get('ma_mon', ''),
                        r_db.get('ten_mon', ''), r_db.get('ten_gv') or '—',
                        r_db.get('lich') or '', r_db.get('phong') or '',
                        int(r_db.get('siso_max') or 40),
                        int(r_db.get('siso_hien_tai') or 0),
                        int(r_db.get('gia') or 0),
                    ))
            except Exception as e:
                print(f'[ADM_CLS] DB loi: {e}')
        if not classes_src:
            classes_src = []
        tbl.setRowCount(len(classes_src))
        for r, cls in enumerate(classes_src):
            ma, mmon, tmon, gv, lich, phong, smax, siso, gia = cls
            for c, val in enumerate([ma, tmon, gv, lich, phong]):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c == 0 else Qt.AlignLeft | Qt.AlignVCenter)
                tbl.setItem(r, c, item)
            # si so
            siso_item = QtWidgets.QTableWidgetItem(f'{siso}/{smax}')
            siso_item.setTextAlignment(Qt.AlignCenter)
            pct = int(siso / smax * 100)
            siso_item.setForeground(QColor(COLORS['red'] if pct >= 95 else COLORS['gold'] if pct >= 70 else COLORS['green']))
            tbl.setItem(r, 5, siso_item)
            # gia
            gia_item = QtWidgets.QTableWidgetItem(f'{gia:,}'.replace(',', '.') + ' đ')
            gia_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            gia_item.setForeground(QColor(COLORS['gold']))
            tbl.setItem(r, 6, gia_item)
            # thao tac
            btn_edit = QtWidgets.QPushButton('Sửa')
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setFixedSize(50, 24)
            btn_edit.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
            btn_del = QtWidgets.QPushButton('Xóa')
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setFixedSize(50, 24)
            btn_del.setStyleSheet(f'QPushButton {{ background: {COLORS["red"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(6)
            hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(btn_edit)
            hl.addWidget(btn_del)
            tbl.setCellWidget(r, 7, w)
            # wire
            btn_edit.clicked.connect(lambda ch, cls_ma=ma: self._admin_edit_class(cls_ma))
            btn_del.clicked.connect(lambda ch, cls_ma=ma, cls_mon=tmon, t=tbl: self._admin_del_row(t, cls_ma, cls_mon, 'lớp'))
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([85, 155, 140, 150, 75, 75, 115, 130]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(classes_src)):
            tbl.setRowHeight(r, 44)

        # noi rong o tim kiem (placeholder dai khong vua)
        widen_search(page, 'txtSearchCls', 300, ['cboAdmClsCourse', 'cboAdmClsTeacher', 'cboAdmClsStatus'])
        # search / filter / add
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchCls')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[0, 1, 2]))
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboAdmClsCourse')
        if cbo_c:
            cbo_c.clear()
            cbo_c.addItem('Tất cả môn học')
            # uu tien lay tu API, fallback sang MOCK neu API loi
            courses_for_cbo = []
            if DB_AVAILABLE:
                try:
                    rs = CourseService.get_all_courses()
                    courses_for_cbo = [(c['ma_mon'], c['ten_mon']) for c in rs]
                except Exception as e:
                    print(f'[ADM_CLS] load courses combo loi: {e}')
            if not courses_for_cbo:
                courses_for_cbo = list(MOCK_COURSES)
            for code, name in courses_for_cbo:
                cbo_c.addItem(name)
        cbo_t = page.findChild(QtWidgets.QComboBox, 'cboAdmClsTeacher')
        if cbo_t:
            cbo_t.clear()
            cbo_t.addItem('Tất cả giảng viên')
            seen = set()
            # build danh sach GV tu classes_src (da lay tu API o tren) hoac MOCK_CLASSES
            tea_source = classes_src if classes_src else MOCK_CLASSES
            for cls in tea_source:
                gv = cls[3] if len(cls) > 3 else None
                if gv and gv != '—' and gv not in seen:
                    seen.add(gv)
                    cbo_t.addItem(gv)
        for nm in ('cboAdmClsCourse', 'cboAdmClsTeacher', 'cboAdmClsStatus'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda: self._admin_filter_classes())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddClass')
        if btn_add:
            btn_add.clicked.connect(self._admin_add_class)

    def _admin_filter_classes(self):
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmClasses')
        if not tbl:
            return
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboAdmClsCourse')
        cbo_t = page.findChild(QtWidgets.QComboBox, 'cboAdmClsTeacher')
        cbo_s = page.findChild(QtWidgets.QComboBox, 'cboAdmClsStatus')
        course_sel = cbo_c.currentText() if cbo_c and cbo_c.currentIndex() > 0 else None
        teacher_sel = cbo_t.currentText() if cbo_t and cbo_t.currentIndex() > 0 else None
        status_sel = cbo_s.currentText() if cbo_s and cbo_s.currentIndex() > 0 else None
        for r in range(tbl.rowCount()):
            show = True
            # col 1 = ten mon, col 2 = GV, col 5 = si so (xac dinh dang mo / dong)
            if course_sel:
                it = tbl.item(r, 1)
                if it and course_sel not in it.text():
                    show = False
            if teacher_sel:
                it = tbl.item(r, 2)
                if it and teacher_sel not in it.text():
                    show = False
            if status_sel:
                it = tbl.item(r, 5)
                if it:
                    siso_text = it.text()
                    try:
                        cur, mx = siso_text.split('/')
                        is_full = int(cur) >= int(mx)
                    except Exception:
                        is_full = False
                    if status_sel == 'Đã đóng' and not is_full:
                        show = False
                    elif status_sel == 'Đang mở' and is_full:
                        show = False
            tbl.setRowHidden(r, not show)

    def _admin_edit_class(self, ma_lop):
        idx = None
        for i, cls in enumerate(MOCK_CLASSES):
            if cls[0] == ma_lop:
                idx = i
                break
        if idx is None:
            msg_warn(self, 'Không tìm thấy', f'Không tìm thấy lớp {ma_lop}')
            return
        cur = MOCK_CLASSES[idx]
        _, mmon, tmon, gv, lich, phong, smax, siso, gia = cur

        dlg = QtWidgets.QDialog(self)

        style_dialog(dlg)
        dlg.setWindowTitle(f'Sửa lớp - {ma_lop}')
        dlg.setFixedSize(420, 400)
        form = QtWidgets.QFormLayout(dlg)
        txt_ma = QtWidgets.QLineEdit(ma_lop); txt_ma.setReadOnly(True)
        txt_ma.setStyleSheet('background: #f7fafc; color: #718096;')
        txt_mon = QtWidgets.QLineEdit(tmon)
        txt_gv = QtWidgets.QLineEdit(gv)
        txt_lich = QtWidgets.QLineEdit(lich)
        txt_phong = QtWidgets.QLineEdit(phong)
        txt_smax = QtWidgets.QLineEdit(str(smax))
        txt_siso = QtWidgets.QLineEdit(str(siso))
        txt_gia = QtWidgets.QLineEdit(str(gia))
        form.addRow('Mã lớp:', txt_ma)
        form.addRow('Môn:', txt_mon)
        form.addRow('Giảng viên:', txt_gv)
        form.addRow('Lịch học:', txt_lich)
        form.addRow('Phòng:', txt_phong)
        form.addRow('Sĩ số max:', txt_smax)
        form.addRow('Sĩ số hiện tại:', txt_siso)
        form.addRow('Học phí (VND):', txt_gia)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        try:
            smax_n = int(txt_smax.text())
            siso_n = int(txt_siso.text())
            gia_n = int(txt_gia.text())
        except ValueError:
            msg_warn(self, 'Sai dữ liệu', 'Sĩ số và học phí phải là số')
            return
        if siso_n > smax_n:
            msg_warn(self, 'Sai dữ liệu', 'Sĩ số hiện tại không được lớn hơn sĩ số max')
            return
        MOCK_CLASSES[idx] = (ma_lop, mmon, txt_mon.text(), txt_gv.text(),
                             txt_lich.text(), txt_phong.text(), smax_n, siso_n, gia_n)
        # ghi DB
        if DB_AVAILABLE:
            try:
                CourseService.update_class(ma_lop,
                    lich=txt_lich.text(), phong=txt_phong.text(),
                    siso_max=smax_n, siso_hien_tai=siso_n, gia=gia_n)
            except Exception as e:
                print(f'[ADM_EDIT_CLS] DB loi: {e}')
        # re-fill bang admin_classes
        self.pages_filled[2] = False
        self._fill_admin_classes()
        self.pages_filled[2] = True
        msg_info(self, 'Đã cập nhật', f'Đã lưu thay đổi cho {ma_lop}')

    def _admin_add_class(self):
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Thêm lớp mới')
        dlg.setFixedSize(460, 460)
        form = QtWidgets.QFormLayout(dlg)
        ma = QtWidgets.QLineEdit(); ma.setPlaceholderText('VD: IT001-D')
        # Mon = combo tu MOCK_COURSES
        cbo_mon = QtWidgets.QComboBox()
        cbo_mon.addItem('-- Chọn môn --')
        for code, name in MOCK_COURSES:
            cbo_mon.addItem(f'{code} - {name}', userData=(code, name))
        # GV = combo tu cac GV co trong MOCK_CLASSES
        cbo_gv = QtWidgets.QComboBox()
        cbo_gv.addItem('-- Chọn giảng viên --')
        seen_gv = set()
        for cls in MOCK_CLASSES:
            if cls[3] not in seen_gv:
                seen_gv.add(cls[3])
                cbo_gv.addItem(cls[3])
        lich = QtWidgets.QLineEdit('T2 (7:00-9:30)')
        phong = QtWidgets.QLineEdit('P.?')
        smax = QtWidgets.QSpinBox(); smax.setRange(10, 100); smax.setValue(40)
        siso_start = QtWidgets.QSpinBox(); siso_start.setRange(0, 100); siso_start.setValue(0)
        gia = QtWidgets.QSpinBox(); gia.setRange(500000, 10000000); gia.setSingleStep(100000); gia.setValue(2000000)
        gia.setSuffix(' đ'); gia.setGroupSeparatorShown(True)
        so_buoi = QtWidgets.QSpinBox(); so_buoi.setRange(4, 60); so_buoi.setValue(24)

        form.addRow('Mã lớp (*):', ma)
        form.addRow('Môn học (*):', cbo_mon)
        form.addRow('Giảng viên (*):', cbo_gv)
        form.addRow('Lịch học:', lich)
        form.addRow('Phòng:', phong)
        form.addRow('Sĩ số tối đa:', smax)
        form.addRow('Sĩ số hiện tại:', siso_start)
        form.addRow('Học phí:', gia)
        form.addRow('Số buổi:', so_buoi)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not ma.text().strip():
            msg_warn(self, 'Thiếu', 'Mã lớp không được trống')
            return
        if cbo_mon.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn môn học')
            return
        if cbo_gv.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn giảng viên')
            return
        if siso_start.value() > smax.value():
            msg_warn(self, 'Sai dữ liệu', 'Sĩ số hiện tại không được lớn hơn sĩ số max')
            return

        mon_code, mon_name = cbo_mon.currentData()
        gv_name = cbo_gv.currentText()
        ma_lop = ma.text().upper()
        MOCK_CLASSES.append((ma_lop, mon_code, mon_name, gv_name,
                             lich.text(), phong.text(),
                             smax.value(), siso_start.value(), gia.value()))
        # ghi DB
        if DB_AVAILABLE:
            try:
                # tim gv_id tu ten
                gv_row = db.fetch_one(
                    'SELECT user_id FROM teachers t JOIN users u ON u.id=t.user_id WHERE u.full_name = %s LIMIT 1',
                    (gv_name,)
                )
                gv_id = gv_row['user_id'] if gv_row else None
                # semester hien tai
                sem = SemesterService.get_current() if SemesterService else None
                sem_id = sem['id'] if sem else 'HK2-2526'
                CourseService.create_class(
                    ma_lop=ma_lop, ma_mon=mon_code, gv_id=gv_id,
                    lich=lich.text(), phong=phong.text(),
                    siso_max=smax.value(), gia=gia.value(),
                    semester_id=sem_id, siso_hien_tai=siso_start.value()
                )
            except Exception as e:
                print(f'[ADM_ADD_CLS] DB loi: {e}')
        # re-fill
        self.pages_filled[2] = False
        self._fill_admin_classes()
        self.pages_filled[2] = True
        msg_info(self, 'Thành công', f'Đã thêm lớp {ma_lop}')

    def _fill_admin_teachers(self):
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmTeachers')
        if not tbl:
            return
        data = None
        if DB_AVAILABLE:
            try:
                rows = TeacherService.get_all()
                data = [[r['ma_gv'], r['full_name'], r.get('khoa') or '—',
                         r.get('hoc_vi') or '—', r.get('sdt') or '—',
                         int(r.get('so_lop') or 0),
                         float(r.get('diem_tb') or 0.0)] for r in rows]
            except Exception as e:
                print(f'[TEACHER] loi: {e}')
        if not data:
            data = [
                ['GV001', 'Nguyễn Đức Thiện', 'CNTT', 'Tiến sĩ', '0901234567', 3, 4.6],
                ['GV002', 'Lê Thị C', 'CNTT', 'Thạc sĩ', '0901234568', 2, 4.3],
                ['GV003', 'Phạm Văn D', 'CNTT', 'Thạc sĩ', '0901234569', 2, 4.1],
                ['GV004', 'Ngô Thảo Anh', 'CNTT', 'Tiến sĩ', '0901234570', 1, 4.5],
                ['GV005', 'Lê Trung Thực', 'CNTT', 'Thạc sĩ', '0901234571', 1, 4.2],
                ['GV006', 'Hoàng Minh Tuấn', 'CNTT', 'Tiến sĩ', '0901234572', 1, 4.7],
                ['GV007', 'Nguyễn Thị E', 'Toán', 'Phó giáo sư', '0901234573', 1, 4.8],
                ['GV008', 'Lê Văn M', 'Toán', 'Tiến sĩ', '0901234574', 1, 4.0],
            ]
        tbl.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, val in enumerate(row[:5]):
                item = QtWidgets.QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter if c in (0, 3) else Qt.AlignLeft | Qt.AlignVCenter)
                tbl.setItem(r, c, item)
            # so lop
            item_lop = QtWidgets.QTableWidgetItem(str(row[5]))
            item_lop.setTextAlignment(Qt.AlignCenter)
            tbl.setItem(r, 5, item_lop)
            # danh gia
            diem = row[6]
            item_dg = QtWidgets.QTableWidgetItem(f'{diem:.1f} ⭐')
            item_dg.setTextAlignment(Qt.AlignCenter)
            item_dg.setForeground(QColor(COLORS['green'] if diem >= 4.5 else COLORS['navy'] if diem >= 4.0 else COLORS['orange']))
            tbl.setItem(r, 6, item_dg)
            # thao tac
            btn_edit = QtWidgets.QPushButton('Chi tiết')
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setFixedSize(62, 24)
            btn_edit.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
            btn_del = QtWidgets.QPushButton('Xóa')
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setFixedSize(50, 24)
            btn_del.setStyleSheet(f'QPushButton {{ background: {COLORS["red"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(6)
            hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(btn_edit)
            hl.addWidget(btn_del)
            tbl.setCellWidget(r, 7, w)
            btn_edit.clicked.connect(lambda ch, rd=row: show_detail_dialog(
                self, 'Chi tiết giảng viên',
                [('Mã GV', rd[0]), ('Họ tên', rd[1]), ('Khoa', rd[2]),
                 ('Học vị', rd[3]), ('Số điện thoại', rd[4]),
                 ('Số lớp đang dạy', rd[5]), ('Điểm đánh giá', f'{rd[6]:.1f}/5 ⭐')],
                avatar_text=rd[1].split()[-1] if rd[1] else '?', subtitle=rd[0]))
            btn_del.clicked.connect(lambda ch, ma=row[0], nm=row[1], t=tbl: self._admin_del_row(t, ma, nm, 'giảng viên'))
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([75, 170, 140, 110, 115, 70, 90, 140]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 44)

        widen_search(page, 'txtSearchTea', 300, ['cboTeaKhoa', 'cboTeaHocVi'])
        # search / filter / add
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchTea')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[0, 1]))
        cbo_k = page.findChild(QtWidgets.QComboBox, 'cboTeaKhoa')
        if cbo_k:
            cbo_k.clear()
            cbo_k.addItems(['Tất cả khoa', 'CNTT', 'Toán', 'Ngoại ngữ'])
        cbo_hv = page.findChild(QtWidgets.QComboBox, 'cboTeaHocVi')
        if cbo_hv:
            cbo_hv.clear()
            cbo_hv.addItems(['Tất cả học vị', 'Tiến sĩ', 'Thạc sĩ', 'Phó giáo sư', 'Cử nhân'])
        for nm in ('cboTeaKhoa', 'cboTeaHocVi'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda: self._admin_filter_teachers())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddTeacher')
        if btn_add:
            btn_add.clicked.connect(lambda: self._admin_add_user('giảng viên', 4, 'tblAdmTeachers',
                                                                  ['Mã GV', 'Họ tên', 'Khoa', 'Học vị', 'SDT']))

    def _admin_filter_teachers(self):
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmTeachers')
        if not tbl:
            return
        cbo_k = page.findChild(QtWidgets.QComboBox, 'cboTeaKhoa')
        cbo_hv = page.findChild(QtWidgets.QComboBox, 'cboTeaHocVi')
        khoa_sel = cbo_k.currentText() if cbo_k and cbo_k.currentIndex() > 0 else None
        hv_sel = cbo_hv.currentText() if cbo_hv and cbo_hv.currentIndex() > 0 else None
        for r in range(tbl.rowCount()):
            show = True
            if khoa_sel:
                it = tbl.item(r, 2)
                if it and khoa_sel not in it.text():
                    show = False
            if hv_sel:
                it = tbl.item(r, 3)
                if it and hv_sel not in it.text():
                    show = False
            tbl.setRowHidden(r, not show)

    def _admin_filter_employees(self):
        page = self.page_widgets[5]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmEmployees')
        if not tbl:
            return
        cbo_r = page.findChild(QtWidgets.QComboBox, 'cboEmpRole')
        cbo_s = page.findChild(QtWidgets.QComboBox, 'cboEmpStatus')
        role_sel = cbo_r.currentText() if cbo_r and cbo_r.currentIndex() > 0 else None
        status_sel = cbo_s.currentText() if cbo_s and cbo_s.currentIndex() > 0 else None
        for r in range(tbl.rowCount()):
            show = True
            if role_sel:
                it = tbl.item(r, 2)
                if it and role_sel not in it.text():
                    show = False
            if status_sel:
                it = tbl.item(r, 5)
                if it and status_sel not in it.text():
                    show = False
            tbl.setRowHidden(r, not show)

    def _admin_add_user(self, role_name, page_idx, tbl_name, fields):
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle(f'Thêm {role_name}')
        dlg.setFixedSize(380, 300)
        form = QtWidgets.QFormLayout(dlg)
        widgets = []
        for label in fields:
            w = QtWidgets.QLineEdit()
            form.addRow(label + ':', w)
            widgets.append(w)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not widgets[0].text().strip() or not widgets[1].text().strip():
            msg_warn(self, 'Thiếu', f'{fields[0]} và {fields[1]} không được trống')
            return
        tbl = self.page_widgets[page_idx].findChild(QtWidgets.QTableWidget, tbl_name)
        if tbl:
            r = tbl.rowCount()
            tbl.insertRow(r)
            for c, w in enumerate(widgets):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(w.text()))
            tbl.setRowHeight(r, 44)
        # ghi DB - tao user + teacher/employee
        if DB_AVAILABLE:
            try:
                vals = [w.text() for w in widgets]
                if role_name == 'giảng viên':
                    # fields = ['Mã GV', 'Họ tên', 'Khoa', 'Học vị', 'SDT']
                    TeacherService.create(
                        username=vals[0].lower(), password='passtea',
                        full_name=vals[1], ma_gv=vals[0],
                        khoa=vals[2], hoc_vi=vals[3], sdt=vals[4] or None,
                    )
                elif role_name == 'nhân viên':
                    # fields = ['Mã NV', 'Họ tên', 'Chức vụ', 'SDT', 'Email']
                    EmployeeService.create(
                        username=vals[0].lower(), password='passemp',
                        full_name=vals[1], ma_nv=vals[0],
                        chuc_vu=vals[2], sdt=vals[3] or None, email=vals[4] or None,
                    )
            except Exception as e:
                print(f'[ADM_ADD_USER] DB loi: {e}')
                msg_warn(self, 'Lỗi', f'Đã hiển thị nhưng chưa lưu được vào hệ thống:\n{e}')
        msg_info(self, 'Thành công', f'Đã thêm {role_name}: {widgets[1].text()}')

    def _fill_admin_employees(self):
        page = self.page_widgets[5]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmEmployees')
        if not tbl:
            return
        data = None
        if DB_AVAILABLE:
            try:
                rows = EmployeeService.get_all()
                data = [[r['ma_nv'], r['full_name'], r.get('chuc_vu') or '—',
                         r.get('sdt') or '—', r.get('email') or '—',
                         'Đang làm' if r.get('is_active') else 'Đã nghỉ'] for r in rows]
            except Exception as e:
                print(f'[EMP] loi: {e}')
        if not data:
            data = [
                ['NV001', 'Trần Thu Hương', 'Nhân viên đăng ký', '0987654321', 'huongtt@eaut.edu.vn', 'Đang làm'],
                ['NV002', 'Lê Minh Đức', 'Nhân viên thu ngân', '0987654322', 'ducm@eaut.edu.vn', 'Đang làm'],
                ['NV003', 'Phạm Quỳnh Anh', 'Nhân viên đăng ký', '0987654323', 'anhpq@eaut.edu.vn', 'Đang làm'],
                ['NV004', 'Nguyễn Hoài Linh', 'Quản lý', '0987654324', 'linh@eaut.edu.vn', 'Đang làm'],
                ['NV005', 'Vũ Thanh Tùng', 'Nhân viên thu ngân', '0987654325', 'tungvt@eaut.edu.vn', 'Nghỉ phép'],
            ]
        tbl.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, val in enumerate(row[:5]):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c == 0 else Qt.AlignLeft | Qt.AlignVCenter)
                tbl.setItem(r, c, item)
            # trang thai
            item_st = QtWidgets.QTableWidgetItem(row[5])
            item_st.setTextAlignment(Qt.AlignCenter)
            item_st.setForeground(QColor(COLORS['green'] if row[5] == 'Đang làm' else COLORS['orange']))
            tbl.setItem(r, 5, item_st)
            # thao tac
            btn_edit = QtWidgets.QPushButton('Chi tiết')
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setFixedSize(62, 24)
            btn_edit.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
            btn_del = QtWidgets.QPushButton('Xóa')
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setFixedSize(50, 24)
            btn_del.setStyleSheet(f'QPushButton {{ background: {COLORS["red"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(6)
            hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(btn_edit)
            hl.addWidget(btn_del)
            tbl.setCellWidget(r, 6, w)
            btn_edit.clicked.connect(lambda ch, rd=row: show_detail_dialog(
                self, 'Chi tiết nhân viên',
                [('Mã NV', rd[0]), ('Họ tên', rd[1]), ('Chức vụ', rd[2]),
                 ('Số điện thoại', rd[3]), ('Email', rd[4]), ('Trạng thái', rd[5])],
                avatar_text=rd[1].split()[-1] if rd[1] else '?', subtitle=rd[0]))
            btn_del.clicked.connect(lambda ch, ma=row[0], nm=row[1], t=tbl: self._admin_del_row(t, ma, nm, 'nhân viên'))
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([75, 170, 170, 115, 195, 90, 140]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 44)

        widen_search(page, 'txtSearchEmp', 300, ['cboEmpRole', 'cboEmpStatus'])
        # search / filter / add
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchEmp')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[0, 1]))
        cbo_r = page.findChild(QtWidgets.QComboBox, 'cboEmpRole')
        if cbo_r:
            cbo_r.clear()
            cbo_r.addItems(['Tất cả chức vụ', 'Nhân viên đăng ký', 'Nhân viên thu ngân', 'Quản lý'])
        cbo_s = page.findChild(QtWidgets.QComboBox, 'cboEmpStatus')
        if cbo_s:
            cbo_s.clear()
            cbo_s.addItems(['Tất cả trạng thái', 'Đang làm', 'Nghỉ phép', 'Đã nghỉ'])
        for nm in ('cboEmpRole', 'cboEmpStatus'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda: self._admin_filter_employees())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddEmp')
        if btn_add:
            btn_add.clicked.connect(lambda: self._admin_add_user('nhân viên', 5, 'tblAdmEmployees',
                                                                  ['Mã NV', 'Họ tên', 'Chức vụ', 'SDT', 'Email']))


class TeacherWindow(QtWidgets.QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.setObjectName('MainWindow')
        self.setWindowTitle('EAUT - Hệ thống giảng viên')
        self.setMinimumSize(1100, 700)
        self.resize(1100, 700)
        self.setWindowIcon(QIcon(os.path.join(RES, 'logo.png')))

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        layout.addWidget(self.sidebar)

        self.stack = QtWidgets.QStackedWidget()
        layout.addWidget(self.stack)

        self.page_widgets = []
        self.pages_filled = [False] * len(TEACHER_PAGES)
        for btn_name, ui_file in TEACHER_PAGES:
            page = self._load_page(ui_file)
            self.page_widgets.append(page)
            self.stack.addWidget(page)

        self._switch_page(0)
        self._fill_tea_dashboard()
        self.pages_filled[0] = True

    def _build_sidebar(self):
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet('QFrame#sidebar { background: #ffffff; border-right: 1px solid #d2d6dc; }')

        lbl_logo = QtWidgets.QLabel(sidebar)
        lbl_logo.setGeometry(20, 20, 42, 42)
        lbl_logo.setScaledContents(True)
        logo_path = os.path.join(RES, 'logo.png')
        if os.path.exists(logo_path):
            lbl_logo.setPixmap(QPixmap(logo_path).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        lbl_school = QtWidgets.QLabel('EAUT', sidebar)
        lbl_school.setGeometry(68, 20, 150, 20)
        lbl_school.setStyleSheet(f'color: {COLORS["navy"]}; font-size: 13px; font-weight: bold; background: transparent;')
        lbl_sub = QtWidgets.QLabel('Giảng viên', sidebar)
        lbl_sub.setGeometry(68, 40, 120, 16)
        lbl_sub.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 11px; background: transparent;')
        add_maximize_button(sidebar, self)

        sep = QtWidgets.QFrame(sidebar)
        sep.setGeometry(15, 74, 200, 1)
        sep.setStyleSheet(f'background: {COLORS["border"]};')

        y = 86
        for btn_name, icon_name, icon_file, label in TEACHER_MENU:
            btn = QtWidgets.QPushButton(label, sidebar)
            btn.setObjectName(btn_name)
            btn.setGeometry(10, y, 210, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(SIDEBAR_NORMAL)
            setattr(self, btn_name, btn)

            icon_lbl = QtWidgets.QLabel(sidebar)
            icon_lbl.setObjectName(icon_name)
            icon_lbl.setGeometry(20, y + 9, 16, 16)
            icon_lbl.setScaledContents(True)
            icon_lbl.setStyleSheet('background: transparent;')
            icon_path = os.path.join(ICONS, f'{icon_file}.png')
            if os.path.exists(icon_path):
                icon_lbl.setPixmap(QPixmap(icon_path).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            setattr(self, icon_name, icon_lbl)
            y += 38

        for i, (btn_name, _) in enumerate(TEACHER_PAGES):
            btn = getattr(self, btn_name)
            btn.clicked.connect(lambda checked, idx=i: self._on_nav(idx))

        sep2 = QtWidgets.QFrame(sidebar)
        sep2.setGeometry(15, 610, 200, 1)
        sep2.setStyleSheet(f'background: {COLORS["border"]};')

        lbl_av = QtWidgets.QLabel(MOCK_TEACHER['initials'], sidebar)
        lbl_av.setGeometry(15, 625, 38, 38)
        lbl_av.setAlignment(Qt.AlignCenter)
        lbl_av.setStyleSheet(f'background: {COLORS["active_bg"]}; border-radius: 19px; color: {COLORS["navy"]}; font-size: 13px; font-weight: bold;')

        lbl_name = QtWidgets.QLabel(MOCK_TEACHER['name'], sidebar)
        lbl_name.setGeometry(60, 626, 130, 17)
        lbl_name.setStyleSheet(f'color: {COLORS["text_dark"]}; font-size: 12px; font-weight: bold; background: transparent;')
        lbl_role = QtWidgets.QLabel('Giảng viên', sidebar)
        lbl_role.setGeometry(60, 644, 110, 15)
        lbl_role.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 10px; background: transparent;')

        icon_lo = QtWidgets.QLabel(sidebar)
        icon_lo.setGeometry(191, 635, 18, 18)
        icon_lo.setScaledContents(True)
        icon_lo.setStyleSheet('background: transparent;')
        lo_path = os.path.join(ICONS, 'log-out.png')
        if os.path.exists(lo_path):
            icon_lo.setPixmap(QPixmap(lo_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        btn_lo = QtWidgets.QPushButton(sidebar)
        btn_lo.setGeometry(183, 627, 34, 34)
        btn_lo.setCursor(Qt.PointingHandCursor)
        btn_lo.setToolTip('Đăng xuất')
        btn_lo.setStyleSheet('QPushButton { background: transparent; border: none; } QPushButton:hover { background: #fce8e6; border-radius: 8px; }')
        btn_lo.clicked.connect(self._on_logout)

        return sidebar

    def _load_page(self, ui_file):
        temp = uic.loadUi(os.path.join(UI, ui_file))
        content = temp.findChild(QtWidgets.QFrame, 'contentArea')
        if content:
            content.setParent(None)
            content.setFixedSize(870, 700)
            return content
        return temp

    def _on_nav(self, index):
        self._switch_page(index)
        if not self.pages_filled[index]:
            fill = [self._fill_tea_dashboard, self._fill_tea_schedule,
                    self._fill_tea_classes, self._fill_tea_students,
                    self._fill_tea_attendance,
                    self._fill_tea_notice, self._fill_tea_grades,
                    self._fill_tea_profile]
            fill[index]()
            self.pages_filled[index] = True

    # ===== DIEM DANH =====
    # 4 trang thai: present (Co mat) | late (Tre) | absent (Vang) | excused (Co phep)
    _ATTEND_STATES = [
        ('present', 'Có mặt', '#276749'),
        ('late', 'Trễ', '#c68a1e'),
        ('absent', 'Vắng', '#c53030'),
        ('excused', 'Có phép', '#3182ce'),
    ]
    _ATTEND_LABEL_MAP = {s[0]: s[1] for s in _ATTEND_STATES}
    _ATTEND_COLOR_MAP = {s[0]: s[2] for s in _ATTEND_STATES}

    def _fill_tea_attendance(self):
        """Trang Diem danh GV: chon lop -> chon buoi -> mark trang thai cho tung HV."""
        page = self.page_widgets[4]

        # 1. Lay danh sach lop GV dang day
        gv_id = MOCK_TEACHER.get('user_id')
        gv_classes = []
        if DB_AVAILABLE:
            try:
                if not CourseService:
                    raise RuntimeError('CourseService chua co')
                rows = CourseService.get_classes_by_teacher(gv_id) if gv_id else []
                gv_classes = [(r['ma_lop'], r.get('ten_mon', '')) for r in rows]
            except Exception as e:
                print(f'[TEA_ATTEND] DB loi load classes: {e}')
        if not gv_classes:
            # Khong co DB hoac GV chua co lop nao - dung ten GV hien tai loc tu mock cu
            gv_name = MOCK_TEACHER.get('name', '')
            gv_classes = [(c[0], c[2]) for c in MOCK_CLASSES if c[3] == gv_name]

        cbo_cls = page.findChild(QtWidgets.QComboBox, 'cboAttendClass')
        if cbo_cls:
            cbo_cls.clear()
            cbo_cls.addItem('-- Chọn lớp --')
            for ma, ten in gv_classes:
                cbo_cls.addItem(f'{ma} — {ten}', ma)

        # 2. Cache du lieu trong memory de save batch
        self._attend_cache = {}
        self._attend_buoi_by_class = {}
        self._attend_hv_by_class = {}

        # 3. Wire signal
        if cbo_cls:
            cbo_cls.currentIndexChanged.connect(self._on_attend_class_changed)
        cbo_buoi = page.findChild(QtWidgets.QComboBox, 'cboAttendBuoi')
        if cbo_buoi:
            cbo_buoi.currentIndexChanged.connect(self._on_attend_buoi_changed)

        btn_save = page.findChild(QtWidgets.QPushButton, 'btnSaveAttend')
        if btn_save:
            btn_save.clicked.connect(self._save_attendance)
        btn_all = page.findChild(QtWidgets.QPushButton, 'btnMarkAllPresent')
        if btn_all:
            btn_all.clicked.connect(self._mark_all_present)

        # 4. Render trang trong (cho user chon lop)
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAttendance')
        if tbl:
            tbl.setRowCount(0)
            tbl.verticalHeader().setVisible(False)
            for c, cw in enumerate([40, 95, 200, 130, 100, 200]):
                tbl.setColumnWidth(c, cw)
            tbl.horizontalHeader().setStretchLastSection(True)

    def _on_attend_class_changed(self, idx):
        """Khi GV doi lop -> load danh sach buoi cua lop do"""
        page = self.page_widgets[4]
        cbo_cls = page.findChild(QtWidgets.QComboBox, 'cboAttendClass')
        cbo_buoi = page.findChild(QtWidgets.QComboBox, 'cboAttendBuoi')
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAttendance')
        info = page.findChild(QtWidgets.QLabel, 'lblAttendInfo')
        if not (cbo_cls and cbo_buoi):
            return
        if idx <= 0:
            cbo_buoi.clear()
            cbo_buoi.addItem('-- Chọn buổi học --')
            if tbl: tbl.setRowCount(0)
            if info: info.setText('Chưa chọn buổi')
            return
        ma_lop = cbo_cls.itemData(idx) or cbo_cls.currentText().split(' — ')[0]

        buois = []
        if DB_AVAILABLE:
            try:
                if not ScheduleService:
                    raise RuntimeError('ScheduleService chua co')
                rows = ScheduleService.get_for_class(ma_lop)
                for r in rows:
                    bid = r.get('id')
                    ngay = r.get('ngay', '')
                    gio_bd = str(r.get('gio_bat_dau', ''))[:5]
                    gio_kt = str(r.get('gio_ket_thuc', ''))[:5]
                    buoi_so = r.get('buoi_so', '?')
                    label = f'Buổi {buoi_so} — {ngay} ({gio_bd}-{gio_kt})'
                    buois.append((bid, label, r))
            except Exception as e:
                print(f'[TEA_ATTEND] DB loi load buoi: {e}')

        if not buois:
            from datetime import date, timedelta
            today = date.today()
            for i in range(6, 0, -1):
                d = today - timedelta(days=i * 7)
                fake_id = -(hash((ma_lop, i)) & 0xFFFFFF)
                label = f'Buổi {7 - i} — {d.strftime("%d/%m/%Y")} (07:00-09:30)'
                buois.append((fake_id, label, {'ngay': d, 'gio_bat_dau': '07:00', 'gio_ket_thuc': '09:30'}))

        self._attend_buoi_by_class[ma_lop] = buois
        cbo_buoi.blockSignals(True)
        cbo_buoi.clear()
        cbo_buoi.addItem('-- Chọn buổi học --')
        for bid, label, _ in buois:
            cbo_buoi.addItem(label, bid)
        cbo_buoi.blockSignals(False)
        if tbl: tbl.setRowCount(0)
        if info: info.setText(f'Lớp {ma_lop} — {len(buois)} buổi')

    def _on_attend_buoi_changed(self, idx):
        """Khi GV chon buoi -> render bang HV + trang thai diem danh"""
        page = self.page_widgets[4]
        cbo_cls = page.findChild(QtWidgets.QComboBox, 'cboAttendClass')
        cbo_buoi = page.findChild(QtWidgets.QComboBox, 'cboAttendBuoi')
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAttendance')
        info = page.findChild(QtWidgets.QLabel, 'lblAttendInfo')
        if not (cbo_cls and cbo_buoi and tbl) or idx <= 0:
            if tbl: tbl.setRowCount(0)
            return
        ma_lop = cbo_cls.itemData(cbo_cls.currentIndex())
        buoi_id = cbo_buoi.itemData(idx)
        if ma_lop is None or buoi_id is None:
            return

        hvs = self._load_class_students(ma_lop)
        existing = {}
        if DB_AVAILABLE and AttendanceService and buoi_id > 0:
            try:
                rows = AttendanceService.get_for_schedule(buoi_id)
                for r in rows:
                    existing[r['hv_id']] = {
                        'trang_thai': r.get('trang_thai', ''),
                        'gio_vao': str(r.get('gio_vao') or ''),
                        'ghi_chu': r.get('ghi_chu') or '',
                    }
            except Exception as e:
                print(f'[TEA_ATTEND] DB loi load attendance: {e}')

        self._render_attend_table(tbl, hvs, existing)
        if info:
            label_buoi = cbo_buoi.currentText()
            info.setText(f'{label_buoi} — {len(hvs)} HV')
        self._update_attend_stats()

    def _load_class_students(self, ma_lop):
        """Lay danh sach HV cua 1 lop tu API. Tra ve [(hv_id, msv, full_name)].
        Cache ket qua trong _attend_hv_by_class."""
        if ma_lop in self._attend_hv_by_class:
            return self._attend_hv_by_class[ma_lop]
        hvs = []
        if DB_AVAILABLE:
            try:
                # API endpoint: GET /classes/{ma_lop}/students
                rows = CourseService.get_students_in_class(ma_lop) or []
                for r in rows:
                    # API tra ve {user_id, full_name, msv, sdt, reg_status}
                    uid = r.get('user_id') or r.get('hv_id')
                    msv = r.get('msv', '')
                    name = r.get('full_name', '')
                    if uid and msv:
                        hvs.append((uid, msv, name))
            except Exception as e:
                print(f'[TEA_ATTEND] API loi load HV lop {ma_lop}: {e}')
        # Khong co API -> KHONG fake data (de tranh hv_id am gay 500 khi save)
        # Bang se hien rong + user thay rang lop chua co HV
        self._attend_hv_by_class[ma_lop] = hvs
        return hvs

    def _render_attend_table(self, tbl, hvs, existing):
        """Render bang diem danh - moi row gom combo trang thai + giờ vào + ghi chú"""
        tbl.setRowCount(len(hvs))
        for r, (hv_id, msv, ten) in enumerate(hvs):
            tbl.setRowHeight(r, 38)
            it_stt = QtWidgets.QTableWidgetItem(str(r + 1))
            it_stt.setTextAlignment(Qt.AlignCenter)
            it_stt.setFlags(it_stt.flags() & ~Qt.ItemIsEditable)
            it_stt.setData(Qt.UserRole, hv_id)
            tbl.setItem(r, 0, it_stt)
            it_msv = QtWidgets.QTableWidgetItem(msv)
            it_msv.setTextAlignment(Qt.AlignCenter)
            it_msv.setFlags(it_msv.flags() & ~Qt.ItemIsEditable)
            tbl.setItem(r, 1, it_msv)
            it_ten = QtWidgets.QTableWidgetItem(ten)
            it_ten.setFlags(it_ten.flags() & ~Qt.ItemIsEditable)
            tbl.setItem(r, 2, it_ten)
            combo = QtWidgets.QComboBox()
            combo.setProperty('hv_id', hv_id)
            combo.addItem('— Chưa điểm danh —', '')
            for code, label, _ in self._ATTEND_STATES:
                combo.addItem(label, code)
            cur_st = existing.get(hv_id, {}).get('trang_thai', '')
            for i in range(combo.count()):
                if combo.itemData(i) == cur_st:
                    combo.setCurrentIndex(i)
                    break
            combo.setStyleSheet(
                'QComboBox { padding: 4px 8px; border: 1px solid #cbd5e0; border-radius: 4px; '
                'background: white; font-size: 12px; min-height: 24px; }'
            )
            combo.currentIndexChanged.connect(lambda _i, rr=r: self._on_attend_combo_changed(rr))
            tbl.setCellWidget(r, 3, combo)
            te = QtWidgets.QTimeEdit()
            te.setDisplayFormat('HH:mm')
            te.setStyleSheet(
                'QTimeEdit { padding: 3px 6px; border: 1px solid #cbd5e0; border-radius: 4px; '
                'background: white; font-size: 12px; min-height: 24px; }'
            )
            cur_gv = existing.get(hv_id, {}).get('gio_vao', '')
            if cur_gv:
                try:
                    h, m = cur_gv.split(':')[:2]
                    te.setTime(QtCore.QTime(int(h), int(m)))
                except Exception:
                    te.setTime(QtCore.QTime(7, 0))
            else:
                te.setTime(QtCore.QTime(7, 0))
            tbl.setCellWidget(r, 4, te)
            it_note = QtWidgets.QTableWidgetItem(existing.get(hv_id, {}).get('ghi_chu', ''))
            tbl.setItem(r, 5, it_note)

    def _on_attend_combo_changed(self, row):
        """Toi mau row khi GV chon trang thai"""
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAttendance')
        if not tbl: return
        combo = tbl.cellWidget(row, 3)
        if not combo: return
        code = combo.currentData()
        color = self._ATTEND_COLOR_MAP.get(code, '#718096')
        for c in (0, 1, 2, 5):
            it = tbl.item(row, c)
            if it:
                if code:
                    it.setBackground(QColor(color + '15'))
                else:
                    it.setBackground(QColor('#ffffff'))
        self._update_attend_stats()

    def _update_attend_stats(self):
        """Cap nhat label thong ke: x co mat / y vang / z tre"""
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAttendance')
        lbl = page.findChild(QtWidgets.QLabel, 'lblAttendStats')
        if not (tbl and lbl): return
        cnt = {'present': 0, 'late': 0, 'absent': 0, 'excused': 0, '': 0}
        for r in range(tbl.rowCount()):
            cb = tbl.cellWidget(r, 3)
            if cb:
                cnt[cb.currentData() or ''] = cnt.get(cb.currentData() or '', 0) + 1
        parts = [
            f'<span style="color:#276749;"><b>{cnt["present"]}</b> Có mặt</span>',
            f'<span style="color:#c68a1e;"><b>{cnt["late"]}</b> Trễ</span>',
            f'<span style="color:#c53030;"><b>{cnt["absent"]}</b> Vắng</span>',
            f'<span style="color:#3182ce;"><b>{cnt["excused"]}</b> Có phép</span>',
        ]
        if cnt['']:
            parts.append(f'<span style="color:#a0aec0;">{cnt[""]} chưa ghi</span>')
        lbl.setText('  ·  '.join(parts))

    def _mark_all_present(self):
        """Quick action: set tat ca HV chua diem danh -> 'present'"""
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAttendance')
        if not tbl or tbl.rowCount() == 0:
            msg_info(self, 'Chưa có dữ liệu', 'Hãy chọn lớp và buổi học trước.')
            return
        for r in range(tbl.rowCount()):
            cb = tbl.cellWidget(r, 3)
            if cb and not cb.currentData():
                for i in range(cb.count()):
                    if cb.itemData(i) == 'present':
                        cb.setCurrentIndex(i)
                        break

    def _save_attendance(self):
        """Luu attendance vao DB qua AttendanceService.mark()
        Neu buoi la MOCK (id am) ma user co DB -> hoi co tu dong tao buoi that khong"""
        page = self.page_widgets[4]
        cbo_cls = page.findChild(QtWidgets.QComboBox, 'cboAttendClass')
        cbo_buoi = page.findChild(QtWidgets.QComboBox, 'cboAttendBuoi')
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAttendance')
        if not (cbo_cls and cbo_buoi and tbl) or cbo_buoi.currentIndex() <= 0:
            msg_info(self, 'Chưa chọn buổi', 'Vui lòng chọn lớp và buổi học trước khi lưu.')
            return
        if tbl.rowCount() == 0:
            msg_info(self, 'Chưa có dữ liệu', 'Không có học viên nào để điểm danh.')
            return

        buoi_id = cbo_buoi.itemData(cbo_buoi.currentIndex())
        ma_lop = cbo_cls.itemData(cbo_cls.currentIndex())
        gv_id = MOCK_TEACHER.get('user_id')
        records = []
        for r in range(tbl.rowCount()):
            it_stt = tbl.item(r, 0)
            cb = tbl.cellWidget(r, 3)
            te = tbl.cellWidget(r, 4)
            it_note = tbl.item(r, 5)
            if not (it_stt and cb): continue
            code = cb.currentData()
            if not code:
                continue
            hv_id = it_stt.data(Qt.UserRole)
            gio_vao = te.time().toString('HH:mm') if te and code in ('present', 'late') else None
            ghi_chu = it_note.text().strip() if it_note else ''
            records.append((hv_id, code, gio_vao, ghi_chu))

        if not records:
            if not msg_confirm(self, 'Chưa điểm danh ai',
                               'Bạn chưa chọn trạng thái cho học viên nào. Vẫn lưu (rỗng)?'):
                return

        # Neu buoi chua co trong he thong lich -> hoi user co tao buoi moi khong
        if DB_AVAILABLE and AttendanceService and (not buoi_id or buoi_id <= 0):
            if msg_confirm(self, 'Buổi học chưa có trong hệ thống',
                           f'Buổi học này chưa được tạo trong hệ thống lịch của lớp {ma_lop}.\n\n'
                           f'Bạn có muốn tạo buổi học mới và lưu điểm danh không?\n\n'
                           f'Chọn "Có" để tạo buổi học mới và lưu lại.\n'
                           f'Chọn "Không" để hủy thao tác.'):
                # Lay info buoi tu cache
                buoi_info = None
                for bid, label, info in self._attend_buoi_by_class.get(ma_lop, []):
                    if bid == buoi_id:
                        buoi_info = info
                        break
                buoi_info = buoi_info or {}
                # Tao schedule moi qua API ScheduleService.create() roi load lai
                try:
                    from datetime import date as _date
                    ngay_val = buoi_info.get('ngay') or _date.today()
                    gio_bd = str(buoi_info.get('gio_bat_dau', '07:00'))[:5]
                    gio_kt = str(buoi_info.get('gio_ket_thuc', '09:30'))[:5]
                    ScheduleService.create(
                        ma_lop, ngay_val, gio_bd, gio_kt,
                        trang_thai='completed'
                    )
                    # Re-query schedule list de lay id moi tao
                    new_schedules = ScheduleService.get_for_class(ma_lop) or []
                    # Tim schedule co ngay khop (moi tao gan day nhat)
                    matched = [s for s in new_schedules
                               if str(s.get('ngay', ''))[:10] == str(ngay_val)[:10]]
                    if matched:
                        buoi_id = matched[-1].get('id')  # lay id cao nhat
                        print(f'[TEA_ATTEND] Tao schedule moi cho {ma_lop}, id={buoi_id}')
                    if not buoi_id or buoi_id <= 0:
                        msg_warn(self, 'Lỗi', 'Đã tạo buổi học nhưng không lấy được mã. Vui lòng thử lại.')
                        return
                except Exception as e:
                    print(f'[TEA_ATTEND] Khong tao duoc schedule: {e}')
                    msg_warn(self, 'Lỗi tạo buổi', f'Không thể tạo buổi học mới:\n{e}')
                    return
            else:
                return  # User chọn "Không" -> hủy

        saved = 0
        last_err = None
        if DB_AVAILABLE and AttendanceService and buoi_id and buoi_id > 0:
            for hv_id, code, gio_vao, ghi_chu in records:
                try:
                    AttendanceService.mark(buoi_id, hv_id, code,
                                           gio_vao=gio_vao,
                                           recorded_by=gv_id,
                                           ghi_chu=ghi_chu or None)
                    saved += 1
                except Exception as e:
                    last_err = str(e)[:120]
                    print(f'[TEA_ATTEND] save hv_id={hv_id}: {e}')
            if saved > 0:
                msg_info(self, 'Lưu điểm danh thành công',
                         f'Đã lưu điểm danh cho {saved}/{len(records)} học viên - lớp {ma_lop}.\n\n'
                         f'Vào trang "Nhập điểm" và bấm "↻ CC từ điểm danh" '
                         f'để cập nhật cột Chuyên cần.')
            else:
                msg_warn(self, 'Lưu điểm danh thất bại',
                         f'Không lưu được học viên nào.\n\nLỗi: {last_err or "không rõ"}')
        else:
            msg_warn(self, 'Không lưu được',
                     'Hiện chưa kết nối được hệ thống. Vui lòng kiểm tra kết nối '
                     'và thử lại sau.')

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
        active = TEACHER_PAGES[index][0]
        for btn_name, _ in TEACHER_PAGES:
            btn = getattr(self, btn_name)
            icon = getattr(self, btn_name.replace('btn', 'icon'))
            if btn_name == active:
                btn.setStyleSheet(SIDEBAR_ACTIVE)
                icon.raise_()
            else:
                btn.setStyleSheet(SIDEBAR_NORMAL)

    def _on_logout(self):
        self.close()
        self.app_ref.show_login()

    # === TEACHER DATA FILL ===

    def _fill_tea_dashboard(self):
        page = self.page_widgets[0]
        w = page.findChild(QtWidgets.QLabel, 'lblWelcome')
        if w:
            w.setText(f"Xin chào, thầy {MOCK_TEACHER['name']}")

        # 4 stat card - lay tu /stats/teacher/{gv_id}/overview
        gv_id = MOCK_TEACHER.get('user_id')
        if DB_AVAILABLE and gv_id:
            try:
                ov = StatsService.teacher_overview(gv_id) or {}
                for lbl_name, key in [('lblStat1', 'so_lop'),
                                       ('lblStat2', 'tong_hv'),
                                       ('lblStat3', 'buoi_tuan'),
                                       ('lblStat4', 'diem_danh_gia')]:
                    w_lbl = page.findChild(QtWidgets.QLabel, lbl_name)
                    if w_lbl:
                        val = ov.get(key, '—')
                        w_lbl.setText(str(val) if val not in (None, '') else '—')
            except Exception as e:
                print(f'[STATS] teacher_overview loi: {e}')

        # Today schedule
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblToday')
        if tbl:
            data = [
                ['7:00-9:30', 'IT001-A (Python)', 'P.A301'],
                ['13:00-15:30', 'IT004-A (AI)', 'P.A301'],
                ['15:40-18:10', 'IT001-C (Python)', 'P.C102'],
            ]
            tbl.setRowCount(len(data))
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter if c != 1 else Qt.AlignLeft | Qt.AlignVCenter)
                    tbl.setItem(r, c, item)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setColumnWidth(0, 100)
            tbl.setColumnWidth(1, 180)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 38)

        # Activity
        tbl2 = page.findChild(QtWidgets.QTableWidget, 'tblActivity')
        if tbl2:
            data = [
                ('30 phút trước', 'Nhận đánh giá mới từ lớp IT001-A'),
                ('2 giờ trước', 'Lớp IT004-A có 2 học viên mới'),
                ('Hôm qua', 'Đã gửi thông báo cho lớp IT001-C'),
                ('2 ngày trước', 'Cập nhật điểm giữa kỳ IT001-A'),
                ('3 ngày trước', 'Admin thông báo: họp khoa CNTT 25/04'),
            ]
            tbl2.setRowCount(len(data))
            for r, (t, c) in enumerate(data):
                ti = QtWidgets.QTableWidgetItem(t)
                ti.setForeground(QColor(COLORS['text_light']))
                ti.setFont(QFont('Segoe UI', 9))
                tbl2.setItem(r, 0, ti)
                tbl2.setItem(r, 1, QtWidgets.QTableWidgetItem(c))
            tbl2.horizontalHeader().setStretchLastSection(True)
            tbl2.setColumnWidth(0, 110)
            tbl2.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl2.setRowHeight(r, 38)

    def _fill_tea_schedule(self):
        # tái sử dụng schedule.ui giống HV nhưng lịch của GV
        page = self.page_widgets[1]
        sf = page.findChild(QtWidgets.QFrame, 'scheduleFrame')
        if sf:
            sf.setGeometry(15, 68, 610, 618)
        cf = page.findChild(QtWidgets.QFrame, 'calendarFrame')
        if cf:
            cf.setGeometry(638, 68, 220, 230)
        lf = page.findChild(QtWidgets.QFrame, 'legendFrame')
        if lf:
            lf.setGeometry(638, 310, 220, 180)

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblSchedule')
        if not tbl:
            return
        hours = ['7:00','8:00','9:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00']
        tbl.setRowCount(len(hours))
        tbl.verticalHeader().setVisible(False)

        today = QDate.currentDate()
        monday = today.addDays(-(today.dayOfWeek() - 1))
        days_vn = ['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7']
        for i in range(6):
            d = monday.addDays(i)
            tbl.horizontalHeaderItem(i+1).setText(f'{d.toString("dd/MM/yyyy")}\n{days_vn[i]}')
        tbl.setColumnWidth(0, 45)
        for i in range(1, 7):
            tbl.setColumnWidth(i, 92)
        # font lon hon cho lich day - dec hon nhin tu xa
        for r in range(len(hours)):
            tbl.setRowHeight(r, 55)
            item = QtWidgets.QTableWidgetItem(hours[r])
            item.setTextAlignment(Qt.AlignRight | Qt.AlignTop)
            item.setForeground(QColor('#718096'))
            item.setFont(QFont('Segoe UI', 9))
            tbl.setItem(r, 0, item)
        for r in range(len(hours)):
            for c in range(1, 7):
                if not tbl.item(r, c) and not tbl.cellWidget(r, c):
                    tbl.setItem(r, c, QtWidgets.QTableWidgetItem(''))

        def mk(ten, ts, toa, phong, ss, color):
            f = QtWidgets.QFrame()
            f.setStyleSheet(f'QFrame {{ background: white; border: 1px solid #d2d6dc; border-radius: 4px; border-top: 3px solid {color}; margin: 1px; }}')
            vb = QtWidgets.QVBoxLayout(f)
            vb.setContentsMargins(5, 4, 5, 4)
            vb.setSpacing(2)
            for txt, st in [(ten, f'color: {color}; font-size: 11px; font-weight: bold; border: none;'),
                            (ts, 'color: #4a5568; font-size: 10px; border: none;'),
                            (f'Tòa {toa} - {phong}', 'color: #718096; font-size: 9px; border: none;'),
                            (ss, 'color: #4a5568; font-size: 9px; border: none;')]:
                l = QtWidgets.QLabel(txt)
                l.setStyleSheet(st)
                l.setWordWrap(True)
                vb.addWidget(l)
            vb.addStretch()
            return f

        # lich day GV
        sched = [
            (0, 3, 2, 'IT001-A Python', '07:00-09:30', 'EAUT', 'P.301', '35 HV', '#002060'),
            (0, 3, 4, 'IT001-A Python', '07:00-09:30', 'EAUT', 'P.301', '35 HV', '#002060'),
            (6, 3, 2, 'IT004-A AI', '13:00-15:30', 'EAUT', 'P.301', '28 HV', '#c68a1e'),
            (9, 3, 1, 'IT001-C Python', '15:40-18:10', 'EAUT', 'P.102', '35 HV', '#276749'),
            (9, 3, 3, 'IT001-C Python', '15:40-18:10', 'EAUT', 'P.102', '35 HV', '#276749'),
        ]
        for rs, span, col, ten, ts, toa, phong, ss, color in sched:
            tbl.setCellWidget(rs, col, mk(ten, ts, toa, phong, ss, color))
            tbl.setSpan(rs, col, span, 1)

        # wire calendar
        cal = page.findChild(QtWidgets.QCalendarWidget, 'calendarWidget')
        if cal:
            def on_click(qdate):
                mon = qdate.addDays(-(qdate.dayOfWeek() - 1))
                for i in range(6):
                    d = mon.addDays(i)
                    tbl.horizontalHeaderItem(i+1).setText(f'{d.toString("dd/MM/yyyy")}\n{days_vn[i]}')
                thu_vn = ['Chủ nhật', 'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7'][qdate.dayOfWeek() % 7]
                msg_info(self, 'Xem lịch dạy',
                         f'{thu_vn}, ngày {qdate.toString("dd/MM/yyyy")}\n'
                         f'Tuần: {mon.toString("dd/MM")} → {mon.addDays(5).toString("dd/MM")}')
            cal.clicked.connect(on_click)

    def _fill_tea_classes(self):
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblTeacherClasses')
        if not tbl:
            return
        # lay tu DB neu co
        my_classes = []
        if DB_AVAILABLE:
            try:
                gv_id = MOCK_TEACHER.get('user_id')
                if gv_id:
                    rows = CourseService.get_classes_by_teacher(gv_id)
                    for r_db in rows:
                        my_classes.append((
                            r_db['ma_lop'], r_db['ma_mon'], r_db['ten_mon'],
                            r_db.get('ten_gv') or MOCK_TEACHER['name'],
                            r_db.get('lich') or '', r_db.get('phong') or '',
                            int(r_db.get('siso_max') or 40),
                            int(r_db.get('siso_hien_tai') or 0),
                            int(r_db.get('gia') or 0),
                        ))
            except Exception as e:
                print(f'[TEA_CLS] DB loi: {e}')
        if not my_classes:
            # Khong co DB - loc theo ten GV hien tai
            gv_name = MOCK_TEACHER.get('name', '')
            my_classes = [c for c in MOCK_CLASSES if c[3] == gv_name]
        tbl.setRowCount(len(my_classes))
        for r, cls in enumerate(my_classes):
            ma, mmon, tmon, gv, lich, phong, smax, siso, gia = cls
            for c, val in enumerate([ma, tmon]):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c == 0 else Qt.AlignLeft | Qt.AlignVCenter)
                tbl.setItem(r, c, item)
            # siso
            siso_item = QtWidgets.QTableWidgetItem(f'{siso}/{smax}')
            siso_item.setTextAlignment(Qt.AlignCenter)
            pct = int(siso / smax * 100)
            siso_item.setForeground(QColor(COLORS['red'] if pct >= 95 else COLORS['gold'] if pct >= 70 else COLORS['green']))
            tbl.setItem(r, 2, siso_item)
            # lich, phong
            item_l = QtWidgets.QTableWidgetItem(lich)
            item_l.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            tbl.setItem(r, 3, item_l)
            item_p = QtWidgets.QTableWidgetItem(phong)
            item_p.setTextAlignment(Qt.AlignCenter)
            tbl.setItem(r, 4, item_p)
            # gia
            gia_item = QtWidgets.QTableWidgetItem(f'{gia:,}'.replace(',', '.') + ' đ')
            gia_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            gia_item.setForeground(QColor(COLORS['gold']))
            tbl.setItem(r, 5, gia_item)
            # action: xem chi tiết
            btn = QtWidgets.QPushButton('Chi tiết')
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(64, 22)
            btn.setStyleSheet(
                f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; '
                f'border-radius: 3px; font-size: 10px; font-weight: bold; padding: 0; }} '
                f'QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}'
            )
            btn.clicked.connect(lambda ch, m=ma, n=tmon, s=siso, mx=smax, p=phong, l=lich, g=gia:
                show_detail_dialog(self, 'Chi tiết lớp', [
                    ('Mã lớp', m), ('Môn học', n), ('Giảng viên', MOCK_TEACHER['name']),
                    ('Lịch học', l), ('Phòng', p),
                    ('Sĩ số', f'{s}/{mx}'),
                    ('Học phí', f'{g:,}'.replace(',', '.') + ' đ'),
                ], avatar_text=m, subtitle=n))
            # Wrapper auto-fit cell + center button (vertical + horizontal)
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(0)
            hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(btn, 0, Qt.AlignCenter)
            tbl.setCellWidget(r, 6, w)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([100, 180, 80, 160, 80, 120, 90]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(my_classes)):
            tbl.setRowHeight(r, 36)

    def _fill_tea_students(self):
        page = self.page_widgets[3]
        # populate class filter
        cbo = page.findChild(QtWidgets.QComboBox, 'cboClass')
        # lay lop cua GV tu DB
        gv_classes_codes = []
        if DB_AVAILABLE:
            try:
                gv_id = MOCK_TEACHER.get('user_id')
                if gv_id:
                    rows = CourseService.get_classes_by_teacher(gv_id)
                    gv_classes_codes = [r['ma_lop'] for r in rows]
            except Exception: pass
        if not gv_classes_codes:
            # fallback dung ten GV hien tai (MOCK_TEACHER['name']) thay vi hardcode
            gv_name = MOCK_TEACHER.get('name')
            gv_classes_codes = [c[0] for c in MOCK_CLASSES if c[3] == gv_name] if gv_name else []
        if cbo:
            cbo.clear()
            cbo.addItem('Tất cả lớp')
            for lop in gv_classes_codes:
                cbo.addItem(lop)

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblStudents')
        if not tbl:
            return
        # lay HV tu DB
        data = None
        if DB_AVAILABLE:
            try:
                gv_id = MOCK_TEACHER.get('user_id')
                if gv_id:
                    rows = CourseService.get_students_by_teacher(gv_id)
                    data = []
                    for i, s in enumerate(rows, start=1):
                        status = 'Đang học' if s.get('trang_thai') == 'paid' else 'Chờ TT'
                        data.append([str(i), s['msv'], s['full_name'],
                                     s.get('lop_id', ''), s.get('sdt') or '—', status])
            except Exception as e:
                print(f'[TEA_STU] DB loi: {e}')
        if not data:
            data = []
        tbl.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, val in enumerate(row[:5]):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c in (0, 3) else Qt.AlignLeft | Qt.AlignVCenter)
                tbl.setItem(r, c, item)
            item_st = QtWidgets.QTableWidgetItem(row[5])
            item_st.setTextAlignment(Qt.AlignCenter)
            item_st.setForeground(QColor(COLORS['green'] if row[5] == 'Đang học' else COLORS['orange']))
            tbl.setItem(r, 5, item_st)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([45, 100, 200, 90, 130, 110]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 40)

        # btnExportStudents nam o headerBar va da o sat phai - khong day
        widen_search(page, 'txtSearchStudent', 280)
        # filter + search
        txt_s = page.findChild(QtWidgets.QLineEdit, 'txtSearchStudent')
        if txt_s:
            txt_s.textChanged.connect(lambda t: table_filter(tbl, t, cols=[1, 2]))
        if cbo:
            cbo.currentIndexChanged.connect(lambda: self._filter_tea_students())
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportStudents')
        if btn_exp:
            btn_exp.clicked.connect(lambda: export_table_csv(self, tbl, 'ds_hocvien.csv', 'Xuất danh sách học viên'))

    def _filter_tea_students(self):
        page = self.page_widgets[3]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblStudents')
        cbo = page.findChild(QtWidgets.QComboBox, 'cboClass')
        if not tbl or not cbo:
            return
        sel = cbo.currentText()
        for r in range(tbl.rowCount()):
            it = tbl.item(r, 3)
            if cbo.currentIndex() == 0:
                tbl.setRowHidden(r, False)
            else:
                tbl.setRowHidden(r, it.text() != sel if it else False)

    def _fill_tea_notice(self):
        page = self.page_widgets[5]
        cbo = page.findChild(QtWidgets.QComboBox, 'cboTargetClass')
        if cbo:
            cbo.clear()
            cbo.addItem('Tất cả lớp đang dạy')
            # Lay lop GV dang day - uu tien API, fallback theo ten
            gv_id = MOCK_TEACHER.get('user_id')
            classes_loaded = False
            if DB_AVAILABLE and gv_id:
                try:
                    rows = CourseService.get_classes_by_teacher(gv_id)
                    for r in rows:
                        cbo.addItem(r['ma_lop'])
                    classes_loaded = True
                except Exception as e:
                    print(f'[TEA_NOTICE] DB loi: {e}')
            if not classes_loaded:
                gv_name = MOCK_TEACHER.get('name', '')
                for cls in MOCK_CLASSES:
                    if cls[3] == gv_name:
                        cbo.addItem(cls[0])

        # populate sent list
        sc = page.findChild(QtWidgets.QWidget, 'sentContent')
        if sc:
            sc.setMinimumHeight(500)
            vlay = QtWidgets.QVBoxLayout(sc)
            vlay.setContentsMargins(4, 4, 4, 4)
            vlay.setSpacing(8)
            self._tea_notice_layout = vlay
            sent = [
                ('IT001-A', 'Nghỉ học ngày 20/04', '2 ngày trước'),
                ('IT004-A', 'Bài tập tuần 8', '3 ngày trước'),
                ('Tất cả', 'Thông báo kiểm tra giữa kỳ', '1 tuần trước'),
                ('IT001-C', 'Đổi phòng học', '1 tuần trước'),
            ]
            for to, subj, t in sent:
                card = self._make_notice_card(to, subj, t)
                vlay.addWidget(card)
            vlay.addStretch()

        # nut gui / clear
        btn_send = page.findChild(QtWidgets.QPushButton, 'btnSendNotice')
        if btn_send:
            btn_send.clicked.connect(self._tea_send_notice)
        btn_clear = page.findChild(QtWidgets.QPushButton, 'btnClearNotice')
        if btn_clear:
            btn_clear.clicked.connect(self._tea_clear_notice)

    def _make_notice_card(self, to, subj, t):
        card = QtWidgets.QFrame()
        card.setFixedHeight(82)
        card.setStyleSheet('QFrame { background: #f7fafc; border-radius: 6px; border-left: 3px solid #002060; }')
        vb = QtWidgets.QVBoxLayout(card)
        vb.setContentsMargins(10, 8, 10, 8)
        vb.setSpacing(3)
        l1 = QtWidgets.QLabel(f'→ {to}')
        l1.setStyleSheet(f'color: {COLORS["navy"]}; font-size: 11px; font-weight: bold; background: transparent; border: none;')
        l2 = QtWidgets.QLabel(subj)
        l2.setStyleSheet('color: #1a1a2e; font-size: 12px; background: transparent; border: none;')
        l2.setWordWrap(True)
        l3 = QtWidgets.QLabel(t)
        l3.setStyleSheet(f'color: {COLORS["text_light"]}; font-size: 10px; background: transparent; border: none;')
        vb.addWidget(l1)
        vb.addWidget(l2)
        vb.addWidget(l3)
        return card

    def _tea_send_notice(self):
        page = self.page_widgets[5]
        subj = page.findChild(QtWidgets.QLineEdit, 'txtSubject')
        content = page.findChild(QtWidgets.QTextEdit, 'txtContent')
        cbo = page.findChild(QtWidgets.QComboBox, 'cboTargetClass')
        if not subj or not content or not cbo:
            return
        if not subj.text().strip():
            msg_warn(self, 'Thiếu dữ liệu', 'Hãy nhập tiêu đề')
            return
        if not content.toPlainText().strip():
            msg_warn(self, 'Thiếu dữ liệu', 'Hãy nhập nội dung')
            return
        target = cbo.currentText()
        title = subj.text().strip()
        body = content.toPlainText().strip()
        # ghi DB neu co
        if DB_AVAILABLE:
            gv_user_id = MOCK_TEACHER.get('user_id')
            if gv_user_id:
                try:
                    den_lop = target if cbo.currentIndex() > 0 else None
                    NotificationService.send(gv_user_id, title, body, den_lop=den_lop, loai='info')
                except Exception as e:
                    print(f'[NOTICE] loi: {e}')
        # them card vao dau danh sach
        if hasattr(self, '_tea_notice_layout') and self._tea_notice_layout:
            card = self._make_notice_card(target, title, 'Vừa xong')
            self._tea_notice_layout.insertWidget(0, card)
        msg_info(self, 'Gửi thông báo', f'Đã gửi thông báo đến: {target}\nTiêu đề: {title}')
        subj.clear(); content.clear()

    def _tea_clear_notice(self):
        page = self.page_widgets[5]
        for name in ('txtSubject',):
            w = page.findChild(QtWidgets.QLineEdit, name)
            if w: w.clear()
        w = page.findChild(QtWidgets.QTextEdit, 'txtContent')
        if w: w.clear()

    def _fill_tea_grades(self):
        page = self.page_widgets[6]
        cbo = page.findChild(QtWidgets.QComboBox, 'cboGradeClass')

        # lay danh sach lop cua GV tu DB
        gv_classes_codes = []
        if DB_AVAILABLE:
            try:
                gv_id = MOCK_TEACHER.get('user_id')
                if gv_id:
                    rows = CourseService.get_classes_by_teacher(gv_id)
                    gv_classes_codes = [r['ma_lop'] for r in rows]
            except Exception: pass
        if not gv_classes_codes:
            # fallback theo ten GV hien tai (MOCK_TEACHER['name']) thay vi hardcode
            gv_name = MOCK_TEACHER.get('name')
            gv_classes_codes = [c[0] for c in MOCK_CLASSES if c[3] == gv_name] if gv_name else []

        if cbo:
            cbo.clear()
            cbo.addItem('-- Chọn lớp để nhập điểm --')
            for lop in gv_classes_codes:
                cbo.addItem(lop)

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblTeacherGrades')
        if not tbl:
            return
        # lay grades tu DB theo lop
        self._tea_grades_by_class = {}
        if DB_AVAILABLE:
            try:
                for lop in gv_classes_codes:
                    rows = GradeService.get_grades_by_class(lop)
                    self._tea_grades_by_class[lop] = [
                        [str(i+1), r['msv'], r['full_name'],
                         f"{float(r['diem_qt']):.1f}" if r.get('diem_qt') is not None else '',
                         f"{float(r['diem_thi']):.1f}" if r.get('diem_thi') is not None else '',
                         f"{float(r['tong_ket']):.1f}" if r.get('tong_ket') is not None else '',
                         r.get('xep_loai') or '']
                        for i, r in enumerate(rows)
                    ]
            except Exception as e:
                print(f'[TEA_GRADES] DB loi: {e}')

        # khong co du lieu -> de empty dict, _tea_grades_render se hien bang rong
        if not self._tea_grades_by_class:
            self._tea_grades_by_class = {}
        # defaut show tat ca
        self._tea_grades_render(tbl, None)

        # setEditTriggers de cho nhap dc
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed
                            | QtWidgets.QAbstractItemView.SelectedClicked)
        tbl.setStyleSheet(
            'QTableWidget QLineEdit { '
            'font-size: 14px; font-weight: bold; color: #1a1a2e; '
            'background: white; padding: 8px 10px; '
            'min-height: 32px; '
            'border: 2px solid #002060; selection-background-color: #002060; '
            'selection-color: white; }'
        )
        # cot CC (3), QT (4), Thi (5) - cho nhap truc tiep tren bang
        tbl.setItemDelegateForColumn(3, _GradeEditorDelegate(tbl))
        tbl.setItemDelegateForColumn(4, _GradeEditorDelegate(tbl))
        tbl.setItemDelegateForColumn(5, _GradeEditorDelegate(tbl))
        tbl.itemChanged.connect(self._recalc_grade_row)
        self._grades_recalc_lock = False

        # save button
        btn = page.findChild(QtWidgets.QPushButton, 'btnSaveGrades')
        if btn:
            btn.clicked.connect(self._save_tea_grades)
        # them nut "Cap nhat tu diem danh" canh nut Luu (1 lan)
        header = page.findChild(QtWidgets.QFrame, 'headerBar')
        if header and not header.findChild(QtWidgets.QPushButton, 'btnSyncAttend'):
            btn_sync = QtWidgets.QPushButton('↻ CC từ điểm danh', header)
            btn_sync.setObjectName('btnSyncAttend')
            btn_sync.setGeometry(560, 12, 145, 32)
            btn_sync.setCursor(Qt.PointingHandCursor)
            btn_sync.setToolTip('Tự động fill cột Chuyên cần = % điểm danh × 10')
            btn_sync.setStyleSheet(
                'QPushButton { background: white; color: #276749; border: 1px solid #276749; '
                'border-radius: 6px; font-size: 12px; font-weight: bold; } '
                'QPushButton:hover { background: #276749; color: white; }'
            )
            btn_sync.clicked.connect(lambda: self._sync_cc_from_attendance(tbl, cbo))
            btn_sync.show()
        # cbo chon lop -> load students cua lop do
        if cbo:
            cbo.currentIndexChanged.connect(lambda idx: self._tea_grades_render(tbl, cbo.currentText() if idx > 0 else None))

    def _sync_cc_from_attendance(self, tbl, cbo):
        """Fill cot Chuyen can (col 3) tu attendance_rate cua tung HV
        Cong thuc: CC = round(attendance_rate / 10, 1)  (= rate% / 10)
        - Lay theo MSV cot 1, fallback theo Ho ten neu MSV khong khop DB
        - Verbose log de debug"""
        if not (tbl and cbo):
            return
        ma_lop = cbo.currentText() if cbo.currentIndex() > 0 else None
        if not ma_lop:
            msg_info(self, 'Chưa chọn lớp', 'Chọn 1 lớp cụ thể trước khi đồng bộ điểm chuyên cần.')
            return
        if tbl.rowCount() == 0:
            msg_info(self, 'Bảng trống',
                     f'Lớp {ma_lop} chưa có học viên trong bảng điểm.\n'
                     'Hãy chọn lớp khác (có dữ liệu) hoặc nhập điểm trước khi đồng bộ.')
            return
        if not (DB_AVAILABLE and AttendanceService):
            msg_warn(self, 'Chưa kết nối được hệ thống',
                     'Tính năng này yêu cầu kết nối hệ thống điểm danh.\n'
                     'Vui lòng kiểm tra mạng và thử lại.')
            return

        # Lay 1 phat tat ca attendance_rate cua HV trong lop nay (tranh N+1 query)
        rates_by_msv = {}
        try:
            rows = db.fetch_all(
                """SELECT s.msv,
                          COUNT(*) FILTER (WHERE a.trang_thai IN ('present','late')) AS present_cnt,
                          COUNT(*) AS total
                     FROM students s
                     JOIN attendance a ON a.hv_id = s.user_id
                     JOIN schedules sc ON sc.id = a.schedule_id
                    WHERE sc.lop_id = %s
                 GROUP BY s.msv""",
                (ma_lop,)
            )
            for r in rows:
                if r['total']:
                    rates_by_msv[r['msv']] = round(r['present_cnt'] / r['total'] * 100, 1)
            print(f"[SYNC_CC] lop={ma_lop} - tim thay attendance cua {len(rates_by_msv)} HV")
        except Exception as e:
            print(f'[SYNC_CC] loi truy van batch: {e}')

        self._grades_recalc_lock = True
        n_filled = 0       # so HV duoc fill CC tu diem danh thuc te
        n_no_data = 0      # so HV chua co diem danh
        n_no_db = 0        # so HV khong tim thay trong DB
        n_total = tbl.rowCount()

        for r in range(n_total):
            it_msv = tbl.item(r, 1)
            it_cc = tbl.item(r, 3)
            if not (it_msv and it_cc): continue
            msv = it_msv.text().strip()
            if not msv: continue
            try:
                if msv in rates_by_msv:
                    rate = rates_by_msv[msv]
                    cc = round(rate / 10, 1)
                    it_cc.setText(f'{cc:.1f}')
                    n_filled += 1
                    print(f'[SYNC_CC] {msv}: rate={rate}% -> CC={cc}')
                else:
                    # check xem msv co trong DB khong
                    hv = db.fetch_one("SELECT user_id FROM students WHERE msv = %s", (msv,))
                    if hv:
                        n_no_data += 1
                        print(f'[SYNC_CC] {msv}: chua co diem danh nao')
                    else:
                        n_no_db += 1
                        print(f'[SYNC_CC] {msv}: khong co trong DB students (mock?)')
            except Exception as e:
                print(f'[SYNC_CC] {msv} exception: {e}')
        self._grades_recalc_lock = False

        # Bao cao chi tiet
        if n_filled > 0:
            extra = []
            if n_no_data: extra.append(f'{n_no_data} HV chưa có điểm danh')
            if n_no_db: extra.append(f'{n_no_db} HV không có trong DB')
            tail = '\n• ' + '\n• '.join(extra) if extra else ''
            msg_info(self, 'Đã đồng bộ',
                     f'Đã fill cột Chuyên cần cho <b>{n_filled}/{n_total}</b> học viên'
                     f' từ điểm danh thực tế.{tail}')
        else:
            # Khong co HV nao co diem danh -> giai thich ngan gon cho user
            reason = []
            if not rates_by_msv:
                reason.append(f'• Lớp {ma_lop} chưa có dữ liệu điểm danh.')
                reason.append('  → Vào trang "Điểm danh", chọn buổi học, mark trạng thái rồi lưu lại.')
            if n_no_db == n_total:
                reason.append(f'• Danh sách học viên có thể chưa được đồng bộ.')
                reason.append('  → Liên hệ quản trị viên để kiểm tra.')
            msg_info(self, 'Chưa cập nhật được Chuyên cần',
                     'Không có học viên nào được cập nhật. Lý do có thể:\n\n' +
                     ('\n'.join(reason) if reason else
                      '• Hệ thống điểm danh chưa có dữ liệu cho lớp này.\n'
                      '• Hãy điểm danh ít nhất 1 buổi rồi thử lại.'))

    def _tea_grades_render(self, tbl, ma_lop):
        """Render bang nhap diem theo lop. ma_lop=None = hien tat ca HV o moi lop
        Cot: STT | Ma HV | Ho ten | Chuyen can | QT | Thi | TK | XL | Thao tac"""
        grade_colors = {'A+': COLORS['green'], 'A': COLORS['green'],
                        'B+': COLORS['navy'], 'B': COLORS['navy'],
                        'C+': COLORS['orange'], 'C': COLORS['orange'],
                        'D': COLORS['red'], 'F': COLORS['red']}

        # helper - normalize 1 row ve dung 8 col (chen CC='' neu thieu)
        def _norm(stt, r, suffix=''):
            ten = r[2] + suffix
            if len(r) == 7:  # legacy: STT|MaHV|HoTen|QT|Thi|TK|XL
                return [str(stt), r[1], ten, '', r[3], r[4], r[5], r[6]]
            return [str(stt), r[1], ten, r[3], r[4], r[5], r[6], r[7]]

        if ma_lop and ma_lop in self._tea_grades_by_class:
            raw = self._tea_grades_by_class[ma_lop]
            data = [_norm(i, r) for i, r in enumerate(raw, start=1)]
        else:
            data = []
            stt = 1
            for lop, rows in self._tea_grades_by_class.items():
                for r in rows:
                    data.append(_norm(stt, r, suffix=f'  ({lop})'))
                    stt += 1

        self._grades_recalc_lock = True
        tbl.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, val in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter if c != 2 else Qt.AlignLeft | Qt.AlignVCenter)
                if c == 7 and val:
                    item.setForeground(QColor(grade_colors.get(val, COLORS['text_mid'])))
                    item.setFont(QFont('Segoe UI', 11, QFont.Bold))
                # cot CC (3), QT (4), Thi (5) cho edit truc tiep tren bang
                if c not in (3, 4, 5):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                tbl.setItem(r, c, item)
        # resize columns - them cot Chuyen can va day Thao tac sang phai
        tbl.setColumnCount(9)
        tbl.setHorizontalHeaderItem(3, QtWidgets.QTableWidgetItem('Chuyên cần'))
        tbl.setHorizontalHeaderItem(4, QtWidgets.QTableWidgetItem('Điểm QT'))
        tbl.setHorizontalHeaderItem(5, QtWidgets.QTableWidgetItem('Điểm thi'))
        tbl.setHorizontalHeaderItem(6, QtWidgets.QTableWidgetItem('Tổng kết'))
        tbl.setHorizontalHeaderItem(7, QtWidgets.QTableWidgetItem('Xếp loại'))
        tbl.setHorizontalHeaderItem(8, QtWidgets.QTableWidgetItem('Thao tác'))
        for c, cw in enumerate([36, 90, 165, 75, 70, 70, 70, 65, 95]):
            tbl.setColumnWidth(c, cw)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 46)
            # nut nhap diem (dialog dang)
            btn_enter = QtWidgets.QPushButton('Nhập điểm')
            btn_enter.setCursor(Qt.PointingHandCursor)
            btn_enter.setFixedSize(84, 28)
            btn_enter.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
            btn_enter.clicked.connect(lambda ch, rr=r: self._tea_grade_dialog(tbl, rr))
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0); hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(btn_enter)
            tbl.setCellWidget(r, 8, w)
        self._grades_recalc_lock = False

    def _tea_grade_dialog(self, tbl, row_idx):
        """Dialog nhap CC + QT + Thi cho 1 HV, tu dong tinh TK + xep loai
        TK = QT*0.3 + Thi*0.7 (chuyen can chi luu de tham khao)"""
        msv = tbl.item(row_idx, 1).text() if tbl.item(row_idx, 1) else ''
        hoten = tbl.item(row_idx, 2).text() if tbl.item(row_idx, 2) else ''
        cur_cc = tbl.item(row_idx, 3).text() if tbl.item(row_idx, 3) else ''
        cur_qt = tbl.item(row_idx, 4).text() if tbl.item(row_idx, 4) else ''
        cur_thi = tbl.item(row_idx, 5).text() if tbl.item(row_idx, 5) else ''

        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle(f'Nhập điểm - {msv}')
        dlg.setFixedSize(440, 410)
        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        lbl_hv = QtWidgets.QLabel(f'<b>{hoten}</b>  ({msv})')
        lbl_hv.setFont(QFont('Segoe UI', 13))
        lay.addWidget(lbl_hv)

        form = QtWidgets.QFormLayout()
        form.setSpacing(12)
        sp_cc = QtWidgets.QDoubleSpinBox()
        sp_cc.setRange(0, 10); sp_cc.setDecimals(1); sp_cc.setSingleStep(0.5)
        sp_cc.setValue(float(cur_cc) if cur_cc else 0)
        sp_qt = QtWidgets.QDoubleSpinBox()
        sp_qt.setRange(0, 10); sp_qt.setDecimals(2); sp_qt.setSingleStep(0.5)
        sp_qt.setValue(float(cur_qt) if cur_qt else 0)
        sp_thi = QtWidgets.QDoubleSpinBox()
        sp_thi.setRange(0, 10); sp_thi.setDecimals(2); sp_thi.setSingleStep(0.5)
        sp_thi.setValue(float(cur_thi) if cur_thi else 0)
        form.addRow('Chuyên cần (/10):', sp_cc)
        form.addRow('Điểm quá trình (30%):', sp_qt)
        form.addRow('Điểm thi (70%):', sp_thi)

        # preview tong ket + xep loai
        lbl_preview = QtWidgets.QLabel('')
        lbl_preview.setStyleSheet('background: #f7fafc; border: 1px solid #d2d6dc; border-radius: 6px; padding: 10px; font-size: 13px;')
        lbl_preview.setMinimumHeight(70)

        def update_preview():
            qt = sp_qt.value()
            thi = sp_thi.value()
            total = round(qt * 0.3 + thi * 0.7, 2)
            if total >= 9: letter = 'A+'
            elif total >= 8.5: letter = 'A'
            elif total >= 8: letter = 'B+'
            elif total >= 6.5: letter = 'B'
            elif total >= 5.5: letter = 'C+'
            elif total >= 5: letter = 'C'
            elif total >= 4: letter = 'D'
            else: letter = 'F'
            color = '#276749' if total >= 7 else '#c05621' if total >= 5 else '#c53030'
            lbl_preview.setText(
                f'<b>Tổng kết:</b> <span style="color:{color}; font-size:18px;">{total}</span> &nbsp;·&nbsp; '
                f'<b>Xếp loại:</b> <span style="color:{color}; font-size:18px;">{letter}</span>'
            )

        sp_qt.valueChanged.connect(update_preview)
        sp_thi.valueChanged.connect(update_preview)
        update_preview()
        form.addRow(lbl_preview)
        lay.addLayout(form)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        # cap nhat table
        self._grades_recalc_lock = True
        qt_val = sp_qt.value()
        thi_val = sp_thi.value()
        total = round(qt_val * 0.3 + thi_val * 0.7, 2)
        if total >= 9: letter = 'A+'
        elif total >= 8.5: letter = 'A'
        elif total >= 8: letter = 'B+'
        elif total >= 6.5: letter = 'B'
        elif total >= 5.5: letter = 'C+'
        elif total >= 5: letter = 'C'
        elif total >= 4: letter = 'D'
        else: letter = 'F'

        grade_colors = {'A+': COLORS['green'], 'A': COLORS['green'],
                        'B+': COLORS['navy'], 'B': COLORS['navy'],
                        'C+': COLORS['orange'], 'C': COLORS['orange'],
                        'D': COLORS['red'], 'F': COLORS['red']}

        cc_val = sp_cc.value()
        tbl.item(row_idx, 3).setText(f'{cc_val:.1f}' if cc_val > 0 else '')
        tbl.item(row_idx, 4).setText(f'{qt_val:.1f}')
        tbl.item(row_idx, 5).setText(f'{thi_val:.1f}')
        it_tk = QtWidgets.QTableWidgetItem(f'{total:.1f}')
        it_tk.setTextAlignment(Qt.AlignCenter)
        it_tk.setFlags(it_tk.flags() & ~Qt.ItemIsEditable)
        tbl.setItem(row_idx, 6, it_tk)
        it_xl = QtWidgets.QTableWidgetItem(letter)
        it_xl.setTextAlignment(Qt.AlignCenter)
        it_xl.setFont(QFont('Segoe UI', 11, QFont.Bold))
        it_xl.setForeground(QColor(grade_colors.get(letter, COLORS['text_mid'])))
        it_xl.setFlags(it_xl.flags() & ~Qt.ItemIsEditable)
        tbl.setItem(row_idx, 7, it_xl)
        self._grades_recalc_lock = False
        msg_info(self, 'Đã cập nhật', f'Điểm của {tbl.item(row_idx,2).text()}: {total} ({letter})')

    def _recalc_grade_row(self, item):
        """Tinh lai TK + XL khi nguoi dung sua CC (3) / QT (4) / Thi (5)
        Cong thuc: TK = QT*0.3 + Thi*0.7 (CC chi luu de tham khao)"""
        if getattr(self, '_grades_recalc_lock', False):
            return
        c = item.column()
        if c not in (3, 4, 5):
            return
        page = self.page_widgets[6]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblTeacherGrades')
        if not tbl:
            return
        r = item.row()
        try:
            qt = float(tbl.item(r, 4).text().replace(',', '.')) if tbl.item(r, 4) else 0
            thi = float(tbl.item(r, 5).text().replace(',', '.')) if tbl.item(r, 5) else 0
        except Exception:
            return
        total = round(qt * 0.3 + thi * 0.7, 2)
        if total >= 9: letter = 'A+'
        elif total >= 8.5: letter = 'A'
        elif total >= 8: letter = 'B+'
        elif total >= 6.5: letter = 'B'
        elif total >= 5.5: letter = 'C+'
        elif total >= 5: letter = 'C'
        elif total >= 4: letter = 'D'
        else: letter = 'F'
        self._grades_recalc_lock = True
        it_tot = QtWidgets.QTableWidgetItem(f'{total:.1f}')
        it_tot.setTextAlignment(Qt.AlignCenter)
        it_tot.setFlags(it_tot.flags() & ~Qt.ItemIsEditable)
        tbl.setItem(r, 6, it_tot)
        grade_colors = {'A+': COLORS['green'], 'A': COLORS['green'], 'B+': COLORS['navy'], 'B': COLORS['navy'],
                        'C+': COLORS['orange'], 'C': COLORS['orange'], 'D': COLORS['red'], 'F': COLORS['red']}
        it_let = QtWidgets.QTableWidgetItem(letter)
        it_let.setTextAlignment(Qt.AlignCenter)
        it_let.setForeground(QColor(grade_colors.get(letter, COLORS['text_mid'])))
        it_let.setFlags(it_let.flags() & ~Qt.ItemIsEditable)
        tbl.setItem(r, 7, it_let)
        self._grades_recalc_lock = False

    def _save_tea_grades(self):
        if not msg_confirm(self, 'Lưu điểm', 'Xác nhận lưu điểm cho tất cả học viên trong bảng?'):
            return
        # Neu co DB va biet lop, ghi that
        saved = 0
        if DB_AVAILABLE:
            page = self.page_widgets[6]
            tbl = page.findChild(QtWidgets.QTableWidget, 'tblTeacherGrades')
            cbo = page.findChild(QtWidgets.QComboBox, 'cboGradeClass')
            gv_user_id = MOCK_TEACHER.get('user_id')
            lop_id = cbo.currentText() if cbo and cbo.currentIndex() > 0 else None
            if tbl and lop_id and gv_user_id:
                # cot moi: STT|MaHV|HoTen|CC(3)|QT(4)|Thi(5)|TK|XL|Action
                for r in range(tbl.rowCount()):
                    try:
                        msv = tbl.item(r, 1).text()
                        qt = float(tbl.item(r, 4).text().replace(',', '.'))
                        thi = float(tbl.item(r, 5).text().replace(',', '.'))
                        hv = db.fetch_one("SELECT user_id FROM students WHERE msv = %s", (msv,))
                        if hv:
                            GradeService.save_grade(hv['user_id'], lop_id, qt, thi, gv_user_id)
                            saved += 1
                    except Exception as e:
                        print(f'[GRADE] loi dong {r}: {e}')
        if saved:
            msg_info(self, 'Thành công', f'Đã lưu điểm cho {saved} học viên.')
        else:
            msg_warn(self, 'Không lưu được',
                     'Không kết nối được hệ thống. Vui lòng kiểm tra mạng và thử lại.')

    def _fill_tea_profile(self):
        page = self.page_widgets[7]
        u = MOCK_TEACHER
        for attr, val in [('lblProfileName', u['name']), ('lblProfileRole', f"Giảng viên - Khoa {u['khoa']}"),
                          ('lblProfileAvatar', u['initials']), ('valMaSV', u['id']), ('valHoTen', u['name']),
                          ('valLop', u['hocvi']), ('valKhoa', u['khoa'])]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setText(val)
        for attr, val in [('txtEmail', u['email']), ('txtPhone', u['sdt'])]:
            w = page.findChild(QtWidgets.QLineEdit, attr)
            if w:
                w.setText(val)

        btn_save = page.findChild(QtWidgets.QPushButton, 'btnSave')
        if btn_save:
            btn_save.clicked.connect(lambda: (
                MOCK_TEACHER.__setitem__('email', page.findChild(QtWidgets.QLineEdit, 'txtEmail').text().strip()),
                MOCK_TEACHER.__setitem__('sdt', page.findChild(QtWidgets.QLineEdit, 'txtPhone').text().strip()),
                msg_info(self, 'Thành công', 'Đã lưu thông tin.')
            ))
        btn_cp = page.findChild(QtWidgets.QPushButton, 'btnChangePass')
        if btn_cp:
            btn_cp.clicked.connect(lambda: self._tea_change_pass())

    def _tea_change_pass(self):
        new = msg_input(self, 'Đổi mật khẩu', 'Nhập mật khẩu mới:')
        if new:
            MOCK_TEACHER['password'] = new
            msg_info(self, 'Thành công', 'Đổi mật khẩu thành công.')


class EmployeeWindow(QtWidgets.QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.setObjectName('MainWindow')
        self.setWindowTitle('EAUT - Hệ thống nhân viên')
        self.setMinimumSize(1100, 700)
        self.resize(1100, 700)
        self.setWindowIcon(QIcon(os.path.join(RES, 'logo.png')))
        # luu ma DK da thanh toan de sync giua 2 bang
        self._paid_dks = set()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        layout.addWidget(self.sidebar)

        self.stack = QtWidgets.QStackedWidget()
        layout.addWidget(self.stack)

        self.page_widgets = []
        self.pages_filled = [False] * len(EMPLOYEE_PAGES)
        for btn_name, ui_file in EMPLOYEE_PAGES:
            page = self._load_page(ui_file)
            self.page_widgets.append(page)
            self.stack.addWidget(page)

        self._switch_page(0)
        self._fill_emp_dashboard()
        self.pages_filled[0] = True

    def _build_sidebar(self):
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet('QFrame#sidebar { background: #ffffff; border-right: 1px solid #d2d6dc; }')

        lbl_logo = QtWidgets.QLabel(sidebar)
        lbl_logo.setGeometry(20, 20, 42, 42)
        lbl_logo.setScaledContents(True)
        logo_path = os.path.join(RES, 'logo.png')
        if os.path.exists(logo_path):
            lbl_logo.setPixmap(QPixmap(logo_path).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        lbl_school = QtWidgets.QLabel('EAUT', sidebar)
        lbl_school.setGeometry(68, 20, 150, 20)
        lbl_school.setStyleSheet(f'color: {COLORS["navy"]}; font-size: 13px; font-weight: bold; background: transparent;')
        lbl_sub = QtWidgets.QLabel('Nhân viên', sidebar)
        lbl_sub.setGeometry(68, 40, 120, 16)
        lbl_sub.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 11px; background: transparent;')
        add_maximize_button(sidebar, self)

        sep = QtWidgets.QFrame(sidebar)
        sep.setGeometry(15, 74, 200, 1)
        sep.setStyleSheet(f'background: {COLORS["border"]};')

        y = 86
        for btn_name, icon_name, icon_file, label in EMPLOYEE_MENU:
            btn = QtWidgets.QPushButton(label, sidebar)
            btn.setObjectName(btn_name)
            btn.setGeometry(10, y, 210, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(SIDEBAR_NORMAL)
            setattr(self, btn_name, btn)

            icon_lbl = QtWidgets.QLabel(sidebar)
            icon_lbl.setObjectName(icon_name)
            icon_lbl.setGeometry(20, y + 9, 16, 16)
            icon_lbl.setScaledContents(True)
            icon_lbl.setStyleSheet('background: transparent;')
            icon_path = os.path.join(ICONS, f'{icon_file}.png')
            if os.path.exists(icon_path):
                icon_lbl.setPixmap(QPixmap(icon_path).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            setattr(self, icon_name, icon_lbl)
            y += 38

        for i, (btn_name, _) in enumerate(EMPLOYEE_PAGES):
            btn = getattr(self, btn_name)
            btn.clicked.connect(lambda checked, idx=i: self._on_nav(idx))

        sep2 = QtWidgets.QFrame(sidebar)
        sep2.setGeometry(15, 610, 200, 1)
        sep2.setStyleSheet(f'background: {COLORS["border"]};')

        lbl_av = QtWidgets.QLabel(MOCK_EMPLOYEE['initials'], sidebar)
        lbl_av.setGeometry(15, 625, 38, 38)
        lbl_av.setAlignment(Qt.AlignCenter)
        lbl_av.setStyleSheet(f'background: {COLORS["active_bg"]}; border-radius: 19px; color: {COLORS["navy"]}; font-size: 13px; font-weight: bold;')

        lbl_name = QtWidgets.QLabel(MOCK_EMPLOYEE['name'], sidebar)
        lbl_name.setGeometry(60, 626, 130, 17)
        lbl_name.setStyleSheet(f'color: {COLORS["text_dark"]}; font-size: 12px; font-weight: bold; background: transparent;')
        lbl_role = QtWidgets.QLabel('Nhân viên', sidebar)
        lbl_role.setGeometry(60, 644, 110, 15)
        lbl_role.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 10px; background: transparent;')

        icon_lo = QtWidgets.QLabel(sidebar)
        icon_lo.setGeometry(191, 635, 18, 18)
        icon_lo.setScaledContents(True)
        icon_lo.setStyleSheet('background: transparent;')
        lo_path = os.path.join(ICONS, 'log-out.png')
        if os.path.exists(lo_path):
            icon_lo.setPixmap(QPixmap(lo_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        btn_lo = QtWidgets.QPushButton(sidebar)
        btn_lo.setGeometry(183, 627, 34, 34)
        btn_lo.setCursor(Qt.PointingHandCursor)
        btn_lo.setToolTip('Đăng xuất')
        btn_lo.setStyleSheet('QPushButton { background: transparent; border: none; } QPushButton:hover { background: #fce8e6; border-radius: 8px; }')
        btn_lo.clicked.connect(self._on_logout)

        return sidebar

    def _load_page(self, ui_file):
        temp = uic.loadUi(os.path.join(UI, ui_file))
        content = temp.findChild(QtWidgets.QFrame, 'contentArea')
        if content:
            content.setParent(None)
            content.setFixedSize(870, 700)
            return content
        return temp

    def _on_nav(self, index):
        self._switch_page(index)
        if not self.pages_filled[index]:
            fill = [self._fill_emp_dashboard, self._fill_emp_register,
                    self._fill_emp_reglist, self._fill_emp_payment,
                    self._fill_emp_classes, self._fill_emp_profile]
            fill[index]()
            self.pages_filled[index] = True

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
        active = EMPLOYEE_PAGES[index][0]
        for btn_name, _ in EMPLOYEE_PAGES:
            btn = getattr(self, btn_name)
            icon = getattr(self, btn_name.replace('btn', 'icon'))
            if btn_name == active:
                btn.setStyleSheet(SIDEBAR_ACTIVE)
                icon.raise_()
            else:
                btn.setStyleSheet(SIDEBAR_NORMAL)

    def _on_logout(self):
        self.close()
        self.app_ref.show_login()

    # === EMPLOYEE DATA FILL ===

    def _fill_emp_dashboard(self):
        page = self.page_widgets[0]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblPending')
        if tbl:
            data = [
                ('Đào Viết Quang Huy', 'IT001-A', 'Chờ thanh toán'),
                ('Trần Thị Bích', 'IT002-A', 'Chờ thanh toán'),
                ('Lê Văn Cường', 'IT004-B', 'Chờ thanh toán'),
            ]
            tbl.setRowCount(len(data))
            for r, (n, cls, st) in enumerate(data):
                tbl.setItem(r, 0, QtWidgets.QTableWidgetItem(n))
                item_cls = QtWidgets.QTableWidgetItem(cls)
                item_cls.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(r, 1, item_cls)
                item_st = QtWidgets.QTableWidgetItem(st)
                item_st.setForeground(QColor(COLORS['orange']))
                item_st.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(r, 2, item_st)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setColumnWidth(0, 150)
            tbl.setColumnWidth(1, 90)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 38)

        tbl2 = page.findChild(QtWidgets.QTableWidget, 'tblActivityEmp')
        if tbl2:
            data = [
                ('10:30 hôm nay', 'Đăng ký mới: Đào Viết Quang Huy - IT001-A'),
                ('10:15 hôm nay', 'Thu học phí: Hoàng Văn Em - 2.500.000đ'),
                ('09:45 hôm nay', 'Đăng ký mới: Trần Thị Bích - IT002-A'),
                ('09:20 hôm nay', 'Thu học phí: Nguyễn Thanh Giang - 1.800.000đ'),
                ('08:50 hôm nay', 'Đăng ký mới: Vũ Thị Phương - IT004-A'),
            ]
            tbl2.setRowCount(len(data))
            for r, (t, c) in enumerate(data):
                ti = QtWidgets.QTableWidgetItem(t)
                ti.setForeground(QColor(COLORS['text_light']))
                ti.setFont(QFont('Segoe UI', 9))
                tbl2.setItem(r, 0, ti)
                tbl2.setItem(r, 1, QtWidgets.QTableWidgetItem(c))
            tbl2.horizontalHeader().setStretchLastSection(True)
            tbl2.setColumnWidth(0, 110)
            tbl2.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl2.setRowHeight(r, 38)

    def _fill_emp_register(self):
        page = self.page_widgets[1]
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboCourse')
        if cbo_c:
            cbo_c.clear()
            cbo_c.addItem('-- Chọn môn học --')
            for code, name in MOCK_COURSES:
                cbo_c.addItem(f'{code} - {name}')
            cbo_c.currentIndexChanged.connect(self._emp_filter_classes)
        cbo_cls = page.findChild(QtWidgets.QComboBox, 'cboClassEmp')
        if cbo_cls:
            cbo_cls.clear()
            cbo_cls.addItem('-- Chọn lớp --')
            for cls in MOCK_CLASSES:
                cbo_cls.addItem(f'{cls[0]} — {cls[3]} ({cls[8]:,}đ)'.replace(',', '.'))

        # buttons
        btn_lk = page.findChild(QtWidgets.QPushButton, 'btnLookup')
        if btn_lk:
            btn_lk.clicked.connect(self._emp_lookup_student)
        btn_rg = page.findChild(QtWidgets.QPushButton, 'btnConfirmReg')
        if btn_rg:
            btn_rg.clicked.connect(self._emp_do_register)
        btn_rs = page.findChild(QtWidgets.QPushButton, 'btnResetReg')
        if btn_rs:
            btn_rs.clicked.connect(self._emp_reset_form)

    def _emp_filter_classes(self, idx):
        page = self.page_widgets[1]
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboCourse')
        cbo_cls = page.findChild(QtWidgets.QComboBox, 'cboClassEmp')
        if not cbo_c or not cbo_cls:
            return
        cbo_cls.clear()
        cbo_cls.addItem('-- Chọn lớp --')
        if idx == 0:
            for cls in MOCK_CLASSES:
                cbo_cls.addItem(f'{cls[0]} — {cls[3]} ({cls[8]:,}đ)'.replace(',', '.'))
            return
        mon_code = MOCK_COURSES[idx - 1][0]
        for cls in MOCK_CLASSES:
            if cls[1] == mon_code:
                cbo_cls.addItem(f'{cls[0]} — {cls[3]} ({cls[8]:,}đ)'.replace(',', '.'))

    def _emp_lookup_student(self):
        page = self.page_widgets[1]
        txt_msv = page.findChild(QtWidgets.QLineEdit, 'txtMSV')
        if not txt_msv or not txt_msv.text().strip():
            msg_warn(self, 'Thiếu MSV', 'Hãy nhập MSV để tra cứu')
            return
        msv = txt_msv.text().strip().upper()
        ten = email = sdt = None
        # tra cuu qua API
        if DB_AVAILABLE:
            try:
                hv = StudentService.get_by_msv(msv)
                if hv:
                    ten = hv.get('full_name') or hv.get('ten') or ''
                    email = hv.get('email') or ''
                    sdt = hv.get('sdt') or ''
            except Exception as e:
                print(f'[EMP_LOOKUP] loi: {e}')
        if not ten:
            msg_warn(self, 'Không tìm thấy', f'Không tìm thấy học viên với MSV: {msv}')
            return
        for attr, val in [('txtHoTen', ten), ('txtEmail', email or ''), ('txtSDT', sdt or '')]:
            w = page.findChild(QtWidgets.QLineEdit, attr)
            if w:
                w.setText(val)
        msg_info(self, 'Tra cứu', f'Đã tìm thấy: {ten}')

    def _emp_do_register(self):
        page = self.page_widgets[1]
        msv = page.findChild(QtWidgets.QLineEdit, 'txtMSV')
        hoten = page.findChild(QtWidgets.QLineEdit, 'txtHoTen')
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboCourse')
        cbo_cls = page.findChild(QtWidgets.QComboBox, 'cboClassEmp')
        if not msv or not msv.text().strip():
            msg_warn(self, 'Thiếu', 'Hãy nhập MSV')
            return
        if not hoten or not hoten.text().strip():
            msg_warn(self, 'Thiếu', 'Hãy nhập họ tên')
            return
        if cbo_c.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn môn học')
            return
        if cbo_cls.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn lớp')
            return
        # === CHECK MON TIEN QUYET tu khung CT ===
        lop_code = cbo_cls.currentText().split()[0]
        ma_mon_lop = MOCK_COURSES[cbo_c.currentIndex() - 1][0] if cbo_c.currentIndex() > 0 else None
        if DB_AVAILABLE and CurriculumService:
            try:
                hv_row = db.fetch_one(
                    "SELECT user_id FROM students WHERE msv = %s", (msv.text().strip(),)
                )
                if hv_row and ma_mon_lop:
                    check = CurriculumService.check_prerequisites_for_student(
                        hv_row['user_id'], ma_mon_lop)
                    if not check['ok']:
                        warn_msg = (
                            f'<b>Học viên chưa đủ điều kiện học môn {ma_mon_lop}!</b><br><br>'
                            f'Theo khung chương trình, cần hoàn thành các môn tiên quyết:<br>'
                            f'<span style="color:red;">• {", ".join(check["missing"])}</span><br><br>'
                            f'Vẫn tiếp tục đăng ký?'
                        )
                        box = QtWidgets.QMessageBox(self)
                        box.setIcon(QtWidgets.QMessageBox.Warning)
                        box.setWindowTitle('Cảnh báo môn tiên quyết')
                        box.setTextFormat(Qt.RichText)
                        box.setText(warn_msg)
                        box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                        box.button(QtWidgets.QMessageBox.Yes).setText('Tiếp tục')
                        box.button(QtWidgets.QMessageBox.No).setText('Hủy')
                        box.setDefaultButton(QtWidgets.QMessageBox.No)
                        _style_msgbox(box)
                        if box.exec_() != QtWidgets.QMessageBox.Yes:
                            return
            except Exception as e:
                print(f'[REG] check prereq loi: {e}')

        if not msg_confirm(self, 'Xác nhận', f'Đăng ký {hoten.text()} vào lớp {cbo_cls.currentText()}?'):
            return
        # ghi DB
        saved_id = None
        if DB_AVAILABLE:
            try:
                hv_row = db.fetch_one(
                    "SELECT user_id FROM students WHERE msv = %s", (msv.text().strip(),)
                )
                nv_id = MOCK_EMPLOYEE.get('user_id')
                if hv_row and nv_id:
                    saved_id = RegistrationService.register_student(
                        hv_row['user_id'], lop_code, nv_id
                    )
            except Exception as e:
                print(f'[REG] loi: {e}')
        if saved_id:
            msg_info(self, 'Thành công', f'Đã đăng ký cho {hoten.text()} - Mã đăng ký #{saved_id}')
        else:
            msg_info(self, 'Thành công', f'Đã đăng ký thành công cho {hoten.text()}')
        self._emp_reset_form()

    def _emp_reset_form(self):
        page = self.page_widgets[1]
        for nm in ('txtMSV', 'txtHoTen', 'txtEmail', 'txtSDT'):
            w = page.findChild(QtWidgets.QLineEdit, nm)
            if w: w.clear()
        for nm in ('cboCourse', 'cboClassEmp'):
            w = page.findChild(QtWidgets.QComboBox, nm)
            if w: w.setCurrentIndex(0)

    def _fill_emp_reglist(self):
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblRegistrations')
        if not tbl:
            return
        # tu DB neu co
        data = None
        if DB_AVAILABLE:
            try:
                rows = RegistrationService.get_all_registrations(limit=50)
                status_map = {
                    'pending_payment': 'Chờ thanh toán',
                    'paid': 'Đã thanh toán',
                    'cancelled': 'Đã hủy',
                    'completed': 'Hoàn thành',
                }
                data = []
                for r in rows:
                    st_vn = status_map.get(r['trang_thai'], r['trang_thai'])
                    ngay = fmt_date(r.get('ngay_dk'))
                    gia = f'{int(r.get("gia", 0)):,}'.replace(',', '.')
                    data.append([f'DK{r["id"]:03d}', ngay, r['ten_hv'],
                                 r['lop_id'], gia, st_vn])
            except Exception as e:
                print(f'[EMP_REG] DB loi: {e}')
        if not data:
            data = [
                ['DK001', '18/04/2026', 'Đào Viết Quang Huy', 'IT001-A', '2.500.000', 'Chờ thanh toán'],
                ['DK002', '18/04/2026', 'Trần Thị Bích', 'IT002-A', '2.200.000', 'Chờ thanh toán'],
                ['DK003', '18/04/2026', 'Hoàng Văn Em', 'IT001-B', '1.800.000', 'Đã thanh toán'],
                ['DK004', '17/04/2026', 'Nguyễn Thanh Giang', 'IT001-B', '1.800.000', 'Đã thanh toán'],
                ['DK005', '17/04/2026', 'Vũ Thị Phương', 'IT004-A', '2.800.000', 'Đã thanh toán'],
                ['DK006', '17/04/2026', 'Phạm Thị Dung', 'MA001-A', '1.500.000', 'Đã thanh toán'],
                ['DK007', '16/04/2026', 'Lê Văn Cường', 'IT004-B', '2.200.000', 'Chờ thanh toán'],
                ['DK008', '16/04/2026', 'Bùi Thị Hồng', 'IT001-C', '2.000.000', 'Đã thanh toán'],
                ['DK009', '15/04/2026', 'Đinh Văn Khánh', 'IT001-A', '2.500.000', 'Đã thanh toán'],
                ['DK010', '15/04/2026', 'Lâm Thị Nga', 'IT002-B', '1.800.000', 'Đã hủy'],
            ]
        tbl.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, val in enumerate(row[:5]):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c in (0, 1, 3) else
                                       Qt.AlignRight | Qt.AlignVCenter if c == 4 else
                                       Qt.AlignLeft | Qt.AlignVCenter)
                tbl.setItem(r, c, item)
            # trang thai - uu tien paid_dks de sync giua 2 trang
            st = 'Đã thanh toán' if row[0] in self._paid_dks else row[5]
            item_st = QtWidgets.QTableWidgetItem(st)
            item_st.setTextAlignment(Qt.AlignCenter)
            color = COLORS['green'] if st == 'Đã thanh toán' else COLORS['orange'] if st == 'Chờ thanh toán' else COLORS['red']
            item_st.setForeground(QColor(color))
            tbl.setItem(r, 5, item_st)
            # action - nut nho hon de khong tran row
            btn = QtWidgets.QPushButton('Xem')
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(54, 22)
            btn.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 3px; font-size: 10px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
            btn.clicked.connect(lambda ch, rdata=row: show_detail_dialog(
                self, 'Chi tiết đăng ký',
                [('Mã đăng ký', rdata[0]), ('Ngày đăng ký', rdata[1]),
                 ('Học viên', rdata[2]), ('Lớp', rdata[3]),
                 ('Học phí', f'{rdata[4]} đ'), ('Trạng thái', rdata[5])],
                avatar_text='DK', subtitle=rdata[2]))
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(btn)
            tbl.setCellWidget(r, 6, w)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([70, 95, 195, 90, 110, 125, 70]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 36)

        widen_search(page, 'txtSearchReg', 300, ['cboRegStatus', 'cboRegDate'])
        # search + filter + export
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchReg')
        if txt:
            txt.textChanged.connect(lambda t: table_filter(tbl, t, cols=[0, 2, 3]))
        cbo_st = page.findChild(QtWidgets.QComboBox, 'cboRegStatus')
        if cbo_st:
            cbo_st.clear()
            cbo_st.addItems(['Tất cả trạng thái', 'Đã thanh toán', 'Chờ thanh toán', 'Đã hủy'])
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboRegDate')
        if cbo_d:
            cbo_d.clear()
            cbo_d.addItems(['Tất cả thời gian', 'Hôm nay (18/04)', '7 ngày qua', '30 ngày qua'])
        for nm in ('cboRegStatus', 'cboRegDate'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda idx, n=nm: self._emp_filter_reg(n))
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportReg')
        if btn_exp:
            btn_exp.clicked.connect(lambda: export_table_csv(self, tbl, 'danh_sach_dang_ky.csv', 'Xuất danh sách đăng ký'))

    def _emp_filter_reg(self, which):
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblRegistrations')
        cbo_st = page.findChild(QtWidgets.QComboBox, 'cboRegStatus')
        if not tbl or not cbo_st:
            return
        st_text = cbo_st.currentText()
        for r in range(tbl.rowCount()):
            it = tbl.item(r, 5)
            show = True
            if cbo_st.currentIndex() > 0 and it:
                show = st_text.lower() in it.text().lower()
            tbl.setRowHidden(r, not show)

    def _fill_emp_payment(self):
        page = self.page_widgets[3]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblPayPending')
        if not tbl:
            return
        # lay tu DB
        data = None
        if DB_AVAILABLE:
            try:
                rows = RegistrationService.get_pending_payments()
                # dung format DK### giong reg list - de match khi sync
                data = [[f'DK{r["id"]:03d}', r['ten_hv'], r['lop_id'],
                         f'{int(r["gia"]):,}'.replace(',', '.')] for r in rows]
            except Exception as e:
                print(f'[EMP_PAY] DB loi: {e}')
        if not data:
            data = [
                ['DK001', 'Đào Viết Quang Huy', 'IT001-A', '2.500.000'],
                ['DK002', 'Trần Thị Bích', 'IT002-A', '2.200.000'],
                ['DK007', 'Lê Văn Cường', 'IT004-B', '2.200.000'],
                ['DK011', 'Phạm Minh Hòa', 'IT003-A', '2.000.000'],
                ['DK012', 'Ngô Thị Kim', 'MA001-B', '1.200.000'],
            ]
        tbl.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, val in enumerate(row):
                item = QtWidgets.QTableWidgetItem(val)
                if c == 0 or c == 2:
                    item.setTextAlignment(Qt.AlignCenter)
                elif c == 3:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setForeground(QColor(COLORS['gold']))
                tbl.setItem(r, c, item)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([70, 170, 90, 110]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 40)
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # buttons
        btn_p = page.findChild(QtWidgets.QPushButton, 'btnConfirmPay')
        if btn_p:
            btn_p.clicked.connect(lambda: self._emp_confirm_pay(tbl))
        btn_r = page.findChild(QtWidgets.QPushButton, 'btnPrintReceipt')
        if btn_r:
            btn_r.clicked.connect(lambda: self._emp_print_receipt(tbl))
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchPay')
        if txt:
            txt.textChanged.connect(lambda t: table_filter(tbl, t, cols=[0, 1]))

    def _emp_confirm_pay(self, tbl):
        rows = tbl.selectionModel().selectedRows() if tbl else []
        if not rows:
            msg_warn(self, 'Chưa chọn', 'Hãy chọn 1 dòng đăng ký cần xác nhận')
            return
        page = self.page_widgets[3]
        cbo = page.findChild(QtWidgets.QComboBox, 'cboPayMethod')
        note = page.findChild(QtWidgets.QLineEdit, 'txtPayNote')
        method = cbo.currentText() if cbo else ''
        r = rows[0].row()
        ma = tbl.item(r, 0).text() if tbl.item(r, 0) else '?'
        ten = tbl.item(r, 1).text() if tbl.item(r, 1) else '?'
        lop = tbl.item(r, 2).text() if tbl.item(r, 2) else '?'
        gia = tbl.item(r, 3).text() if tbl.item(r, 3) else '?'
        if not msg_confirm(self, 'Xác nhận thu tiền', f'Thu {gia} đ từ {ten} ({ma}) - {method}?'):
            return
        ghi_chu = note.text().strip() if note else ''
        # parse ma_dk: "DK001" → 1, "1" → 1
        ma_digits = ''.join(ch for ch in ma if ch.isdigit())
        # ghi DB truoc
        if DB_AVAILABLE and ma_digits:
            try:
                nv_id = MOCK_EMPLOYEE.get('user_id')
                so_tien = int(gia.replace('.', '').replace(',', '').replace('đ', '').strip())
                RegistrationService.confirm_payment(int(ma_digits), so_tien, method, nv_id, ghi_chu)
                print(f'[PAY] da ghi DB: {ma}, {so_tien}đ')
            except Exception as e:
                print(f'[PAY] loi: {e}')
        tbl.removeRow(r)
        if note: note.clear()
        # cap nhat trang thai ben bang ds dang ky
        self._emp_sync_reg_paid(ma)
        self._emp_show_receipt(ma, ten, lop, gia, method, ghi_chu)

    def _emp_sync_reg_paid(self, ma_dk):
        """doi trang thai dong co ma_dk sang 'Da thanh toan' ben bang Registrations"""
        self._paid_dks.add(ma_dk)
        reg_page = self.page_widgets[2]
        reg_tbl = reg_page.findChild(QtWidgets.QTableWidget, 'tblRegistrations')
        if not reg_tbl:
            return
        for r in range(reg_tbl.rowCount()):
            it_ma = reg_tbl.item(r, 0)
            if it_ma and it_ma.text() == ma_dk:
                new_st = QtWidgets.QTableWidgetItem('Đã thanh toán')
                new_st.setTextAlignment(Qt.AlignCenter)
                new_st.setForeground(QColor(COLORS['green']))
                reg_tbl.setItem(r, 5, new_st)
                break

    def _emp_show_receipt(self, ma, ten, lop, gia, method, ghi_chu):
        """hien dialog bien lai thu hoc phi"""
        import datetime
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Biên lai thu học phí')
        dlg.setFixedSize(420, 520)
        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)

        header = QtWidgets.QLabel('TRUNG TÂM NGOẠI KHÓA EAUT')
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(f'color: {COLORS["navy"]}; font-size: 14px; font-weight: bold;')
        lay.addWidget(header)

        addr = QtWidgets.QLabel('Km 23, QL5, Trưng Trắc, Văn Lâm, Hưng Yên\nHotline: 024.3999.1111')
        addr.setAlignment(Qt.AlignCenter)
        addr.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 10px;')
        lay.addWidget(addr)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet(f'color: {COLORS["border"]};')
        lay.addWidget(line)

        title = QtWidgets.QLabel('BIÊN LAI THU TIỀN')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f'color: {COLORS["text_dark"]}; font-size: 16px; font-weight: bold; padding: 8px;')
        lay.addWidget(title)

        now = datetime.datetime.now()
        receipt_no = f'BL{now.strftime("%Y%m%d%H%M%S")}'
        form = QtWidgets.QFormLayout()
        form.setSpacing(8)
        for label, val in [
            ('Số biên lai:', receipt_no),
            ('Ngày thu:', now.strftime('%d/%m/%Y %H:%M')),
            ('Mã đăng ký:', ma),
            ('Học viên:', ten),
            ('Lớp:', lop),
            ('Số tiền:', f'{gia} đ'),
            ('Hình thức:', method),
            ('Ghi chú:', ghi_chu or '(không)'),
            ('Nhân viên thu:', MOCK_EMPLOYEE['name']),
        ]:
            lbl = QtWidgets.QLabel(label)
            lbl.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 11px;')
            val_lbl = QtWidgets.QLabel(val)
            val_lbl.setStyleSheet(f'color: {COLORS["text_dark"]}; font-size: 12px; font-weight: bold;')
            form.addRow(lbl, val_lbl)
        lay.addLayout(form)

        thanks = QtWidgets.QLabel('--- Cảm ơn quý học viên ---')
        thanks.setAlignment(Qt.AlignCenter)
        thanks.setStyleSheet(f'color: {COLORS["text_light"]}; font-size: 10px; font-style: italic; padding: 10px;')
        lay.addWidget(thanks)

        btns = QtWidgets.QHBoxLayout()
        btn_save = QtWidgets.QPushButton('Lưu biên lai (.txt)')
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; padding: 8px 12px; border-radius: 4px; font-weight: bold; }}')
        btn_save.clicked.connect(lambda: self._emp_save_receipt_file(receipt_no, ma, ten, lop, gia, method, ghi_chu, now))
        btn_close = QtWidgets.QPushButton('Đóng')
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet('QPushButton { background: #edf2f7; color: #4a5568; border: 1px solid #d2d6dc; padding: 8px 12px; border-radius: 4px; }')
        btn_close.clicked.connect(dlg.accept)
        btns.addWidget(btn_save)
        btns.addWidget(btn_close)
        lay.addLayout(btns)

        dlg.exec_()

    def _emp_save_receipt_file(self, receipt_no, ma, ten, lop, gia, method, ghi_chu, dt):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Lưu biên lai',
            os.path.join(os.path.expanduser('~'), 'Desktop', f'{receipt_no}.txt'),
            'Text (*.txt)'
        )
        if not path:
            return
        content = (
            'TRUNG TAM NGOAI KHOA EAUT\n'
            'Km 23, QL5, Trung Trac, Van Lam, Hung Yen\n'
            'Hotline: 024.3999.1111\n'
            '--------------------------------------\n'
            'BIEN LAI THU TIEN\n'
            '--------------------------------------\n'
            f'So bien lai:  {receipt_no}\n'
            f'Ngay thu:     {dt.strftime("%d/%m/%Y %H:%M")}\n'
            f'Ma dang ky:   {ma}\n'
            f'Hoc vien:     {ten}\n'
            f'Lop:          {lop}\n'
            f'So tien:      {gia} d\n'
            f'Hinh thuc:    {method}\n'
            f'Ghi chu:      {ghi_chu or "(khong)"}\n'
            f'Nhan vien:    {MOCK_EMPLOYEE["name"]}\n'
            '--------------------------------------\n'
            '--- Cam on quy hoc vien ---\n'
        )
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            msg_info(self, 'Đã lưu', f'Biên lai đã được lưu:\n{path}')
        except Exception as e:
            msg_warn(self, 'Lỗi', f'Không lưu được:\n{e}')

    def _emp_print_receipt(self, tbl):
        rows = tbl.selectionModel().selectedRows() if tbl else []
        if not rows:
            msg_warn(self, 'Chưa chọn', 'Hãy chọn 1 dòng để in biên lai')
            return
        r = rows[0].row()
        ma = tbl.item(r, 0).text() if tbl.item(r, 0) else '?'
        ten = tbl.item(r, 1).text() if tbl.item(r, 1) else '?'
        lop = tbl.item(r, 2).text() if tbl.item(r, 2) else '?'
        gia = tbl.item(r, 3).text() if tbl.item(r, 3) else '?'
        page = self.page_widgets[3]
        cbo = page.findChild(QtWidgets.QComboBox, 'cboPayMethod')
        note = page.findChild(QtWidgets.QLineEdit, 'txtPayNote')
        method = cbo.currentText() if cbo else 'Tiền mặt'
        ghi_chu = note.text().strip() if note else ''
        self._emp_show_receipt(ma, ten, lop, gia, method, ghi_chu)

    def _fill_emp_classes(self):
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblEmpClasses')
        if not tbl:
            return
        tbl.setColumnCount(8)
        tbl.setHorizontalHeaderItem(7, QtWidgets.QTableWidgetItem('Thao tác'))

        # uu tien lay tu API, fallback sang [] neu loi -> bang rong
        cls_list = []
        if DB_AVAILABLE:
            try:
                rows = CourseService.get_all_classes()
                for r_db in rows:
                    cls_list.append((
                        r_db['ma_lop'], r_db.get('ma_mon', ''),
                        r_db.get('ten_mon', ''), r_db.get('ten_gv') or '—',
                        r_db.get('lich') or '', r_db.get('phong') or '',
                        int(r_db.get('siso_max') or 40),
                        int(r_db.get('siso_hien_tai') or 0),
                        int(r_db.get('gia') or 0),
                    ))
            except Exception as e:
                print(f'[EMP_CLS] loi: {e}')

        if not cls_list:
            # khong co data -> hien dong placeholder
            tbl.setRowCount(1)
            ph = QtWidgets.QTableWidgetItem('Chưa có dữ liệu')
            ph.setTextAlignment(Qt.AlignCenter)
            ph.setForeground(QColor(COLORS['text_light']))
            tbl.setItem(0, 0, ph)
            tbl.setSpan(0, 0, 1, tbl.columnCount())
            tbl.setRowHeight(0, 50)
        else:
            tbl.setRowCount(len(cls_list))
            for r, cls in enumerate(cls_list):
                ma, mmon, tmon, gv, lich, phong, smax, siso, gia = cls
                for c, val in enumerate([ma, tmon, gv, lich]):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter if c == 0 else Qt.AlignLeft | Qt.AlignVCenter)
                    tbl.setItem(r, c, item)
                siso_item = QtWidgets.QTableWidgetItem(f'{siso}/{smax}')
                siso_item.setTextAlignment(Qt.AlignCenter)
                pct = int(siso / smax * 100) if smax else 0
                siso_item.setForeground(QColor(COLORS['red'] if pct >= 95 else COLORS['gold'] if pct >= 70 else COLORS['green']))
                tbl.setItem(r, 4, siso_item)
                gia_item = QtWidgets.QTableWidgetItem(f'{gia:,}'.replace(',', '.') + ' đ')
                gia_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                gia_item.setForeground(QColor(COLORS['gold']))
                tbl.setItem(r, 5, gia_item)
                trang_thai = 'Đầy' if pct >= 100 else 'Còn chỗ'
                item_tt = QtWidgets.QTableWidgetItem(trang_thai)
                item_tt.setTextAlignment(Qt.AlignCenter)
                item_tt.setForeground(QColor(COLORS['red'] if trang_thai == 'Đầy' else COLORS['green']))
                tbl.setItem(r, 6, item_tt)
                # nut chi tiet lop - thu nho de hop voi row (NV chi xem)
                btn_detail = QtWidgets.QPushButton('Xem')
                btn_detail.setCursor(Qt.PointingHandCursor)
                btn_detail.setFixedSize(54, 22)
                btn_detail.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 3px; font-size: 10px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
                btn_detail.clicked.connect(lambda ch, cls_data=cls: show_detail_dialog(
                    self, 'Chi tiết lớp',
                    [('Mã lớp', cls_data[0]), ('Môn học', cls_data[2]),
                     ('Giảng viên', cls_data[3]), ('Lịch học', cls_data[4]),
                     ('Phòng', cls_data[5]),
                     ('Sĩ số', f'{cls_data[7]}/{cls_data[6]}'),
                     ('Học phí', f'{cls_data[8]:,}'.replace(',', '.') + ' đ'),
                     ('Trạng thái', 'Đầy' if cls_data[7] >= cls_data[6] else 'Còn chỗ')],
                    avatar_text=cls_data[0][:2], subtitle=cls_data[2]))
                w = QtWidgets.QWidget()
                hl = QtWidgets.QHBoxLayout(w)
                hl.setContentsMargins(0, 0, 0, 0); hl.setAlignment(Qt.AlignCenter)
                hl.addWidget(btn_detail)
                tbl.setCellWidget(r, 7, w)
            for r in range(len(cls_list)):
                tbl.setRowHeight(r, 36)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([78, 150, 125, 140, 68, 100, 85, 70]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)

        widen_search(page, 'txtSearchEmpCls', 290, ['cboEmpClsCourse', 'cboEmpClsStatus'])
        # search + filter
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchEmpCls')
        if txt:
            txt.textChanged.connect(lambda t: table_filter(tbl, t, cols=[0, 1, 2]))
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboEmpClsCourse')
        if cbo_c:
            cbo_c.clear()
            cbo_c.addItem('Tất cả môn học')
            # uu tien lay courses tu API, fallback MOCK_COURSES
            courses_for_cbo = []
            if DB_AVAILABLE:
                try:
                    rs = CourseService.get_all_courses()
                    courses_for_cbo = [(c['ma_mon'], c['ten_mon']) for c in rs]
                except Exception as e:
                    print(f'[EMP_CLS] courses combo loi: {e}')
            if not courses_for_cbo:
                courses_for_cbo = list(MOCK_COURSES)
            for code, name in courses_for_cbo:
                cbo_c.addItem(name)
            cbo_c.currentIndexChanged.connect(lambda: self._emp_filter_cls())
        cbo_s = page.findChild(QtWidgets.QComboBox, 'cboEmpClsStatus')
        if cbo_s:
            cbo_s.clear()
            cbo_s.addItems(['Tất cả trạng thái', 'Còn chỗ', 'Đầy'])
            cbo_s.currentIndexChanged.connect(lambda: self._emp_filter_cls())

    def _emp_filter_cls(self):
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblEmpClasses')
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboEmpClsCourse')
        cbo_s = page.findChild(QtWidgets.QComboBox, 'cboEmpClsStatus')
        if not tbl:
            return
        course_sel = cbo_c.currentText() if cbo_c and cbo_c.currentIndex() > 0 else None
        st_sel = cbo_s.currentText() if cbo_s and cbo_s.currentIndex() > 0 else None
        for r in range(tbl.rowCount()):
            it_mon = tbl.item(r, 1)
            it_st = tbl.item(r, 6)
            show = True
            if course_sel and it_mon and course_sel not in it_mon.text():
                show = False
            if st_sel and it_st and st_sel.lower() not in it_st.text().lower():
                show = False
            tbl.setRowHidden(r, not show)

    def _fill_emp_profile(self):
        page = self.page_widgets[5]
        u = MOCK_EMPLOYEE
        for attr, val in [('lblProfileName', u['name']), ('lblProfileRole', f"Nhân viên - {u['chucvu']}"),
                          ('lblProfileAvatar', u['initials']), ('valMaSV', u['id']), ('valHoTen', u['name']),
                          ('valLop', u['chucvu'])]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setText(val)
        for attr, val in [('txtEmail', u['email']), ('txtPhone', u['sdt'])]:
            w = page.findChild(QtWidgets.QLineEdit, attr)
            if w:
                w.setText(val)

        btn_save = page.findChild(QtWidgets.QPushButton, 'btnSave')
        if btn_save:
            btn_save.clicked.connect(lambda: (
                MOCK_EMPLOYEE.__setitem__('email', page.findChild(QtWidgets.QLineEdit, 'txtEmail').text().strip()),
                MOCK_EMPLOYEE.__setitem__('sdt', page.findChild(QtWidgets.QLineEdit, 'txtPhone').text().strip()),
                msg_info(self, 'Thành công', 'Đã lưu thông tin.')
            ))
        btn_cp = page.findChild(QtWidgets.QPushButton, 'btnChangePass')
        if btn_cp:
            btn_cp.clicked.connect(lambda: self._emp_change_pass())

    def _emp_change_pass(self):
        new = msg_input(self, 'Đổi mật khẩu', 'Nhập mật khẩu mới:')
        if new:
            MOCK_EMPLOYEE['password'] = new
            msg_info(self, 'Thành công', 'Đổi mật khẩu thành công.')


class App:
    def __init__(self):
        self.qapp = QtWidgets.QApplication(sys.argv)
        load_theme(self.qapp)
        # Prefetch courses + classes tu API (cache de cac combo dung lai)
        _load_app_data()
        self.main_win = None
        self.login_win = None

    def _sync_mock_from_user(self, user_obj):
        """dong bo MOCK dict tu User object tra ve DB (sidebar/profile dung MOCK)"""
        common = {
            'username': user_obj.username,
            'name': user_obj.full_name,
            'initials': user_obj.initials,
            'email': user_obj.email or '',
            'sdt': user_obj.sdt or '',
            'id': user_obj.id,
        }
        if user_obj.role == 'student':
            MOCK_USER.update(common)
            MOCK_USER['msv'] = user_obj.msv
            MOCK_USER['gioitinh'] = user_obj.gioitinh or ''
            MOCK_USER['diachi'] = user_obj.diachi or ''
            if user_obj.ngaysinh:
                MOCK_USER['ngaysinh'] = str(user_obj.ngaysinh)
            MOCK_USER['role'] = 'Học viên'
        elif user_obj.role == 'teacher':
            MOCK_TEACHER.update(common)
            MOCK_TEACHER['id'] = user_obj.ma_gv
            MOCK_TEACHER['hocvi'] = user_obj.hoc_vi or ''
            MOCK_TEACHER['khoa'] = user_obj.khoa or ''
            MOCK_TEACHER['role'] = 'Giảng viên'
            MOCK_TEACHER['user_id'] = user_obj.id  # luu id thuc de goi service
        elif user_obj.role == 'employee':
            MOCK_EMPLOYEE.update(common)
            MOCK_EMPLOYEE['id'] = user_obj.ma_nv
            MOCK_EMPLOYEE['chucvu'] = user_obj.chuc_vu or ''
            MOCK_EMPLOYEE['role'] = 'Nhân viên'
            MOCK_EMPLOYEE['user_id'] = user_obj.id
        elif user_obj.role == 'admin':
            MOCK_ADMIN.update(common)
            MOCK_ADMIN['role'] = 'Quản trị viên'

    def show_login(self):
        if self.main_win:
            self.main_win.close()
            self.main_win = None

        self.login_win = uic.loadUi(os.path.join(UI, 'login.ui'))

        # set anh
        self.login_win.lblCampus.setPixmap(
            QPixmap(os.path.join(RES, 'bg_campus.png')).scaled(480, 600, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        self.login_win.lblLogoLeft.setPixmap(QPixmap(os.path.join(RES, 'logo.png')))
        self.login_win.lblLibrary.setPixmap(
            QPixmap(os.path.join(RES, 'bg_library.png')).scaled(520, 140, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        self.login_win.setWindowIcon(QIcon(os.path.join(RES, 'logo.png')))

        def on_login():
            u = self.login_win.txtUsername.text().strip()
            p = self.login_win.txtPassword.text().strip()

            # uu tien DB - dung AuthService
            if DB_AVAILABLE:
                try:
                    user_obj = AuthService.login(u, p)
                    if user_obj:
                        # set MOCK dict theo user that de sidebar/profile hien tai
                        self._sync_mock_from_user(user_obj)
                        self.login_win.close()
                        window_cls = {
                            'student': MainWindow, 'admin': AdminWindow,
                            'teacher': TeacherWindow, 'employee': EmployeeWindow,
                        }.get(user_obj.role)
                        if window_cls:
                            self.main_win = window_cls(self)
                            self.main_win.current_user = user_obj
                            self.main_win.show()
                            return
                    self.login_win.lblError.setText('Sai tài khoản hoặc mật khẩu!')
                    return
                except Exception as e:
                    print(f'[AUTH] loi DB, fallback MOCK: {e}')
                    # roi xuong fallback MOCK

            # fallback: MOCK login
            if u == MOCK_USER['username'] and p == MOCK_USER['password']:
                self.login_win.close()
                self.main_win = MainWindow(self)
                self.main_win.show()
            elif u == MOCK_ADMIN['username'] and p == MOCK_ADMIN['password']:
                self.login_win.close()
                self.main_win = AdminWindow(self)
                self.main_win.show()
            elif u == MOCK_TEACHER['username'] and p == MOCK_TEACHER['password']:
                self.login_win.close()
                self.main_win = TeacherWindow(self)
                self.main_win.show()
            elif u == MOCK_EMPLOYEE['username'] and p == MOCK_EMPLOYEE['password']:
                self.login_win.close()
                self.main_win = EmployeeWindow(self)
                self.main_win.show()
            else:
                self.login_win.lblError.setText('Sai tài khoản hoặc mật khẩu!')

        self.login_win.btnLogin.clicked.connect(on_login)
        self.login_win.txtPassword.returnPressed.connect(on_login)
        self.login_win.txtUsername.returnPressed.connect(on_login)
        self.login_win.show()

    def run(self):
        self.show_login()
        sys.exit(self.qapp.exec_())


if __name__ == '__main__':
    app = App()
    app.run()
