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


def clear_session_state():
    """Clean global state khi logout. Tranh leak data sang user moi login."""
    global MOCK_USER, MOCK_TEACHER, MOCK_EMPLOYEE
    # Clear sensitive dicts
    for d in (MOCK_USER, MOCK_TEACHER, MOCK_EMPLOYEE):
        if isinstance(d, dict):
            d.clear()


def safe_connect(signal, slot):
    """Disconnect tat ca handler cu cua signal roi connect handler moi.
    Tranh signal accumulation khi fill_* duoc goi nhieu lan (mỗi lần
    cbo.connect() them 1 handler -> click 1 lan trigger N lan).

    Goi thay vi `signal.connect(slot)` truc tiep cho cac widget tai su dung
    (combo filter, search box). Khong can dung cho button tao moi moi lan.
    """
    try:
        signal.disconnect()
    except (TypeError, RuntimeError):
        pass
    signal.connect(slot)


def is_valid_email(email):
    """Email format check (don gian, du dung cho HV/GV/NV)."""
    if not email: return True  # empty = OK (optional field)
    import re
    return bool(re.match(r'^[\w.+-]+@[\w-]+(\.[\w-]+)+$', email))


def is_valid_phone_vn(phone):
    """SDT VN: 10-11 chu so, bat dau bang 0 hoac +84."""
    if not phone: return True  # empty = OK
    import re
    digits = re.sub(r'\D', '', phone)
    return 10 <= len(digits) <= 11


def api_error_msg(e):
    """Parse exception tu API call -> message tieng Viet ro rang.

    Backend giờ tra ve 409 + JSON {detail: 'msg'} cho FK violation,
    400 cho check violation, etc. Helper nay extract detail an toan.
    """
    try:
        import requests
        if isinstance(e, requests.HTTPError) and e.response is not None:
            try:
                body = e.response.json()
                detail = body.get('detail') if isinstance(body, dict) else None
                if detail:
                    return str(detail)
            except Exception:
                pass
            return f'HTTP {e.response.status_code}: {e.response.text[:200]}'
    except Exception:
        pass
    return str(e) or 'Lỗi không xác định'


def make_action_cell(buttons):
    """Tao 1 cell widget chua 2 nut thao tac (Sua/Xoa/Chi tiet/Duyet/...).

    Args:
        buttons: list of (text, color_key) - color_key la key trong COLORS
                 (vd 'navy', 'red', 'green', 'orange', 'gold')
                 Hoac (text, color_key, hover) neu muon hover effect

    Returns:
        (widget, [QPushButton]) - caller phai connect button.clicked

    Pattern dong bo voi _fill_admin_courses (mau chuan):
    - Button: 50x24 (60x24 cho text >4 chars), font 11px bold, white
    - Container: QHBoxLayout no margin, spacing 6, center align
    - Row height ben goi nen set 44, column width 150
    """
    w = QtWidgets.QWidget()
    hl = QtWidgets.QHBoxLayout(w)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(6)
    hl.setAlignment(Qt.AlignCenter)
    btns = []
    for spec in buttons:
        if len(spec) == 2:
            text, color_key = spec
            with_hover = True  # mac dinh co hover cho tat ca color (da co _hover variants)
        else:
            text, color_key, with_hover = spec
        b = QtWidgets.QPushButton(text)
        b.setCursor(Qt.PointingHandCursor)
        # Size theo do dai text
        width = 70 if len(text) >= 7 else 60 if len(text) >= 4 else 50
        b.setFixedSize(width, 24)
        bg = COLORS.get(color_key, COLORS['navy'])
        hover_css = ''
        if with_hover:
            hover_key = f'{color_key}_hover'
            hover_bg = COLORS.get(hover_key, bg)
            hover_css = f' QPushButton:hover {{ background: {hover_bg}; }}'
        b.setStyleSheet(
            f'QPushButton {{ background: {bg}; color: white; border: none; '
            f'border-radius: 4px; font-size: 11px; font-weight: bold; }}{hover_css}'
        )
        hl.addWidget(b)
        btns.append(b)
    return w, btns


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
        clear_session_state()
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

        # Bang khoa hoc cua HV - lay tu API thuc
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        data = []
        n_paid = 0
        n_pending = 0
        if DB_AVAILABLE and hv_id:
            try:
                rows = CourseService.get_classes_by_student(hv_id) or []
                for r in rows:
                    st = r.get('reg_status', r.get('trang_thai', 'paid'))
                    st_vn = {'paid': 'Đã thanh toán', 'pending_payment': 'Chờ thanh toán',
                             'completed': 'Hoàn thành', 'cancelled': 'Đã hủy'}.get(st, st)
                    if st in ('paid', 'completed'):
                        n_paid += 1
                    elif st == 'pending_payment':
                        n_pending += 1
                    data.append([
                        r.get('ma_lop', ''), r.get('ten_mon', ''), '3',
                        r.get('ten_gv', '') or '—', r.get('lich', '') or '—', st_vn
                    ])
            except Exception as e:
                print(f'[STU_DASH] Loi load classes: {e}')

        # Update stat cards: lblStatCourses (so lop), lblStatCredits, lblStatRemaining
        for attr, val in [('lblStatCourses', str(n_paid)),
                           ('lblStatCredits', str(n_paid * 3)),  # 3 tin chi/lop
                           ('lblStatRemaining', str(n_pending))]:
            wlbl = page.findChild(QtWidgets.QLabel, attr)
            if wlbl:
                wlbl.setText(val)

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCourses')
        if tbl:
            tbl.setRowCount(len(data) if data else 1)
            if not data:
                ph = QtWidgets.QTableWidgetItem('Chưa có khóa học nào đăng ký')
                ph.setTextAlignment(Qt.AlignCenter)
                ph.setForeground(QColor(COLORS['text_light']))
                tbl.setItem(0, 0, ph)
                tbl.setSpan(0, 0, 1, tbl.columnCount())
                tbl.setRowHeight(0, 50)
            else:
                for r, row in enumerate(data):
                    for c, val in enumerate(row):
                        item = QtWidgets.QTableWidgetItem(val)
                        if c == 5 and 'thanh toán' in val.lower() and 'chờ' not in val.lower():
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

        # Header bar phai resize de khong overflow ra ngoai contentArea (870 wide)
        hb = page.findChild(QtWidgets.QFrame, 'headerBar')
        if hb:
            hb.setGeometry(0, 0, 870, 56)

        # Schedule frame to, calendar Frame giu nhung an cal widget va dat prev/next button
        sf = page.findChild(QtWidgets.QFrame, 'scheduleFrame')
        if sf:
            sf.setGeometry(15, 68, 615, 618)
        cf = page.findChild(QtWidgets.QFrame, 'calendarFrame')
        if cf:
            cf.setGeometry(635, 68, 225, 230)
        lf = page.findChild(QtWidgets.QFrame, 'legendFrame')
        if lf:
            lf.setGeometry(635, 308, 225, 190)

        # An calendar widget cu (Qt khong fit 7 cot tot trong frame nay), thay bang nav button
        cal_w = page.findChild(QtWidgets.QCalendarWidget, 'calendarWidget')
        if cal_w:
            cal_w.hide()

        # Tao nav panel inside calendarFrame: tieu de + 3 nut (prev/today/next)
        if cf and not cf.findChild(QtWidgets.QPushButton, 'btnPrevWeek'):
            nav_title = QtWidgets.QLabel('Điều hướng tuần', cf)
            nav_title.setObjectName('lblNavTitle')
            nav_title.setGeometry(15, 12, 195, 20)
            nav_title.setStyleSheet('color: #1a1a2e; font-size: 13px; font-weight: bold; background: transparent;')
            nav_title.show()

            self._lblNavWeek = QtWidgets.QLabel('—', cf)
            self._lblNavWeek.setObjectName('lblNavWeek')
            self._lblNavWeek.setGeometry(15, 38, 195, 40)
            self._lblNavWeek.setStyleSheet('color: #002060; font-size: 12px; font-weight: bold; background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px;')
            self._lblNavWeek.setAlignment(Qt.AlignCenter)
            self._lblNavWeek.setWordWrap(True)
            self._lblNavWeek.show()

            btn_prev = QtWidgets.QPushButton('‹ Tuần trước', cf)
            btn_prev.setObjectName('btnPrevWeek')
            btn_prev.setGeometry(15, 92, 95, 32)
            btn_prev.setStyleSheet('QPushButton { background: white; color: #4a5568; border: 1px solid #d2d6dc; border-radius: 6px; font-size: 11px; } QPushButton:hover { background: #edf2f7; border-color: #002060; color: #002060; }')
            btn_prev.setCursor(Qt.PointingHandCursor)
            btn_prev.show()

            btn_next = QtWidgets.QPushButton('Tuần sau ›', cf)
            btn_next.setObjectName('btnNextWeek')
            btn_next.setGeometry(115, 92, 95, 32)
            btn_next.setStyleSheet(btn_prev.styleSheet())
            btn_next.setCursor(Qt.PointingHandCursor)
            btn_next.show()

            btn_today = QtWidgets.QPushButton('Tuần hiện tại', cf)
            btn_today.setObjectName('btnTodayWeek')
            btn_today.setGeometry(15, 132, 195, 32)
            btn_today.setStyleSheet('QPushButton { background: #002060; color: white; border: none; border-radius: 6px; font-size: 11px; font-weight: bold; } QPushButton:hover { background: #003080; }')
            btn_today.setCursor(Qt.PointingHandCursor)
            btn_today.show()

            hint = QtWidgets.QLabel('Dùng nút trên để chuyển tuần', cf)
            hint.setObjectName('lblNavHint')
            hint.setGeometry(15, 175, 195, 40)
            hint.setStyleSheet('color: #a0aec0; font-size: 10px; background: transparent;')
            hint.setWordWrap(True)
            hint.setAlignment(Qt.AlignCenter)
            hint.show()

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblSchedule')
        if not tbl:
            return
        tbl.setGeometry(0, 0, 615, 618)

        hours = ['7:00','8:00','9:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00']
        tbl.setRowCount(len(hours))
        tbl.verticalHeader().setVisible(False)
        days_vn = ['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7']

        # Day col = 92: 45 + 6*92 = 597 + scrollbar 16 = 613 fits 615
        tbl.setColumnWidth(0, 45)
        for i in range(1, 7):
            tbl.setColumnWidth(i, 92)

        # Row cao hon → card co cho tho cho 5 dong text
        for r in range(len(hours)):
            tbl.setRowHeight(r, 50)
            item = QtWidgets.QTableWidgetItem(hours[r])
            item.setTextAlignment(Qt.AlignRight | Qt.AlignTop)
            item.setForeground(QColor('#718096'))
            item.setFont(QFont('Segoe UI', 9))
            tbl.setItem(r, 0, item)

        # Khoi tao label hien thi tuan dang xem (ngay tren scheduleFrame, ke tieu de)
        title = page.findChild(QtWidgets.QLabel, 'lblPageTitle')
        if title and not page.findChild(QtWidgets.QLabel, 'lblWeekRange'):
            wr = QtWidgets.QLabel(page)
            wr.setObjectName('lblWeekRange')
            wr.setGeometry(180, 0, 450, 56)
            wr.setStyleSheet('color: #4a5568; font-size: 13px; background: transparent;')
            wr.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            wr.show()

        # State: tuan dang xem - dung nearest_week (backend uu tien tuan hien tai neu co lich)
        # Chi 1 API call -> giam lag khi mo trang
        today = QDate.currentDate()
        self._stu_current_monday = today.addDays(-(today.dayOfWeek() - 1))
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        if DB_AVAILABLE and hv_id:
            try:
                near = ScheduleService.nearest_week_for_student(hv_id, today.toPyDate())
                if near:
                    from datetime import date as _date
                    if isinstance(near, str):
                        near = _date.fromisoformat(near)
                    self._stu_current_monday = QDate(near.year, near.month, near.day)
            except Exception as e:
                print(f'[STU_SCHED] nearest_week loi: {e}')
        self._load_student_schedule_week(page, tbl, self._stu_current_monday, hours, days_vn)

        # Wire prev/next/today buttons
        btn_prev = cf.findChild(QtWidgets.QPushButton, 'btnPrevWeek') if cf else None
        btn_next = cf.findChild(QtWidgets.QPushButton, 'btnNextWeek') if cf else None
        btn_today = cf.findChild(QtWidgets.QPushButton, 'btnTodayWeek') if cf else None
        if btn_prev:
            btn_prev.clicked.connect(lambda: (
                setattr(self, '_stu_current_monday', self._stu_current_monday.addDays(-7)),
                self._load_student_schedule_week(page, tbl, self._stu_current_monday, hours, days_vn)
            ))
        if btn_next:
            btn_next.clicked.connect(lambda: (
                setattr(self, '_stu_current_monday', self._stu_current_monday.addDays(7)),
                self._load_student_schedule_week(page, tbl, self._stu_current_monday, hours, days_vn)
            ))
        if btn_today:
            btn_today.clicked.connect(lambda: (
                setattr(self, '_stu_current_monday', QDate.currentDate().addDays(-(QDate.currentDate().dayOfWeek() - 1))),
                self._load_student_schedule_week(page, tbl, self._stu_current_monday, hours, days_vn)
            ))

    def _load_student_schedule_week(self, page, tbl, monday, hours, days_vn):
        """Reload lich hoc HV cho tuan bat dau bang `monday` (QDate)."""
        # Update header cot ngay + label tuan
        for i in range(6):
            d = monday.addDays(i)
            hi = tbl.horizontalHeaderItem(i+1)
            if hi:
                hi.setText(f'{d.toString("dd/MM/yyyy")}\n{days_vn[i]}')
        wr_lbl = page.findChild(QtWidgets.QLabel, 'lblWeekRange')
        if wr_lbl:
            wr_lbl.setText(f'Tuần: {monday.toString("dd/MM/yyyy")} → {monday.addDays(5).toString("dd/MM/yyyy")}')
        # Update label nav week
        nav_lbl = page.findChild(QtWidgets.QLabel, 'lblNavWeek')
        if nav_lbl:
            nav_lbl.setText(f'{monday.toString("dd/MM/yyyy")}\n→ {monday.addDays(5).toString("dd/MM/yyyy")}')

        # Xoa cell cu (cellWidget va span) - chi un-span neu cell co span > 1
        for r in range(len(hours)):
            for c in range(1, 7):
                cw = tbl.cellWidget(r, c)
                if cw:
                    tbl.removeCellWidget(r, c)
                if tbl.rowSpan(r, c) > 1 or tbl.columnSpan(r, c) > 1:
                    tbl.setSpan(r, c, 1, 1)
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(''))

        def mk_card(ma_lop, ten_mon, ts, phong, gv, color):
            f = QtWidgets.QFrame()
            f.setStyleSheet(f'QFrame {{ background: white; border: 1px solid #d2d6dc; border-radius: 4px; border-top: 3px solid {color}; margin: 1px; }}')
            vb = QtWidgets.QVBoxLayout(f)
            vb.setContentsMargins(4, 3, 4, 3)
            vb.setSpacing(1)
            # Dong 1: ma lop (bold, mau chu de)
            l1 = QtWidgets.QLabel(ma_lop)
            l1.setStyleSheet(f'color: {color}; font-size: 11px; font-weight: bold; border: none; background: transparent;')
            l1.setWordWrap(False)
            vb.addWidget(l1)
            # Dong 2: ten mon (wrap neu dai)
            l2 = QtWidgets.QLabel(ten_mon)
            l2.setStyleSheet('color: #2d3748; font-size: 10px; border: none; background: transparent;')
            l2.setWordWrap(True)
            vb.addWidget(l2)
            # Dong 3: gio
            l3 = QtWidgets.QLabel(ts)
            l3.setStyleSheet('color: #4a5568; font-size: 9px; font-weight: bold; border: none; background: transparent;')
            vb.addWidget(l3)
            # Dong 4: phong (smart prefix: chi them "P. " neu chua co)
            phong_disp = phong if phong.lower().startswith(('p.', 'p ', 'phòng', 'phong')) else f'P. {phong}'
            l4 = QtWidgets.QLabel(phong_disp)
            l4.setStyleSheet('color: #718096; font-size: 9px; border: none; background: transparent;')
            vb.addWidget(l4)
            # Dong 5: gv (rut gon neu qua dai)
            gv_short = gv if len(gv) <= 18 else gv[:16] + '…'
            l5 = QtWidgets.QLabel(gv_short)
            l5.setStyleSheet('color: #4a5568; font-size: 9px; border: none; background: transparent;')
            vb.addWidget(l5)
            vb.addStretch()
            return f

        # Lay lich tu API
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        sched = []
        if DB_AVAILABLE and hv_id:
            try:
                rows = ScheduleService.get_for_student_week(hv_id, monday.toPyDate()) or []
                color_palette = ['#002060', '#c68a1e', '#276749', '#c53030', '#3182ce']
                color_by_lop = {}
                from datetime import date as _date
                for r in rows:
                    try:
                        d = r['ngay'] if isinstance(r['ngay'], _date) else _date.fromisoformat(str(r['ngay'])[:10])
                        wd = d.weekday()
                        if wd > 5:
                            continue
                        col = wd + 1
                        gio_bd = str(r.get('gio_bat_dau', ''))[:5]
                        gio_kt = str(r.get('gio_ket_thuc', ''))[:5]
                        try:
                            hour_idx = int(gio_bd.split(':')[0]) - 7
                        except Exception:
                            hour_idx = 0
                        if hour_idx < 0 or hour_idx >= len(hours):
                            continue
                        try:
                            h1, m1 = gio_bd.split(':'); h2, m2 = gio_kt.split(':')
                            duration_min = (int(h2) * 60 + int(m2)) - (int(h1) * 60 + int(m1))
                            span = max(1, round(duration_min / 60))
                        except Exception:
                            span = 3
                        ma_lop = r.get('lop_id', '')
                        if ma_lop not in color_by_lop:
                            color_by_lop[ma_lop] = color_palette[len(color_by_lop) % len(color_palette)]
                        sched.append((
                            hour_idx, span, col,
                            ma_lop,
                            r.get("ten_mon", "") or '',
                            f'{gio_bd}-{gio_kt}',
                            r.get('phong', '') or '—',
                            r.get('ten_gv', '') or '',
                            color_by_lop[ma_lop],
                        ))
                    except Exception as e:
                        print(f'[STU_SCHED] parse row loi: {e}')
            except Exception as e:
                print(f'[STU_SCHED] API loi: {e}')

        # Empty state - hien card placeholder o giua bang neu tuan rong
        if not sched:
            ph = QtWidgets.QFrame()
            ph.setStyleSheet('QFrame { background: #f7fafc; border: 1px dashed #cbd5e0; border-radius: 6px; }')
            vb = QtWidgets.QVBoxLayout(ph)
            vb.setContentsMargins(12, 12, 12, 12)
            vb.setAlignment(Qt.AlignCenter)
            l1 = QtWidgets.QLabel('Tuần này không có lịch học')
            l1.setStyleSheet('color: #4a5568; font-size: 13px; font-weight: bold; border: none; background: transparent;')
            l1.setAlignment(Qt.AlignCenter)
            l2 = QtWidgets.QLabel('Chọn tuần khác trên lịch bên phải')
            l2.setStyleSheet('color: #718096; font-size: 11px; border: none; background: transparent;')
            l2.setAlignment(Qt.AlignCenter)
            vb.addWidget(l1)
            vb.addWidget(l2)
            tbl.setCellWidget(3, 1, ph)
            tbl.setSpan(3, 1, 4, 6)
        else:
            for rs, span, col, ma_lop, ten_mon, ts, phong, gv, color in sched:
                tbl.setCellWidget(rs, col, mk_card(ma_lop, ten_mon, ts, phong, gv, color))
                tbl.setSpan(rs, col, span, 1)

    def _fill_exam(self):
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblExam')
        if not tbl:
            return
        # Load exams cua HV tu API
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        data = []
        if DB_AVAILABLE and hv_id and ExamService:
            try:
                rows = ExamService.get_for_student(hv_id) or []
                for i, r in enumerate(rows, start=1):
                    ngay = fmt_date(r.get('ngay_thi'))
                    ca = r.get('ca_thi', '')
                    gio_bd = str(r.get('gio_bat_dau', ''))[:5]
                    gio_kt = str(r.get('gio_ket_thuc', ''))[:5]
                    if gio_bd and gio_kt:
                        ca = f'{ca} ({gio_bd}-{gio_kt})' if ca else f'{gio_bd}-{gio_kt}'
                    data.append([
                        str(i), r.get('ma_mon', '') or r.get('lop_id', ''),
                        r.get('ten_mon', ''), ngay, ca,
                        r.get('phong', '') or '—',
                        r.get('hinh_thuc', '') or '',
                    ])
            except Exception as e:
                print(f'[STU_EXAM] API loi: {e}')

        tbl.setRowCount(len(data) if data else 1)
        if not data:
            ph = QtWidgets.QTableWidgetItem('Chưa có lịch thi nào')
            ph.setTextAlignment(Qt.AlignCenter)
            ph.setForeground(QColor(COLORS['text_light']))
            tbl.setItem(0, 0, ph)
            tbl.setSpan(0, 0, 1, tbl.columnCount())
            tbl.setRowHeight(0, 50)
        else:
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    tbl.setItem(r, c, QtWidgets.QTableWidgetItem(val))
            for r in range(len(data)):
                tbl.setRowHeight(r, 40)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, w in enumerate([30, 65, 140, 85, 135, 80]):
            tbl.setColumnWidth(c, w)
        tbl.verticalHeader().setVisible(False)

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
                    # group theo semester_id (lay 1 lan tu API classes)
                    from collections import defaultdict
                    by_sem = defaultdict(list)
                    # Cache class semester_id de tranh N+1 query
                    sem_cache = {}
                    try:
                        all_classes = CourseService.get_all_classes() or []
                        for c in all_classes:
                            sem_cache[c.get('ma_lop')] = c.get('semester_id') or 'HK2-2526'
                    except Exception as _e:
                        pass
                    for g in rows:
                        sid = sem_cache.get(g['lop_id'], 'HK2-2526')
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

        # Lay danh sach GV tu API + diem danh gia trung binh
        data = []
        gv_ids = []  # song song voi data, luu gv_id de pass vao dialog
        if DB_AVAILABLE:
            try:
                gvs = TeacherService.get_for_review() or []
                for i, gv in enumerate(gvs, start=1):
                    avg = gv.get('avg_rating') or gv.get('diem_tb') or 0
                    cnt = gv.get('review_count') or gv.get('so_danh_gia') or gv.get('so_dg') or 0
                    data.append([
                        str(i), gv.get('full_name', '') or '',
                        gv.get('khoa', '') or '',
                        f'{float(avg):.1f}' if avg else '0.0',
                        str(cnt),
                    ])
                    gv_ids.append(gv.get('gv_id') or gv.get('user_id') or gv.get('id'))
            except Exception as e:
                print(f'[REVIEW] API loi: {e}')
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblReview')
        if tbl:
            tbl.setRowCount(len(data) if data else 1)
            if not data:
                ph = QtWidgets.QTableWidgetItem('Chưa có dữ liệu giảng viên')
                ph.setTextAlignment(Qt.AlignCenter)
                ph.setForeground(QColor(COLORS['text_light']))
                tbl.setItem(0, 0, ph)
                tbl.setSpan(0, 0, 1, tbl.columnCount())
                tbl.setRowHeight(0, 50)
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter if c >= 3 else Qt.AlignLeft | Qt.AlignVCenter)
                    if c == 3:
                        try:
                            score = float(val)
                            color = COLORS['green'] if score >= 4.5 else COLORS['navy'] if score >= 4.0 else COLORS['orange']
                            item.setForeground(QColor(color))
                            item.setFont(QFont('Segoe UI', 11, QFont.Bold))
                        except (ValueError, TypeError): pass
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
            # connect nut danh gia - pass ca gv_id (de submit_review chinh xac)
            for r, row in enumerate(data):
                w = tbl.cellWidget(r, 5)
                if w:
                    b = w.findChild(QtWidgets.QPushButton)
                    if b:
                        gv_name = row[1]
                        gv_id = gv_ids[r] if r < len(gv_ids) else None
                        b.clicked.connect(
                            lambda ch, gv=gv_name, gid=gv_id: self._open_review_dialog(gv, gid)
                        )

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

    def _open_review_dialog(self, gv_name, gv_id=None):
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

        # Validate
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        if not (DB_AVAILABLE and hv_id and gv_id):
            msg_warn(self, 'Đánh giá', 'Không xác định được học viên/giảng viên. Hãy đăng nhập lại.')
            return

        diem = sp.value()
        nhan_xet = ta.toPlainText().strip()

        # Tim 1 lop ma HV + GV cung co (qua API class-by-student)
        lop_id = None
        try:
            classes = CourseService.get_classes_by_student(hv_id) or []
            for cls in classes:
                if cls.get('gv_id') == gv_id:
                    lop_id = cls.get('ma_lop')
                    break
        except Exception as e:
            print(f'[REVIEW] tim lop loi: {e}')

        if not lop_id:
            msg_warn(self, 'Đánh giá',
                     f'Bạn chưa học lớp nào của giảng viên {gv_name}. Chỉ HV đã đăng ký lớp mới có thể đánh giá.')
            return

        # Submit qua API
        try:
            ReviewService.submit_review(hv_id, gv_id, lop_id, diem, nhan_xet)
            print(f'[REVIEW] OK: HV {hv_id} → GV {gv_id} ({gv_name}) lop {lop_id}: {diem}/5')
            msg_info(self, 'Đánh giá', f'Đã gửi đánh giá {diem}/5 cho {gv_name}')
            # Reload bang de cap nhat diem TB + so danh gia
            self._fill_review()
        except Exception as e:
            print(f'[REVIEW] submit loi: {e}')
            msg_warn(self, 'Đánh giá', f'Lưu đánh giá thất bại:\n{e}')

    def _fill_notifications(self):
        """Generate cards dong theo so notif tu API, giu design cua .ui (border-left mau theo loai)."""
        page = self.page_widgets[5]
        sc = page.findChild(QtWidgets.QWidget, 'scrollContent')
        if not sc:
            return

        # An 6 card hardcode cua .ui (dung lam template thoi)
        for i in range(1, 7):
            c = page.findChild(QtWidgets.QFrame, f'card{i}')
            if c:
                c.hide()

        # Xoa cac card dynamic da render lan truoc
        for old in sc.findChildren(QtWidgets.QFrame):
            if old.objectName().startswith('dynNotifCard'):
                old.deleteLater()
        old_empty = sc.findChild(QtWidgets.QLabel, 'lblNoNotif')
        if old_empty:
            old_empty.deleteLater()

        # Lay notifs tu API
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        notifs = []
        if DB_AVAILABLE and hv_id:
            try:
                notifs = NotificationService.get_for_student(hv_id) or []
            except Exception as e:
                print(f'[STU_NOTIF] API loi: {e}')

        if not notifs:
            empty = QtWidgets.QLabel('Không có thông báo nào', sc)
            empty.setObjectName('lblNoNotif')
            empty.setGeometry(25, 20, 820, 80)
            empty.setStyleSheet(f'color: {COLORS["text_light"]}; font-size: 13px; padding: 20px; background: white; border: 1px dashed #cbd5e0; border-radius: 8px;')
            empty.setAlignment(Qt.AlignCenter)
            empty.show()
            sc.setMinimumHeight(120)
            return

        # Mau border-left theo loai
        color_map = {'urgent': '#c53030', 'warning': '#e8710a', 'info': '#002060'}

        # Render moi notif thanh 1 card voi absolute geometry → scrollContent expand theo so card
        card_x = 25
        card_w = 820
        card_h = 105
        gap = 14
        y = 20

        for i, n in enumerate(notifs):
            loai = n.get('loai', 'info')
            color = color_map.get(loai, '#002060')

            card = QtWidgets.QFrame(sc)
            card.setObjectName(f'dynNotifCard{i}')
            card.setGeometry(card_x, y, card_w, card_h)
            card.setStyleSheet(
                f'QFrame#dynNotifCard{i} {{ background: white; border: 1px solid #d2d6dc; '
                f'border-radius: 10px; border-left: 4px solid {color}; }}'
            )

            # Title
            title_lbl = QtWidgets.QLabel(n.get('tieu_de', '') or '(Không tiêu đề)', card)
            title_lbl.setGeometry(20, 14, 780, 22)
            title_lbl.setStyleSheet('color: #1a1a2e; font-size: 14px; font-weight: bold; background: transparent; border: none;')
            title_lbl.show()

            # Date - source
            date_lbl = QtWidgets.QLabel(card)
            date_str = fmt_date(n.get('ngay_tao'), fmt='%d/%m/%Y')
            src = n.get('tu_ten') or 'Hệ thống'
            date_lbl.setText(f'{date_str} - {src}')
            date_lbl.setGeometry(20, 40, 400, 16)
            date_lbl.setStyleSheet('color: #718096; font-size: 11px; background: transparent; border: none;')
            date_lbl.show()

            # Content
            content_lbl = QtWidgets.QLabel(n.get('noi_dung', '') or '', card)
            content_lbl.setGeometry(20, 62, 780, 32)
            content_lbl.setStyleSheet('color: #4a5568; font-size: 12px; background: transparent; border: none;')
            content_lbl.setWordWrap(True)
            content_lbl.show()

            card.show()
            y += card_h + gap

        # Set min height de scroll lam viec
        sc.setMinimumHeight(y + 20)

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
        # Doc truoc tu form, khong update MOCK_USER cho den khi API success
        updates = {}
        for attr, key in [('txtEmail', 'email'), ('txtPhone', 'sdt'), ('txtAddress', 'diachi')]:
            w = page.findChild(QtWidgets.QLineEdit, attr)
            if w:
                updates[key] = w.text().strip()
        # Validate format
        if updates.get('email') and not is_valid_email(updates['email']):
            msg_warn(self, 'Sai định dạng', 'Email không hợp lệ (vd: ten@example.com)')
            return
        if updates.get('sdt') and not is_valid_phone_vn(updates['sdt']):
            msg_warn(self, 'Sai định dạng', 'Số điện thoại không hợp lệ (10-11 chữ số)')
            return

        hv_user_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        if not (DB_AVAILABLE and hv_user_id and updates):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # Goi API truoc, MOCK update sau
        try:
            StudentService.update(hv_user_id, **updates)
        except Exception as e:
            print(f'[STU_PROFILE] loi: {e}')
            msg_warn(self, 'Không lưu được', api_error_msg(e))
            return
        # API OK -> update local cache
        for k, v in updates.items():
            MOCK_USER[k] = v
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
        if len(new1.text()) < 4:
            msg_warn(self, 'Lỗi', 'Mật khẩu mới phải tối thiểu 4 ký tự')
            return
        if not (DB_AVAILABLE and MOCK_USER.get('id')):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # Goi API truoc, chi update local khi success
        try:
            AuthService.change_password(MOCK_USER['id'], new1.text())
        except Exception as e:
            print(f'[AUTH] loi doi mk: {e}')
            msg_warn(self, 'Không đổi được', api_error_msg(e))
            return
        MOCK_USER['password'] = new1.text()
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
        clear_session_state()
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
                # thao tac - pattern chuan
                cell, (btn_edit, btn_del) = make_action_cell([('Sửa', 'navy'), ('Xóa', 'red')])
                tbl.setCellWidget(r, 6, cell)
                btn_edit.clicked.connect(lambda ch, ma=row[0], nm=row[1]: self._admin_edit_course(ma, nm))
                btn_del.clicked.connect(lambda ch, ma=row[0], nm=row[1], t=tbl: self._admin_del_row(t, ma, nm, 'môn học'))
            tbl.horizontalHeader().setStretchLastSection(True)
            for c, cw in enumerate([70, 180, 30, 140, 130, 110, 150]):
                tbl.setColumnWidth(c, cw)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)

        # Khong day btnSearchCourse vi no o sat mep phai roi - chi day combo + separator
        widen_search(page, 'txtSearchCourse', 300, ['sepFilter1', 'cboFilterDept'])
        # wire search / filter / add - dung safe_connect tranh signal accumulation
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchCourse')
        if txt:
            safe_connect(txt.textChanged, lambda s: table_filter(tbl, s, cols=[0, 1, 3]))
        btn_s = page.findChild(QtWidgets.QPushButton, 'btnSearchCourse')
        if btn_s and txt:
            safe_connect(btn_s.clicked, lambda: table_filter(tbl, txt.text(), cols=[0, 1, 3]))
        cbo = page.findChild(QtWidgets.QComboBox, 'cboFilterDept')
        if cbo:
            cbo.clear()
            cbo.addItems(['Tất cả khoa', 'Công nghệ thông tin (CNTT)', 'Toán', 'Ngoại ngữ'])
            safe_connect(cbo.currentIndexChanged, lambda: self._admin_filter_courses())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddCourse')
        if btn_add:
            safe_connect(btn_add.clicked, self._admin_add_course)

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
        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        new_code = txt_code.text().upper().strip()
        new_name = txt_name.text().strip()
        # Goi API TRUOC khi update UI
        try:
            CourseService.create_course(
                ma_mon=new_code,
                ten_mon=new_name,
                mo_ta=f'TC: {txt_tc.text() or 3}, GV: {txt_gv.text() or ""}'
            )
        except Exception as e:
            print(f'[ADM_ADD_COURSE] DB loi: {e}')
            msg_warn(self, 'Không thêm được', api_error_msg(e))
            return
        # DB OK -> update UI
        MOCK_COURSES.append((new_code, new_name))
        tbl = self.page_widgets[1].findChild(QtWidgets.QTableWidget, 'tblAdminCourses')
        if tbl:
            r = tbl.rowCount()
            tbl.insertRow(r)
            vals = [new_code, new_name, txt_tc.text() or '3', txt_gv.text() or '—', '—']
            for c, v in enumerate(vals):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(v))
            item_ss = QtWidgets.QTableWidgetItem('0/40')
            item_ss.setTextAlignment(Qt.AlignCenter)
            item_ss.setForeground(QColor(COLORS['green']))
            tbl.setItem(r, 5, item_ss)
            tbl.setRowHeight(r, 44)
            cell, (btn_edit, btn_del) = make_action_cell([('Sửa', 'navy'), ('Xóa', 'red')])
            tbl.setCellWidget(r, 6, cell)
            btn_edit.clicked.connect(lambda ch, ma=new_code, nm=new_name: self._admin_edit_course(ma, nm))
            btn_del.clicked.connect(lambda ch, ma=new_code, nm=new_name: self._admin_del_row(tbl, ma, nm, 'môn học'))
        msg_info(self, 'Thành công', f'Đã thêm môn {new_code} - {new_name}')

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
        new_code = txt_code.text().strip()
        new_name = txt_name.text().strip()

        # Persist len server qua API. mo_ta luu them tin_chi/gv/lich vi schema courses
        # khong co cot rieng - dung mo_ta nhu metadata
        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        mo_ta = f'TC: {txt_tc.text() or 3}, GV: {txt_gv.text() or "—"}, Lịch: {txt_lich.text() or "—"}'
        try:
            CourseService.update_course(ma, ten_mon=new_name, mo_ta=mo_ta)
            _refresh_cache()
        except Exception as e:
            print(f'[ADM_EDIT_COURSE] loi: {e}')
            msg_warn(self, 'Không lưu được', api_error_msg(e))
            return

        # Update UI sau khi save thanh cong
        for c, w in enumerate([txt_code, txt_name, txt_tc, txt_gv, txt_lich]):
            tbl.setItem(target_row, c, QtWidgets.QTableWidgetItem(w.text()))
        msg_info(self, 'Đã cập nhật', f'Đã lưu thay đổi cho {new_code}')

    def _admin_del_row(self, tbl, ma, nm, loai):
        if not msg_confirm(self, 'Xác nhận xóa', f'Xóa {loai} {ma} - {nm}?'):
            return
        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # Ghi DB - PHAI thanh cong moi xoa UI. Khong silent catch nua.
        try:
            if loai == 'môn học':
                CourseService.delete_course(ma)
            elif loai == 'lớp':
                CourseService.delete_class(ma)
            elif loai == 'học viên':
                row = StudentService.get_by_msv(ma)
                if not row:
                    msg_warn(self, 'Không tìm thấy', f'Học viên {ma} không tồn tại trong hệ thống.')
                    return
                StudentService.delete(row.get('user_id') or row.get('id'))
            elif loai == 'giảng viên':
                row = TeacherService.get_by_code(ma)
                if not row:
                    msg_warn(self, 'Không tìm thấy', f'Giảng viên {ma} không tồn tại.')
                    return
                TeacherService.delete(row.get('user_id') or row.get('id'))
            elif loai == 'nhân viên':
                row = EmployeeService.get_by_code(ma)
                if not row:
                    msg_warn(self, 'Không tìm thấy', f'Nhân viên {ma} không tồn tại.')
                    return
                EmployeeService.delete(row.get('user_id') or row.get('id'))
            elif loai == 'môn trong CT':
                # ma o cot 0 trong tblCurriculum la STT (so), can lookup theo ma_mon (cot 1)
                # tim row trong tbl, lay ma_mon roi resolve curriculum id
                cur_row = None
                for r in range(tbl.rowCount()):
                    it0 = tbl.item(r, 0)
                    if it0 and it0.text() == ma:
                        it1 = tbl.item(r, 1)
                        if it1: cur_row = (it1.text(), r)
                        break
                if cur_row and CurriculumService:
                    ma_mon, _ = cur_row
                    items = CurriculumService.get_all() or []
                    target = next((c for c in items if c.get('ma_mon') == ma_mon), None)
                    if not target:
                        msg_warn(self, 'Không tìm thấy', f'Mục {ma_mon} không có trong khung CT.')
                        return
                    CurriculumService.delete(target['id'])
                else:
                    msg_warn(self, 'Lỗi', 'Không xác định được mục cần xóa.')
                    return
        except Exception as e:
            print(f'[ADM_DEL] {loai} {ma} loi: {e}')
            msg_warn(self, 'Không xóa được', api_error_msg(e))
            return  # khong xoa UI neu DB fail

        # DB delete OK - moi xoa UI
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
                # thao tac - pattern chuan
                cell, (btn_detail, btn_del) = make_action_cell([('Chi tiết', 'navy'), ('Xóa', 'red')])
                tbl.setCellWidget(r, 6, cell)
                btn_detail.clicked.connect(lambda ch, rd=row: show_detail_dialog(
                    self, 'Chi tiết học viên',
                    [('MSV', rd[0]), ('Họ tên', rd[1]), ('Lớp', rd[2]),
                     ('Khoa', rd[3]), ('Số điện thoại', rd[4]),
                     ('Số môn đăng ký', rd[5])],
                    avatar_text=rd[1].split()[-1] if rd[1] else '?', subtitle=rd[0]))
                btn_del.clicked.connect(lambda ch, ma=row[0], nm=row[1], t=tbl: self._admin_del_row(t, ma, nm, 'học viên'))
            tbl.horizontalHeader().setStretchLastSection(True)
            for c, cw in enumerate([75, 140, 100, 95, 90, 100, 150]):
                tbl.setColumnWidth(c, cw)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)

        # btnSearchStudent o sat phai - khong day, chi day combo
        widen_search(page, 'txtSearchStudent', 300, ['cboFilterClass', 'cboFilterDeptSt'])
        # search / filter / add
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchStudent')
        if txt:
            safe_connect(txt.textChanged, lambda s: table_filter(tbl, s, cols=[0, 1]))
        btn_s = page.findChild(QtWidgets.QPushButton, 'btnSearchStudent')
        if btn_s and txt:
            safe_connect(btn_s.clicked, lambda: table_filter(tbl, txt.text(), cols=[0, 1]))
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
            safe_connect(cbo_d.currentIndexChanged, self._adm_st_khoa_changed)
        # Lop sau (con) - mac dinh tat ca, doi khi khoa thay doi
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboFilterClass')
        if cbo_c:
            cbo_c.clear()
            cbo_c.addItem('Tất cả lớp')
            for lops in self._adm_lop_by_khoa.values():
                for lop in lops:
                    cbo_c.addItem(lop)
            safe_connect(cbo_c.currentIndexChanged, lambda: self._admin_filter_students())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddStudent')
        if btn_add:
            safe_connect(btn_add.clicked, self._admin_add_student)

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
        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # Goi API truoc
        msv_val = widgets['msv'].text().strip()
        try:
            StudentService.create(
                username=msv_val.lower(),
                password='passuser',   # default password
                full_name=widgets['ten'].text().strip(),
                msv=msv_val,
                sdt=widgets['sdt'].text().strip() or None,
            )
        except Exception as e:
            print(f'[ADM_ADD_HV] DB loi: {e}')
            msg_warn(self, 'Không thêm được', api_error_msg(e))
            return
        # DB OK -> update UI (re-fill cho an toan vi co the BE return data day du hon)
        self.pages_filled[3] = False
        self._fill_admin_students()
        self.pages_filled[3] = True
        msg_info(self, 'Thành công', f'Đã thêm học viên {msv_val} (mật khẩu mặc định: passuser)')

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
                # Toggle button: doi mau theo trang thai - dung pattern chuan
                toggle_text = 'Đóng ĐK' if is_open else 'Mở ĐK'
                toggle_color = 'orange' if is_open else 'green'
                cell, (btn_toggle,) = make_action_cell([(toggle_text, toggle_color)])
                tbl.setCellWidget(r, 6, cell)
                btn_toggle.clicked.connect(lambda ch, ma=row[0], b=btn_toggle: self._admin_toggle_sem(ma, b))
            tbl.horizontalHeader().setStretchLastSection(True)
            for c, cw in enumerate([95, 90, 95, 105, 105, 95, 130]):
                tbl.setColumnWidth(c, cw)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)

        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddSemester')
        if btn_add:
            safe_connect(btn_add.clicked, self._admin_add_semester)

    def _admin_toggle_sem(self, ma, btn):
        current = btn.text()
        is_open = 'Đóng' in current
        new_state = 'mở' if not is_open else 'đóng'
        if not msg_confirm(self, 'Xác nhận', f'{"Đóng" if is_open else "Mở"} đăng ký cho {ma}?'):
            return
        if not (DB_AVAILABLE and SemesterService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        try:
            SemesterService.set_status(ma, 'closed' if is_open else 'open')
        except Exception as e:
            print(f'[ADM_TOGGLE_SEM] DB loi: {e}')
            msg_warn(self, 'Lỗi', f'Không cập nhật được trạng thái:\n{api_error_msg(e)}')
            return
        # Re-fill bang de cap nhat ca cot trang thai (cot 5) lan button (cot 6)
        self.pages_filled[6] = False
        self._fill_admin_semester()
        self.pages_filled[6] = True
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
        # Validate input
        if not ma.text().strip() or not ten.text().strip():
            msg_warn(self, 'Thiếu', 'Mã HK và tên không được trống')
            return
        if not (DB_AVAILABLE and SemesterService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # Parse + validate date
        from datetime import datetime
        def parse_dd_mm_yyyy(s):
            return datetime.strptime(s.strip(), '%d/%m/%Y').date()
        try:
            bd_date = parse_dd_mm_yyyy(bd.text())
            kt_date = parse_dd_mm_yyyy(kt.text())
        except ValueError:
            msg_warn(self, 'Sai dữ liệu', 'Ngày phải đúng định dạng dd/mm/yyyy')
            return
        if kt_date <= bd_date:
            msg_warn(self, 'Sai dữ liệu', 'Ngày kết thúc phải sau ngày bắt đầu')
            return
        # Goi API truoc
        try:
            SemesterService.create(
                sem_id=ma.text().strip(), ten=ten.text().strip(), nam_hoc=nam.text().strip(),
                bat_dau=bd_date, ket_thuc=kt_date, trang_thai='open'
            )
        except Exception as e:
            print(f'[ADM_ADD_SEM] DB loi: {e}')
            msg_warn(self, 'Không thêm được', api_error_msg(e))
            return
        # DB OK -> re-fill bang
        self.pages_filled[6] = False
        self._fill_admin_semester()
        self.pages_filled[6] = True
        msg_info(self, 'Thành công', f'Đã thêm học kỳ {ma.text().strip()}')

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
        # Tinh so lop per ma_mon - lay tu cache MOCK_CLASSES (da load tu API)
        # tranh dung db.fetch_all shim (returns []) gay [WARN] khi walkthrough
        ma_mon_count = {}
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
                # cot 8: nut sua/xoa - pattern chuan
                cell, (btn_edit, btn_del) = make_action_cell([('Sửa', 'navy'), ('Xóa', 'red')])
                tbl.setCellWidget(r, 8, cell)
                btn_edit.clicked.connect(lambda ch, rr=r: self._admin_edit_curriculum(rr))
                btn_del.clicked.connect(lambda ch, ma=row[1], nm=row[2], t=tbl: self._admin_del_row(t, ma, nm, 'môn trong CT'))
            # tang cot Hoc ky tu 48 -> 70 cho "Hoc ky X" hien thi du
            for c, cw in enumerate([32, 65, 150, 28, 90, 70, 95, 90, 130]):
                tbl.setColumnWidth(c, cw)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)

        # btnExportCurr o frame khac va o phai - khong day
        widen_search(page, 'txtSearchCurr', 280, ['cboNganh', 'cboLoai', 'cboHocKy'])
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchCurr')
        if txt:
            safe_connect(txt.textChanged, lambda s: table_filter(tbl, s, cols=[1, 2]))
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
                safe_connect(cbo.currentIndexChanged, lambda idx: self._admin_filter_curriculum())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddCurr')
        if btn_add:
            safe_connect(btn_add.clicked, self._admin_add_curriculum)
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportCurr')
        if btn_exp:
            safe_connect(btn_exp.clicked, lambda: export_table_csv(self, tbl, 'khung_chuong_trinh.csv', 'Xuất khung chương trình'))

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

        # Persist via API CurriculumService.update()
        if not (DB_AVAILABLE and CurriculumService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        try:
            # find cur_id by ma_mon (CHUNG voi ma_mon goc cur[1] truoc khi user sua)
            from_curr = CurriculumService.get_all() or []
            old_ma = cur[1]
            cur_id = None
            for cc in from_curr:
                if cc.get('ma_mon') == old_ma:
                    cur_id = cc.get('id')
                    break
            if not cur_id:
                msg_warn(self, 'Không tìm thấy', f'Không tìm thấy môn {old_ma} trong khung CT.')
                return
            type_to_db = {'Bắt buộc': 'Bat buoc', 'Tự chọn': 'Tu chon', 'Đại cương': 'Dai cuong'}
            CurriculumService.update(cur_id,
                ma_mon=new_vals[1],
                tin_chi=int(new_vals[3]),
                loai=type_to_db.get(new_vals[4], new_vals[4]),
                hoc_ky_de_nghi=new_vals[5],
                mon_tien_quyet=new_vals[6] if new_vals[6] != '—' else None)
        except Exception as e:
            print(f'[ADM_EDIT_CURR] loi: {e}')
            msg_warn(self, 'Không lưu được', api_error_msg(e))
            return

        # DB OK -> update UI
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
        # Lay danh sach mon hoc co san - curriculum.ma_mon FK ve courses.ma_mon
        try:
            courses = CourseService.get_all_courses() or []
        except Exception:
            courses = []
        if not courses:
            msg_warn(self, 'Không có môn nào', 'Hãy thêm môn học trước khi đưa vào khung CT.')
            return

        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Thêm môn vào khung CT')
        dlg.setFixedSize(440, 360)
        form = QtWidgets.QFormLayout(dlg)
        # Combobox chon mon (chi mon co san trong courses)
        cbo_mon = QtWidgets.QComboBox()
        for c in courses:
            cbo_mon.addItem(f"{c['ma_mon']} - {c.get('ten_mon', '')}", c['ma_mon'])
        txt_tc = QtWidgets.QLineEdit('3')
        cbo_loai = QtWidgets.QComboBox(); cbo_loai.addItems(['Bắt buộc', 'Tự chọn', 'Đại cương'])
        cbo_hk = QtWidgets.QComboBox(); cbo_hk.addItems([f'HK{i}' for i in range(1, 9)])
        txt_prereq = QtWidgets.QLineEdit()
        txt_prereq.setPlaceholderText('Vd: IT001 (để trống nếu không có)')
        form.addRow('Môn:', cbo_mon)
        form.addRow('Tín chỉ:', txt_tc)
        form.addRow('Loại:', cbo_loai)
        form.addRow('Học kỳ:', cbo_hk)
        form.addRow('Môn tiên quyết:', txt_prereq)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        # Validate tin_chi
        try:
            tin_chi_n = int(txt_tc.text().strip())
            if tin_chi_n < 1 or tin_chi_n > 10:
                raise ValueError()
        except ValueError:
            msg_warn(self, 'Sai dữ liệu', 'Tín chỉ phải là số từ 1-10')
            return
        if not (DB_AVAILABLE and CurriculumService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        ma_mon_sel = cbo_mon.currentData()
        # Goi API truoc
        loai_map = {'Bắt buộc': 'Bat buoc', 'Tự chọn': 'Tu chon', 'Đại cương': 'Dai cuong'}
        try:
            CurriculumService.create(
                ma_mon=ma_mon_sel,
                tin_chi=tin_chi_n,
                loai=loai_map.get(cbo_loai.currentText(), 'Bat buoc'),
                hoc_ky_de_nghi=cbo_hk.currentText(),
                mon_tien_quyet=txt_prereq.text().strip() or None,
                nganh='CNTT',
            )
        except Exception as e:
            print(f'[ADM_ADD_CURR] DB loi: {e}')
            msg_warn(self, 'Không thêm được', api_error_msg(e))
            return
        # DB OK -> re-fill
        self.pages_filled[7] = False
        self._fill_admin_curriculum()
        self.pages_filled[7] = True
        msg_info(self, 'Thành công', f'Đã thêm môn {ma_mon_sel} vào khung CT')

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
        # Populate cbo voi danh sach hoc ky tu API
        page = self.page_widgets[9]
        cbo = page.findChild(QtWidgets.QComboBox, 'cboStatSemester')
        self._stats_sem_ids = []
        default_idx = 0
        if cbo:
            cbo.blockSignals(True)
            cbo.clear()
            sems = []
            current_sem_id = None
            if DB_AVAILABLE:
                try:
                    sems = SemesterService.get_all() or []
                except Exception as e:
                    print(f'[ADM_STATS] sem loi: {e}')
                # Tim sem dang open (current) de default chon
                try:
                    cur = SemesterService.get_current() if SemesterService else None
                    current_sem_id = cur.get('id') if cur else None
                except Exception:
                    pass
            for i, s in enumerate(sems):
                cbo.addItem(f"{s.get('ten', s.get('id', ''))} ({s.get('nam_hoc', '')})")
                sid = s.get('id', '')
                self._stats_sem_ids.append(sid)
                if sid == current_sem_id:
                    default_idx = i
            cbo.setCurrentIndex(default_idx)
            cbo.blockSignals(False)
            safe_connect(cbo.currentIndexChanged, self._render_admin_stats)
        # Render initial voi sem hien tai (khong phai sem cu nhat = idx 0)
        self._render_admin_stats(default_idx)

    def _render_admin_stats(self, idx):
        page = self.page_widgets[9]
        # Lay sem_id tu cbo cache - default HK hien tai
        sem_id = None
        if hasattr(self, '_stats_sem_ids') and 0 <= idx < len(self._stats_sem_ids):
            sem_id = self._stats_sem_ids[idx]

        # Default empty
        ds = {'chart': [], 'dept': [], 'class': []}
        if DB_AVAILABLE and sem_id:
            try:
                stat = StatsService.stats_by_semester(sem_id) or {}
                # Map response: chart=[{ten_mon,cur,mx}], dept=[{khoa,so_hv,so_lop}],
                #               class_stats=[{ma_lop,siso_hien_tai,gpa,doanh_thu}]
                ds['chart'] = [(c.get('ten_mon', '?'),
                                int(c.get('cur', 0) or 0),
                                int(c.get('mx', 40) or 40))
                               for c in stat.get('chart', [])]
                total_hv = sum(int(d.get('so_hv', 0) or 0) for d in stat.get('dept', []))
                ds['dept'] = [[d.get('khoa', '?'),
                               str(d.get('so_hv', 0)),
                               f"{int(d.get('so_hv', 0) or 0)*100//max(total_hv, 1)}%"]
                              for d in stat.get('dept', [])]
                ds['class'] = [[c.get('ma_lop', '?'),
                                str(c.get('siso_hien_tai', 0)),
                                f"{c.get('gpa', 0):.1f}" if c.get('gpa') else '0.0',
                                str(c.get('doanh_thu', 0))]
                               for c in stat.get('class_stats', [])]
            except Exception as e:
                print(f'[ADM_STATS] semester {sem_id} loi: {e}')

        def _render_table_with_empty(tbl, data, fill_func, col_widths):
            """Helper render table voi placeholder empty state."""
            tbl.setRowCount(len(data) if data else 1)
            if not data:
                ph = QtWidgets.QTableWidgetItem('Chưa có dữ liệu')
                ph.setTextAlignment(Qt.AlignCenter)
                ph.setForeground(QColor(COLORS['text_light']))
                tbl.setItem(0, 0, ph)
                tbl.setSpan(0, 0, 1, tbl.columnCount())
                tbl.setRowHeight(0, 50)
            else:
                for r, row in enumerate(data):
                    fill_func(r, row)
                for r in range(len(data)):
                    tbl.setRowHeight(r, 36)
            tbl.horizontalHeader().setStretchLastSection(True)
            for c, w in enumerate(col_widths):
                tbl.setColumnWidth(c, w)
            tbl.verticalHeader().setVisible(False)

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblChartData')
        if tbl:
            def fill_chart(r, row):
                name, cur, mx = row
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
            _render_table_with_empty(tbl, ds['chart'], fill_chart, [160, 60, 60])

        tbl2 = page.findChild(QtWidgets.QTableWidget, 'tblDeptStats')
        if tbl2:
            def fill_dept(r, row):
                for c, val in enumerate(row):
                    tbl2.setItem(r, c, QtWidgets.QTableWidgetItem(val))
            _render_table_with_empty(tbl2, ds['dept'], fill_dept, [100, 60])

        tbl3 = page.findChild(QtWidgets.QTableWidget, 'tblClassStats')
        if tbl3:
            def fill_cls(r, row):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter if c > 0 else Qt.AlignLeft | Qt.AlignVCenter)
                    tbl3.setItem(r, c, item)
            _render_table_with_empty(tbl3, ds['class'], fill_cls, [200, 80, 120])

        # update stat cards neu co
        if ds['chart']:
            totals_regs = sum(d[1] for d in ds['chart'])
            totals_students = sum(int(d[1]) for d in ds['dept']) if ds['dept'] else 0
            for attr, val in [('lblStatTotalRegs', str(totals_regs)),
                              ('lblStatTotalStudents', str(totals_students)),
                              ('lblStatTotalClasses', str(len(ds['chart'])))]:
                wlbl = page.findChild(QtWidgets.QLabel, attr)
                if wlbl:
                    wlbl.setText(val)

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
            # thao tac - dung pattern chuan tu _fill_admin_courses
            cell, (btn_edit, btn_del) = make_action_cell([('Sửa', 'navy'), ('Xóa', 'red')])
            tbl.setCellWidget(r, 7, cell)
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
            safe_connect(txt.textChanged, lambda s: table_filter(tbl, s, cols=[0, 1, 2]))
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
                safe_connect(cbo.currentIndexChanged, lambda: self._admin_filter_classes())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddClass')
        if btn_add:
            safe_connect(btn_add.clicked, self._admin_add_class)

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
        dlg.setFixedSize(440, 460)
        form = QtWidgets.QFormLayout(dlg)
        txt_ma = QtWidgets.QLineEdit(ma_lop); txt_ma.setReadOnly(True)
        txt_ma.setStyleSheet('background: #f7fafc; color: #718096;')
        # Mon: dung combobox de user chon ma_mon hop le (khong cho free type ten)
        cbo_mon = QtWidgets.QComboBox()
        try:
            courses = CourseService.get_all_courses() or []
        except Exception:
            courses = []
        idx_mon_sel = 0
        for i, c in enumerate(courses):
            cbo_mon.addItem(f"{c['ma_mon']} - {c.get('ten_mon', '')}", c['ma_mon'])
            if c['ma_mon'] == mmon:
                idx_mon_sel = i
        cbo_mon.setCurrentIndex(idx_mon_sel)
        # GV: combobox cho cac GV trong DB
        cbo_gv = QtWidgets.QComboBox()
        cbo_gv.addItem('(Chưa phân công)', None)
        idx_gv_sel = 0
        try:
            teachers = TeacherService.get_all() or []
        except Exception:
            teachers = []
        for i, t in enumerate(teachers, start=1):
            tid = t.get('id') or t.get('user_id')
            cbo_gv.addItem(t.get('full_name', ''), tid)
            if (t.get('full_name') or '').strip() == (gv or '').strip():
                idx_gv_sel = i
        cbo_gv.setCurrentIndex(idx_gv_sel)
        txt_lich = QtWidgets.QLineEdit(lich)
        txt_phong = QtWidgets.QLineEdit(phong)
        txt_smax = QtWidgets.QLineEdit(str(smax))
        txt_siso = QtWidgets.QLineEdit(str(siso))
        txt_gia = QtWidgets.QLineEdit(str(gia))
        # so_buoi - lay tu API neu co, mac dinh 24
        cur_so_buoi = 24
        try:
            cls_db = CourseService.get_class(ma_lop) or {}
            cur_so_buoi = int(cls_db.get('so_buoi') or 24)
        except Exception:
            pass
        txt_buoi = QtWidgets.QLineEdit(str(cur_so_buoi))
        form.addRow('Mã lớp:', txt_ma)
        form.addRow('Môn:', cbo_mon)
        form.addRow('Giảng viên:', cbo_gv)
        form.addRow('Lịch học:', txt_lich)
        form.addRow('Phòng:', txt_phong)
        form.addRow('Sĩ số max:', txt_smax)
        form.addRow('Sĩ số hiện tại:', txt_siso)
        form.addRow('Học phí (VND):', txt_gia)
        form.addRow('Số buổi:', txt_buoi)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        try:
            smax_n = int(txt_smax.text())
            siso_n = int(txt_siso.text())
            gia_n = int(txt_gia.text())
            buoi_n = int(txt_buoi.text())
        except ValueError:
            msg_warn(self, 'Sai dữ liệu', 'Sĩ số, học phí và số buổi phải là số')
            return
        if siso_n > smax_n:
            msg_warn(self, 'Sai dữ liệu', 'Sĩ số hiện tại không được lớn hơn sĩ số max')
            return
        if buoi_n < 1 or buoi_n > 100:
            msg_warn(self, 'Sai dữ liệu', 'Số buổi phải trong [1-100]')
            return
        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return

        # Lay ma_mon + gv_id tu combobox (chinh xac, khong drop)
        ma_mon_new = cbo_mon.currentData() or mmon
        gv_id_new = cbo_gv.currentData()  # None neu chua phan cong
        gv_name_new = cbo_gv.currentText() if gv_id_new else ''

        # Goi API - gui DAY DU cac field
        try:
            CourseService.update_class(ma_lop,
                ma_mon=ma_mon_new,
                gv_id=gv_id_new,
                lich=txt_lich.text(), phong=txt_phong.text(),
                siso_max=smax_n, siso_hien_tai=siso_n, gia=gia_n,
                so_buoi=buoi_n,
            )
        except Exception as e:
            print(f'[ADM_EDIT_CLS] DB loi: {e}')
            msg_warn(self, 'Không lưu được', api_error_msg(e))
            return

        # DB OK -> update local cache + re-fill bang
        # tim ten_mon moi (neu user doi mon)
        ten_mon_new = next((c.get('ten_mon', '') for c in courses if c['ma_mon'] == ma_mon_new), tmon)
        MOCK_CLASSES[idx] = (ma_lop, ma_mon_new, ten_mon_new, gv_name_new,
                             txt_lich.text(), txt_phong.text(), smax_n, siso_n, gia_n)
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
        ma_lop = ma.text().upper().strip()

        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return

        # Tim gv_id qua API
        gv_id = None
        try:
            teachers = TeacherService.get_all() or []
            for t in teachers:
                if (t.get('full_name') or '').strip() == gv_name.strip():
                    gv_id = t.get('id') or t.get('user_id')
                    break
        except Exception as e:
            print(f'[ADM_ADD_CLS] tim GV loi: {e}')
            msg_warn(self, 'Lỗi', f'Không lấy được danh sách GV:\n{api_error_msg(e)}')
            return
        if not gv_id:
            msg_warn(self, 'Lỗi', f'Không tìm thấy giảng viên "{gv_name}" trong hệ thống.')
            return

        # Semester hien tai
        sem_id = 'HK2-2526'
        try:
            sem = SemesterService.get_current() if SemesterService else None
            if sem: sem_id = sem.get('id', sem_id)
        except Exception as e:
            print(f'[ADM_ADD_CLS] get_current sem loi: {e}')

        # Goi API tao lop - GUI DAY DU TAT CA FIELD CO TRONG FORM (so_buoi truoc bi drop)
        try:
            CourseService.create_class(
                ma_lop=ma_lop, ma_mon=mon_code, gv_id=gv_id,
                lich=lich.text(), phong=phong.text(),
                siso_max=smax.value(), gia=gia.value(),
                semester_id=sem_id, siso_hien_tai=siso_start.value(),
                so_buoi=so_buoi.value(),
            )
        except Exception as e:
            print(f'[ADM_ADD_CLS] DB loi: {e}')
            msg_warn(self, 'Không thêm được', api_error_msg(e))
            return

        # DB OK -> append cache + refresh UI
        MOCK_CLASSES.append((ma_lop, mon_code, mon_name, gv_name,
                             lich.text(), phong.text(),
                             smax.value(), siso_start.value(), gia.value()))
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
            # thao tac - pattern chuan
            cell, (btn_edit, btn_del) = make_action_cell([('Chi tiết', 'navy'), ('Xóa', 'red')])
            tbl.setCellWidget(r, 7, cell)
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
        # search / filter / add - safe_connect tranh accumulation
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchTea')
        if txt:
            safe_connect(txt.textChanged, lambda s: table_filter(tbl, s, cols=[0, 1]))
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
                safe_connect(cbo.currentIndexChanged, lambda: self._admin_filter_teachers())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddTeacher')
        if btn_add:
            safe_connect(btn_add.clicked, lambda: self._admin_add_user('giảng viên', 4, 'tblAdmTeachers',
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
        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # Goi API truoc khi update UI
        vals = [w.text().strip() for w in widgets]
        try:
            if role_name == 'giảng viên':
                # fields = ['Mã GV', 'Họ tên', 'Khoa', 'Học vị', 'SDT']
                TeacherService.create(
                    username=vals[0].lower(), password='passtea',
                    full_name=vals[1], ma_gv=vals[0],
                    khoa=vals[2] or None, hoc_vi=vals[3] or None, sdt=vals[4] or None,
                )
            elif role_name == 'nhân viên':
                # fields = ['Mã NV', 'Họ tên', 'Chức vụ', 'SDT', 'Email']
                EmployeeService.create(
                    username=vals[0].lower(), password='passemp',
                    full_name=vals[1], ma_nv=vals[0],
                    chuc_vu=vals[2] or None, sdt=vals[3] or None, email=vals[4] or None,
                )
            else:
                msg_warn(self, 'Lỗi', f'Role không hợp lệ: {role_name}')
                return
        except Exception as e:
            print(f'[ADM_ADD_USER] DB loi: {e}')
            msg_warn(self, 'Không thêm được', api_error_msg(e))
            return
        # DB OK -> re-fill bang
        self.pages_filled[page_idx] = False
        if role_name == 'giảng viên':
            self._fill_admin_teachers()
        elif role_name == 'nhân viên':
            self._fill_admin_employees()
        self.pages_filled[page_idx] = True
        default_pwd = 'passtea' if role_name == 'giảng viên' else 'passemp'
        msg_info(self, 'Thành công', f'Đã thêm {role_name}: {vals[1]} (mật khẩu mặc định: {default_pwd})')

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
            # thao tac - pattern chuan
            cell, (btn_edit, btn_del) = make_action_cell([('Chi tiết', 'navy'), ('Xóa', 'red')])
            tbl.setCellWidget(r, 6, cell)
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
        # search / filter / add - safe_connect
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchEmp')
        if txt:
            safe_connect(txt.textChanged, lambda s: table_filter(tbl, s, cols=[0, 1]))
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
                safe_connect(cbo.currentIndexChanged, lambda: self._admin_filter_employees())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddEmp')
        if btn_add:
            safe_connect(btn_add.clicked, lambda: self._admin_add_user('nhân viên', 5, 'tblAdmEmployees',
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

        # 3. Wire signal - safe_connect tranh accumulation moi lan re-fill
        if cbo_cls:
            safe_connect(cbo_cls.currentIndexChanged, self._on_attend_class_changed)
        cbo_buoi = page.findChild(QtWidgets.QComboBox, 'cboAttendBuoi')
        if cbo_buoi:
            safe_connect(cbo_buoi.currentIndexChanged, self._on_attend_buoi_changed)

        btn_save = page.findChild(QtWidgets.QPushButton, 'btnSaveAttend')
        if btn_save:
            safe_connect(btn_save.clicked, self._save_attendance)
        btn_all = page.findChild(QtWidgets.QPushButton, 'btnMarkAllPresent')
        if btn_all:
            safe_connect(btn_all.clicked, self._mark_all_present)

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
        clear_session_state()
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

        # Today schedule - lay tu API ScheduleService.get_today() filter theo gv_id
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblToday')
        if tbl:
            data = []
            if DB_AVAILABLE and gv_id and ScheduleService:
                try:
                    today_rows = ScheduleService.get_today() or []
                    for r in today_rows:
                        # filter buoi cua gv hien tai
                        if r.get('gv_id') and r.get('gv_id') != gv_id:
                            continue
                        gio_bd = str(r.get('gio_bat_dau', ''))[:5]
                        gio_kt = str(r.get('gio_ket_thuc', ''))[:5]
                        time_str = f'{gio_bd}-{gio_kt}' if gio_bd else '—'
                        ma_lop = r.get('lop_id', '')
                        ten_mon = r.get('ten_mon', '')
                        data.append([
                            time_str,
                            f'{ma_lop} ({ten_mon})' if ten_mon else ma_lop,
                            r.get('phong', '') or '—',
                        ])
                except Exception as e:
                    print(f'[TEA_DASH] today loi: {e}')
            tbl.setRowCount(len(data) if data else 1)
            if not data:
                ph = QtWidgets.QTableWidgetItem('Hôm nay không có buổi dạy')
                ph.setTextAlignment(Qt.AlignCenter)
                ph.setForeground(QColor(COLORS['text_light']))
                tbl.setItem(0, 0, ph)
                tbl.setSpan(0, 0, 1, tbl.columnCount())
                tbl.setRowHeight(0, 50)
            else:
                for r, row in enumerate(data):
                    for c, val in enumerate(row):
                        item = QtWidgets.QTableWidgetItem(val)
                        item.setTextAlignment(Qt.AlignCenter if c != 1 else Qt.AlignLeft | Qt.AlignVCenter)
                        tbl.setItem(r, c, item)
                for r in range(len(data)):
                    tbl.setRowHeight(r, 38)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setColumnWidth(0, 100)
            tbl.setColumnWidth(1, 180)
            tbl.verticalHeader().setVisible(False)

        # Activity - dung NotificationService.get_sent_by_teacher() de hien activity gan day
        tbl2 = page.findChild(QtWidgets.QTableWidget, 'tblActivity')
        if tbl2:
            data = []
            if DB_AVAILABLE and gv_id:
                try:
                    sent = NotificationService.get_sent_by_teacher(gv_id, limit=5) or []
                    for n in sent:
                        t_str = fmt_date(n.get('ngay_tao'), fmt='%d/%m %H:%M')
                        target = n.get('den_lop') or 'Tat ca'
                        data.append((t_str, f"Đã gửi '{n.get('tieu_de', '')}' đến {target}"))
                except Exception as e:
                    print(f'[TEA_DASH] activity loi: {e}')
            tbl2.setRowCount(len(data) if data else 1)
            if not data:
                ph = QtWidgets.QTableWidgetItem('Chưa có hoạt động')
                ph.setTextAlignment(Qt.AlignCenter)
                ph.setForeground(QColor(COLORS['text_light']))
                tbl2.setItem(0, 0, ph)
                tbl2.setSpan(0, 0, 1, tbl2.columnCount())
                tbl2.setRowHeight(0, 50)
            else:
                for r, (t, c) in enumerate(data):
                    ti = QtWidgets.QTableWidgetItem(t)
                    ti.setForeground(QColor(COLORS['text_light']))
                    ti.setFont(QFont('Segoe UI', 9))
                    tbl2.setItem(r, 0, ti)
                    tbl2.setItem(r, 1, QtWidgets.QTableWidgetItem(c))
                for r in range(len(data)):
                    tbl2.setRowHeight(r, 38)
            tbl2.horizontalHeader().setStretchLastSection(True)
            tbl2.setColumnWidth(0, 110)
            tbl2.verticalHeader().setVisible(False)

    def _fill_tea_schedule(self):
        # tái sử dụng schedule.ui giống HV nhưng lịch của GV
        page = self.page_widgets[1]

        hb = page.findChild(QtWidgets.QFrame, 'headerBar')
        if hb:
            hb.setGeometry(0, 0, 870, 56)
        sf = page.findChild(QtWidgets.QFrame, 'scheduleFrame')
        if sf:
            sf.setGeometry(15, 68, 615, 618)
        cf = page.findChild(QtWidgets.QFrame, 'calendarFrame')
        if cf:
            cf.setGeometry(635, 68, 225, 230)
        lf = page.findChild(QtWidgets.QFrame, 'legendFrame')
        if lf:
            lf.setGeometry(635, 308, 225, 190)
        cal_w = page.findChild(QtWidgets.QCalendarWidget, 'calendarWidget')
        if cal_w:
            cal_w.hide()

        # Tao nav panel inside calendarFrame: tieu de + nut prev/today/next
        if cf and not cf.findChild(QtWidgets.QPushButton, 'btnPrevWeek'):
            nav_title = QtWidgets.QLabel('Điều hướng tuần', cf)
            nav_title.setObjectName('lblNavTitle')
            nav_title.setGeometry(15, 12, 195, 20)
            nav_title.setStyleSheet('color: #1a1a2e; font-size: 13px; font-weight: bold; background: transparent;')
            nav_title.show()

            self._lblNavWeekTea = QtWidgets.QLabel('—', cf)
            self._lblNavWeekTea.setObjectName('lblNavWeek')
            self._lblNavWeekTea.setGeometry(15, 38, 195, 40)
            self._lblNavWeekTea.setStyleSheet('color: #002060; font-size: 12px; font-weight: bold; background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px;')
            self._lblNavWeekTea.setAlignment(Qt.AlignCenter)
            self._lblNavWeekTea.setWordWrap(True)
            self._lblNavWeekTea.show()

            btn_prev = QtWidgets.QPushButton('‹ Tuần trước', cf)
            btn_prev.setObjectName('btnPrevWeek')
            btn_prev.setGeometry(15, 92, 95, 32)
            btn_prev.setStyleSheet('QPushButton { background: white; color: #4a5568; border: 1px solid #d2d6dc; border-radius: 6px; font-size: 11px; } QPushButton:hover { background: #edf2f7; border-color: #002060; color: #002060; }')
            btn_prev.setCursor(Qt.PointingHandCursor)
            btn_prev.show()

            btn_next = QtWidgets.QPushButton('Tuần sau ›', cf)
            btn_next.setObjectName('btnNextWeek')
            btn_next.setGeometry(115, 92, 95, 32)
            btn_next.setStyleSheet(btn_prev.styleSheet())
            btn_next.setCursor(Qt.PointingHandCursor)
            btn_next.show()

            btn_today = QtWidgets.QPushButton('Tuần hiện tại', cf)
            btn_today.setObjectName('btnTodayWeek')
            btn_today.setGeometry(15, 132, 195, 32)
            btn_today.setStyleSheet('QPushButton { background: #002060; color: white; border: none; border-radius: 6px; font-size: 11px; font-weight: bold; } QPushButton:hover { background: #003080; }')
            btn_today.setCursor(Qt.PointingHandCursor)
            btn_today.show()

            hint = QtWidgets.QLabel('Dùng nút trên để chuyển tuần', cf)
            hint.setObjectName('lblNavHint')
            hint.setGeometry(15, 175, 195, 40)
            hint.setStyleSheet('color: #a0aec0; font-size: 10px; background: transparent;')
            hint.setWordWrap(True)
            hint.setAlignment(Qt.AlignCenter)
            hint.show()

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblSchedule')
        if not tbl:
            return
        tbl.setGeometry(0, 0, 615, 618)
        hours = ['7:00','8:00','9:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00']
        tbl.setRowCount(len(hours))
        tbl.verticalHeader().setVisible(False)
        days_vn = ['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7']

        tbl.setColumnWidth(0, 45)
        for i in range(1, 7):
            tbl.setColumnWidth(i, 92)

        for r in range(len(hours)):
            tbl.setRowHeight(r, 50)
            item = QtWidgets.QTableWidgetItem(hours[r])
            item.setTextAlignment(Qt.AlignRight | Qt.AlignTop)
            item.setForeground(QColor('#718096'))
            item.setFont(QFont('Segoe UI', 9))
            tbl.setItem(r, 0, item)

        # Label hien thi tuan dang xem (header)
        title = page.findChild(QtWidgets.QLabel, 'lblPageTitle')
        if title and not page.findChild(QtWidgets.QLabel, 'lblWeekRange'):
            wr = QtWidgets.QLabel(page)
            wr.setObjectName('lblWeekRange')
            wr.setGeometry(180, 0, 450, 56)
            wr.setStyleSheet('color: #4a5568; font-size: 13px; background: transparent;')
            wr.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            wr.show()

        today = QDate.currentDate()
        self._tea_current_monday = today.addDays(-(today.dayOfWeek() - 1))
        gv_id = MOCK_TEACHER.get('user_id')
        if DB_AVAILABLE and gv_id:
            try:
                near = ScheduleService.nearest_week_for_teacher(gv_id, today.toPyDate())
                if near:
                    from datetime import date as _date
                    if isinstance(near, str):
                        near = _date.fromisoformat(near)
                    self._tea_current_monday = QDate(near.year, near.month, near.day)
            except Exception as e:
                print(f'[TEA_SCHED] nearest_week loi: {e}')
        self._load_teacher_schedule_week(page, tbl, self._tea_current_monday, hours, days_vn)

        # Wire prev/next/today buttons
        btn_prev = cf.findChild(QtWidgets.QPushButton, 'btnPrevWeek') if cf else None
        btn_next = cf.findChild(QtWidgets.QPushButton, 'btnNextWeek') if cf else None
        btn_today = cf.findChild(QtWidgets.QPushButton, 'btnTodayWeek') if cf else None
        if btn_prev:
            btn_prev.clicked.connect(lambda: (
                setattr(self, '_tea_current_monday', self._tea_current_monday.addDays(-7)),
                self._load_teacher_schedule_week(page, tbl, self._tea_current_monday, hours, days_vn)
            ))
        if btn_next:
            btn_next.clicked.connect(lambda: (
                setattr(self, '_tea_current_monday', self._tea_current_monday.addDays(7)),
                self._load_teacher_schedule_week(page, tbl, self._tea_current_monday, hours, days_vn)
            ))
        if btn_today:
            btn_today.clicked.connect(lambda: (
                setattr(self, '_tea_current_monday', QDate.currentDate().addDays(-(QDate.currentDate().dayOfWeek() - 1))),
                self._load_teacher_schedule_week(page, tbl, self._tea_current_monday, hours, days_vn)
            ))

    def _load_teacher_schedule_week(self, page, tbl, monday, hours, days_vn):
        """Reload lich day GV cho tuan bat dau bang `monday` (QDate)."""
        for i in range(6):
            d = monday.addDays(i)
            hi = tbl.horizontalHeaderItem(i+1)
            if hi:
                hi.setText(f'{d.toString("dd/MM/yyyy")}\n{days_vn[i]}')
        wr_lbl = page.findChild(QtWidgets.QLabel, 'lblWeekRange')
        if wr_lbl:
            wr_lbl.setText(f'Tuần: {monday.toString("dd/MM/yyyy")} → {monday.addDays(5).toString("dd/MM/yyyy")}')
        nav_lbl = page.findChild(QtWidgets.QLabel, 'lblNavWeek')
        if nav_lbl:
            nav_lbl.setText(f'{monday.toString("dd/MM/yyyy")}\n→ {monday.addDays(5).toString("dd/MM/yyyy")}')

        # Xoa cell cu
        for r in range(len(hours)):
            for c in range(1, 7):
                cw = tbl.cellWidget(r, c)
                if cw:
                    tbl.removeCellWidget(r, c)
                if tbl.rowSpan(r, c) > 1 or tbl.columnSpan(r, c) > 1:
                    tbl.setSpan(r, c, 1, 1)
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(''))

        def mk(ma_lop, ten_mon, ts, phong, ss, color):
            f = QtWidgets.QFrame()
            f.setStyleSheet(f'QFrame {{ background: white; border: 1px solid #d2d6dc; border-radius: 4px; border-top: 3px solid {color}; margin: 1px; }}')
            vb = QtWidgets.QVBoxLayout(f)
            vb.setContentsMargins(4, 3, 4, 3)
            vb.setSpacing(1)
            l1 = QtWidgets.QLabel(ma_lop)
            l1.setStyleSheet(f'color: {color}; font-size: 11px; font-weight: bold; border: none; background: transparent;')
            l1.setWordWrap(False)
            vb.addWidget(l1)
            l2 = QtWidgets.QLabel(ten_mon)
            l2.setStyleSheet('color: #2d3748; font-size: 10px; border: none; background: transparent;')
            l2.setWordWrap(True)
            vb.addWidget(l2)
            l3 = QtWidgets.QLabel(ts)
            l3.setStyleSheet('color: #4a5568; font-size: 9px; font-weight: bold; border: none; background: transparent;')
            vb.addWidget(l3)
            phong_disp = phong if phong.lower().startswith(('p.', 'p ', 'phòng', 'phong')) else f'P. {phong}'
            l4 = QtWidgets.QLabel(phong_disp)
            l4.setStyleSheet('color: #718096; font-size: 9px; border: none; background: transparent;')
            vb.addWidget(l4)
            l5 = QtWidgets.QLabel(ss)
            l5.setStyleSheet('color: #4a5568; font-size: 9px; border: none; background: transparent;')
            vb.addWidget(l5)
            vb.addStretch()
            return f

        gv_id = MOCK_TEACHER.get('user_id')
        sched = []
        if DB_AVAILABLE and gv_id and ScheduleService:
            try:
                rows = ScheduleService.get_for_teacher_week(gv_id, monday.toPyDate()) or []
                colors = ['#002060', '#c68a1e', '#276749', '#c53030', '#3182ce']
                color_by_lop = {}
                from datetime import date as _date
                for r in rows:
                    try:
                        d = r['ngay'] if isinstance(r['ngay'], _date) else _date.fromisoformat(str(r['ngay'])[:10])
                        wd = d.weekday()
                        if wd > 5: continue
                        col = wd + 1
                        gio_bd = str(r.get('gio_bat_dau', ''))[:5]
                        gio_kt = str(r.get('gio_ket_thuc', ''))[:5]
                        try:
                            hour_idx = int(gio_bd.split(':')[0]) - 7
                        except Exception:
                            hour_idx = 0
                        if hour_idx < 0 or hour_idx >= len(hours): continue
                        try:
                            h1, m1 = gio_bd.split(':'); h2, m2 = gio_kt.split(':')
                            span = max(1, round(((int(h2)*60+int(m2)) - (int(h1)*60+int(m1))) / 60))
                        except Exception:
                            span = 3
                        ma_lop = r.get('lop_id', '')
                        if ma_lop not in color_by_lop:
                            color_by_lop[ma_lop] = colors[len(color_by_lop) % len(colors)]
                        siso = r.get('siso_hien_tai', '?')
                        sched.append((
                            hour_idx, span, col,
                            ma_lop,
                            r.get("ten_mon", "") or '',
                            f'{gio_bd}-{gio_kt}',
                            r.get('phong', '') or '—',
                            f'{siso} HV',
                            color_by_lop[ma_lop],
                        ))
                    except Exception as e:
                        print(f'[TEA_SCHED] parse: {e}')
            except Exception as e:
                print(f'[TEA_SCHED] API loi: {e}')

        if not sched:
            ph = QtWidgets.QFrame()
            ph.setStyleSheet('QFrame { background: #f7fafc; border: 1px dashed #cbd5e0; border-radius: 6px; }')
            vb = QtWidgets.QVBoxLayout(ph)
            vb.setContentsMargins(12, 12, 12, 12)
            vb.setAlignment(Qt.AlignCenter)
            l1 = QtWidgets.QLabel('Tuần này không có lịch dạy')
            l1.setStyleSheet('color: #4a5568; font-size: 13px; font-weight: bold; border: none; background: transparent;')
            l1.setAlignment(Qt.AlignCenter)
            l2 = QtWidgets.QLabel('Chọn tuần khác trên lịch bên phải')
            l2.setStyleSheet('color: #718096; font-size: 11px; border: none; background: transparent;')
            l2.setAlignment(Qt.AlignCenter)
            vb.addWidget(l1)
            vb.addWidget(l2)
            tbl.setCellWidget(3, 1, ph)
            tbl.setSpan(3, 1, 4, 6)
        else:
            for rs, span, col, ma_lop, ten_mon, ts, phong, ss, color in sched:
                tbl.setCellWidget(rs, col, mk(ma_lop, ten_mon, ts, phong, ss, color))
                tbl.setSpan(rs, col, span, 1)

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
            # action: xem chi tiet - DUNG PATTERN cua tblReview (da work)
            btn = QtWidgets.QPushButton('Chi tiết')
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(82, 24)
            btn.setStyleSheet(
                f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; '
                f'border-radius: 5px; font-size: 11px; font-weight: bold; }} '
                f'QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}'
            )
            btn.clicked.connect(lambda ch, m=ma, n=tmon, s=siso, mx=smax, p=phong, l=lich, g=gia:
                show_detail_dialog(self, 'Chi tiết lớp', [
                    ('Mã lớp', m), ('Môn học', n), ('Giảng viên', MOCK_TEACHER['name']),
                    ('Lịch học', l), ('Phòng', p),
                    ('Sĩ số', f'{s}/{mx}'),
                    ('Học phí', f'{g:,}'.replace(',', '.') + ' đ'),
                ], avatar_text=m, subtitle=n))
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(btn)
            tbl.setCellWidget(r, 6, w)
        for c, cw in enumerate([80, 175, 75, 145, 65, 115, 130]):
            tbl.setColumnWidth(c, cw)
        tbl.horizontalHeader().setStretchLastSection(False)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(my_classes)):
            tbl.setRowHeight(r, 50)

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
        # filter + search - safe_connect tranh accumulation
        txt_s = page.findChild(QtWidgets.QLineEdit, 'txtSearchStudent')
        if txt_s:
            safe_connect(txt_s.textChanged, lambda t: table_filter(tbl, t, cols=[1, 2]))
        if cbo:
            safe_connect(cbo.currentIndexChanged, lambda: self._filter_tea_students())
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportStudents')
        if btn_exp:
            safe_connect(btn_exp.clicked, lambda: export_table_csv(self, tbl, 'ds_hocvien.csv', 'Xuất danh sách học viên'))

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

        # Populate sent list - lay tu API NotificationService.get_sent_by_teacher()
        sc = page.findChild(QtWidgets.QWidget, 'sentContent')
        if sc:
            sc.setMinimumHeight(500)
            # Clear cu neu da co layout
            if sc.layout() is None:
                vlay = QtWidgets.QVBoxLayout(sc)
                vlay.setContentsMargins(4, 4, 4, 4)
                vlay.setSpacing(8)
            else:
                vlay = sc.layout()
                while vlay.count():
                    it = vlay.takeAt(0)
                    if it.widget():
                        it.widget().deleteLater()
            self._tea_notice_layout = vlay

            sent_data = []
            gv_id = MOCK_TEACHER.get('user_id')
            if DB_AVAILABLE and gv_id:
                try:
                    rows = NotificationService.get_sent_by_teacher(gv_id, limit=10) or []
                    for n in rows:
                        target = n.get('den_lop') or 'Tất cả'
                        sent_data.append((
                            target,
                            n.get('tieu_de', '') or '(không tiêu đề)',
                            fmt_date(n.get('ngay_tao'), fmt='%d/%m/%Y %H:%M'),
                        ))
                except Exception as e:
                    print(f'[TEA_NOTICE] sent loi: {e}')

            if not sent_data:
                empty = QtWidgets.QLabel('Chưa gửi thông báo nào')
                empty.setStyleSheet(f'color: {COLORS["text_light"]}; font-size: 13px; padding: 20px;')
                empty.setAlignment(Qt.AlignCenter)
                vlay.addWidget(empty)
            else:
                for to, subj, t in sent_data:
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
        gv_user_id = MOCK_TEACHER.get('user_id')
        if not (DB_AVAILABLE and gv_user_id):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # Goi API truoc
        den_lop = target if cbo.currentIndex() > 0 else None
        try:
            NotificationService.send(gv_user_id, title, body, den_lop=den_lop, loai='info')
        except Exception as e:
            print(f'[NOTICE] loi: {e}')
            msg_warn(self, 'Không gửi được', api_error_msg(e))
            return
        # API OK -> them card vao dau danh sach
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
            safe_connect(cbo.currentIndexChanged, lambda idx: self._tea_grades_render(tbl, cbo.currentText() if idx > 0 else None))

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

        # Lay 1 phat tat ca attendance_rate cua HV trong lop nay qua API (tranh N+1)
        rates_by_msv = {}
        try:
            rows = AttendanceService.class_summary(ma_lop) or []
            for r in rows:
                if r.get('total'):
                    rates_by_msv[r['msv']] = r.get('rate', 0.0)
            print(f"[SYNC_CC] lop={ma_lop} - tim thay attendance cua {len(rates_by_msv)} HV")
        except Exception as e:
            print(f'[SYNC_CC] API class_summary loi: {e}')
            msg_warn(self, 'Không sync được',
                     f'Không lấy được dữ liệu điểm danh từ hệ thống:\n{api_error_msg(e)}\n\n'
                     'Hãy kiểm tra kết nối backend và thử lại.')
            return

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
                    # check xem msv co trong DB khong qua API
                    try:
                        hv = StudentService.get_by_msv(msv)
                    except Exception:
                        hv = None
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
        # Col widths: 8 cot dau fixed, cot Thao tac (last) auto-stretch
        for c, cw in enumerate([40, 95, 175, 70, 70, 70, 70, 65]):
            tbl.setColumnWidth(c, cw)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 50)  # PATTERN tblReview: row 50 cho button 24 co cho center
            # Nut Nhap diem - DUNG PATTERN tblReview
            btn_enter = QtWidgets.QPushButton('Nhập điểm')
            btn_enter.setCursor(Qt.PointingHandCursor)
            btn_enter.setFixedSize(82, 24)
            btn_enter.setStyleSheet(
                f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; '
                f'border-radius: 5px; font-size: 11px; font-weight: bold; }} '
                f'QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}'
            )
            btn_enter.clicked.connect(lambda ch, rr=r: self._tea_grade_dialog(tbl, rr))
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setAlignment(Qt.AlignCenter)
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
        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        page = self.page_widgets[6]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblTeacherGrades')
        cbo = page.findChild(QtWidgets.QComboBox, 'cboGradeClass')
        gv_user_id = MOCK_TEACHER.get('user_id')
        lop_id = cbo.currentText() if cbo and cbo.currentIndex() > 0 else None
        if not (tbl and lop_id and gv_user_id):
            msg_warn(self, 'Thiếu', 'Hãy chọn lớp cụ thể trước khi lưu điểm.')
            return

        saved = 0
        skipped = []  # list (msv, ly_do)
        for r in range(tbl.rowCount()):
            msv = ''
            try:
                msv = (tbl.item(r, 1).text() or '').strip() if tbl.item(r, 1) else ''
                if not msv:
                    continue
                qt_text = (tbl.item(r, 4).text() if tbl.item(r, 4) else '0').replace(',', '.')
                thi_text = (tbl.item(r, 5).text() if tbl.item(r, 5) else '0').replace(',', '.')
                qt = float(qt_text)
                thi = float(thi_text)
                if not (0 <= qt <= 10 and 0 <= thi <= 10):
                    skipped.append((msv, 'điểm ngoài [0-10]'))
                    continue
                hv = StudentService.get_by_msv(msv)
                if not hv:
                    skipped.append((msv, 'không có trong DB'))
                    continue
                uid = hv.get('user_id') or hv.get('id')
                GradeService.save_grade(uid, lop_id, qt, thi, gv_user_id)
                saved += 1
            except Exception as e:
                print(f'[GRADE] {msv} loi: {e}')
                skipped.append((msv, api_error_msg(e)[:60]))

        # Bao cao chi tiet
        n_total = tbl.rowCount()
        if saved == n_total:
            msg_info(self, 'Thành công', f'Đã lưu điểm cho tất cả {saved} học viên.')
        elif saved > 0:
            tail = '\n• '.join([f'{m}: {ly}' for m, ly in skipped[:5]])
            extra = f'\n\nKhông lưu được {len(skipped)} HV:\n• {tail}'
            if len(skipped) > 5:
                extra += f'\n  (+ {len(skipped) - 5} dòng khác)'
            msg_warn(self, 'Lưu một phần', f'Đã lưu {saved}/{n_total} HV.{extra}')
        else:
            tail = '\n• '.join([f'{m}: {ly}' for m, ly in skipped[:5]])
            msg_warn(self, 'Không lưu được', f'Tất cả {n_total} HV đều fail:\n• {tail}')

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
            btn_save.clicked.connect(self._save_tea_profile)
        btn_cp = page.findChild(QtWidgets.QPushButton, 'btnChangePass')
        if btn_cp:
            btn_cp.clicked.connect(lambda: self._tea_change_pass())

    def _save_tea_profile(self):
        page = self.page_widgets[7]
        email = page.findChild(QtWidgets.QLineEdit, 'txtEmail')
        phone = page.findChild(QtWidgets.QLineEdit, 'txtPhone')
        updates = {}
        if email:
            updates['email'] = email.text().strip()
        if phone:
            updates['sdt'] = phone.text().strip()
        # Validate
        if updates.get('email') and not is_valid_email(updates['email']):
            msg_warn(self, 'Sai định dạng', 'Email không hợp lệ (vd: ten@example.com)')
            return
        if updates.get('sdt') and not is_valid_phone_vn(updates['sdt']):
            msg_warn(self, 'Sai định dạng', 'Số điện thoại không hợp lệ (10-11 chữ số)')
            return

        gv_user_id = MOCK_TEACHER.get('user_id')
        if not (DB_AVAILABLE and gv_user_id and updates):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # API truoc, MOCK sau
        try:
            TeacherService.update(gv_user_id, **updates)
        except Exception as e:
            print(f'[TEA_PROFILE] loi: {e}')
            msg_warn(self, 'Không lưu được', api_error_msg(e))
            return
        for k, v in updates.items():
            MOCK_TEACHER[k] = v
        msg_info(self, 'Thành công', 'Đã lưu thông tin cá nhân.')

    def _tea_change_pass(self):
        new = msg_input(self, 'Đổi mật khẩu', 'Nhập mật khẩu mới:')
        if not new:
            return
        gv_user_id = MOCK_TEACHER.get('user_id')
        if not (DB_AVAILABLE and gv_user_id):
            msg_warn(self, 'Lỗi', 'Không xác định được tài khoản. Hãy đăng nhập lại.')
            return
        try:
            AuthService.change_password(gv_user_id, new)
            MOCK_TEACHER['password'] = new
            msg_info(self, 'Thành công', 'Đổi mật khẩu thành công.')
        except Exception as e:
            msg_warn(self, 'Lỗi', f'Đổi mật khẩu thất bại:\n{e}')


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
        clear_session_state()
        self.close()
        self.app_ref.show_login()

    # === EMPLOYEE DATA FILL ===

    def _fill_emp_dashboard(self):
        page = self.page_widgets[0]
        emp_id = MOCK_EMPLOYEE.get('user_id')

        # Stat cards: today reg / paid / revenue / pending - tu API
        if DB_AVAILABLE and emp_id:
            try:
                stat = StatsService.employee_today(emp_id) or {}
                for attr, key, fmt in [
                    ('lblStatRegToday', 'today_reg', str),
                    ('lblStatPaidToday', 'today_paid', str),
                    ('lblStatRevenueToday', 'today_revenue',
                     lambda v: f"{int(v):,}".replace(',', '.') + ' đ' if v else '0 đ'),
                    ('lblStatPending', 'pending', str),
                ]:
                    wlbl = page.findChild(QtWidgets.QLabel, attr)
                    if wlbl:
                        v = stat.get(key, 0)
                        wlbl.setText(fmt(v) if v is not None else '0')
            except Exception as e:
                print(f'[EMP_DASH] stats loi: {e}')

        # tblPending: cac DK chua TT - tu API
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblPending')
        if tbl:
            data = []
            if DB_AVAILABLE:
                try:
                    rows = StatsService.recent_pending_registrations(limit=5) or []
                    data = [(r.get('ten_hv', '') or r.get('full_name', ''),
                             r.get('lop_id', ''),
                             {'pending_payment': 'Chờ thanh toán'}.get(
                                 r.get('trang_thai', ''), r.get('trang_thai', '')))
                            for r in rows]
                except Exception as e:
                    print(f'[EMP_DASH] pending loi: {e}')
            tbl.setRowCount(len(data) if data else 1)
            if not data:
                ph = QtWidgets.QTableWidgetItem('Chưa có đăng ký chờ xử lý')
                ph.setTextAlignment(Qt.AlignCenter)
                ph.setForeground(QColor(COLORS['text_light']))
                tbl.setItem(0, 0, ph)
                tbl.setSpan(0, 0, 1, tbl.columnCount())
                tbl.setRowHeight(0, 50)
            else:
                for r, (n, cls, st) in enumerate(data):
                    tbl.setItem(r, 0, QtWidgets.QTableWidgetItem(n))
                    item_cls = QtWidgets.QTableWidgetItem(cls)
                    item_cls.setTextAlignment(Qt.AlignCenter)
                    tbl.setItem(r, 1, item_cls)
                    item_st = QtWidgets.QTableWidgetItem(st)
                    item_st.setForeground(QColor(COLORS['orange']))
                    item_st.setTextAlignment(Qt.AlignCenter)
                    tbl.setItem(r, 2, item_st)
                for r in range(len(data)):
                    tbl.setRowHeight(r, 38)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setColumnWidth(0, 150)
            tbl.setColumnWidth(1, 90)
            tbl.verticalHeader().setVisible(False)

        # tblActivityEmp: hoat dong gan day - tu API
        tbl2 = page.findChild(QtWidgets.QTableWidget, 'tblActivityEmp')
        if tbl2:
            data = []
            if DB_AVAILABLE:
                try:
                    acts = StatsService.recent_activity(limit=5) or []
                    data = [(str(a.get('thoi_gian', ''))[:16], a.get('noi_dung', '')) for a in acts]
                except Exception as e:
                    print(f'[EMP_DASH] activity loi: {e}')
            tbl2.setRowCount(len(data) if data else 1)
            if not data:
                ph = QtWidgets.QTableWidgetItem('Chưa có hoạt động')
                ph.setTextAlignment(Qt.AlignCenter)
                ph.setForeground(QColor(COLORS['text_light']))
                tbl2.setItem(0, 0, ph)
                tbl2.setSpan(0, 0, 1, tbl2.columnCount())
                tbl2.setRowHeight(0, 50)
            else:
                for r, (t, c) in enumerate(data):
                    ti = QtWidgets.QTableWidgetItem(t)
                    ti.setForeground(QColor(COLORS['text_light']))
                    ti.setFont(QFont('Segoe UI', 9))
                    tbl2.setItem(r, 0, ti)
                    tbl2.setItem(r, 1, QtWidgets.QTableWidgetItem(c))
                for r in range(len(data)):
                    tbl2.setRowHeight(r, 38)
            tbl2.horizontalHeader().setStretchLastSection(True)
            tbl2.setColumnWidth(0, 110)
            tbl2.verticalHeader().setVisible(False)

    def _fill_emp_register(self):
        page = self.page_widgets[1]
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboCourse')
        if cbo_c:
            cbo_c.clear()
            cbo_c.addItem('-- Chọn môn học --')
            for code, name in MOCK_COURSES:
                cbo_c.addItem(f'{code} - {name}')
            safe_connect(cbo_c.currentIndexChanged, self._emp_filter_classes)
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
        # === CHECK DUPLICATE: HV da dang ky lop nay chua? ===
        if DB_AVAILABLE:
            try:
                hv_check = StudentService.get_by_msv(msv.text().strip())
                if hv_check:
                    hv_uid_check = hv_check.get('user_id') or hv_check.get('id')
                    existing = CourseService.get_classes_by_student(hv_uid_check) or []
                    for cls in existing:
                        if cls.get('ma_lop') == lop_code and cls.get('reg_status') in ('pending_payment', 'paid', 'completed'):
                            msg_warn(self, 'Đã đăng ký',
                                     f'Học viên {msv.text().strip()} đã đăng ký lớp {lop_code} rồi '
                                     f'(trạng thái: {cls.get("reg_status")}). Không thể đăng ký lại.')
                            return
            except Exception as e:
                print(f'[REG] check duplicate loi: {e}')
        if DB_AVAILABLE and CurriculumService:
            try:
                hv_row = StudentService.get_by_msv(msv.text().strip())
                if hv_row and ma_mon_lop:
                    hv_uid = hv_row.get('user_id') or hv_row.get('id')
                    check = CurriculumService.check_prerequisites_for_student(
                        hv_uid, ma_mon_lop)
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
                hv_row = StudentService.get_by_msv(msv.text().strip())
                nv_id = MOCK_EMPLOYEE.get('user_id')
                if hv_row and nv_id:
                    hv_uid = hv_row.get('user_id') or hv_row.get('id')
                    saved_id = RegistrationService.register_student(
                        hv_uid, lop_code, nv_id
                    )
            except Exception as e:
                print(f'[REG] loi: {e}')
                msg_warn(self, 'Lỗi', f'Đăng ký thất bại:\n{e}')
                return
        if saved_id:
            msg_info(self, 'Thành công', f'Đã đăng ký cho {hoten.text()} - Mã đăng ký #{saved_id}')
        else:
            msg_warn(self, 'Lỗi', 'Không xác định được học viên hoặc nhân viên. Hãy kiểm tra MSV.')
            return
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
            # action - 2 nut: Xem + Hủy. An nut Huy neu da huy/hoan thanh
            btn_view = QtWidgets.QPushButton('Xem')
            btn_view.setCursor(Qt.PointingHandCursor)
            btn_view.setFixedSize(48, 22)
            btn_view.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 3px; font-size: 10px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
            btn_view.clicked.connect(lambda ch, rdata=row: show_detail_dialog(
                self, 'Chi tiết đăng ký',
                [('Mã đăng ký', rdata[0]), ('Ngày đăng ký', rdata[1]),
                 ('Học viên', rdata[2]), ('Lớp', rdata[3]),
                 ('Học phí', f'{rdata[4]} đ'), ('Trạng thái', rdata[5])],
                avatar_text='DK', subtitle=rdata[2]))
            btn_cancel = QtWidgets.QPushButton('Hủy')
            btn_cancel.setCursor(Qt.PointingHandCursor)
            btn_cancel.setFixedSize(40, 22)
            # an nut huy neu trang thai khong cho phep
            cur_status = 'Đã thanh toán' if row[0] in self._paid_dks else row[5]
            can_cancel = cur_status == 'Chờ thanh toán'
            if can_cancel:
                btn_cancel.setStyleSheet(f'QPushButton {{ background: {COLORS["red"]}; color: white; border: none; border-radius: 3px; font-size: 10px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["red_hover"]}; }}')
                btn_cancel.clicked.connect(lambda ch, ma_dk=row[0], hv=row[2], lop=row[3], t=tbl: self._emp_cancel_reg(t, ma_dk, hv, lop))
            else:
                btn_cancel.setEnabled(False)
                btn_cancel.setStyleSheet('QPushButton { background: #e2e8f0; color: #a0aec0; border: none; border-radius: 3px; font-size: 10px; font-weight: bold; }')
                btn_cancel.setToolTip(f'Không thể hủy ở trạng thái "{cur_status}"')
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(4)
            hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(btn_view)
            hl.addWidget(btn_cancel)
            tbl.setCellWidget(r, 6, w)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([70, 95, 195, 90, 110, 125, 70]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 36)

        widen_search(page, 'txtSearchReg', 300, ['cboRegStatus', 'cboRegDate'])
        # search + filter + export - safe_connect tranh accumulation
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchReg')
        if txt:
            safe_connect(txt.textChanged, lambda t: table_filter(tbl, t, cols=[0, 2, 3]))
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
                safe_connect(cbo.currentIndexChanged, lambda idx, n=nm: self._emp_filter_reg(n))
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportReg')
        if btn_exp:
            safe_connect(btn_exp.clicked, lambda: export_table_csv(self, tbl, 'danh_sach_dang_ky.csv', 'Xuất danh sách đăng ký'))

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

    def _emp_cancel_reg(self, tbl, ma_dk, hv_name, lop_id):
        """Huy 1 dang ky (chi cho phep neu Cho thanh toan)."""
        if not msg_confirm(self, 'Xác nhận hủy', f'Hủy đăng ký {ma_dk} của {hv_name} - lớp {lop_id}?'):
            return
        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # parse reg_id tu ma_dk (vd 'DK001' -> 1)
        ma_digits = ''.join(ch for ch in ma_dk if ch.isdigit())
        if not ma_digits:
            msg_warn(self, 'Lỗi', f'Mã đăng ký không hợp lệ: {ma_dk}')
            return
        try:
            RegistrationService.cancel_registration(int(ma_digits))
        except Exception as e:
            print(f'[EMP_CANCEL] loi: {e}')
            msg_warn(self, 'Không hủy được', api_error_msg(e))
            return
        # DB OK -> re-fill bang
        self.pages_filled[2] = False
        self._fill_emp_reglist()
        self.pages_filled[2] = True
        msg_info(self, 'Đã hủy', f'Đã hủy đăng ký {ma_dk}')

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

        # buttons - safe_connect tranh accumulation
        btn_p = page.findChild(QtWidgets.QPushButton, 'btnConfirmPay')
        if btn_p:
            safe_connect(btn_p.clicked, lambda: self._emp_confirm_pay(tbl))
        btn_r = page.findChild(QtWidgets.QPushButton, 'btnPrintReceipt')
        if btn_r:
            safe_connect(btn_r.clicked, lambda: self._emp_print_receipt(tbl))
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchPay')
        if txt:
            safe_connect(txt.textChanged, lambda t: table_filter(tbl, t, cols=[0, 1]))

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
        # Validate so_tien va ma_dk truoc
        if not (DB_AVAILABLE and ma_digits):
            msg_warn(self, 'Lỗi', 'Không xác định được mã đăng ký hoặc chưa kết nối hệ thống.')
            return
        try:
            so_tien = int(gia.replace('.', '').replace(',', '').replace('đ', '').strip())
        except ValueError:
            msg_warn(self, 'Sai dữ liệu', f'Số tiền không hợp lệ: {gia}')
            return
        if so_tien <= 0:
            msg_warn(self, 'Sai dữ liệu', f'Số tiền phải > 0 (hiện tại: {so_tien})')
            return
        nv_id = MOCK_EMPLOYEE.get('user_id')
        if not nv_id:
            msg_warn(self, 'Lỗi', 'Không xác định được nhân viên thu tiền. Hãy đăng nhập lại.')
            return
        # Goi API truoc
        try:
            RegistrationService.confirm_payment(int(ma_digits), so_tien, method, nv_id, ghi_chu)
            print(f'[PAY] da ghi DB: {ma}, {so_tien}đ')
        except Exception as e:
            print(f'[PAY] loi: {e}')
            msg_warn(self, 'Không xác nhận được', api_error_msg(e))
            return
        # API OK -> update UI
        tbl.removeRow(r)
        if note: note.clear()
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
        # search + filter - safe_connect tranh accumulation
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchEmpCls')
        if txt:
            safe_connect(txt.textChanged, lambda t: table_filter(tbl, t, cols=[0, 1, 2]))
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
            safe_connect(cbo_c.currentIndexChanged, lambda: self._emp_filter_cls())
        cbo_s = page.findChild(QtWidgets.QComboBox, 'cboEmpClsStatus')
        if cbo_s:
            cbo_s.clear()
            cbo_s.addItems(['Tất cả trạng thái', 'Còn chỗ', 'Đầy'])
            safe_connect(cbo_s.currentIndexChanged, lambda: self._emp_filter_cls())

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
            btn_save.clicked.connect(self._save_emp_profile)
        btn_cp = page.findChild(QtWidgets.QPushButton, 'btnChangePass')
        if btn_cp:
            btn_cp.clicked.connect(lambda: self._emp_change_pass())

    def _save_emp_profile(self):
        page = self.page_widgets[5]
        email = page.findChild(QtWidgets.QLineEdit, 'txtEmail')
        phone = page.findChild(QtWidgets.QLineEdit, 'txtPhone')
        updates = {}
        if email:
            updates['email'] = email.text().strip()
        if phone:
            updates['sdt'] = phone.text().strip()
        # Validate
        if updates.get('email') and not is_valid_email(updates['email']):
            msg_warn(self, 'Sai định dạng', 'Email không hợp lệ (vd: ten@example.com)')
            return
        if updates.get('sdt') and not is_valid_phone_vn(updates['sdt']):
            msg_warn(self, 'Sai định dạng', 'Số điện thoại không hợp lệ (10-11 chữ số)')
            return

        emp_user_id = MOCK_EMPLOYEE.get('user_id')
        if not (DB_AVAILABLE and emp_user_id and updates):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # API truoc, MOCK sau
        try:
            EmployeeService.update(emp_user_id, **updates)
        except Exception as e:
            print(f'[EMP_PROFILE] loi: {e}')
            msg_warn(self, 'Không lưu được', api_error_msg(e))
            return
        for k, v in updates.items():
            MOCK_EMPLOYEE[k] = v
        msg_info(self, 'Thành công', 'Đã lưu thông tin cá nhân.')

    def _emp_change_pass(self):
        new = msg_input(self, 'Đổi mật khẩu', 'Nhập mật khẩu mới:')
        if not new:
            return
        emp_user_id = MOCK_EMPLOYEE.get('user_id')
        if not (DB_AVAILABLE and emp_user_id):
            msg_warn(self, 'Lỗi', 'Không xác định được tài khoản. Hãy đăng nhập lại.')
            return
        try:
            AuthService.change_password(emp_user_id, new)
            MOCK_EMPLOYEE['password'] = new
            msg_info(self, 'Thành công', 'Đổi mật khẩu thành công.')
        except Exception as e:
            msg_warn(self, 'Lỗi', f'Đổi mật khẩu thất bại:\n{e}')


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
