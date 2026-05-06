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
                            ExamService, AttendanceService, AuditService,
                            AssignmentService, is_alive)
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
        _load_sem_status()
        n_open = sum(1 for v in MOCK_SEM_STATUS.values() if v == 'open')
        print(f'[CACHE] Loaded {len(MOCK_COURSES)} courses + {len(MOCK_CLASSES)} classes + {n_open}/{len(MOCK_SEM_STATUS)} dot open')
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
    API tra ve ISO string (do JSON), nen luc parse can detect string.
    Truoc strip phan sau 'T' o ISO -> datetime time bi reset = 00:00, fmt
    co %H:%M se hien sai 'han nop 31/12/2025 00:00' thay vi '10:30'.
    Fix: parse full ISO string khi co 'T' (datetime.fromisoformat ho tro)."""
    if not value:
        return default
    if isinstance(value, str):
        try:
            from datetime import datetime
            # Parse ISO format full (vd '2025-12-31T10:00:00' giu time)
            # Drop fractional seconds + 'Z' suffix neu co (Python <3.11 chi
            # ho tro chuong trinh chuan)
            v = value
            if v.endswith('Z'):
                v = v[:-1] + '+00:00'
            value = datetime.fromisoformat(v)
        except Exception:
            try:
                # Fallback: chi parse phan date
                from datetime import datetime as _dt2
                value = _dt2.fromisoformat(value.split('T')[0])
            except Exception:
                return str(value)  # parse fail -> tra string nguyen
    try:
        return value.strftime(fmt)
    except Exception:
        return str(value)


def parse_iso_date(value):
    """Parse value (str/date/datetime/None) -> date object hoac None neu fail.

    API tra ngay_dk/ngay_thi... duoi 2 dang: date object (Python serialize) hoac
    str ISO 'YYYY-MM-DD' (JSON). Helper nay handle ca 2 case + truncate sau ky tu
    thu 10 de bo time component neu co (vd '2026-05-06T10:00:00').

    Lưu ý: nếu value là datetime (subclass cua date), tra ve .date() de tranh
    TypeError khi caller so sanh voi date thuong (datetime < date raise).

    Replace duplicate pattern:
        if isinstance(v, _date): d = v
        else:
            try: d = _date.fromisoformat(str(v)[:10])
            except Exception: d = None
    """
    if value is None or value == '':
        return None
    from datetime import date as _date, datetime as _dt
    # datetime kiem tra TRUOC date vi datetime la subclass cua date
    if isinstance(value, _dt):
        return value.date()
    if isinstance(value, _date):
        return value
    try:
        return _date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def parse_iso_datetime(value):
    """Parse ISO datetime string (kem 'Z' suffix UTC) -> naive datetime hoac None.

    Replace pattern duplicate:
        han_dt = _dt.fromisoformat(han) if isinstance(han, str) else han
    Truoc khong handle 'Z' suffix (Python <3.11) -> ValueError, va khi ISO co
    timezone se tra aware datetime khong so sanh voi naive `now()` duoc.
    """
    if value is None or value == '':
        return None
    from datetime import datetime as _dt
    if isinstance(value, _dt):
        return value.replace(tzinfo=None) if value.tzinfo is not None else value
    try:
        s = str(value)
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        d = _dt.fromisoformat(s)
        if d.tzinfo is not None:
            d = d.replace(tzinfo=None)
        return d
    except (ValueError, TypeError):
        return None


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


def validate_password(pw: str, min_len: int = 6) -> str:
    """Validate password strength. Tra '' neu OK, str loi neu sai.

    Tieu chi (don gian, khong qua kho cho moi truong giao duc):
    - Toi thieu min_len ky tu (default 6)
    - Co it nhat 1 chu cai
    - Co it nhat 1 chu so
    - Khong chua khoang trang
    """
    if not pw:
        return 'Mật khẩu không được trống'
    if len(pw) < min_len:
        return f'Mật khẩu phải tối thiểu {min_len} ký tự'
    if ' ' in pw:
        return 'Mật khẩu không được chứa khoảng trắng'
    has_alpha = any(c.isalpha() for c in pw)
    has_digit = any(c.isdigit() for c in pw)
    if not has_alpha:
        return 'Mật khẩu phải có ít nhất 1 chữ cái'
    if not has_digit:
        return 'Mật khẩu phải có ít nhất 1 chữ số'
    return ''  # OK


def password_strength(pw: str):
    """Tinh do manh mat khau dua tren do dai + chuc nang.

    Tra ve tuple (label, color, score 0-100) - dung de hien progress bar.
    """
    if not pw:
        return ('—', '#a0aec0', 0)
    score = 0
    n = len(pw)
    if n >= 6: score += 20
    if n >= 8: score += 15
    if n >= 12: score += 15
    if any(c.islower() for c in pw): score += 10
    if any(c.isupper() for c in pw): score += 15
    if any(c.isdigit() for c in pw): score += 10
    if any(not c.isalnum() for c in pw): score += 15
    score = min(score, 100)
    if score < 40:
        return ('Yếu', '#dc2626', score)
    if score < 70:
        return ('Trung bình', '#d97706', score)
    if score < 90:
        return ('Mạnh', '#059669', score)
    return ('Rất mạnh', '#16a34a', score)


def attach_password_strength_indicator(line_edit):
    """Tao 1 QLabel hien strength dong - cap nhat khi user go vao line_edit.

    Caller tu append vao layout (form.addRow / vbox.addWidget) - khong tu add o day
    de dialog co the dat label dung vi tri (vd ngay duoi field "Mat khau moi").

    Returns: QLabel widget.
    """
    lbl = QtWidgets.QLabel('—')
    lbl.setStyleSheet('color: #a0aec0; font-size: 11px; padding: 2px 0; '
                       'background: transparent; border: none;')
    lbl.setMinimumHeight(20)

    def _update(text):
        lbl_str, color, score = password_strength(text or '')
        if not text:
            lbl.setText('—')
            lbl.setStyleSheet('color: #a0aec0; font-size: 11px; padding: 2px 0; '
                               'background: transparent; border: none;')
        else:
            # Visual bar bang ky tu (■ filled, □ empty)
            n_bars = max(1, score // 10)
            bars_filled = '▰' * n_bars
            bars_empty = '▱' * (10 - n_bars)
            lbl.setText(f'<span style="color:{color}; font-weight:bold;">{lbl_str}</span> '
                         f'<span style="color:{color};">{bars_filled}</span>'
                         f'<span style="color:#e2e8f0;">{bars_empty}</span>'
                         f'  <span style="color:#a0aec0; font-size:10px;">({score}/100)</span>')
            lbl.setStyleSheet(f'color: {color}; font-size: 11px; padding: 2px 0; '
                               'background: transparent; border: none;')
            lbl.setTextFormat(Qt.RichText)

    line_edit.textChanged.connect(_update)
    return lbl


APP_VERSION = '1.0.0'
APP_NAME = 'EAUT - Hệ thống đăng ký khoá học ngoại khoá'


def fmt_relative_date(value, full_fmt='%d/%m/%Y') -> str:
    """Format ngay theo dang relative: 'Vua xong' / 'X phut truoc' / 'Hom qua' / 'X ngay truoc' / dd/mm/yyyy.

    Truoc parse loop voi format strings + slicing hacky `value[:len(fmt)+5]`,
    khong handle 'Z' suffix UTC. Dung parse_iso_datetime() helper de robust.

    Args:
        value: datetime/date/ISO str/None
        full_fmt: format khi date xa (>7 ngay)
    """
    from datetime import datetime, date as _date
    if value is None or value == '':
        return '—'
    try:
        if isinstance(value, datetime):
            dt = value.replace(tzinfo=None) if value.tzinfo is not None else value
        elif isinstance(value, _date):
            dt = datetime(value.year, value.month, value.day)
        else:
            # str path - dung helper xu ly 'Z' suffix + tzinfo
            dt = parse_iso_datetime(value)
            if dt is None:
                return str(value)[:20]

        now = datetime.now()
        diff = now - dt
        secs = diff.total_seconds()

        if secs < 0:
            # Future date - tra full
            return dt.strftime(full_fmt)
        if secs < 60:
            return 'Vừa xong'
        if secs < 3600:
            return f'{int(secs // 60)} phút trước'
        if secs < 86400:
            return f'{int(secs // 3600)} giờ trước'
        if secs < 86400 * 2:
            return 'Hôm qua'
        if secs < 86400 * 7:
            return f'{int(secs // 86400)} ngày trước'
        return dt.strftime(full_fmt)
    except Exception:
        return str(value)[:20] if value else '—'


def show_about_dialog(parent):
    """About dialog hien thi version + tac gia + tech stack + phim tat + backend status."""
    dlg = QtWidgets.QDialog(parent)
    dlg.setWindowTitle(f'Giới thiệu - {APP_NAME}')
    dlg.setFixedSize(480, 460)
    dlg.setStyleSheet('QDialog { background: white; }')
    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(24, 20, 24, 18)
    lay.setSpacing(8)

    # Logo
    logo_path = os.path.join(RES, 'logo.png')
    if os.path.exists(logo_path):
        lbl_logo = QtWidgets.QLabel()
        lbl_logo.setAlignment(Qt.AlignCenter)
        lbl_logo.setPixmap(QPixmap(logo_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lay.addWidget(lbl_logo)

    title = QtWidgets.QLabel(f'<b style="font-size:16px;">{APP_NAME}</b>')
    title.setAlignment(Qt.AlignCenter)
    title.setWordWrap(True)
    lay.addWidget(title)

    ver = QtWidgets.QLabel(f'<span style="color:#718096;">Phiên bản {APP_VERSION}</span>')
    ver.setAlignment(Qt.AlignCenter)
    lay.addWidget(ver)

    sep = QtWidgets.QFrame()
    sep.setFrameShape(QtWidgets.QFrame.HLine)
    sep.setStyleSheet('color: #e2e8f0;')
    lay.addWidget(sep)

    # Backend status: fetch /health/db de hien thi PostgreSQL version + ket noi
    backend_info = 'PostgreSQL (chưa kết nối)'
    try:
        import requests
        from api_client import API_URL  # respect EAUT_API_URL env var
        r = requests.get(f'{API_URL}/health/db', timeout=2)
        if r.ok:
            d = r.json()
            ver_str = d.get('version', 'unknown')
            backend_info = f'{ver_str} • {d.get("public_tables", "?")} bảng • {d.get("active_connections", "?")} kết nối'
    except Exception:
        pass

    info = QtWidgets.QLabel(
        '<table cellspacing="4">'
        '<tr><td><b>Mục đích:</b></td><td>Quản lý khoá học ngoại khoá EAUT</td></tr>'
        f'<tr><td><b>Backend:</b></td><td>FastAPI + {backend_info}</td></tr>'
        '<tr><td><b>Frontend:</b></td><td>PyQt5 desktop</td></tr>'
        '<tr><td><b>Đối tượng:</b></td><td>Học viên / Giảng viên / Nhân viên / Admin</td></tr>'
        '</table>'
    )
    info.setStyleSheet('color: #4a5568; font-size: 12px;')
    info.setWordWrap(True)
    lay.addWidget(info)

    sep2 = QtWidgets.QFrame()
    sep2.setFrameShape(QtWidgets.QFrame.HLine)
    sep2.setStyleSheet('color: #e2e8f0;')
    lay.addWidget(sep2)

    shortcuts = QtWidgets.QLabel(
        '<b>Phím tắt:</b><br>'
        '<table cellspacing="3">'
        '<tr><td style="color:#002060;"><b>F5</b> / <b>Ctrl+R</b></td><td style="color:#718096;">Refresh trang hiện tại</td></tr>'
        '<tr><td style="color:#002060;"><b>F1</b></td><td style="color:#718096;">Hiển thị giới thiệu</td></tr>'
        '<tr><td style="color:#002060;"><b>Ctrl+1..9</b></td><td style="color:#718096;">Chuyển nhanh sidebar tab</td></tr>'
        '<tr><td style="color:#002060;"><b>Esc</b></td><td style="color:#718096;">Đóng dialog đang mở</td></tr>'
        '</table>'
    )
    shortcuts.setStyleSheet('font-size: 11px;')
    shortcuts.setWordWrap(True)
    lay.addWidget(shortcuts)

    lay.addStretch(1)
    btn = QtWidgets.QPushButton('Đóng')
    btn.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; '
                      f'border: none; border-radius: 4px; padding: 8px 24px; font-weight: bold; }}')
    btn.clicked.connect(dlg.accept)
    btn_row = QtWidgets.QHBoxLayout()
    btn_row.addStretch(1)
    btn_row.addWidget(btn)
    lay.addLayout(btn_row)

    dlg.exec_()


def center_on_screen(window):
    """Di chuyen window ra giua man hinh chinh - dung sau .show()."""
    try:
        screen = window.screen() if hasattr(window, 'screen') else None
        if not screen:
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
        if not screen:
            return
        sg = screen.availableGeometry()
        wg = window.frameGeometry()
        window.move(
            sg.x() + (sg.width() - wg.width()) // 2,
            sg.y() + (sg.height() - wg.height()) // 2,
        )
    except Exception:
        pass


def install_refresh_shortcut(window):
    """Bind shortcut tren window:
      - F5 / Ctrl+R: re-fill page hien tai
      - F1: show About dialog
      - Ctrl+1..9: switch sang sidebar tab so 1..9 (neu co)

    window can co attributes:
      - stack: QStackedWidget
      - pages_filled: list[bool]
      - _on_nav(idx)
    """
    from PyQt5.QtGui import QKeySequence
    from PyQt5.QtWidgets import QShortcut

    def _refresh():
        if not (hasattr(window, 'stack') and hasattr(window, 'pages_filled')):
            return
        idx = window.stack.currentIndex()
        if 0 <= idx < len(window.pages_filled):
            window.pages_filled[idx] = False
            if hasattr(window, '_on_nav'):
                window._on_nav(idx)

    sc1 = QShortcut(QKeySequence('F5'), window)
    sc1.activated.connect(_refresh)
    sc2 = QShortcut(QKeySequence('Ctrl+R'), window)
    sc2.activated.connect(_refresh)
    sc3 = QShortcut(QKeySequence('F1'), window)
    sc3.activated.connect(lambda: show_about_dialog(window))

    # Ctrl+1..9 -> switch sidebar tab so 1..9 (neu page ton tai)
    def _make_nav(i):
        def _nav():
            if (hasattr(window, '_on_nav') and hasattr(window, 'stack') and
                    i < window.stack.count()):
                window._on_nav(i)
        return _nav

    for n in range(1, 10):  # Ctrl+1 = idx 0, Ctrl+9 = idx 8
        sc = QShortcut(QKeySequence(f'Ctrl+{n}'), window)
        sc.activated.connect(_make_nav(n - 1))


def export_schedule_ics(parent, schedules: list, default_filename='lich_hoc.ics',
                         calendar_name='Lich hoc EAUT'):
    """Xuat schedules sang file .ics (iCalendar) - import duoc vao Google/Apple Calendar.

    Args:
        schedules: list of dict chua: lop_id, ngay, gio_bat_dau, gio_ket_thuc,
                   phong, ten_mon, ten_gv, noi_dung
        default_filename: ten file mac dinh khi save
        calendar_name: ten calendar trong app
    """
    if not schedules:
        msg_warn(parent, 'Trống', 'Không có buổi học nào để xuất.')
        return False
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent, 'Xuất lịch học (iCalendar)',
        os.path.join(os.path.expanduser('~'), 'Desktop', default_filename),
        'iCalendar (*.ics)'
    )
    if not path:
        return False
    if not path.lower().endswith('.ics'):
        path += '.ics'

    from datetime import datetime as _dt, date as _date, time as _time

    def _ics_dt(d, t):
        """Format datetime cho ICS: 20260505T070000 (local time)."""
        if isinstance(d, str):
            try:
                d = _date.fromisoformat(d[:10])
            except Exception:
                return None
        if isinstance(t, str):
            try:
                parts = t[:8].split(':')
                t = _time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
            except Exception:
                t = _time(0)
        if not (hasattr(d, 'year') and hasattr(t, 'hour')):
            return None
        return _dt.combine(d, t).strftime('%Y%m%dT%H%M%S')

    def _escape(s):
        """ICS escape: comma, semicolon, backslash, newline."""
        if s is None:
            return ''
        s = str(s).replace('\\', '\\\\').replace(',', '\\,').replace(';', '\\;')
        s = s.replace('\n', '\\n').replace('\r', '')
        return s

    now_stamp = _dt.now().strftime('%Y%m%dT%H%M%S')
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//EAUT//Schedule Export//VN',
        'CALSCALE:GREGORIAN',
        f'X-WR-CALNAME:{_escape(calendar_name)}',
        'X-WR-TIMEZONE:Asia/Ho_Chi_Minh',
    ]
    valid = 0
    for sc in schedules:
        dt_start = _ics_dt(sc.get('ngay'), sc.get('gio_bat_dau'))
        dt_end = _ics_dt(sc.get('ngay'), sc.get('gio_ket_thuc'))
        if not dt_start or not dt_end:
            continue
        sid = sc.get('id', valid)
        lop = sc.get('lop_id', '?')
        ten_mon = sc.get('ten_mon', '') or ''
        phong = sc.get('phong', '') or ''
        gv = sc.get('ten_gv', '') or ''
        buoi_so = sc.get('buoi_so')
        nd = sc.get('noi_dung', '') or ''
        # Summary: "IT001-A · Lap trinh Python"
        summary = f'{lop}'
        if ten_mon:
            summary += f' · {ten_mon}'
        # Description: GV + buoi + noi dung
        desc_parts = []
        if gv:
            desc_parts.append(f'GV: {gv}')
        if buoi_so:
            desc_parts.append(f'Buổi {buoi_so}')
        if nd:
            desc_parts.append(nd)
        desc = '\\n'.join(_escape(p) for p in desc_parts)
        lines.extend([
            'BEGIN:VEVENT',
            f'UID:eaut-{sid}-{now_stamp}@eaut.edu.vn',
            f'DTSTAMP:{now_stamp}',
            f'DTSTART:{dt_start}',
            f'DTEND:{dt_end}',
            f'SUMMARY:{_escape(summary)}',
            f'LOCATION:{_escape(phong)}',
            f'DESCRIPTION:{desc}',
            'STATUS:CONFIRMED',
            'END:VEVENT',
        ])
        valid += 1
    lines.append('END:VCALENDAR')
    try:
        # ICS spec: CRLF line ending
        content = '\r\n'.join(lines) + '\r\n'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        msg_info(parent, 'Đã xuất lịch',
                 f'Đã xuất {valid} buổi học ra:\n{path}\n\n'
                 'Bạn có thể import file này vào Google Calendar, Apple Calendar, '
                 'Outlook, hoặc Samsung Calendar...')
        return True
    except Exception as e:
        msg_warn(parent, 'Lỗi', f'Không xuất được:\n{e}')
        return False


def _make_vn_textdoc(html: str):
    """Helper: tao QTextDocument voi default font Segoe UI 10pt - tranh fallback Tahoma
    lam mat hoac sai diac tieng Viet trong PDF render. Goi thay vi QTextDocument() truc tiep.
    Returns: QTextDocument da setHtml.
    """
    from PyQt5.QtGui import QTextDocument, QFont
    doc = QTextDocument()
    f = QFont('Segoe UI', 10)
    f.setStyleHint(QFont.SansSerif)
    doc.setDefaultFont(f)
    doc.setHtml(html)
    return doc


def export_schedule_week_pdf(parent, schedules: list, monday_qdate,
                              owner_role='hv', owner_name='', owner_code='',
                              default_filename='LichTuan.pdf'):
    """In lich hoc 1 tuan ra PDF (de in mang theo / dan bang).

    schedules: list dict da loc theo tuan (gom 7 ngay tu Thu 2 -> CN)
    monday_qdate: QDate cua thu 2 trong tuan
    owner_role: 'hv' | 'gv'
    """
    try:
        from PyQt5.QtPrintSupport import QPrinter
        from PyQt5.QtGui import QTextDocument
    except ImportError:
        msg_warn(parent, 'Lỗi', 'PyQt5.QtPrintSupport không có sẵn.')
        return False

    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent, 'In lịch tuần (PDF)',
        os.path.join(os.path.expanduser('~'), 'Desktop', default_filename),
        'PDF Files (*.pdf)'
    )
    if not path:
        return False
    if not path.lower().endswith('.pdf'):
        path += '.pdf'

    from datetime import datetime as _dt, date as _date
    # Group schedules theo ngay (yyyy-mm-dd)
    by_day = {}
    for s in (schedules or []):
        ngay = str(s.get('ngay', ''))[:10]
        if not ngay:
            continue
        by_day.setdefault(ngay, []).append(s)
    # Sort theo gio bat dau
    for k in by_day:
        by_day[k].sort(key=lambda x: str(x.get('gio_bat_dau', '')))

    # Build 7 hang Thu 2 - CN
    days_vn = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật']
    rows_html = []
    for offset in range(7):
        d = monday_qdate.addDays(offset)
        iso = d.toString('yyyy-MM-dd')
        ddmm = d.toString('dd/MM')
        sess = by_day.get(iso, [])
        # Cot trai: ten thu + ngay
        is_today = (d == QDate.currentDate())
        bg_left = '#fff8e1' if is_today else '#edf2f7'
        border_left = '4px solid #c05621' if is_today else '4px solid #002060'
        if sess:
            # Build cells session
            sess_rows = []
            for sc in sess:
                gio_bd = str(sc.get('gio_bat_dau', ''))[:5]
                gio_kt = str(sc.get('gio_ket_thuc', ''))[:5]
                lop = sc.get('lop_id', '?') or '?'
                ten_mon = sc.get('ten_mon', '') or ''
                phong = sc.get('phong', '') or '—'
                buoi_so = sc.get('buoi_so')
                buoi_str = f' · Buổi {buoi_so}' if buoi_so else ''
                # GV thi hien lop / ten_mon, HV thi hien GV
                if owner_role == 'gv':
                    extra = ''
                else:
                    gv = sc.get('ten_gv', '') or ''
                    extra = f' · GV: {gv}' if gv else ''
                sess_rows.append(f'''
                    <div style="margin-bottom: 6px; padding: 6px 8px; background: white; border-left: 3px solid #5c8a5c; border-radius: 4px;">
                        <div style="color: #1a1a2e; font-weight: bold; font-size: 11px;">
                            {gio_bd} - {gio_kt} &nbsp;·&nbsp; {lop}
                        </div>
                        <div style="color: #4a5568; font-size: 10px; margin-top: 2px;">
                            {ten_mon} · Phòng {phong}{buoi_str}{extra}
                        </div>
                    </div>''')
            sess_html = ''.join(sess_rows)
        else:
            sess_html = '<div style="color: #a0aec0; font-size: 10px; font-style: italic; padding: 4px;">— Không có buổi —</div>'

        rows_html.append(f'''
            <tr>
                <td style="width: 16%; padding: 8px; background: {bg_left}; border: 1px solid #e2e8f0; border-left: {border_left}; vertical-align: top;">
                    <div style="font-weight: bold; color: #002060; font-size: 12px;">{days_vn[offset]}</div>
                    <div style="color: #4a5568; font-size: 11px; margin-top: 2px;">{ddmm}</div>
                </td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; vertical-align: top;">{sess_html}</td>
            </tr>
        ''')

    # Header info
    role_label = 'Học viên' if owner_role == 'hv' else 'Giảng viên'
    code_label = 'MSV' if owner_role == 'hv' else 'Mã GV'
    sun = monday_qdate.addDays(6)
    range_str = f'{monday_qdate.toString("dd/MM/yyyy")} — {sun.toString("dd/MM/yyyy")}'
    total = sum(len(v) for v in by_day.values())

    html = f'''
    <html><head><meta charset="utf-8"></head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e;">
    <div style="text-align: center; border-bottom: 3px solid #002060; padding-bottom: 12px; margin-bottom: 14px;">
        <h1 style="color: #002060; margin: 0; font-size: 22px;">TRUNG TÂM NGOẠI KHÓA EAUT</h1>
        <p style="margin: 4px 0; color: #4a5568; font-size: 11px;">
            Km 23, QL5, Trưng Trắc, Văn Lâm, Hưng Yên · Hotline: 024.3999.1111
        </p>
    </div>

    <h2 style="text-align: center; color: #c05621; margin: 0 0 4px 0;">LỊCH HỌC TUẦN</h2>
    <p style="text-align: center; color: #4a5568; font-size: 12px; margin: 0 0 14px 0;">
        {range_str} &nbsp;·&nbsp; <b>{total}</b> buổi
    </p>

    <table cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 14px;">
        <tr style="background: #edf2f7;">
            <td style="width: 18%; padding: 6px 8px; color: #4a5568;">{role_label}:</td>
            <td style="padding: 6px 8px;"><b>{owner_name or '—'}</b></td>
            <td style="width: 14%; padding: 6px 8px; color: #4a5568;">{code_label}:</td>
            <td style="padding: 6px 8px;"><b>{owner_code or '—'}</b></td>
        </tr>
        <tr>
            <td style="padding: 6px 8px; color: #4a5568;">Ngày in:</td>
            <td style="padding: 6px 8px;">{_dt.now().strftime('%d/%m/%Y %H:%M')}</td>
            <td style="padding: 6px 8px; color: #4a5568;">Tổng buổi:</td>
            <td style="padding: 6px 8px;"><b style="color: #c05621;">{total}</b> buổi</td>
        </tr>
    </table>

    <table cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 10px;">
        <thead><tr style="background: #002060; color: white;">
            <th style="padding: 8px; border: 1px solid #002060; text-align: left;">Ngày</th>
            <th style="padding: 8px; border: 1px solid #002060; text-align: left;">Buổi học</th>
        </tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
    </table>

    <p style="margin-top: 14px; color: #a0aec0; font-size: 9px; text-align: center; font-style: italic;">
        File này được in từ phần mềm quản lý ngoại khoá EAUT. Nếu có thay đổi, vui lòng kiểm tra trên hệ thống.
    </p>
    </body></html>
    '''

    try:
        doc = _make_vn_textdoc(html)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Portrait)
        printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
        doc.print_(printer)
        msg_info(parent, 'Đã xuất PDF', f'Lịch tuần đã lưu:\n{path}\n\nTổng {total} buổi.')
        return True
    except Exception as e:
        msg_warn(parent, 'Lỗi xuất PDF', f'Không xuất được:\n{e}')
        return False


def export_class_roster_pdf(parent, class_info: dict, students: list,
                             default_filename='DanhSachLop.pdf'):
    """Xuat danh sach HV cua 1 lop ra PDF chuyen nghiep.

    Args:
        class_info: dict {ma_lop, ten_mon, ten_gv, lich, phong, semester_id, siso_max}
        students: list of dict {msv, full_name, sdt, email, gioitinh, ngaysinh, ngay_dk, reg_status}
    """
    if not students:
        msg_warn(parent, 'Trống', 'Lớp này chưa có học viên nào để in.')
        return False
    try:
        from PyQt5.QtPrintSupport import QPrinter
        from PyQt5.QtGui import QTextDocument
    except ImportError:
        msg_warn(parent, 'Lỗi', 'PyQt5.QtPrintSupport không có sẵn.')
        return False
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent, 'Xuất danh sách lớp PDF',
        os.path.join(os.path.expanduser('~'), 'Desktop', default_filename),
        'PDF Files (*.pdf)'
    )
    if not path:
        return False
    if not path.lower().endswith('.pdf'):
        path += '.pdf'

    from datetime import datetime as _dt
    # Status map -> Vietnamese
    st_vn = {'paid': 'Đã thanh toán', 'pending_payment': 'Chờ TT',
             'completed': 'Hoàn thành', 'cancelled': 'Đã huỷ'}

    # Build student rows
    rows_html = []
    for i, s in enumerate(students, 1):
        zebra = '#f7fafc' if i % 2 == 0 else 'white'
        ngay_sinh = s.get('ngaysinh') or '—'
        if hasattr(ngay_sinh, 'strftime'):
            ngay_sinh = ngay_sinh.strftime('%d/%m/%Y')
        ngay_dk = s.get('ngay_dk') or '—'
        if hasattr(ngay_dk, 'strftime'):
            ngay_dk = ngay_dk.strftime('%d/%m/%Y')
        st_raw = s.get('reg_status', '')
        st_color = '#166534' if st_raw == 'paid' else ('#92400e' if st_raw == 'pending_payment'
                                                       else '#1e3a8a' if st_raw == 'completed' else '#991b1b')
        rows_html.append(f'''
            <tr style="background: {zebra};">
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center;">{i}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; font-weight: bold;">{s.get('msv', '—')}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0;">{s.get('full_name', '—')}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center;">{s.get('gioitinh', '—') or '—'}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center;">{ngay_sinh}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0;">{s.get('sdt', '—') or '—'}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0;">{s.get('email', '—') or '—'}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center; color: {st_color}; font-weight: bold;">{st_vn.get(st_raw, st_raw)}</td>
            </tr>
        ''')

    # Class info header
    ma_lop = class_info.get('ma_lop', '—')
    ten_mon = class_info.get('ten_mon', '—')
    ten_gv = class_info.get('ten_gv', '—')
    lich = class_info.get('lich', '—') or '—'
    phong = class_info.get('phong', '—') or '—'
    sem_id = class_info.get('semester_id', '—') or '—'
    siso_max = class_info.get('siso_max', 0)

    html = f'''
    <html><head><meta charset="utf-8"></head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e;">
    <div style="text-align: center; border-bottom: 3px solid #002060; padding-bottom: 12px; margin-bottom: 16px;">
        <h1 style="color: #002060; margin: 0; font-size: 22px;">TRUNG TÂM NGOẠI KHÓA EAUT</h1>
        <p style="margin: 4px 0; color: #4a5568; font-size: 11px;">
            Km 23, QL5, Trưng Trắc, Văn Lâm, Hưng Yên · Hotline: 024.3999.1111
        </p>
    </div>

    <h2 style="text-align: center; color: #c05621; margin: 0 0 4px 0;">DANH SÁCH HỌC VIÊN</h2>
    <p style="text-align: center; color: #4a5568; font-size: 12px; margin: 0 0 16px 0;">
        Lớp <b>{ma_lop}</b> · {ten_mon}
    </p>

    <table cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 16px;">
        <tr style="background: #edf2f7;">
            <td style="width: 25%; padding: 8px; color: #4a5568;">Mã lớp:</td>
            <td style="padding: 8px;"><b>{ma_lop}</b></td>
            <td style="width: 25%; padding: 8px; color: #4a5568;">Đợt:</td>
            <td style="padding: 8px;">{sem_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; color: #4a5568;">Khóa học:</td>
            <td style="padding: 8px;"><b>{ten_mon}</b></td>
            <td style="padding: 8px; color: #4a5568;">Giảng viên:</td>
            <td style="padding: 8px;"><b>{ten_gv}</b></td>
        </tr>
        <tr style="background: #edf2f7;">
            <td style="padding: 8px; color: #4a5568;">Lịch học:</td>
            <td style="padding: 8px;">{lich}</td>
            <td style="padding: 8px; color: #4a5568;">Phòng:</td>
            <td style="padding: 8px;">{phong}</td>
        </tr>
        <tr>
            <td style="padding: 8px; color: #4a5568;">Sĩ số:</td>
            <td style="padding: 8px;"><b style="color: #c05621;">{len(students)}</b> / {siso_max} HV</td>
            <td style="padding: 8px; color: #4a5568;">Ngày in:</td>
            <td style="padding: 8px;">{_dt.now().strftime('%d/%m/%Y %H:%M')}</td>
        </tr>
    </table>

    <table cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 10px;">
        <thead><tr style="background: #002060; color: white;">
            <th style="padding: 6px; border: 1px solid #002060; width: 4%;">#</th>
            <th style="padding: 6px; border: 1px solid #002060; width: 11%;">MSV</th>
            <th style="padding: 6px; border: 1px solid #002060;">Họ và tên</th>
            <th style="padding: 6px; border: 1px solid #002060; width: 7%;">Giới tính</th>
            <th style="padding: 6px; border: 1px solid #002060; width: 11%;">Ngày sinh</th>
            <th style="padding: 6px; border: 1px solid #002060; width: 12%;">SĐT</th>
            <th style="padding: 6px; border: 1px solid #002060;">Email</th>
            <th style="padding: 6px; border: 1px solid #002060; width: 12%;">Trạng thái</th>
        </tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
    </table>

    <div style="margin-top: 30px; display: flex; justify-content: space-between;">
        <div style="text-align: center; width: 40%;">
            <p style="color: #4a5568; font-size: 11px;">Lớp trưởng</p>
            <p style="font-size: 10px; color: #718096; font-style: italic;">(ký tên)</p>
        </div>
        <div style="text-align: center; width: 40%;">
            <p style="color: #4a5568; font-size: 11px;">Hà Nội, ngày {_dt.now().day}/{_dt.now().month}/{_dt.now().year}</p>
            <p style="margin-top: 4px;"><b>Giảng viên / Quản lý</b></p>
            <p style="font-size: 10px; color: #718096; font-style: italic;">(ký tên)</p>
        </div>
    </div>
    </body></html>
    '''
    try:
        doc = _make_vn_textdoc(html)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Landscape)  # ngang cho table rong
        printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
        doc.print_(printer)
        msg_info(parent, 'Đã xuất PDF', f'Danh sách lớp đã lưu:\n{path}')
        return True
    except Exception as e:
        msg_warn(parent, 'Lỗi xuất PDF', f'Không xuất được:\n{e}')
        return False


def export_class_full_schedule_pdf(parent, lop_id, ten_mon, schedules,
                                     ten_gv='', default_filename='LichLop.pdf'):
    """In toan bo lich (24 buoi du kien) cua 1 lop ra PDF.

    schedules: list dict {id, ngay, gio_bat_dau, gio_ket_thuc, phong, buoi_so,
                          noi_dung, trang_thai}
    """
    if not schedules:
        msg_warn(parent, 'Trống', 'Lớp này chưa có buổi học nào.')
        return False
    try:
        from PyQt5.QtPrintSupport import QPrinter
        from PyQt5.QtGui import QTextDocument
    except ImportError:
        msg_warn(parent, 'Lỗi', 'PyQt5.QtPrintSupport không có sẵn.')
        return False
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent, 'In lịch toàn bộ lớp PDF',
        os.path.join(os.path.expanduser('~'), 'Desktop', default_filename),
        'PDF Files (*.pdf)'
    )
    if not path:
        return False
    if not path.lower().endswith('.pdf'):
        path += '.pdf'

    from datetime import datetime as _dt, date as _date
    today = _date.today()

    # Sap xep theo ngay -> gio bat dau
    rows = list(schedules)

    def _key(s):
        ngay = s.get('ngay', '')
        if isinstance(ngay, _date):
            return (ngay.isoformat(), str(s.get('gio_bat_dau', '')))
        return (str(ngay)[:10], str(s.get('gio_bat_dau', '')))

    rows.sort(key=_key)

    days_vn_short = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
    # Map khop voi DB CHECK constraint schema.sql (truoc dung 'planned'/'done'
    # khong khop voi DB 'scheduled'/'completed' -> raw key fall through)
    st_vn = {'scheduled': 'Đã lên lịch', 'completed': 'Đã diễn ra',
             'cancelled': 'Đã huỷ', 'postponed': 'Đã dời lịch'}
    st_color = {'scheduled': '#1e3a8a', 'completed': '#166534',
                'cancelled': '#991b1b', 'postponed': '#92400e'}

    # Stats: tong / da dien ra / sap toi / huy
    n_done = n_upcoming = n_cancel = 0
    for s in rows:
        ng = parse_iso_date(s.get('ngay', ''))
        st = s.get('trang_thai') or ''
        if st == 'cancelled':
            n_cancel += 1
        elif ng and ng < today:
            n_done += 1
        else:
            n_upcoming += 1

    rows_html = []
    for i, sc in enumerate(rows, 1):
        zebra = '#f7fafc' if i % 2 == 0 else 'white'
        buoi_so = sc.get('buoi_so') or i
        ngay_v = sc.get('ngay', '')
        ngay_d = parse_iso_date(ngay_v)
        ngay_str = ngay_d.strftime('%d/%m/%Y') if ngay_d else (str(ngay_v)[:10] or '—')
        thu_str = days_vn_short[ngay_d.weekday()] if ngay_d else '—'
        gio_bd = str(sc.get('gio_bat_dau', ''))[:5]
        gio_kt = str(sc.get('gio_ket_thuc', ''))[:5]
        gio_str = f'{gio_bd}-{gio_kt}' if gio_bd and gio_kt else '—'
        phong = sc.get('phong', '') or '—'
        nd = sc.get('noi_dung', '') or '—'
        st_raw = sc.get('trang_thai') or 'scheduled'
        # Auto downgrade scheduled -> completed neu da qua ngay hien tai
        display_st = st_raw
        if st_raw == 'scheduled' and ngay_d and ngay_d < today:
            display_st = 'completed'
        st_label = st_vn.get(display_st, display_st)
        st_clr = st_color.get(display_st, '#1a1a2e')
        # Highlight today
        ngay_style = ''
        if ngay_d and ngay_d == today:
            ngay_style = 'color: #c05621; font-weight: bold;'

        rows_html.append(f'''
            <tr style="background: {zebra};">
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center; font-weight: bold;">{buoi_so}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center; {ngay_style}">{ngay_str}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center; color: #718096;">{thu_str}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center;">{gio_str}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center;">{phong}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center; color: {st_clr}; font-weight: bold;">{st_label}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0;">{nd}</td>
            </tr>
        ''')

    html = f'''
    <html><head><meta charset="utf-8"></head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e;">
    <div style="text-align: center; border-bottom: 3px solid #002060; padding-bottom: 12px; margin-bottom: 14px;">
        <h1 style="color: #002060; margin: 0; font-size: 22px;">TRUNG TÂM NGOẠI KHÓA EAUT</h1>
        <p style="margin: 4px 0; color: #4a5568; font-size: 11px;">
            Km 23, QL5, Trưng Trắc, Văn Lâm, Hưng Yên · Hotline: 024.3999.1111
        </p>
    </div>

    <h2 style="text-align: center; color: #c05621; margin: 0 0 4px 0;">LỊCH HỌC TOÀN BỘ LỚP</h2>
    <p style="text-align: center; color: #4a5568; font-size: 12px; margin: 0 0 14px 0;">
        Lớp <b>{lop_id}</b> · {ten_mon or '—'}
    </p>

    <table cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 14px;">
        <tr style="background: #edf2f7;">
            <td style="width: 18%; padding: 6px 8px; color: #4a5568;">Mã lớp:</td>
            <td style="padding: 6px 8px;"><b>{lop_id}</b></td>
            <td style="width: 14%; padding: 6px 8px; color: #4a5568;">Giảng viên:</td>
            <td style="padding: 6px 8px;"><b>{ten_gv or '—'}</b></td>
        </tr>
        <tr>
            <td style="padding: 6px 8px; color: #4a5568;">Khóa học:</td>
            <td style="padding: 6px 8px;"><b>{ten_mon or '—'}</b></td>
            <td style="padding: 6px 8px; color: #4a5568;">Ngày in:</td>
            <td style="padding: 6px 8px;">{_dt.now().strftime('%d/%m/%Y %H:%M')}</td>
        </tr>
        <tr style="background: #edf2f7;">
            <td style="padding: 6px 8px; color: #4a5568;">Tổng buổi:</td>
            <td style="padding: 6px 8px;"><b style="color: #002060;">{len(rows)}</b></td>
            <td style="padding: 6px 8px; color: #4a5568;">Phân bổ:</td>
            <td style="padding: 6px 8px;">
                <span style="color: #166534;"><b>{n_done}</b> đã diễn ra</span>
                &nbsp;·&nbsp; <span style="color: #c05621;"><b>{n_upcoming}</b> sắp tới</span>
                &nbsp;·&nbsp; <span style="color: #991b1b;"><b>{n_cancel}</b> đã huỷ</span>
            </td>
        </tr>
    </table>

    <table cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 11px;">
        <thead><tr style="background: #002060; color: white;">
            <th style="padding: 8px; border: 1px solid #002060; width: 6%;">Buổi</th>
            <th style="padding: 8px; border: 1px solid #002060; width: 12%;">Ngày</th>
            <th style="padding: 8px; border: 1px solid #002060; width: 6%;">Thứ</th>
            <th style="padding: 8px; border: 1px solid #002060; width: 12%;">Giờ</th>
            <th style="padding: 8px; border: 1px solid #002060; width: 10%;">Phòng</th>
            <th style="padding: 8px; border: 1px solid #002060; width: 14%;">Trạng thái</th>
            <th style="padding: 8px; border: 1px solid #002060;">Nội dung buổi</th>
        </tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
    </table>

    <div style="margin-top: 24px; display: flex; justify-content: space-between;">
        <div style="text-align: center; width: 35%;">
            <p style="color: #4a5568; font-size: 11px;">Lớp trưởng</p>
            <p style="font-size: 10px; color: #718096; font-style: italic;">(ký tên)</p>
        </div>
        <div style="text-align: center; width: 35%;">
            <p style="color: #4a5568; font-size: 11px;">Hà Nội, ngày {_dt.now().day}/{_dt.now().month}/{_dt.now().year}</p>
            <p style="margin-top: 4px;"><b>Giảng viên</b></p>
            <p style="font-size: 10px; color: #718096; font-style: italic;">(ký tên)</p>
        </div>
    </div>
    </body></html>
    '''
    try:
        doc = _make_vn_textdoc(html)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Portrait)
        printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
        doc.print_(printer)
        msg_info(parent, 'Đã xuất PDF', f'Lịch toàn bộ lớp {lop_id} đã lưu:\n{path}\n\nTổng {len(rows)} buổi.')
        return True
    except Exception as e:
        msg_warn(parent, 'Lỗi xuất PDF', f'Không xuất được:\n{e}')
        return False


def export_exam_schedule_pdf(parent, exams: list, owner_role='hv',
                               owner_name='', owner_code='',
                               default_filename='LichThi.pdf'):
    """In lich thi cua HV / GV ra PDF.

    exams: list dict {lop_id, ten_mon, ngay_thi, ca_thi, gio_bat_dau, gio_ket_thuc,
                       phong, hinh_thuc, semester_id}
    """
    if not exams:
        msg_warn(parent, 'Trống', 'Không có lịch thi nào để in.')
        return False
    try:
        from PyQt5.QtPrintSupport import QPrinter
        from PyQt5.QtGui import QTextDocument
    except ImportError:
        msg_warn(parent, 'Lỗi', 'PyQt5.QtPrintSupport không có sẵn.')
        return False
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent, 'In lịch thi PDF',
        os.path.join(os.path.expanduser('~'), 'Desktop', default_filename),
        'PDF Files (*.pdf)'
    )
    if not path:
        return False
    if not path.lower().endswith('.pdf'):
        path += '.pdf'

    from datetime import datetime as _dt, date as _date
    today = _date.today()

    # Sap xep theo ngay thi -> gio bat dau
    rows = list(exams)

    def _key(s):
        ngay = s.get('ngay_thi') or s.get('ngay', '')
        if isinstance(ngay, _date):
            return (ngay.isoformat(), str(s.get('gio_bat_dau', '')))
        return (str(ngay)[:10], str(s.get('gio_bat_dau', '')))

    rows.sort(key=_key)

    n_done = n_upcoming = 0
    for s in rows:
        ng = parse_iso_date(s.get('ngay_thi') or s.get('ngay', ''))
        if ng and ng < today:
            n_done += 1
        else:
            n_upcoming += 1

    days_vn_short = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
    rows_html = []
    for i, ex in enumerate(rows, 1):
        zebra = '#f7fafc' if i % 2 == 0 else 'white'
        ma_lop = ex.get('lop_id', '') or ex.get('ma_mon', '') or '—'
        ten_mon = ex.get('ten_mon', '') or '—'
        ngay_v = ex.get('ngay_thi') or ex.get('ngay', '')
        ngay_d = parse_iso_date(ngay_v)
        ngay_str = ngay_d.strftime('%d/%m/%Y') if ngay_d else (str(ngay_v)[:10] or '—')
        thu_str = days_vn_short[ngay_d.weekday()] if ngay_d else '—'
        ca = ex.get('ca_thi', '') or ''
        gio_bd = str(ex.get('gio_bat_dau', ''))[:5]
        gio_kt = str(ex.get('gio_ket_thuc', ''))[:5]
        if gio_bd and gio_kt:
            ca = f'{ca}<br><span style="color:#718096; font-size:9px;">{gio_bd}-{gio_kt}</span>' if ca else f'{gio_bd}-{gio_kt}'
        phong = ex.get('phong', '') or '—'
        ht = ex.get('hinh_thuc', '') or '—'

        # Highlight: ngay thi sap toi (<=7 ngay) -> bold cam
        ngay_style = ''
        if ngay_d and ngay_d >= today:
            days_left = (ngay_d - today).days
            if days_left <= 7:
                ngay_style = 'color: #c05621; font-weight: bold;'

        rows_html.append(f'''
            <tr style="background: {zebra};">
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center; font-weight: bold;">{i}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center; font-weight: bold;">{ma_lop}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0;">{ten_mon}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center; {ngay_style}">{ngay_str}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center; color: #718096;">{thu_str}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center;">{ca}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center;">{phong}</td>
                <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center; color: #1e3a8a;">{ht}</td>
            </tr>
        ''')

    role_label = 'Học viên' if owner_role == 'hv' else 'Giảng viên'
    code_label = 'MSV' if owner_role == 'hv' else 'Mã GV'

    html = f'''
    <html><head><meta charset="utf-8"></head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e;">
    <div style="text-align: center; border-bottom: 3px solid #002060; padding-bottom: 12px; margin-bottom: 14px;">
        <h1 style="color: #002060; margin: 0; font-size: 22px;">TRUNG TÂM NGOẠI KHÓA EAUT</h1>
        <p style="margin: 4px 0; color: #4a5568; font-size: 11px;">
            Km 23, QL5, Trưng Trắc, Văn Lâm, Hưng Yên · Hotline: 024.3999.1111
        </p>
    </div>

    <h2 style="text-align: center; color: #c05621; margin: 0 0 4px 0;">LỊCH KIỂM TRA</h2>
    <p style="text-align: center; color: #4a5568; font-size: 12px; margin: 0 0 14px 0;">
        Tổng <b>{len(rows)}</b> môn thi
    </p>

    <table cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 14px;">
        <tr style="background: #edf2f7;">
            <td style="width: 18%; padding: 6px 8px; color: #4a5568;">{role_label}:</td>
            <td style="padding: 6px 8px;"><b>{owner_name or '—'}</b></td>
            <td style="width: 14%; padding: 6px 8px; color: #4a5568;">{code_label}:</td>
            <td style="padding: 6px 8px;"><b>{owner_code or '—'}</b></td>
        </tr>
        <tr>
            <td style="padding: 6px 8px; color: #4a5568;">Ngày in:</td>
            <td style="padding: 6px 8px;">{_dt.now().strftime('%d/%m/%Y %H:%M')}</td>
            <td style="padding: 6px 8px; color: #4a5568;">Phân bổ:</td>
            <td style="padding: 6px 8px;">
                <span style="color: #166534;"><b>{n_done}</b> đã thi</span>
                &nbsp;·&nbsp; <span style="color: #c05621;"><b>{n_upcoming}</b> sắp tới</span>
            </td>
        </tr>
    </table>

    <table cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 11px;">
        <thead><tr style="background: #002060; color: white;">
            <th style="padding: 8px; border: 1px solid #002060; width: 5%;">#</th>
            <th style="padding: 8px; border: 1px solid #002060; width: 11%;">Lớp</th>
            <th style="padding: 8px; border: 1px solid #002060;">Khóa học</th>
            <th style="padding: 8px; border: 1px solid #002060; width: 11%;">Ngày thi</th>
            <th style="padding: 8px; border: 1px solid #002060; width: 5%;">Thứ</th>
            <th style="padding: 8px; border: 1px solid #002060; width: 14%;">Ca / Giờ</th>
            <th style="padding: 8px; border: 1px solid #002060; width: 10%;">Phòng</th>
            <th style="padding: 8px; border: 1px solid #002060; width: 12%;">Hình thức</th>
        </tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
    </table>

    <p style="margin-top: 14px; color: #718096; font-size: 10px;">
        <b>Ghi chú:</b> Ngày thi <span style="color: #c05621; font-weight: bold;">tô cam</span> = trong vòng 7 ngày tới — vui lòng chú ý chuẩn bị.
    </p>

    <p style="margin-top: 18px; color: #a0aec0; font-size: 9px; text-align: center; font-style: italic;">
        File này được in từ phần mềm quản lý ngoại khoá EAUT.
    </p>
    </body></html>
    '''
    try:
        doc = _make_vn_textdoc(html)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Portrait)
        printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
        doc.print_(printer)
        msg_info(parent, 'Đã xuất PDF', f'Lịch thi đã lưu:\n{path}\n\nTổng {len(rows)} môn thi.')
        return True
    except Exception as e:
        msg_warn(parent, 'Lỗi xuất PDF', f'Không xuất được:\n{e}')
        return False


def export_class_grades_pdf(parent, class_info: dict, grades: list,
                              default_filename='BangDiemLop.pdf'):
    """Xuat bang diem ca lop ra PDF (cho GV in nop van phong / dan bang).

    Args:
        class_info: dict {ma_lop, ten_mon, ten_gv, semester_id, siso_max}
        grades: list of dict {msv, full_name, diem_qt, diem_thi, tong_ket, xep_loai}
    """
    if not grades:
        msg_warn(parent, 'Trống', 'Lớp này chưa có học viên hoặc chưa có điểm.')
        return False
    try:
        from PyQt5.QtPrintSupport import QPrinter
        from PyQt5.QtGui import QTextDocument
    except ImportError:
        msg_warn(parent, 'Lỗi', 'PyQt5.QtPrintSupport không có sẵn.')
        return False
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent, 'Xuất bảng điểm lớp PDF',
        os.path.join(os.path.expanduser('~'), 'Desktop', default_filename),
        'PDF Files (*.pdf)'
    )
    if not path:
        return False
    if not path.lower().endswith('.pdf'):
        path += '.pdf'

    from datetime import datetime as _dt

    # Compute aggregate stats
    total_g = [g for g in grades if g.get('tong_ket') is not None]
    n_passed = sum(1 for g in total_g if float(g['tong_ket']) >= 4.0)
    n_excellent = sum(1 for g in total_g if float(g['tong_ket']) >= 8.0)
    avg = sum(float(g['tong_ket']) for g in total_g) / len(total_g) if total_g else 0
    n_total = len(grades)
    n_pending = n_total - len(total_g)  # chua cham

    # Build student rows
    rows_html = []
    for i, g in enumerate(grades, 1):
        zebra = '#f7fafc' if i % 2 == 0 else 'white'
        qt = f"{float(g['diem_qt']):.1f}" if g.get('diem_qt') is not None else '—'
        thi = f"{float(g['diem_thi']):.1f}" if g.get('diem_thi') is not None else '—'
        tk = g.get('tong_ket')
        xl = g.get('xep_loai') or '—'
        if tk is not None:
            tk_v = float(tk)
            tk_disp = f'{tk_v:.1f}'
            tk_color = '#166534' if tk_v >= 8 else ('#1e3a8a' if tk_v >= 6.5
                       else '#92400e' if tk_v >= 5 else '#991b1b')
        else:
            tk_disp = '—'
            tk_color = '#a0aec0'
        # XL color
        xl_color = '#166534' if xl in ('A+', 'A') else (
            '#1e3a8a' if xl in ('B+', 'B') else (
                '#92400e' if xl in ('C+', 'C') else (
                    '#991b1b' if xl in ('D', 'F') else '#a0aec0')))
        rows_html.append(f'''
            <tr style="background: {zebra};">
                <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center;">{i}</td>
                <td style="padding: 5px; border: 1px solid #e2e8f0; font-weight: bold;">{g.get('msv', '—')}</td>
                <td style="padding: 5px; border: 1px solid #e2e8f0;">{g.get('full_name', '—')}</td>
                <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center;">{qt}</td>
                <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center;">{thi}</td>
                <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center; color: {tk_color}; font-weight: bold;">{tk_disp}</td>
                <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center; color: {xl_color}; font-weight: bold;">{xl}</td>
            </tr>
        ''')

    ma_lop = class_info.get('ma_lop', '—')
    ten_mon = class_info.get('ten_mon', '—')
    ten_gv = class_info.get('ten_gv', '—')
    sem_id = class_info.get('semester_id', '—') or '—'
    siso_max = class_info.get('siso_max', 0)

    html = f'''
    <html><head><meta charset="utf-8"></head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e;">
    <div style="text-align: center; border-bottom: 3px solid #002060; padding-bottom: 12px; margin-bottom: 16px;">
        <h1 style="color: #002060; margin: 0; font-size: 22px;">TRUNG TÂM NGOẠI KHÓA EAUT</h1>
        <p style="margin: 4px 0; color: #4a5568; font-size: 11px;">
            Km 23, QL5, Trưng Trắc, Văn Lâm, Hưng Yên · Hotline: 024.3999.1111
        </p>
    </div>

    <h2 style="text-align: center; color: #c05621; margin: 0 0 4px 0;">BẢNG ĐIỂM LỚP HỌC</h2>
    <p style="text-align: center; color: #4a5568; font-size: 12px; margin: 0 0 16px 0;">
        Lớp <b>{ma_lop}</b> · {ten_mon}
    </p>

    <table cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 12px;">
        <tr style="background: #edf2f7;">
            <td style="width: 25%; padding: 8px; color: #4a5568;">Mã lớp:</td>
            <td style="padding: 8px;"><b>{ma_lop}</b></td>
            <td style="width: 25%; padding: 8px; color: #4a5568;">Khóa học:</td>
            <td style="padding: 8px;"><b>{ten_mon}</b></td>
        </tr>
        <tr>
            <td style="padding: 8px; color: #4a5568;">Giảng viên:</td>
            <td style="padding: 8px;"><b>{ten_gv}</b></td>
            <td style="padding: 8px; color: #4a5568;">Đợt:</td>
            <td style="padding: 8px;">{sem_id}</td>
        </tr>
        <tr style="background: #edf2f7;">
            <td style="padding: 8px; color: #4a5568;">Sĩ số:</td>
            <td style="padding: 8px;"><b>{n_total}</b> / {siso_max} HV</td>
            <td style="padding: 8px; color: #4a5568;">Ngày in:</td>
            <td style="padding: 8px;">{_dt.now().strftime('%d/%m/%Y %H:%M')}</td>
        </tr>
    </table>

    <table cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 11px;">
        <thead><tr style="background: #002060; color: white;">
            <th style="padding: 6px; border: 1px solid #002060; width: 5%;">#</th>
            <th style="padding: 6px; border: 1px solid #002060; width: 14%;">MSV</th>
            <th style="padding: 6px; border: 1px solid #002060;">Họ và tên</th>
            <th style="padding: 6px; border: 1px solid #002060; width: 9%;">QT</th>
            <th style="padding: 6px; border: 1px solid #002060; width: 9%;">Thi</th>
            <th style="padding: 6px; border: 1px solid #002060; width: 11%;">Tổng kết</th>
            <th style="padding: 6px; border: 1px solid #002060; width: 11%;">Xếp loại</th>
        </tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
    </table>

    <div style="margin-top: 18px; padding: 12px; background: #f7fafc; border-left: 4px solid #002060; border-radius: 4px;">
        <p style="margin: 4px 0; font-size: 12px;"><b style="color: #002060;">Tổng kết lớp:</b></p>
        <p style="margin: 4px 0; font-size: 12px;">
            · Tổng học viên: <b>{n_total}</b> (đã chấm: <b>{len(total_g)}</b> · chưa chấm: <b>{n_pending}</b>)<br>
            · Đậu (≥ 4.0): <b style="color:#166534;">{n_passed}/{len(total_g)}</b>
                ({(n_passed*100//len(total_g)) if total_g else 0}%)<br>
            · Xuất sắc (≥ 8.0): <b style="color:#c05621;">{n_excellent}/{len(total_g)}</b><br>
            · Điểm trung bình lớp: <b style="color:#c05621;">{avg:.2f}</b>
        </p>
    </div>

    <div style="margin-top: 30px; display: flex; justify-content: space-between;">
        <div style="text-align: center; width: 40%;">
            <p style="color: #4a5568; font-size: 11px;">Phòng đào tạo</p>
            <p style="font-size: 10px; color: #718096; font-style: italic;">(ký tên, đóng dấu)</p>
        </div>
        <div style="text-align: center; width: 40%;">
            <p style="color: #4a5568; font-size: 11px;">Hà Nội, ngày {_dt.now().day}/{_dt.now().month}/{_dt.now().year}</p>
            <p style="margin-top: 4px;"><b>Giảng viên</b></p>
            <p style="font-size: 10px; color: #718096; font-style: italic;">(ký, họ tên)</p>
            <p style="margin-top: 40px;"><b>{ten_gv}</b></p>
        </div>
    </div>
    </body></html>
    '''
    try:
        doc = _make_vn_textdoc(html)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPrinter.A4)
        printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
        doc.print_(printer)
        msg_info(parent, 'Đã xuất PDF', f'Bảng điểm lớp đã lưu:\n{path}')
        return True
    except Exception as e:
        msg_warn(parent, 'Lỗi xuất PDF', f'Không xuất được:\n{e}')
        return False


def check_schedule_conflict_warn(parent, ngay, gio_bd, gio_kt, phong=None,
                                  lop_id=None, gv_id=None, exclude_id=None) -> bool:
    """Check conflict + hoi user confirm neu trung. Tra ve True = continue, False = cancel.

    Goi truoc khi save schedule (create/update). Format msg_confirm voi ds buoi conflict.
    """
    if not DB_AVAILABLE:
        return True  # khong check duoc -> cho qua
    try:
        result = ScheduleService.check_conflict(
            ngay=ngay, gio_bat_dau=gio_bd, gio_ket_thuc=gio_kt,
            phong=phong, lop_id=lop_id, gv_id=gv_id, exclude_id=exclude_id,
        )
        conflicts = result.get('conflicts', []) if result else []
    except Exception as e:
        print(f'[CHECK_CONFLICT] loi: {e}')
        return True  # API loi -> cho qua, khong block user
    if not conflicts:
        return True
    # Build msg chi tiet
    lines = [f'⚠ <b>Trùng lịch với {len(conflicts)} buổi đã có:</b><br>']
    for c in conflicts[:5]:  # cap 5 dong
        lop = c.get('lop_id', '?')
        gio = f"{str(c.get('gio_bat_dau', ''))[:5]}-{str(c.get('gio_ket_thuc', ''))[:5]}"
        phong_c = c.get('phong', '—') or '—'
        gv = c.get('ten_gv', '—') or '—'
        lines.append(f'• <b>{lop}</b> ({c.get("ten_mon", "")}) · {gio} · P.{phong_c} · GV {gv}')
    if len(conflicts) > 5:
        lines.append(f'<i>... và {len(conflicts) - 5} buổi nữa</i>')
    lines.append('<br>Bạn có muốn tạo buổi học này không (sẽ tạo dù trùng)?')
    msg = '<br>'.join(lines)
    return msg_confirm(parent, '⚠ Trùng lịch', msg)


def fmt_vnd(amount, suffix=' đ', empty_zero=False) -> str:
    """Format so tien Viet Nam Dong: 1500000 -> '1.500.000 đ'.

    Args:
        amount: int/float/None
        suffix: hau to (default ' đ', dung '' neu khong muon)
        empty_zero: True -> tra '—' khi amount = 0/None (cho UI co data 'rong')
    """
    try:
        n = int(amount or 0)
    except (ValueError, TypeError):
        return '—' if empty_zero else f'0{suffix}'
    if n == 0 and empty_zero:
        return '—'
    return f'{n:,}'.replace(',', '.') + suffix


def time_greeting(now=None) -> str:
    """Tra ve loi chao theo gio trong ngay (Chao buoi sang/chieu/toi/khuya).

    - 5h-11h: sang
    - 11h-13h: trua
    - 13h-18h: chieu
    - 18h-22h: toi
    - 22h-5h: khuya

    Args:
        now: datetime (default = now). Truyen vao de unit-test
    """
    from datetime import datetime
    h = (now or datetime.now()).hour
    if 5 <= h < 11:
        return 'Chào buổi sáng'
    if 11 <= h < 13:
        return 'Chào buổi trưa'
    if 13 <= h < 18:
        return 'Chào buổi chiều'
    if 18 <= h < 22:
        return 'Chào buổi tối'
    return 'Chào buổi khuya'


# ===== Avatar palette =====
# 8 mau pastel + chu navy de tuong phan; chon theo hash(initials) -> moi user 1 mau co dinh
_AVATAR_PALETTE = [
    ('#dbe7ff', '#1a4480'),  # blue
    ('#e0f2e9', '#1e6b3a'),  # green
    ('#fff4d4', '#7a4f00'),  # gold
    ('#fde2e2', '#9b1e1e'),  # red
    ('#e9deff', '#4b1d8a'),  # purple
    ('#d3f0f5', '#0d5862'),  # teal
    ('#ffe4cf', '#8a3d00'),  # orange
    ('#f0e1d6', '#5e3a1f'),  # brown
]


def avatar_style(initials: str) -> str:
    """Sinh QSS background+color cho lblAvatar dua tren initials.

    Cung 1 user -> cung 1 mau qua moi lan run app (deterministic).
    Truoc dung Python builtin hash() nhung no co PYTHONHASHSEED random nen
    moi run cho mau khac nhau - DH co the la xanh hom nay, vang ngay mai...
    Nay dung sum(ord(c)) deterministic - khong can hashlib (overkill cho 8 mau).
    """
    key = (initials or '?').strip().upper() or '?'
    idx = sum(ord(c) for c in key) % len(_AVATAR_PALETTE)
    bg, fg = _AVATAR_PALETTE[idx]
    return (f'background: {bg}; border-radius: 19px; color: {fg}; '
            f'font-size: 13px; font-weight: bold;')


# ===== Status badge =====
# Map cac trang thai len mau (bg / fg) cho cell widget badge style.
# Key normalize: lowercase, strip dau de match nhanh.
_STATUS_BADGE_MAP = {
    # Thanh toan / dang ky
    'da thanh toan': ('#dcfce7', '#166534'),  # green
    'cho thanh toan': ('#fef3c7', '#92400e'),  # amber
    'da huy': ('#fee2e2', '#991b1b'),  # red
    'huy': ('#fee2e2', '#991b1b'),
    'hoan thanh': ('#dbeafe', '#1e3a8a'),  # blue
    'hoan tien': ('#fee2e2', '#991b1b'),
    # Lop / hoc ky
    'open': ('#dcfce7', '#166534'),
    'mo dang ky': ('#dcfce7', '#166534'),
    'dang mo': ('#dcfce7', '#166534'),
    'closed': ('#e5e7eb', '#374151'),
    'dong': ('#e5e7eb', '#374151'),
    'da dong': ('#e5e7eb', '#374151'),
    'full': ('#fef3c7', '#92400e'),
    'da day': ('#fef3c7', '#92400e'),
    'upcoming': ('#dbeafe', '#1e3a8a'),
    'sap mo': ('#dbeafe', '#1e3a8a'),
    'sap toi': ('#dbeafe', '#1e3a8a'),
    # Diem danh
    'co mat': ('#dcfce7', '#166534'),
    'present': ('#dcfce7', '#166534'),
    'tre': ('#fef3c7', '#92400e'),
    'late': ('#fef3c7', '#92400e'),
    'vang': ('#fee2e2', '#991b1b'),
    'absent': ('#fee2e2', '#991b1b'),
    'co phep': ('#dbeafe', '#1e3a8a'),
    'excused': ('#dbeafe', '#1e3a8a'),
    # Curriculum / progress
    'dang hoc': ('#dbeafe', '#1e3a8a'),  # blue
    'cho tt': ('#fef3c7', '#92400e'),
    'da tt': ('#dcfce7', '#166534'),  # green - alias 'Đã thanh toán' viet tat
    'da pass': ('#dcfce7', '#166534'),
    'pass': ('#dcfce7', '#166534'),
    'chua hoc': ('#e5e7eb', '#374151'),
    'fail': ('#fee2e2', '#991b1b'),
    'rot': ('#fee2e2', '#991b1b'),
    # Xep loai (thang 10): A+/A xanh dam, B+/B xanh duong, C+/C cam, D/F do
    'a+': ('#bbf7d0', '#14532d'),
    'a': ('#dcfce7', '#166534'),
    'b+': ('#bfdbfe', '#1e3a8a'),
    'b': ('#dbeafe', '#1e40af'),
    'c+': ('#fde68a', '#78350f'),
    'c': ('#fef3c7', '#92400e'),
    'd': ('#fecaca', '#7f1d1d'),
    'f': ('#fee2e2', '#991b1b'),
}


def _status_normalize(text: str) -> str:
    """Bo dau + lowercase de map status (cho ca 'Đã thanh toán' va 'da thanh toan')."""
    import unicodedata
    s = unicodedata.normalize('NFD', text or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower().strip().replace('đ', 'd')


def score_to_letter(total) -> str:
    """Quy doi diem TK (thang 10) sang xep loai chu A+/A/.../F.

    Bac thang theo quy che dao tao: A+ ≥9, A ≥8.5, B+ ≥8, B ≥7, C+ ≥6.5,
    C ≥5.5, D ≥4, con lai F. KHOP voi backend GradeService._xep_loai_10
    (truoc co divergence: FE B ≥6.5, BE B ≥7 -> user nhap 6.5 thay 'B' o
    dialog nhung DB luu 'C+' -> reload se thay khac).

    Dung chung cho dialog nhap diem + auto-recalc khi user sua o cot QT/Thi
    truc tiep tren bang.
    """
    try:
        s = float(total)
    except (TypeError, ValueError):
        return ''
    if s >= 9: return 'A+'
    if s >= 8.5: return 'A'
    if s >= 8: return 'B+'
    if s >= 7: return 'B'
    if s >= 6.5: return 'C+'
    if s >= 5.5: return 'C'
    if s >= 4: return 'D'
    return 'F'


def style_status_item(item: 'QtWidgets.QTableWidgetItem', text: str):
    """Style 1 QTableWidgetItem voi mau + bold theo status text.

    Don gian: KHONG dung widget (tranh double text khi co ca setItem + setCellWidget).
    Apply truc tiep tren QTableWidgetItem: foreground color + bold font + center align.
    """
    norm = _status_normalize(text)
    _bg, fg = _STATUS_BADGE_MAP.get(norm, ('#f1f5f9', '#475569'))
    item.setForeground(QColor(fg))
    item.setFont(QFont('Segoe UI', 11, QFont.Bold))
    item.setTextAlignment(Qt.AlignCenter)
    return item


def set_sidebar_badge(lbl, count: int, cap: int = 99):
    """Set sidebar badge label theo count: an khi count<=0, hien "N" hoac "99+" khi vuot cap.

    Dung chung cho 4 windows (HV/GV/NV/Adm) - tranh duplicate logic
    str(min(n, 99)) + ('+' if n > 99 else '') o moi cho update badge.

    Args:
        lbl: QLabel badge (co the None - silent skip)
        count: so luong (thong bao/bai tap/dk qua han...)
        cap: nguong cap, qua thi hien "{cap}+" (default 99)
    """
    if not lbl:
        return
    if count and count > 0:
        lbl.setText(f'{min(count, cap)}+' if count > cap else str(count))
        lbl.show()
    else:
        lbl.hide()


def cleanup_banner(parent, name: str, kind=None):
    """Remove tat ca QFrame con co objectName = name (cho re-render banner an toan).

    Qt deleteLater() khong xoa instant - re-render lien tiep (vd nav qua lai
    HV dashboard) co the de lai banner cu chong banner moi. Helper nay tim
    TAT CA child match name + setParent(None) + deleteLater() de schedule
    cleanup ngay cycle event loop tiep theo.

    Args:
        parent: widget cha (page/QWidget)
        name: objectName cua banner can xoa
        kind: optional widget class (default QFrame) - co the truyen QLabel...
    """
    klass = kind or QtWidgets.QFrame
    for old in parent.findChildren(klass):
        if old.objectName() == name:
            old.setParent(None)
            old.deleteLater()


def count_overdue_pending_registrations(threshold_days: int = 7) -> int:
    """Dem so dang ky 'pending_payment' qua han thanh toan (>threshold_days ngay tu ngay_dk).

    Dung chung cho sidebar badge: Adm reg overdue + NV pay overdue (truoc duplicate
    20+ dong loop). Trahve 0 neu DB chua available hoac API loi.

    Args:
        threshold_days: nguong ngay (default 7) - moi DK 'pending_payment' co
            ngay_dk cu hon threshold_days se duoc dem.
    """
    if not (DB_AVAILABLE and RegistrationService):
        return 0
    from datetime import date as _date
    n = 0
    try:
        rows = RegistrationService.get_all_registrations(limit=500) or []
        today_d = _date.today()
        for r in rows:
            if r.get('trang_thai') != 'pending_payment':
                continue
            ng = parse_iso_date(r.get('ngay_dk'))
            if ng is None:
                continue
            if (today_d - ng).days > threshold_days:
                n += 1
    except Exception as e:
        print(f'[BADGE] count_overdue_pending_registrations loi: {e}')
    return n


def set_table_empty_state(tbl, message='Chưa có dữ liệu', row_height=50,
                          cta_text=None, cta_callback=None, icon='📭'):
    """Set bang ve trang thai rong: row span full width voi message centered.

    Tien ich chung cho cac _fill_*() khi khong co data tu DB - nhat quan UI.
    Args:
        message: text hien chinh
        row_height: chieu cao row (tang neu co CTA button)
        cta_text: optional, neu co se hien button "Action ↗" o duoi message
        cta_callback: callable () -> None khi click CTA button
        icon: emoji icon (default 📭 hop thu rong)
    """
    tbl.setRowCount(1)
    tbl.clearSpans()
    if tbl.columnCount() > 1:
        tbl.setSpan(0, 0, 1, tbl.columnCount())

    # Neu co CTA -> dung widget container (item-only khong fit button)
    if cta_text and cta_callback:
        container = QtWidgets.QFrame()
        container.setStyleSheet('QFrame { background: transparent; border: none; }')
        v = QtWidgets.QVBoxLayout(container)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(8)
        v.setAlignment(Qt.AlignCenter)
        # Icon + message
        lbl_msg = QtWidgets.QLabel(f'{icon}  {message}')
        lbl_msg.setStyleSheet('color: #a0aec0; font-size: 13px; background: transparent; border: none;')
        lbl_msg.setAlignment(Qt.AlignCenter)
        fnt = QFont('Segoe UI', 11)
        fnt.setItalic(True)
        lbl_msg.setFont(fnt)
        v.addWidget(lbl_msg)
        # CTA button
        btn = QtWidgets.QPushButton(cta_text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(220, 34)
        btn.setStyleSheet(
            'QPushButton { background: #002060; color: white; border: none; '
            'border-radius: 6px; font-size: 12px; font-weight: bold; padding: 4px 16px; } '
            'QPushButton:hover { background: #1a3a6c; }'
        )
        btn.clicked.connect(cta_callback)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn)
        btn_row.addStretch()
        v.addLayout(btn_row)
        tbl.setCellWidget(0, 0, container)
        tbl.setRowHeight(0, max(row_height, 110))
    else:
        ph = QtWidgets.QTableWidgetItem(f'{icon}  {message}' if icon else message)
        ph.setTextAlignment(Qt.AlignCenter)
        ph.setForeground(QColor('#a0aec0'))  # text_light
        fnt = QFont('Segoe UI', 10)
        fnt.setItalic(True)
        ph.setFont(fnt)
        tbl.setItem(0, 0, ph)
        tbl.setRowHeight(0, row_height)


def msg_confirm_delete(parent, item_type, item_code, item_name='', related=''):
    """Confirm dialog danh rieng cho XOA - icon warning + nut do + canh bao mat data.

    Args:
        item_type: loai item ('khóa học', 'lớp', 'học viên', ...)
        item_code: ma/id item
        item_name: ten item (optional)
        related: text canh bao ve du lieu lien quan se mat (vd "Lop nay co 25 HV dang ky")
    """
    box = QtWidgets.QMessageBox(parent)
    box.setIcon(QtWidgets.QMessageBox.Warning)
    box.setWindowTitle(f'⚠ Xác nhận xóa {item_type}')
    label = f'<b>{item_code}</b>'
    if item_name:
        label += f' — {item_name}'
    box.setText(f'Bạn có chắc muốn xóa {item_type} {label}?')
    info_lines = ['Thao tác này KHÔNG THỂ HOÀN TÁC.']
    if related:
        info_lines.insert(0, related)
    box.setInformativeText('\n\n'.join(info_lines))
    box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    box.setDefaultButton(QtWidgets.QMessageBox.No)
    box.button(QtWidgets.QMessageBox.Yes).setText('Xóa')
    box.button(QtWidgets.QMessageBox.No).setText('Huỷ')
    # Style nut Yes mau do nguy hiem
    _style_msgbox(box)
    yes_btn = box.button(QtWidgets.QMessageBox.Yes)
    yes_btn.setStyleSheet(
        'QPushButton { background: #c53030; color: white; border: none; '
        'padding: 6px 18px; border-radius: 4px; font-weight: bold; } '
        'QPushButton:hover { background: #a03030; }'
    )
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
    """bo dau + lower + strip whitespace cho search.
    Truoc khong strip -> user go ' admin' (leading space) co the bi miss
    vi ' admin' khong la substring cua 'admin'."""
    if not s:
        return ''
    import unicodedata
    s = unicodedata.normalize('NFD', str(s))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower().replace('đ', 'd').replace('Đ', 'd').strip()


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


def show_today_sessions_dialog(parent, sessions, role='hv'):
    """Popup hien tat ca buoi hoc/day cua HOM NAY voi gio + lop + phong + GV/siso.
    Sap xep theo gio_bat_dau."""
    from datetime import date as _date, datetime as _dt
    navy = '#002060'
    border = '#d2d6dc'

    # Sort theo gio bat dau
    rows = sorted(sessions or [], key=lambda s: str(s.get('gio_bat_dau', '')))

    dlg = QtWidgets.QDialog(parent)
    title_role = 'Lịch học hôm nay' if role == 'hv' else 'Lịch dạy hôm nay'
    dlg.setWindowTitle(title_role)
    dlg.setFixedSize(540, min(180 + len(rows) * 90, 600))
    dlg.setFont(QFont('Segoe UI', 10))
    dlg.setStyleSheet('QDialog { background: white; font-family: "Segoe UI"; }')

    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    # Header navy
    header = QtWidgets.QFrame()
    header.setFixedHeight(72)
    header.setStyleSheet(f'QFrame {{ background: {navy}; border: none; }}')
    hv = QtWidgets.QVBoxLayout(header)
    hv.setContentsMargins(20, 12, 20, 10)
    hv.setSpacing(2)
    today_str = _dt.now().strftime('%A, %d/%m/%Y')
    # Translate weekday EN -> VN
    en_to_vn = {'Monday': 'Thứ Hai', 'Tuesday': 'Thứ Ba', 'Wednesday': 'Thứ Tư',
                'Thursday': 'Thứ Năm', 'Friday': 'Thứ Sáu', 'Saturday': 'Thứ Bảy',
                'Sunday': 'Chủ Nhật'}
    for en, vn in en_to_vn.items():
        if today_str.startswith(en):
            today_str = today_str.replace(en, vn, 1)
            break
    lbl_title = QtWidgets.QLabel(f'🕐  {title_role}')
    lbl_title.setStyleSheet('color: white; font-size: 15px; font-weight: bold; background: transparent;')
    hv.addWidget(lbl_title)
    lbl_sub = QtWidgets.QLabel(f'{today_str}  ·  {len(rows)} buổi')
    lbl_sub.setStyleSheet('color: rgba(255,255,255,0.78); font-size: 11px; background: transparent;')
    hv.addWidget(lbl_sub)
    lay.addWidget(header)

    # Body: scrollable list of session cards
    body = QtWidgets.QScrollArea()
    body.setWidgetResizable(True)
    body.setStyleSheet('QScrollArea { border: none; background: white; } '
                        'QScrollBar:vertical { width: 8px; background: transparent; } '
                        'QScrollBar::handle:vertical { background: #c4c7cc; border-radius: 4px; min-height: 30px; }')
    inner = QtWidgets.QWidget()
    inner.setStyleSheet('background: white;')
    iv = QtWidgets.QVBoxLayout(inner)
    iv.setContentsMargins(18, 14, 18, 14)
    iv.setSpacing(10)

    if not rows:
        empty = QtWidgets.QLabel('✓ Không có buổi nào hôm nay')
        empty.setStyleSheet('color: #718096; font-size: 13px; padding: 30px; '
                             'background: #f7fafc; border: 1px dashed #cbd5e0; border-radius: 8px;')
        empty.setAlignment(Qt.AlignCenter)
        iv.addWidget(empty)
    else:
        # Color palette per lop
        palette = ['#002060', '#c68a1e', '#276749', '#c53030', '#3182ce']
        color_by_lop = {}
        for sc in rows:
            ma_lop = sc.get('lop_id', '?') or '?'
            if ma_lop not in color_by_lop:
                color_by_lop[ma_lop] = palette[len(color_by_lop) % len(palette)]
            color = color_by_lop[ma_lop]
            ten_mon = sc.get('ten_mon', '') or '—'
            gio_bd = str(sc.get('gio_bat_dau', ''))[:5]
            gio_kt = str(sc.get('gio_ket_thuc', ''))[:5]
            phong = sc.get('phong', '') or '—'
            buoi_so = sc.get('buoi_so')

            card = QtWidgets.QFrame()
            card.setStyleSheet(f'QFrame {{ background: white; border: 1px solid #e2e8f0; '
                                f'border-radius: 8px; border-left: 4px solid {color}; }}')
            cv = QtWidgets.QVBoxLayout(card)
            cv.setContentsMargins(14, 10, 14, 10)
            cv.setSpacing(4)

            # Dong 1: Gio + Lop
            l1 = QtWidgets.QLabel(f'<b style="color:{color}; font-size:14px;">{gio_bd} - {gio_kt}</b>'
                                    f'  <span style="color:#4a5568; font-size:13px;">·  {ma_lop}</span>')
            l1.setStyleSheet('background: transparent; border: none;')
            cv.addWidget(l1)

            # Dong 2: Ten mon
            l2 = QtWidgets.QLabel(ten_mon)
            l2.setStyleSheet('color: #1a1a2e; font-size: 12px; font-weight: bold; '
                              'background: transparent; border: none;')
            l2.setWordWrap(True)
            cv.addWidget(l2)

            # Dong 3: Info phu
            extra_parts = [f'📍 Phòng {phong}']
            if buoi_so:
                extra_parts.append(f'📖 Buổi {buoi_so}')
            if role == 'hv':
                gv = sc.get('ten_gv', '') or ''
                if gv:
                    extra_parts.append(f'👨‍🏫 {gv}')
            else:
                siso = sc.get('siso_hien_tai')
                if siso is not None:
                    extra_parts.append(f'👥 {siso} HV')
            l3 = QtWidgets.QLabel('  ·  '.join(extra_parts))
            l3.setStyleSheet('color: #718096; font-size: 11px; background: transparent; border: none;')
            cv.addWidget(l3)

            iv.addWidget(card)

    iv.addStretch()
    body.setWidget(inner)
    lay.addWidget(body, 1)

    # Footer
    footer = QtWidgets.QFrame()
    footer.setFixedHeight(54)
    footer.setStyleSheet(f'QFrame {{ background: #f7fafc; border-top: 1px solid {border}; }}')
    fl = QtWidgets.QHBoxLayout(footer)
    fl.setContentsMargins(20, 10, 20, 10)
    fl.setAlignment(Qt.AlignRight)
    btn_close = QtWidgets.QPushButton('Đóng')
    btn_close.setFixedSize(110, 34)
    btn_close.setCursor(Qt.PointingHandCursor)
    btn_close.setStyleSheet(f'QPushButton {{ background: {navy}; color: white; border: none; '
                              f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                              f'QPushButton:hover {{ background: #1a3a6c; }}')
    btn_close.clicked.connect(dlg.accept)
    fl.addWidget(btn_close)
    lay.addWidget(footer)

    dlg.exec_()


def show_exam_detail_dialog(parent, exam_row, role='hv'):
    """Popup chi tiet 1 ca thi khi click vao row tbl. role: 'hv' | 'gv'.
    exam_row: dict {ma_mon, ten_mon, lop_id, ngay_thi, ca_thi, gio_bat_dau, gio_ket_thuc,
                    phong, hinh_thuc, ten_gv, semester_id, ...}
    """
    from datetime import date as _date
    ngay_v = exam_row.get('ngay_thi') or exam_row.get('ngay', '')
    ngay_d = parse_iso_date(ngay_v)
    ngay_str = ngay_d.strftime('%d/%m/%Y') if ngay_d else (str(ngay_v)[:10] or '—')
    if ngay_d:
        thu_vn = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm',
                   'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật'][ngay_d.weekday()]
        ngay_str = f'{thu_vn}, {ngay_str}'
        # Days_left countdown
        today = _date.today()
        dl = (ngay_d - today).days
        if dl > 0:
            ngay_str += f'  ·  Còn {dl} ngày'
        elif dl == 0:
            ngay_str += '  ·  HÔM NAY'
        else:
            ngay_str += f'  ·  Đã thi {-dl} ngày trước'

    gio_bd = str(exam_row.get('gio_bat_dau', ''))[:5]
    gio_kt = str(exam_row.get('gio_ket_thuc', ''))[:5]
    gio_str = f'{gio_bd} - {gio_kt}' if gio_bd and gio_kt else '—'
    ca_thi = exam_row.get('ca_thi', '') or ''
    if gio_str != '—' and ca_thi:
        ca_full = f'{ca_thi}  ({gio_str})'
    elif ca_thi:
        ca_full = ca_thi
    else:
        ca_full = gio_str

    ma_lop = exam_row.get('lop_id', '') or '—'
    ten_mon = exam_row.get('ten_mon', '') or '—'
    ma_mon = exam_row.get('ma_mon', '') or ma_lop
    phong = exam_row.get('phong', '') or '—'
    hinh_thuc = exam_row.get('hinh_thuc', '') or '—'
    sem_id = exam_row.get('semester_id', '') or '—'

    fields = [
        ('NGÀY THI', ngay_str),
        ('CA THI / GIỜ', ca_full),
        ('PHÒNG THI', phong),
        ('LỚP', ma_lop),
        ('KHÓA HỌC', ten_mon),
        ('HÌNH THỨC', hinh_thuc),
    ]
    if role == 'hv':
        gv_name = exam_row.get('ten_gv', '') or ''
        if gv_name:
            fields.append(('GIẢNG VIÊN', gv_name))
    if sem_id and sem_id != '—':
        fields.append(('ĐỢT', sem_id))

    show_detail_dialog(
        parent,
        title=f'Chi tiết ca thi · {ma_lop}',
        fields=fields,
        avatar_text=ma_mon[:2] if ma_mon != '—' else '?',
        subtitle=ten_mon,
    )


def pick_week_jumper_dialog(parent, current_qdate=None, title='Chọn ngày để xem tuần'):
    """Dialog cho user chon 1 ngay tuy y -> tra ve QDate cua ngay duoc chon
    (caller tu lay Monday cua tuan chua ngay do).

    Returns: QDate hoac None neu user huy.
    """
    navy = '#002060'
    border = '#d2d6dc'

    dlg = QtWidgets.QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setFixedSize(360, 380)
    dlg.setFont(QFont('Segoe UI', 10))
    dlg.setStyleSheet('QDialog { background: white; font-family: "Segoe UI"; }')

    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    # Header navy
    header = QtWidgets.QFrame()
    header.setFixedHeight(60)
    header.setStyleSheet(f'QFrame {{ background: {navy}; border: none; }}')
    hv = QtWidgets.QVBoxLayout(header)
    hv.setContentsMargins(20, 10, 20, 8)
    hv.setSpacing(2)
    lbl_title = QtWidgets.QLabel('📅 Chọn ngày để xem tuần')
    lbl_title.setStyleSheet('color: white; font-size: 14px; font-weight: bold; background: transparent;')
    hv.addWidget(lbl_title)
    lbl_sub = QtWidgets.QLabel('Tuần chứa ngày bạn chọn sẽ được hiển thị')
    lbl_sub.setStyleSheet('color: rgba(255,255,255,0.75); font-size: 10px; background: transparent;')
    hv.addWidget(lbl_sub)
    lay.addWidget(header)

    # Body: calendar widget
    body = QtWidgets.QFrame()
    bv = QtWidgets.QVBoxLayout(body)
    bv.setContentsMargins(15, 12, 15, 12)
    bv.setSpacing(8)

    cal = QtWidgets.QCalendarWidget()
    cal.setVerticalHeaderFormat(QtWidgets.QCalendarWidget.NoVerticalHeader)
    cal.setGridVisible(False)
    cal.setFirstDayOfWeek(Qt.Monday)
    cal.setNavigationBarVisible(True)
    if current_qdate:
        cal.setSelectedDate(current_qdate)
    cal.setStyleSheet(
        'QCalendarWidget QToolButton { color: white; background: #002060; '
        '  font-size: 12px; padding: 4px 8px; border: none; } '
        'QCalendarWidget QToolButton:hover { background: #003080; } '
        'QCalendarWidget QMenu { background: white; } '
        'QCalendarWidget QSpinBox { background: white; padding: 2px 4px; } '
        'QCalendarWidget QAbstractItemView:enabled { '
        '  font-size: 12px; color: #1a1a2e; '
        '  selection-background-color: #002060; selection-color: white; }'
    )
    bv.addWidget(cal, 1)

    # Hien thi tuan tuong ung
    lbl_preview = QtWidgets.QLabel()
    lbl_preview.setStyleSheet('color: #4a5568; font-size: 11px; background: #f7fafc; '
                               'border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px;')
    lbl_preview.setAlignment(Qt.AlignCenter)

    def _update_preview():
        d = cal.selectedDate()
        mon = d.addDays(-(d.dayOfWeek() - 1))
        sun = mon.addDays(6)
        lbl_preview.setText(
            f'Tuần: {mon.toString("dd/MM/yyyy")} → {sun.toString("dd/MM/yyyy")}'
        )

    cal.selectionChanged.connect(_update_preview)
    _update_preview()
    bv.addWidget(lbl_preview)
    lay.addWidget(body, 1)

    # Footer
    footer = QtWidgets.QFrame()
    footer.setFixedHeight(54)
    footer.setStyleSheet(f'QFrame {{ background: #f7fafc; border-top: 1px solid {border}; }}')
    fl = QtWidgets.QHBoxLayout(footer)
    fl.setContentsMargins(15, 10, 15, 10)
    fl.setSpacing(8)

    btn_today = QtWidgets.QPushButton('Hôm nay')
    btn_today.setFixedHeight(32)
    btn_today.setMinimumWidth(80)
    btn_today.setCursor(Qt.PointingHandCursor)
    btn_today.setStyleSheet('QPushButton { background: white; color: #4a5568; '
                             'border: 1px solid #d2d6dc; border-radius: 6px; font-size: 11px; '
                             'padding: 0 12px; } '
                             'QPushButton:hover { background: #edf2f7; border-color: #002060; color: #002060; }')
    btn_today.clicked.connect(lambda: cal.setSelectedDate(QDate.currentDate()))
    fl.addWidget(btn_today)
    fl.addStretch()

    btn_cancel = QtWidgets.QPushButton('Huỷ')
    btn_cancel.setFixedSize(80, 32)
    btn_cancel.setCursor(Qt.PointingHandCursor)
    btn_cancel.setStyleSheet('QPushButton { background: white; color: #4a5568; '
                              'border: 1px solid #d2d6dc; border-radius: 6px; font-size: 12px; } '
                              'QPushButton:hover { background: #edf2f7; }')
    btn_cancel.clicked.connect(dlg.reject)
    fl.addWidget(btn_cancel)

    btn_ok = QtWidgets.QPushButton('Đi đến tuần')
    btn_ok.setFixedHeight(32)
    btn_ok.setMinimumWidth(110)
    btn_ok.setCursor(Qt.PointingHandCursor)
    btn_ok.setStyleSheet(f'QPushButton {{ background: {navy}; color: white; border: none; '
                          f'border-radius: 6px; font-size: 12px; font-weight: bold; padding: 0 12px; }} '
                          f'QPushButton:hover {{ background: #1a3a6c; }}')
    btn_ok.clicked.connect(dlg.accept)
    fl.addWidget(btn_ok)

    lay.addWidget(footer)

    if dlg.exec_() == QtWidgets.QDialog.Accepted:
        return cal.selectedDate()
    return None


def show_class_full_schedule_dialog(parent, lop_id, ten_mon, schedules, role='hv', ten_gv=''):
    """Dialog hien tat ca buoi cua 1 lop (24 buoi du kien) - dung cho HV va GV.

    schedules: list dict {id, ngay, gio_bat_dau, gio_ket_thuc, phong, buoi_so,
                          noi_dung, trang_thai, ten_gv}
    ten_gv: dung cho header PDF khi user click "In PDF"
    """
    navy = '#002060'
    text_dark = '#1a1a2e'
    text_light = '#718096'
    border = '#d2d6dc'

    dlg = QtWidgets.QDialog(parent)
    dlg.setWindowTitle(f'Toàn bộ lịch lớp {lop_id}')
    dlg.setFixedSize(720, 580)
    dlg.setFont(QFont('Segoe UI', 10))
    dlg.setStyleSheet('QDialog { background: white; font-family: "Segoe UI"; }')

    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    # Header navy
    header = QtWidgets.QFrame()
    header.setFixedHeight(80)
    header.setStyleSheet(f'QFrame {{ background: {navy}; border: none; }}')
    hv = QtWidgets.QVBoxLayout(header)
    hv.setContentsMargins(20, 14, 20, 14)
    hv.setSpacing(2)
    lbl_title = QtWidgets.QLabel(f'Lịch học toàn bộ · {lop_id}')
    lbl_title.setStyleSheet('color: white; font-size: 15px; font-weight: bold; background: transparent;')
    hv.addWidget(lbl_title)
    lbl_sub = QtWidgets.QLabel(ten_mon or '—')
    lbl_sub.setStyleSheet('color: rgba(255,255,255,0.75); font-size: 11px; background: transparent;')
    hv.addWidget(lbl_sub)
    lay.addWidget(header)

    # Body
    body = QtWidgets.QFrame()
    body.setStyleSheet('QFrame { background: white; border: none; }')
    bv = QtWidgets.QVBoxLayout(body)
    bv.setContentsMargins(20, 16, 20, 16)
    bv.setSpacing(10)

    from datetime import date as _date, datetime as _dt
    # Sap xep: ngay -> gio_bat_dau
    rows = list(schedules or [])

    def _key(s):
        ngay = s.get('ngay', '')
        if isinstance(ngay, _date):
            ngay_iso = ngay.isoformat()
        else:
            ngay_iso = str(ngay)[:10]
        return (ngay_iso, str(s.get('gio_bat_dau', '')))

    rows.sort(key=_key)

    # Tinh: bao nhieu buoi da xay ra, bao nhieu sap toi
    today = _date.today()
    done_count = 0
    upcoming_count = 0
    cancelled_count = 0
    for s in rows:
        ngay = parse_iso_date(s.get('ngay', ''))
        st = s.get('trang_thai') or ''
        if st == 'cancelled':
            cancelled_count += 1
        elif ngay and ngay < today:
            done_count += 1
        else:
            upcoming_count += 1

    # Stats bar
    stat_bar = QtWidgets.QFrame()
    stat_bar.setFixedHeight(48)
    stat_bar.setStyleSheet('QFrame { background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 6px; }')
    sb = QtWidgets.QHBoxLayout(stat_bar)
    sb.setContentsMargins(14, 8, 14, 8)
    sb.setSpacing(0)
    for label, val, color in [
        (f'Tổng', f'{len(rows)}', navy),
        (f'Đã diễn ra', f'{done_count}', '#276749'),
        (f'Sắp tới', f'{upcoming_count}', '#c05621'),
        (f'Đã huỷ', f'{cancelled_count}', '#991b1b'),
    ]:
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(0)
        l1 = QtWidgets.QLabel(label)
        l1.setStyleSheet(f'color: {text_light}; font-size: 10px; background: transparent; border: none;')
        l1.setAlignment(Qt.AlignCenter)
        l2 = QtWidgets.QLabel(val)
        l2.setStyleSheet(f'color: {color}; font-size: 16px; font-weight: bold; background: transparent; border: none;')
        l2.setAlignment(Qt.AlignCenter)
        col.addWidget(l1)
        col.addWidget(l2)
        sb.addLayout(col, 1)
    bv.addWidget(stat_bar)

    # Table
    tbl = QtWidgets.QTableWidget()
    tbl.setColumnCount(7)
    tbl.setHorizontalHeaderLabels(['Buổi', 'Ngày', 'Thứ', 'Giờ', 'Phòng', 'Trạng thái', 'Nội dung'])
    tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    tbl.setShowGrid(False)
    tbl.setAlternatingRowColors(True)
    tbl.verticalHeader().setVisible(False)
    tbl.setStyleSheet(
        f'QTableWidget {{ background: white; border: 1px solid {border}; border-radius: 6px; '
        f'gridline-color: #edf2f7; alternate-background-color: #fafbfc; font-size: 12px; }} '
        f'QHeaderView::section {{ background: {navy}; color: white; padding: 6px; '
        f'border: none; font-weight: bold; font-size: 11px; }}'
    )

    if not rows:
        tbl.setRowCount(1)
        item = QtWidgets.QTableWidgetItem('Lớp này chưa có buổi học nào được lập lịch')
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(QColor(text_light))
        tbl.setItem(0, 0, item)
        tbl.setSpan(0, 0, 1, 7)
        tbl.setRowHeight(0, 60)
    else:
        tbl.setRowCount(len(rows))
        days_vn_short = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
        # Map khop voi DB CHECK schema.sql: 'scheduled'/'completed'/'cancelled'/'postponed'
        st_vn = {'scheduled': 'Đã lên lịch', 'completed': 'Đã diễn ra',
                 'cancelled': 'Đã huỷ', 'postponed': 'Đã dời lịch'}
        st_color = {'scheduled': '#1e3a8a', 'completed': '#166534',
                    'cancelled': '#991b1b', 'postponed': '#92400e'}
        for r, sc in enumerate(rows):
            tbl.setRowHeight(r, 36)
            buoi_so = sc.get('buoi_so')
            it_buoi = QtWidgets.QTableWidgetItem(str(buoi_so) if buoi_so else str(r + 1))
            it_buoi.setTextAlignment(Qt.AlignCenter)
            f = it_buoi.font(); f.setBold(True); it_buoi.setFont(f)
            tbl.setItem(r, 0, it_buoi)

            ngay_v = sc.get('ngay', '')
            ngay_d = parse_iso_date(ngay_v)
            ngay_str = ngay_d.strftime('%d/%m/%Y') if ngay_d else (str(ngay_v)[:10] or '—')
            it_ngay = QtWidgets.QTableWidgetItem(ngay_str)
            it_ngay.setTextAlignment(Qt.AlignCenter)
            # Highlight today
            if ngay_d and ngay_d == today:
                it_ngay.setForeground(QColor('#c05621'))
                f = it_ngay.font(); f.setBold(True); it_ngay.setFont(f)
            tbl.setItem(r, 1, it_ngay)

            thu_str = days_vn_short[ngay_d.weekday()] if ngay_d else '—'
            it_thu = QtWidgets.QTableWidgetItem(thu_str)
            it_thu.setTextAlignment(Qt.AlignCenter)
            tbl.setItem(r, 2, it_thu)

            gio_bd = str(sc.get('gio_bat_dau', ''))[:5]
            gio_kt = str(sc.get('gio_ket_thuc', ''))[:5]
            gio_str = f'{gio_bd}-{gio_kt}' if gio_bd and gio_kt else '—'
            it_gio = QtWidgets.QTableWidgetItem(gio_str)
            it_gio.setTextAlignment(Qt.AlignCenter)
            tbl.setItem(r, 3, it_gio)

            it_phong = QtWidgets.QTableWidgetItem(sc.get('phong', '') or '—')
            it_phong.setTextAlignment(Qt.AlignCenter)
            tbl.setItem(r, 4, it_phong)

            st_raw = sc.get('trang_thai') or 'scheduled'
            # Auto downgrade scheduled -> completed neu ngay da qua
            display_st = st_raw
            if st_raw == 'scheduled' and ngay_d and ngay_d < today:
                display_st = 'completed'
            it_st = QtWidgets.QTableWidgetItem(st_vn.get(display_st, display_st))
            it_st.setTextAlignment(Qt.AlignCenter)
            it_st.setForeground(QColor(st_color.get(display_st, text_dark)))
            f = it_st.font(); f.setBold(True); it_st.setFont(f)
            tbl.setItem(r, 5, it_st)

            nd = sc.get('noi_dung', '') or '—'
            it_nd = QtWidgets.QTableWidgetItem(nd)
            it_nd.setToolTip(nd if nd != '—' else '')
            tbl.setItem(r, 6, it_nd)

        tbl.setColumnWidth(0, 50)
        tbl.setColumnWidth(1, 95)
        tbl.setColumnWidth(2, 40)
        tbl.setColumnWidth(3, 90)
        tbl.setColumnWidth(4, 70)
        tbl.setColumnWidth(5, 100)
        tbl.horizontalHeader().setStretchLastSection(True)

    bv.addWidget(tbl, 1)
    lay.addWidget(body, 1)

    # Footer: nut "In PDF" + "Dong"
    footer = QtWidgets.QFrame()
    footer.setFixedHeight(58)
    footer.setStyleSheet(f'QFrame {{ background: #f7fafc; border-top: 1px solid {border}; }}')
    fl = QtWidgets.QHBoxLayout(footer)
    fl.setContentsMargins(20, 10, 20, 10)
    fl.setSpacing(10)

    # Nut In PDF (chi enable neu co buoi)
    btn_pdf = QtWidgets.QPushButton('🖨 In toàn bộ lịch lớp (PDF)')
    btn_pdf.setFixedHeight(36)
    btn_pdf.setMinimumWidth(220)
    btn_pdf.setCursor(Qt.PointingHandCursor)
    btn_pdf.setStyleSheet('QPushButton { background: #c05621; color: white; border: none; '
                          'border-radius: 6px; font-size: 12px; font-weight: bold; padding: 0 12px; } '
                          'QPushButton:hover { background: #9c4419; } '
                          'QPushButton:disabled { background: #cbd5e0; color: #a0aec0; }')
    btn_pdf.setEnabled(bool(rows))
    btn_pdf.clicked.connect(lambda: export_class_full_schedule_pdf(
        dlg, lop_id, ten_mon, rows, ten_gv=ten_gv,
        default_filename=f'LichLop_{lop_id}.pdf'
    ))
    fl.addWidget(btn_pdf)

    fl.addStretch()

    btn_close = QtWidgets.QPushButton('Đóng')
    btn_close.setFixedSize(110, 36)
    btn_close.setCursor(Qt.PointingHandCursor)
    btn_close.setStyleSheet(f'QPushButton {{ background: {navy}; color: white; border: none; '
                            f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                            f'QPushButton:hover {{ background: #1a3a6c; }}')
    btn_close.clicked.connect(dlg.accept)
    fl.addWidget(btn_close)
    lay.addWidget(footer)

    dlg.exec_()


def toggle_max_window(win):
    """Toggle phong to / thu nho cua so"""
    if win.isMaximized():
        win.showNormal()
    else:
        win.showMaximized()


def add_maximize_button(sidebar, win):
    """Them nut phong to/thu nho o goc tren ben phai cua sidebar."""
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


def add_reload_button(sidebar, win):
    """Them nut Reload (🔄) trang hien tai - dat ben trai maximize button.

    Yeu cau win co attrs: stack, pages_filled, _on_nav.
    """
    btn = QtWidgets.QPushButton('🔄', sidebar)
    btn.setGeometry(167, 20, 24, 24)  # 195 - 28 = 167 (28px gap to maximize)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setToolTip('Tải lại trang hiện tại  (F5)')
    btn.setStyleSheet(
        'QPushButton { background: transparent; border: none; '
        'font-size: 13px; color: #4a5568; } '
        'QPushButton:hover { background: #edf2f7; border-radius: 4px; color: #002060; }'
    )

    def _do_reload():
        if not (hasattr(win, 'stack') and hasattr(win, 'pages_filled')):
            return
        idx = win.stack.currentIndex()
        if 0 <= idx < len(win.pages_filled):
            win.pages_filled[idx] = False
            if hasattr(win, '_on_nav'):
                win._on_nav(idx)

    btn.clicked.connect(_do_reload)
    return btn


def add_sidebar_context_widget(sidebar, show_semester=True):
    """Hop 'Hom nay + Dot' o duoi sidebar - dat truoc sep2 (y=610).

    Hien:
        Hom nay
        Thu X · dd/MM/yyyy
        ──────────────
        Đợt: HK2 · 2025-2026   (neu show_semester va co data)
    """
    from datetime import date as _date
    today = _date.today()
    thu_vn = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm',
               'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật'][today.weekday()]
    date_str = today.strftime('%d/%m/%Y')

    # Lay current semester (best-effort, khong block UI)
    sem_text = ''
    if show_semester:
        try:
            if 'SemesterService' in globals() and SemesterService and DB_AVAILABLE:
                cur = SemesterService.get_current()
                if cur:
                    nm = cur.get('ten') or cur.get('id', '')
                    nh = cur.get('nam_hoc', '')
                    sem_text = f'{nm} · {nh}' if nh else nm
        except Exception:
            sem_text = ''

    # Frame chua + chieu cao linh hoat tuy theo co semester hay khong
    h = 70 if sem_text else 48
    y = 610 - h - 8  # cach sep2 8px
    frame = QtWidgets.QFrame(sidebar)
    frame.setObjectName('sidebarContextBox')
    frame.setGeometry(15, y, 200, h)
    frame.setStyleSheet(
        'QFrame#sidebarContextBox { background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 6px; }'
    )

    cap = QtWidgets.QLabel('📅 Hôm nay', frame)
    cap.setGeometry(10, 6, 180, 14)
    cap.setStyleSheet('color: #718096; font-size: 9px; font-weight: bold; '
                      'background: transparent; border: none; letter-spacing: 0.5px;')

    val = QtWidgets.QLabel(f'{thu_vn} · {date_str}', frame)
    val.setGeometry(10, 22, 180, 18)
    val.setStyleSheet('color: #002060; font-size: 11px; font-weight: bold; '
                      'background: transparent; border: none;')

    if sem_text:
        # Mini sep
        mini = QtWidgets.QFrame(frame)
        mini.setGeometry(10, 42, 180, 1)
        mini.setStyleSheet('background: #e2e8f0; border: none;')

        cap2 = QtWidgets.QLabel('🎓 Đợt hiện tại', frame)
        cap2.setGeometry(10, 46, 180, 14)
        cap2.setStyleSheet('color: #718096; font-size: 9px; font-weight: bold; '
                           'background: transparent; border: none; letter-spacing: 0.5px;')

        val2 = QtWidgets.QLabel(sem_text, frame)
        val2.setGeometry(10, 56, 180, 12)
        val2.setStyleSheet('color: #c05621; font-size: 10px; font-weight: bold; '
                           'background: transparent; border: none;')

    frame.setToolTip(f'Hôm nay: {thu_vn}, {date_str}'
                     + (f'\nĐợt: {sem_text}' if sem_text else ''))
    return frame


def widen_search(page, txt_name, new_width, shift_after=None):
    """noi rong o tim kiem + bat clear button (X) + day widget ben phai neu can"""
    txt = page.findChild(QtWidgets.QLineEdit, txt_name)
    if not txt:
        return
    # Clear button (X) hien khi co text - native Qt feature, khong them dependency
    txt.setClearButtonEnabled(True)
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


_LAST_LOGIN_FILE = os.path.join(os.path.expanduser('~'), '.eaut_last_user')


def load_last_username() -> str:
    """Load username dang nhap lan cuoi (khong luu password)."""
    try:
        if os.path.exists(_LAST_LOGIN_FILE):
            with open(_LAST_LOGIN_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()[:50]  # cap dai an toan
    except Exception:
        pass
    return ''


def save_last_username(username: str):
    """Luu username de tu dien lan dang nhap sau."""
    try:
        with open(_LAST_LOGIN_FILE, 'w', encoding='utf-8') as f:
            f.write(username[:50])
    except Exception:
        pass


def clear_session_state():
    """Clean global state khi logout. Tranh leak data sang user moi login.

    KHONG xoa toan bo dict (dict.clear()) vi se mat structure default keys
    -> KeyError khi access. Thay vao do reset ve template default.
    """
    global MOCK_USER, MOCK_TEACHER, MOCK_EMPLOYEE, MOCK_ADMIN
    # Reset ve template default thay vi clear() (giu structure, tranh KeyError)
    MOCK_USER.clear(); MOCK_USER.update(CURRENT_USER)
    MOCK_TEACHER.clear(); MOCK_TEACHER.update(CURRENT_TEACHER)
    MOCK_EMPLOYEE.clear(); MOCK_EMPLOYEE.update(CURRENT_EMPLOYEE)
    MOCK_ADMIN.clear(); MOCK_ADMIN.update(CURRENT_ADMIN)


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


def verify_old_password(username: str, old_password: str) -> bool:
    """Xac thuc mat khau cu bang cach goi lai AuthService.login.

    Truoc kia 4 dialog doi mat khau (HV/Adm/GV/NV) compare voi MOCK_*['password']
    nhung field nay khong bao gio duoc set tu API login -> luon empty -> check
    luon fail "Sai mat khau cu" du nguoi dung nhap dung. Bug nay khien feature
    doi mat khau khong dung duoc trong online mode.

    Fix: re-login voi (username, old_password). Login OK = mat khau cu dung,
    khong phai luu plain text trong dict.
    """
    if not (DB_AVAILABLE and AuthService and username and old_password):
        return False
    try:
        # Lowercase username dong bo voi on_login (DB WHERE username=%s case-sensitive)
        return AuthService.login(username.strip().lower(), old_password) is not None
    except Exception:
        return False


def show_change_password_dialog(parent, mock_dict, user_id_resolver):
    """Dialog doi mat khau dung chung cho ca 4 role (HV/Adm/GV/NV).

    Truoc duplicate ~30 dong x 4 cho - 95% giong nhau, chi khac:
    - mock_dict: MOCK_USER vs MOCK_TEACHER vs MOCK_ADMIN vs MOCK_EMPLOYEE
    - user_id_resolver: callable tra ve user_id thuc (id/user_id/current_user.id)

    Args:
        parent: window parent
        mock_dict: dict cua role hien tai - dung lookup username
        user_id_resolver: callable () -> int|None
    """
    dlg = QtWidgets.QDialog(parent)
    style_dialog(dlg)
    dlg.setWindowTitle('Đổi mật khẩu')
    dlg.setFixedSize(420, 260)
    form = QtWidgets.QFormLayout(dlg)
    old = QtWidgets.QLineEdit(); old.setEchoMode(QtWidgets.QLineEdit.Password)
    new1 = QtWidgets.QLineEdit(); new1.setEchoMode(QtWidgets.QLineEdit.Password)
    new2 = QtWidgets.QLineEdit(); new2.setEchoMode(QtWidgets.QLineEdit.Password)
    form.addRow('Mật khẩu cũ:', old)
    form.addRow('Mật khẩu mới:', new1)
    strength_lbl = attach_password_strength_indicator(new1)
    form.addRow('', strength_lbl)
    form.addRow('Nhập lại:', new2)
    btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    btns.accepted.connect(dlg.accept)
    btns.rejected.connect(dlg.reject)
    form.addRow(btns)
    if dlg.exec_() != QtWidgets.QDialog.Accepted:
        return
    # Step 1: ban old phai duoc nhap (truoc neu de trong -> verify_old_password
    # se goi API voi password rong gay loi 422 thay vi msg ro)
    if not old.text():
        msg_warn(parent, 'Lỗi', 'Vui lòng nhập mật khẩu cũ')
        return
    if not verify_old_password(mock_dict.get('username', ''), old.text()):
        msg_warn(parent, 'Lỗi', 'Sai mật khẩu cũ')
        return
    # Step 2: ban moi phai duoc nhap (truoc 'không khớp' bi nham vi
    # 2 chuoi rong = bang nhau, nguoi dung khong hieu vi sao bi loi)
    if not new1.text():
        msg_warn(parent, 'Lỗi', 'Vui lòng nhập mật khẩu mới')
        return
    if new1.text() != new2.text():
        msg_warn(parent, 'Lỗi', 'Mật khẩu mới và xác nhận không khớp')
        return
    # Step 3: khong cho doi sang chinh mat khau cu (vo nghia + dau hieu user nham)
    if new1.text() == old.text():
        msg_warn(parent, 'Lỗi', 'Mật khẩu mới phải khác mật khẩu cũ')
        return
    err = validate_password(new1.text())
    if err:
        msg_warn(parent, 'Mật khẩu yếu', err)
        return
    user_id = user_id_resolver()
    if not (DB_AVAILABLE and user_id):
        msg_warn(parent, 'Lỗi', 'Chưa kết nối được hệ thống.')
        return
    try:
        AuthService.change_password(user_id, new1.text())
    except Exception as e:
        print(f'[AUTH] doi mk loi: {e}')
        msg_warn(parent, 'Không đổi được', api_error_msg(e))
        return
    msg_info(parent, 'Thành công', 'Đổi mật khẩu thành công.')


def is_valid_email(email):
    """Email format check (don gian, du dung cho HV/GV/NV)."""
    if not email: return True  # empty = OK (optional field)
    import re
    return bool(re.match(r'^[\w.+-]+@[\w-]+(\.[\w-]+)+$', email))


def is_valid_phone_vn(phone):
    """SDT VN: 10 chu so bat dau '0', hoac +84... (11 chu so).

    Chap nhan space/dash/dot trong format (vd '0901 234 567').
    Reject so khong bat dau 0 hoac +84 (vd '1234567890').
    """
    if not phone: return True  # empty = OK (optional field)
    import re
    digits = re.sub(r'\D', '', phone)
    # +84 prefix: '+8490...' -> 11 digits, dau '8'
    if digits.startswith('84') and len(digits) == 11:
        return True
    # Local '0...': 10 digits, dau '0'
    if digits.startswith('0') and len(digits) == 10:
        return True
    return False


def api_error_msg(e):
    """Parse exception tu API call -> message tieng Viet ro rang.

    Backend tra ve 409 + JSON {detail: 'msg'} cho FK violation,
    400 cho check violation, 422 cho Pydantic validation, etc.
    Network/timeout errors duoc format ro rang cho user.
    """
    try:
        import requests
        # 1. HTTP error voi response: lay {detail} tu JSON body
        if isinstance(e, requests.HTTPError) and e.response is not None:
            try:
                body = e.response.json()
                detail = body.get('detail') if isinstance(body, dict) else None
                if detail:
                    # Pydantic 422: detail la list of {loc, msg, type, ...}
                    if isinstance(detail, list) and detail:
                        msgs = []
                        for d in detail[:3]:  # toi da 3 loi de tranh ngap
                            if isinstance(d, dict):
                                m = d.get('msg', '')
                                loc = d.get('loc', [])
                                field = loc[-1] if loc else ''
                                msgs.append(f'{field}: {m}' if field else m)
                            else:
                                msgs.append(str(d))
                        return 'Dữ liệu sai:\n  - ' + '\n  - '.join(msgs)
                    return str(detail)
            except Exception:
                pass
            sc = e.response.status_code
            # Status code -> message tieng Viet
            sc_map = {
                400: 'Dữ liệu không hợp lệ',
                401: 'Sai tài khoản hoặc mật khẩu',
                403: 'Không có quyền thực hiện',
                404: 'Không tìm thấy dữ liệu',
                409: 'Xung đột dữ liệu (trùng/ràng buộc)',
                422: 'Dữ liệu sai định dạng',
                500: 'Lỗi máy chủ - hãy báo admin',
                502: 'Máy chủ không phản hồi',
                503: 'Dịch vụ tạm dừng',
            }
            return f'{sc_map.get(sc, "Lỗi HTTP")} (mã {sc})'

        # 2. Connection error: backend chua chay / network down
        if isinstance(e, requests.ConnectionError):
            return ('Không kết nối được máy chủ.\n'
                    'Kiểm tra: backend đã chạy chưa? (uvicorn port 8000)')

        # 3. Timeout: request qua lau (mac dinh 10s)
        if isinstance(e, requests.Timeout):
            return ('Máy chủ phản hồi quá chậm (>10 giây).\n'
                    'Hãy thử lại hoặc kiểm tra mạng.')

        # 4. Cac exception khac cua requests
        if isinstance(e, requests.RequestException):
            return f'Lỗi kết nối: {str(e)[:150]}'
    except Exception:
        pass
    return str(e) or 'Lỗi không xác định'


def make_action_cell(buttons, spacing=6):
    """Tao 1 cell widget chua 2 nut thao tac (Sua/Xoa/Chi tiet/Duyet/...).

    Args:
        buttons: list of (text, color_key) - color_key la key trong COLORS
                 (vd 'navy', 'red', 'green', 'orange', 'gold')
                 Hoac (text, color_key, hover) neu muon hover effect
        spacing: khoang cach giua cac nut (px). Default 6px.

    Returns:
        (widget, [QPushButton]) - caller phai connect button.clicked

    Pattern dong bo voi _fill_admin_courses (mau chuan):
    - Button: 50x24 (60x24 cho text >4 chars), font 11px bold, white
    - Container: QHBoxLayout no margin, spacing 6, center align
    - Row height ben goi nen set 44, column width 150
    """
    # Tooltip mac dinh dua tren text nut - tieng Viet day du de chi user (button text rat ngan)
    _ACTION_TOOLTIPS = {
        'Sửa': 'Chỉnh sửa thông tin',
        'Xóa': 'Xóa khỏi hệ thống',
        'Xem': 'Xem chi tiết',
        'Chi tiết': 'Xem chi tiết',
        'Đánh giá': 'Mở dialog đánh giá',
        'Hủy': 'Huỷ đăng ký',
        'Mở ĐK': 'Mở đợt đăng ký',
        'Đóng ĐK': 'Đóng đợt đăng ký',
        'Nhập điểm': 'Nhập điểm cho học viên',
        'Duyệt': 'Duyệt đăng ký',
    }
    w = QtWidgets.QWidget()
    hl = QtWidgets.QHBoxLayout(w)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(spacing)
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
        # Tooltip chi tiet hon text nut (ngan)
        tip = _ACTION_TOOLTIPS.get(text)
        if tip:
            b.setToolTip(tip)
        # Size theo do dai text - height 28 de chu co dau tieng Viet (Sua/Xoa) khong bi crop
        # Width tang ra 5-10px so voi truoc de chua dau tieng Viet day du
        # ('Sửa điểm'/'Chấm bài' moi truoc bi truncate o 70px)
        n = len(text)
        if n >= 8:
            width = 85
        elif n >= 7:
            width = 78
        elif n >= 4:
            width = 65
        else:
            width = 55
        b.setFixedSize(width, 28)
        bg = COLORS.get(color_key, COLORS['navy'])
        hover_css = ''
        if with_hover:
            hover_key = f'{color_key}_hover'
            hover_bg = COLORS.get(hover_key, bg)
            hover_css = f' QPushButton:hover {{ background: {hover_bg}; }}'
        b.setStyleSheet(
            f'QPushButton {{ background: {bg}; color: white; border: none; '
            f'border-radius: 4px; font-size: 11px; font-weight: bold; '
            f'padding: 0px; }}{hover_css}'
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
    'username': '', 'role': 'Học viên',
    'name': '', 'msv': '', 'lop': '',
    'khoa': '', 'ngaysinh': '', 'gioitinh': '',
    'nienkhoa': '', 'hedt': '',
    'email': '', 'sdt': '',
    'diachi': '', 'initials': '?',
}

CURRENT_ADMIN = {
    'username': '',
    'name': '', 'role': 'Quản trị viên', 'initials': 'AD',
}

CURRENT_TEACHER = {
    'username': '', 'role': 'Giảng viên',
    'id': '', 'name': '', 'initials': '?',
    'khoa': '', 'hocvi': '',
    'email': '', 'sdt': '',
}

CURRENT_EMPLOYEE = {
    'username': '', 'role': 'Nhân viên',
    'id': '', 'name': '', 'initials': '?',
    'chucvu': '',
    'email': '', 'sdt': '',
}

# Backward-compat aliases - de tranh break code cu chua sua het
# CHU Y: dict() copy de tranh CURRENT_* va MOCK_* cung ref -> clear() bi mat template
MOCK_USER = dict(CURRENT_USER)
MOCK_ADMIN = dict(CURRENT_ADMIN)
MOCK_TEACHER = dict(CURRENT_TEACHER)
MOCK_EMPLOYEE = dict(CURRENT_EMPLOYEE)

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


# Cache mapping {semester_id: 'open'/'closed'/'upcoming'} - dung filter classes theo dot active
MOCK_SEM_STATUS = {}


def _load_sem_status():
    """Load mapping semester_id -> trang_thai vao MOCK_SEM_STATUS."""
    global MOCK_SEM_STATUS
    try:
        sems = SemesterService.get_all() or []
        MOCK_SEM_STATUS = {s.get('id', ''): s.get('trang_thai', 'closed') for s in sems}
    except Exception as e:
        print(f'[CACHE] Load semesters loi: {e}')
        MOCK_SEM_STATUS = {}
    return MOCK_SEM_STATUS


def _load_classes_cache():
    """Load classes tu API. Cache vao MOCK_CLASSES.
    Format: list of (ma_lop, ma_mon, ten_mon, ten_gv, lich, phong, smax, scur, gia, sem_id)."""
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
            r.get('semester_id', '') or '',  # idx 9: dung filter theo dot
        ) for r in rows]
    except Exception as e:
        print(f'[CACHE] Load classes loi: {e}')
        MOCK_CLASSES = []
    return MOCK_CLASSES


def is_class_active(cls_tuple) -> bool:
    """Check 1 lop co thuoc dot dang OPEN khong (cls_tuple co sem_id o idx 9)."""
    if len(cls_tuple) < 10:
        return True  # backward compat: tuple cu khong co sem -> coi nhu active
    sem_id = cls_tuple[9]
    if not sem_id:
        return False  # khong co dot -> khong active
    return MOCK_SEM_STATUS.get(sem_id, 'closed') == 'open'


def _refresh_cache():
    """Force refresh cache - goi sau khi admin them/sua/xoa."""
    global MOCK_COURSES, MOCK_CLASSES
    MOCK_COURSES = []
    MOCK_CLASSES = []
    _load_courses_cache()
    _load_classes_cache()
    _load_sem_status()  # Refresh sem status cung de NV thay ngay khi admin toggle dot


# STUDENT pages - ui_file=None nghia la build pure Python (cho Bai tap)
PAGES = [
    ('btnHome', 'dashboard_student.ui'),
    ('btnSchedule', 'schedule.ui'),
    ('btnExam', 'exam_schedule.ui'),
    ('btnGrades', 'grades.ui'),
    ('btnAssign', None),  # Bai tap - build Python
    ('btnReview', 'teacher_review.ui'),
    ('btnNotice', 'notifications.ui'),
    ('btnProfile', 'profile.ui'),
]

MENU_ITEMS = [
    ('btnHome', 'iconHome', 'home', 'Trang chủ'),
    ('btnSchedule', 'iconSchedule', 'calendar', 'Lịch học'),
    ('btnExam', 'iconExam', 'clipboard', 'Lịch kiểm tra'),
    ('btnGrades', 'iconGrades', 'bar-chart', 'Xem điểm'),
    ('btnAssign', 'iconAssign', 'file-text', 'Bài tập'),
    ('btnReview', 'iconReview', 'star', 'Đánh giá giảng viên'),
    ('btnNotice', 'iconNotice', 'bell', 'Thông báo'),
    ('btnProfile', 'iconProfile', 'user', 'Thông tin cá nhân'),
]

# TEACHER pages - ui_file=None nghia la build pure Python (khong load .ui)
TEACHER_PAGES = [
    ('btnTeaDash', 'teacher_dashboard.ui'),
    ('btnTeaSchedule', 'schedule.ui'),
    ('btnTeaClasses', 'teacher_classes.ui'),
    ('btnTeaStudents', 'teacher_students.ui'),
    ('btnTeaAttend', 'teacher_attendance.ui'),
    ('btnTeaNotice', 'teacher_notice.ui'),
    ('btnTeaGrades', 'teacher_grades.ui'),
    ('btnTeaAssign', None),  # Bai tap - build pure Python
    ('btnTeaExam', None),    # Lich thi - build pure Python
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
    ('btnTeaAssign', 'iconTeaAssign', 'file-text', 'Giao bài tập'),
    ('btnTeaExam', 'iconTeaExam', 'clipboard', 'Lịch thi'),
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
    ('btnAdminSchedule', None),  # Quan ly lich hoc - build pure Python
    ('btnAdminAudit', 'admin_audit.ui'),
    ('btnAdminStats', 'admin_stats.ui'),
]

ADMIN_MENU = [
    ('btnAdminDash', 'iconAdminDash', 'grid', 'Tổng quan'),
    ('btnAdminCourse', 'iconAdminCourse', 'database', 'Quản lý khóa học'),
    ('btnAdminClasses', 'iconAdminClasses', 'layers', 'Quản lý lớp'),
    ('btnAdminStudent', 'iconAdminStudent', 'users', 'Quản lý học viên'),
    ('btnAdminTeacher', 'iconAdminTeacher', 'user-check', 'Quản lý giảng viên'),
    ('btnAdminEmployee', 'iconAdminEmployee', 'briefcase', 'Quản lý nhân viên'),
    ('btnAdminSemester', 'iconAdminSemester', 'sliders', 'Quản lý đợt'),
    ('btnAdminCurriculum', 'iconAdminCurriculum', 'file-text', 'Lộ trình học'),
    ('btnAdminSchedule', 'iconAdminSchedule', 'calendar', 'Quản lý lịch học'),
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

        # Load badge thong bao chua doc luc init
        self._update_notif_badge()

        # F5/Ctrl+R: refresh trang hien tai
        install_refresh_shortcut(self)

    def _update_notif_badge(self):
        """Update tat ca badges sidebar HV: notif + exam (≤7 ngay) + bai tap chua nop."""
        from datetime import date as _date, datetime as _dt
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')

        # Notif badge - tru di so notif HV da dismiss (an UI-only)
        n_notif = 0
        if DB_AVAILABLE and hv_id:
            try:
                notifs = NotificationService.get_for_student(hv_id) or []
                dismissed = getattr(self, '_stu_notif_dismissed', set())
                n_notif = sum(1 for n in notifs if n.get('id') not in dismissed)
            except Exception:
                pass
        set_sidebar_badge(getattr(self, 'lblNotifBadge', None), n_notif)

        # Exam badge - count ≤7 days
        n_exam_soon = 0
        if DB_AVAILABLE and hv_id and ExamService:
            try:
                today = _date.today()
                exams = ExamService.get_for_student(hv_id) or []
                for e in exams:
                    ngay_d = parse_iso_date(e.get('ngay_thi') or e.get('ngay', ''))
                    if ngay_d is None:
                        continue
                    dl = (ngay_d - today).days
                    if 0 <= dl <= 7:
                        n_exam_soon += 1
            except Exception as e:
                print(f'[STU_BADGE] exam loi: {e}')
        set_sidebar_badge(getattr(self, 'lblExamBadge', None), n_exam_soon)

        # Assignment badge - chưa nộp + chưa quá hạn (pending + due_soon)
        n_asg = 0
        if DB_AVAILABLE and hv_id and AssignmentService:
            try:
                now = _dt.now()
                rows = AssignmentService.get_pending(hv_id) or []
                for r in rows:
                    if r.get('submission_id') is not None or r.get('diem') is not None:
                        continue
                    han = r.get('han_nop')
                    if han:
                        han_dt = parse_iso_datetime(han)
                        if han_dt and han_dt < now:
                            continue  # qua han khong tinh
                    n_asg += 1
            except Exception as e:
                print(f'[STU_BADGE] asg loi: {e}')
        set_sidebar_badge(getattr(self, 'lblAssignBadge', None), n_asg)

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
        add_reload_button(sidebar, self)

        # duong ke
        sep = QtWidgets.QFrame(sidebar)
        sep.setGeometry(15, 74, 200, 1)
        sep.setStyleSheet(f'background: {COLORS["border"]};')

        # menu buttons
        y = 86
        for i, (btn_name, icon_name, icon_file, label) in enumerate(MENU_ITEMS):
            btn = QtWidgets.QPushButton(label, sidebar)
            btn.setObjectName(btn_name)
            btn.setGeometry(10, y, 210, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(SIDEBAR_NORMAL)
            # Tooltip kèm phím tat Ctrl+N (i+1) cho 9 tab dau
            if i < 9:
                btn.setToolTip(f'{label}  ·  Ctrl+{i + 1}')
            else:
                btn.setToolTip(label)
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

        # Hop "Hom nay + Dot" - context-aware UX
        add_sidebar_context_widget(sidebar)

        # duong ke duoi
        sep2 = QtWidgets.QFrame(sidebar)
        sep2.setGeometry(15, 610, 200, 1)
        sep2.setStyleSheet(f'background: {COLORS["border"]};')

        # user info
        self.lblAvatar = QtWidgets.QLabel(MOCK_USER['initials'], sidebar)
        self.lblAvatar.setGeometry(15, 625, 38, 38)
        self.lblAvatar.setAlignment(Qt.AlignCenter)
        self.lblAvatar.setStyleSheet(avatar_style(MOCK_USER['initials']))

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

        # Badge thong bao chua doc - nam o goc tren phai btnNotice
        # btnNotice index = 5 trong PAGES (Home, Schedule, Exam, Grades, Review, Notice, Profile)
        notice_idx = next((i for i, (n, _) in enumerate(PAGES) if n == 'btnNotice'), 5)
        notice_y = 86 + notice_idx * 38
        self.lblNotifBadge = QtWidgets.QLabel('', sidebar)
        self.lblNotifBadge.setGeometry(192, notice_y + 4, 22, 18)
        self.lblNotifBadge.setAlignment(Qt.AlignCenter)
        self.lblNotifBadge.setStyleSheet(
            'QLabel { background: #c53030; color: white; border-radius: 9px; '
            'font-size: 10px; font-weight: bold; padding: 0px 4px; }'
        )
        self.lblNotifBadge.hide()

        # Badge "Lich thi sap toi" - nam o goc btnExam (idx 2)
        exam_idx = next((i for i, (n, _) in enumerate(PAGES) if n == 'btnExam'), 2)
        exam_y = 86 + exam_idx * 38
        self.lblExamBadge = QtWidgets.QLabel('', sidebar)
        self.lblExamBadge.setGeometry(192, exam_y + 4, 22, 18)
        self.lblExamBadge.setAlignment(Qt.AlignCenter)
        self.lblExamBadge.setStyleSheet(
            'QLabel { background: #c05621; color: white; border-radius: 9px; '
            'font-size: 10px; font-weight: bold; padding: 0px 4px; }'
        )
        self.lblExamBadge.hide()

        # Badge "Bai tap chua nop" - nam o goc btnAssign (idx 4)
        asg_idx = next((i for i, (n, _) in enumerate(PAGES) if n == 'btnAssign'), 4)
        asg_y = 86 + asg_idx * 38
        self.lblAssignBadge = QtWidgets.QLabel('', sidebar)
        self.lblAssignBadge.setGeometry(192, asg_y + 4, 22, 18)
        self.lblAssignBadge.setAlignment(Qt.AlignCenter)
        self.lblAssignBadge.setStyleSheet(
            'QLabel { background: #d97706; color: white; border-radius: 9px; '
            'font-size: 10px; font-weight: bold; padding: 0px 4px; }'
        )
        self.lblAssignBadge.hide()

        return sidebar

    def _load_page(self, ui_file):
        """load .ui, tach contentArea ra. ui_file=None -> tao QFrame trong (cho Bai tap)"""
        if ui_file is None:
            content = QtWidgets.QFrame()
            content.setObjectName('contentArea')
            content.setFixedSize(870, 700)
            content.setStyleSheet('QFrame#contentArea { background: #edf2f7; }')
            return content
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
            fill_methods = [
                self._fill_dashboard, self._fill_schedule, self._fill_exam,
                self._fill_grades, self._fill_assignments, self._fill_review,
                self._fill_notifications, self._fill_profile,
            ]
            if fill_methods[index]:
                fill_methods[index]()
            self.pages_filled[index] = True
        # Khi vao trang Notifications -> coi nhu da doc, an badge
        if PAGES[index][0] == 'btnNotice' and hasattr(self, 'lblNotifBadge'):
            self.lblNotifBadge.hide()

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
        if not msg_confirm(self, 'Đăng xuất', 'Bạn có chắc muốn đăng xuất?'):
            return
        clear_session_state()
        self.close()
        self.app_ref.show_login()

    # === DATA FILL ===

    def _fill_dashboard(self):
        page = self.page_widgets[0]

        # Header semester label - lay tu DB (semester active) thay vi hardcode HK
        lbl_sem = page.findChild(QtWidgets.QLabel, 'lblSemester')
        if lbl_sem and DB_AVAILABLE:
            try:
                cur_sem = SemesterService.get_current() if SemesterService else None
                if cur_sem:
                    nm = cur_sem.get('ten') or cur_sem.get('id', '')
                    nh = cur_sem.get('nam_hoc', '')
                    lbl_sem.setText(f'{nm} - Năm {nh}' if nh else nm)
                else:
                    # Khong co dot nao open -> bao user biet
                    lbl_sem.setText('⚠ Hiện chưa có đợt đăng ký nào đang mở')
                    lbl_sem.setStyleSheet('color: #c05621; font-weight: bold;')
            except Exception:
                lbl_sem.setText('Khóa học ngoại khoá EAUT')

        # stat icons - 24x24 (tang tu 20 cho de nhin hon)
        for attr, icon_file in [('iconStat1Img', 'layers'), ('iconStat2Img', 'check-circle'), ('iconStat3Img', 'clock')]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setPixmap(QPixmap(os.path.join(ICONS, f'{icon_file}.png')).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))

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
            w.setText(f"{time_greeting()}, {MOCK_USER['name']}")

        # Bang khoa hoc cua HV - lay tu API thuc
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        data = []
        n_paid = 0          # so lop da thanh toan
        total_buoi = 0      # tong so buoi cua tat ca lop da TT
        attended = 0        # so buoi da diem danh (present|late)
        # Counter cho payment alert banner
        n_pending_pay = 0
        total_pending_fee = 0
        if DB_AVAILABLE and hv_id:
            try:
                rows = CourseService.get_classes_by_student(hv_id) or []
                for r in rows:
                    st = r.get('reg_status', r.get('trang_thai', 'paid'))
                    st_vn = {'paid': 'Đã thanh toán', 'pending_payment': 'Chờ thanh toán',
                             'completed': 'Hoàn thành', 'cancelled': 'Đã hủy'}.get(st, st)
                    so_buoi_lop = int(r.get('so_buoi') or 0)
                    if st in ('paid', 'completed'):
                        n_paid += 1
                        total_buoi += so_buoi_lop
                        # diem danh thuc te qua API attendance
                        try:
                            summary = AttendanceService.attendance_rate(hv_id, r.get('ma_lop', '')) or 0.0
                            # rate * so_buoi / 100 = so buoi attended (uoc luong)
                            attended += round(summary * so_buoi_lop / 100)
                        except Exception:
                            pass
                    elif st == 'pending_payment':
                        n_pending_pay += 1
                        try:
                            total_pending_fee += int(r.get('gia') or 0)
                        except (TypeError, ValueError):
                            pass
                    data.append([
                        r.get('ma_lop', ''), r.get('ten_mon', ''),
                        str(so_buoi_lop) if so_buoi_lop else '—',
                        r.get('ten_gv', '') or '—', r.get('lich', '') or '—', st_vn
                    ])
            except Exception as e:
                print(f'[STU_DASH] Loi load classes: {e}')
        # Cache de _render_pending_payment_banner_hv reuse
        self._stu_pending_pay = (n_pending_pay, total_pending_fee)

        remaining_buoi = max(0, total_buoi - attended)

        # Lich hoc hom nay - render banner dynamic
        self._render_today_banner_hv(page, hv_id)

        # Update stat cards: 3 / Tong buoi / Buoi con lai
        for attr, val in [('lblStatCourses', str(n_paid)),
                           ('lblStatCredits', str(total_buoi)),
                           ('lblStatRemaining', str(remaining_buoi))]:
            wlbl = page.findChild(QtWidgets.QLabel, attr)
            if wlbl:
                wlbl.setText(val)

        # Update progress label + bar (truoc hardcode "15/25 tin chi")
        lbl_prog = page.findChild(QtWidgets.QLabel, 'lblProgressLabel')
        if lbl_prog:
            if total_buoi > 0:
                lbl_prog.setText(f'Đã học {attended} / {total_buoi} buổi')
            else:
                lbl_prog.setText('Chưa đăng ký lớp nào')
        bar = page.findChild(QtWidgets.QProgressBar, 'progressCredits')
        if bar:
            pct = int(attended / total_buoi * 100) if total_buoi > 0 else 0
            bar.setValue(min(100, pct))

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCourses')
        if tbl:
            if not data:
                set_table_empty_state(
                    tbl, 'Chưa có khóa học nào đăng ký',
                    icon='📚',
                    cta_text='💡 Liên hệ Nhân viên để đăng ký',
                    cta_callback=lambda: msg_info(self, 'Đăng ký khóa học',
                        'Để đăng ký khóa học mới, vui lòng:\n\n'
                        '☎ Liên hệ Nhân viên Trung tâm\n'
                        '📍 Trực tiếp tại Văn phòng EAUT\n'
                        '📧 Email: admin@eaut.edu.vn\n\n'
                        'Nhân viên sẽ thực hiện đăng ký giúp bạn.'))
            else:
                tbl.setRowCount(len(data))
                for r, row in enumerate(data):
                    for c, val in enumerate(row):
                        item = QtWidgets.QTableWidgetItem(val)
                        # Cot 5 (trang thai): style item voi mau + bold (truc tiep, khong dung widget)
                        if c == 5 and val:
                            style_status_item(item, val)
                        tbl.setItem(r, c, item)
                    # Tooltip cot Ma KH va Ten khoa hoc -> nhac user double-click
                    if tbl.item(r, 0):
                        tbl.item(r, 0).setToolTip('Double-click để xem toàn bộ lịch của lớp này')
                    if tbl.item(r, 1):
                        tbl.item(r, 1).setToolTip('Double-click để xem toàn bộ lịch của lớp này')
                # Wire double-click row -> show full schedule (1 lan)
                if not getattr(self, '_stu_courses_dblclick_wired', False):
                    tbl.cellDoubleClicked.connect(self._stu_on_course_dblclick)
                    self._stu_courses_dblclick_wired = True
            # Stretch col 1 (Ten khoa hoc) - cot dai nhat - cho cac cot khac giu width
            tbl.setColumnWidth(0, 70)    # Ma KH
            tbl.setColumnWidth(1, 180)   # Ten khoa hoc (se stretch) - shrink cho cot trang thai
            tbl.setColumnWidth(2, 70)    # So buoi
            tbl.setColumnWidth(3, 130)   # Giang vien
            tbl.setColumnWidth(4, 110)   # Lich hoc
            tbl.setColumnWidth(5, 230)   # Trang thai badge "Đã thanh toán" can rong
            tbl.horizontalHeader().setStretchLastSection(False)
            tbl.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
            tbl.verticalHeader().setVisible(False)

        # === 3 stat cards clickable -> jump to detail page (1 lan) ===
        # card1=Lop dang ky -> idx 3 (Xem diem) - thay diem cac lop
        # card2=Tong buoi -> idx 1 (Lich hoc) - thay tat ca buoi
        # card3=Buoi con lai -> idx 1 (Lich hoc) - thay buoi sap toi
        if not getattr(self, '_stu_stat_cards_wired', False):
            stat_to_idx = {
                'card1': (3, 'Đi đến trang Xem điểm'),
                'card2': (1, 'Đi đến trang Lịch học'),
                'card3': (1, 'Đi đến trang Lịch học (xem buổi sắp tới)'),
            }
            base_style = ('QFrame#{name} {{ background: white; border: 1px solid #d2d6dc; border-radius: 12px; }} '
                          'QFrame#{name}:hover {{ border: 2px solid #002060; background: #f0f7ff; }}')
            for name, (idx, tip) in stat_to_idx.items():
                card = page.findChild(QtWidgets.QFrame, name)
                if not card:
                    continue
                card.setCursor(Qt.PointingHandCursor)
                card.setStyleSheet(base_style.format(name=name))
                card.setToolTip(tip)
                def _make_click(_idx):
                    def _click(ev):
                        if ev.button() == Qt.LeftButton:
                            self._on_nav(_idx)
                    return _click
                card.mousePressEvent = _make_click(idx)
            self._stu_stat_cards_wired = True

    def _stu_export_ics(self):
        """Xuat tat ca lich hoc cua HV ra file .ics."""
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        if not hv_id:
            msg_warn(self, 'Lỗi', 'Chưa có thông tin học viên')
            return
        if not (DB_AVAILABLE and ScheduleService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống')
            return
        try:
            schedules = ScheduleService.get_all_for_student(hv_id) or []
        except Exception as e:
            msg_warn(self, 'Lỗi tải', api_error_msg(e))
            return
        msv = MOCK_USER.get('msv', 'HV')
        export_schedule_ics(self, schedules,
                            default_filename=f'LichHoc_{msv}.ics',
                            calendar_name=f'Lịch học EAUT - {MOCK_USER.get("name", "")}')

    def _stu_export_schedule_week_pdf(self):
        """In lich tuan dang xem ra PDF."""
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        if not hv_id:
            msg_warn(self, 'Lỗi', 'Chưa có thông tin học viên')
            return
        monday = getattr(self, '_stu_current_monday', None)
        if monday is None:
            today = QDate.currentDate()
            monday = today.addDays(-(today.dayOfWeek() - 1))
        if not (DB_AVAILABLE and ScheduleService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống')
            return
        try:
            schedules = ScheduleService.get_for_student_week(hv_id, monday.toPyDate()) or []
        except Exception as e:
            msg_warn(self, 'Lỗi tải', api_error_msg(e))
            return
        msv = MOCK_USER.get('msv', 'HV')
        name = MOCK_USER.get('name', '') or MOCK_USER.get('full_name', '')
        fname = f'LichTuan_{msv}_{monday.toString("yyyyMMdd")}.pdf'
        export_schedule_week_pdf(self, schedules, monday,
                                  owner_role='hv', owner_name=name, owner_code=msv,
                                  default_filename=fname)

    def _stu_export_exam_pdf(self):
        """In lich thi cua HV ra PDF."""
        # Re-fetch de data luon fresh (user co the vao trang lich thi luu lau)
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        if not hv_id:
            msg_warn(self, 'Lỗi', 'Chưa có thông tin học viên')
            return
        rows = []
        if DB_AVAILABLE and ExamService:
            try:
                rows = ExamService.get_for_student(hv_id) or []
            except Exception as e:
                msg_warn(self, 'Lỗi tải', api_error_msg(e))
                return
        if not rows:
            # Fallback dung cache neu co
            rows = getattr(self, '_stu_exam_rows_cache', [])
        if not rows:
            msg_warn(self, 'Trống', 'Chưa có lịch thi nào để in.')
            return
        msv = MOCK_USER.get('msv', 'HV')
        name = MOCK_USER.get('name', '') or MOCK_USER.get('full_name', '')
        fname = f'LichThi_{msv}.pdf'
        export_exam_schedule_pdf(self, rows, owner_role='hv',
                                  owner_name=name, owner_code=msv,
                                  default_filename=fname)

    def _stu_on_course_dblclick(self, row, col):
        """HV double-click 1 row tbl tblCourses -> mo dialog xem toan bo lich cua lop."""
        page = self.page_widgets[0]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCourses')
        if not tbl:
            return
        it_ma = tbl.item(row, 0)
        it_ten = tbl.item(row, 1)
        it_gv = tbl.item(row, 3)  # cot Giang vien
        if not it_ma:
            return
        ma_lop = it_ma.text().strip()
        ten_mon = it_ten.text().strip() if it_ten else ''
        ten_gv = it_gv.text().strip() if it_gv else ''
        if ten_gv == '—':
            ten_gv = ''
        if not ma_lop:
            return
        if not (DB_AVAILABLE and ScheduleService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống')
            return
        try:
            schedules = ScheduleService.get_for_class(ma_lop) or []
        except Exception as e:
            msg_warn(self, 'Lỗi tải', api_error_msg(e))
            return
        show_class_full_schedule_dialog(self, ma_lop, ten_mon, schedules,
                                          role='hv', ten_gv=ten_gv)

    def _show_session_detail(self, sched_row, role='hv'):
        """Popup chi tiet 1 buoi hoc khi click vao card lich. role: 'hv' | 'gv'."""
        ngay_v = sched_row.get('ngay', '')
        ngay_d = parse_iso_date(ngay_v)
        if ngay_d:
            thu_vn = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm',
                      'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật'][ngay_d.weekday()]
            ngay_str = f'{thu_vn}, {ngay_d.strftime("%d/%m/%Y")}'
        else:
            ngay_str = str(ngay_v)[:10] or '—'
        gio_bd = str(sched_row.get('gio_bat_dau', ''))[:5]
        gio_kt = str(sched_row.get('gio_ket_thuc', ''))[:5]
        gio_str = f'{gio_bd} - {gio_kt}' if gio_bd and gio_kt else '—'
        phong = sched_row.get('phong', '') or '—'
        ma_lop = sched_row.get('lop_id', '?') or '?'
        ten_mon = sched_row.get('ten_mon', '') or '—'
        ten_gv = sched_row.get('ten_gv', '') or '—'
        buoi_so = sched_row.get('buoi_so')
        nd = sched_row.get('noi_dung', '') or ''
        trang_thai = sched_row.get('trang_thai') or 'scheduled'
        # Map khop DB CHECK schema.sql ('scheduled'/'completed'/'cancelled'/'postponed')
        st_vn = {'scheduled': 'Đã lên lịch', 'completed': 'Đã diễn ra',
                 'cancelled': 'Đã huỷ', 'postponed': 'Đã dời lịch'}
        st_label = st_vn.get(trang_thai, trang_thai)

        fields = [
            ('NGÀY HỌC', ngay_str),
            ('THỜI GIAN', gio_str),
            ('PHÒNG', phong),
            ('LỚP', ma_lop),
            ('KHÓA HỌC', ten_mon),
        ]
        if role == 'hv':
            fields.append(('GIẢNG VIÊN', ten_gv))
        if buoi_so:
            fields.append(('BUỔI SỐ', f'Buổi {buoi_so}'))
        if nd:
            fields.append(('NỘI DUNG BUỔI', nd))
        fields.append(('TRẠNG THÁI', st_label))

        show_detail_dialog(
            self,
            title=f'Chi tiết buổi học · {ma_lop}',
            fields=fields,
            avatar_text=ma_lop[:2],
            subtitle=ten_mon,
        )

    def _render_today_banner_hv(self, page, hv_id):
        """Render banner 'Lich hoc hom nay' giua 3 stat cards va tableFrame.
        Tu dong an neu khong co buoi nao hom nay.
        """
        from datetime import date as _date, timedelta as _td

        # Cleanup TAT CA banner cu (deleteLater khong immediate -> can find all)
        cleanup_banner(page, 'todayBanner')

        today = _date.today()
        # Monday cua tuan hien tai
        monday = today - _td(days=today.weekday())
        sched_today = []
        if DB_AVAILABLE and hv_id and ScheduleService:
            try:
                week = ScheduleService.get_for_student_week(hv_id, monday.isoformat()) or []
                today_iso = today.isoformat()
                for s in week:
                    ngay = str(s.get('ngay', ''))[:10]
                    if ngay == today_iso:
                        sched_today.append(s)
            except Exception as e:
                print(f'[STU_TODAY] loi: {e}')

        # Tao banner moi (van them ke ca khi rong - de hien text "khong co lich")
        # Shrink width 820 -> 400 de chừa chỗ cho asgBanner ben canh
        banner = QtWidgets.QFrame(page)
        banner.setObjectName('todayBanner')
        banner.setGeometry(25, 248, 400, 38)
        if sched_today:
            banner.setStyleSheet('QFrame#todayBanner { background: #f0f7ff; border: 1px solid #c0d4eb; border-left: 4px solid #002060; border-radius: 8px; }')
            banner.setCursor(Qt.PointingHandCursor)
            # Lay buoi som nhat
            sched_today.sort(key=lambda s: str(s.get('gio_bat_dau', '')))
            # Tim buoi sap toi hoac dang dien ra de countdown
            from datetime import datetime as _dt2
            now_t = _dt2.now()
            upcoming = None
            ongoing = None
            for s in sched_today:
                try:
                    bd = _dt2.combine(today, _dt2.strptime(str(s.get('gio_bat_dau', ''))[:5], '%H:%M').time())
                    kt = _dt2.combine(today, _dt2.strptime(str(s.get('gio_ket_thuc', ''))[:5], '%H:%M').time())
                except Exception:
                    continue
                if bd <= now_t <= kt:
                    ongoing = s
                    break
                if now_t < bd and upcoming is None:
                    upcoming = s
            target = ongoing or upcoming or sched_today[0]
            gio_bd = str(target.get('gio_bat_dau', ''))[:5]
            gio_kt = str(target.get('gio_ket_thuc', ''))[:5]
            ten_mon = target.get('ten_mon', '?')
            phong = target.get('phong', '') or '—'
            extra = f' (và {len(sched_today) - 1} buổi nữa)' if len(sched_today) > 1 else ''
            # Countdown ngan gon
            countdown = ''
            try:
                if ongoing:
                    kt2 = _dt2.combine(today, _dt2.strptime(gio_kt, '%H:%M').time())
                    rem = int((kt2 - now_t).total_seconds() // 60)
                    countdown = f'  ⏳ Đang diễn ra · còn {rem}p' if rem > 0 else '  ⏳ Sắp kết thúc'
                elif upcoming:
                    bd2 = _dt2.combine(today, _dt2.strptime(gio_bd, '%H:%M').time())
                    diff = int((bd2 - now_t).total_seconds() // 60)
                    if 0 < diff <= 30:
                        countdown = f'  🔔 Còn {diff}p nữa'
                    elif 30 < diff <= 180:
                        h, m = diff // 60, diff % 60
                        countdown = f'  ⏰ Còn {h}h{m:02d}'
            except Exception:
                pass
            text = f'🕐  Hôm nay: {gio_bd} - {gio_kt}  •  {ten_mon}  •  Phòng {phong}{extra}{countdown}'
            color = '#1a1a2e'
            banner.setToolTip('Click để xem chi tiết tất cả buổi học hôm nay')
            # Click banner -> popup show all sessions today
            def _click(ev, _list=sched_today):
                if ev.button() == Qt.LeftButton:
                    show_today_sessions_dialog(self, _list, role='hv')
            banner.mousePressEvent = _click
        else:
            banner.setStyleSheet('QFrame#todayBanner { background: #f7fafc; border: 1px dashed #cbd5e0; border-radius: 8px; }')
            text = '✓  Hôm nay không có lịch học'
            color = '#718096'

        lbl = QtWidgets.QLabel(text, banner)
        lbl.setGeometry(15, 0, 380, 38)
        lbl.setStyleSheet(f'color: {color}; font-size: 12px; background: transparent; border: none;')
        lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        # Forward click tu label sang banner (label co the chan event)
        if sched_today:
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.mousePressEvent = banner.mousePressEvent
        banner.show()

        # Render banner bai tap sap het han ben canh (luôn render kế bên)
        self._render_assignment_banner_hv(page, hv_id)

        # Day tableFrame xuong de chua banner row 1 (truoc payment banner co the push them)
        tf = page.findChild(QtWidgets.QFrame, 'tableFrame')
        if tf:
            g = tf.geometry()
            new_y = 296
            if g.y() != new_y:
                # Giam height tuong ung de bottom edge khong tran
                new_h = max(g.height() - (new_y - g.y()), 200)
                tf.setGeometry(g.x(), new_y, g.width(), new_h)
                # Resize tblCourses ben trong (geometry cua table tinh tu top tableFrame)
                tbl_inner = tf.findChild(QtWidgets.QTableWidget, 'tblCourses')
                if tbl_inner:
                    tg = tbl_inner.geometry()
                    tbl_inner.setGeometry(tg.x(), tg.y(), tg.width(), max(tg.height() - 38, 180))

        # Render banner thanh toan o row 2 (chi hien neu co lop pending) - sau cung de
        # khong bi today banner overwrite tableFrame y
        self._render_pending_payment_banner_hv(page)
        # Render banner thi sap toi (≤7 ngay) - tu xep o vi tri tiep theo
        self._render_exam_alert_banner_hv(page)

    def _render_assignment_banner_hv(self, page, hv_id):
        """Banner alert 'X bai tap chua nop / sap het han'.

        Dat ke ben todayBanner (x=445, y=248, w=400, h=38).
        Click -> jump to assignments page (idx 4).
        """
        from datetime import datetime as _dt

        # Cleanup banner cu
        cleanup_banner(page, 'asgBanner')

        rows = []
        if DB_AVAILABLE and hv_id and AssignmentService:
            try:
                rows = AssignmentService.get_pending(hv_id) or []
            except Exception as e:
                print(f'[STU_DASH_ASG] loi: {e}')

        # Phan loai: chua nop + chua qua han, sap het han (<=3 ngay), qua han
        now = _dt.now()
        n_pending = 0     # chưa nộp + còn hạn
        n_due_soon = 0    # chưa nộp + còn ≤3 ngày
        n_overdue = 0     # chưa nộp + đã quá hạn
        for r in rows:
            has_sub = r.get('submission_id') is not None
            graded = r.get('diem') is not None
            if has_sub or graded:
                continue
            han = r.get('han_nop')
            if not han:
                n_pending += 1
                continue
            han_dt = parse_iso_datetime(han)
            if han_dt is None:
                n_pending += 1
                continue
            if han_dt < now:
                n_overdue += 1
            else:
                delta = (han_dt - now).total_seconds() / 86400  # days
                if delta <= 3:
                    n_due_soon += 1
                else:
                    n_pending += 1

        banner = QtWidgets.QFrame(page)
        banner.setObjectName('asgBanner')
        banner.setGeometry(445, 248, 400, 38)

        # Style theo do uu tien: overdue > due_soon > pending > empty
        if n_overdue > 0:
            bg, left, fg = '#fee2e2', '#dc2626', '#991b1b'
            text = f'⚠  <b>{n_overdue}</b> bài tập <b>QUÁ HẠN</b>'
            if n_due_soon > 0:
                text += f' · {n_due_soon} sắp hết hạn'
            tip = f'{n_overdue} quá hạn, {n_due_soon} sắp hết hạn (≤3 ngày)'
        elif n_due_soon > 0:
            bg, left, fg = '#fef3c7', '#c05621', '#9a3412'
            text = f'⏰  <b>{n_due_soon}</b> bài tập sắp hết hạn (≤3 ngày)'
            tip = f'{n_due_soon} sắp hết hạn'
        elif n_pending > 0:
            bg, left, fg = '#f0f7ff', '#002060', '#1a1a2e'
            text = f'📝  <b>{n_pending}</b> bài tập đang chờ nộp'
            tip = f'{n_pending} bài tập chưa nộp'
        else:
            bg, left, fg = '#f7fafc', '#cbd5e0', '#718096'
            text = '✓  Không có bài tập chờ nộp'
            tip = ''

        banner.setStyleSheet(
            f'QFrame#asgBanner {{ background: {bg}; border: 1px solid {left}; '
            f'border-left: 4px solid {left}; border-radius: 8px; }}'
        )

        lbl = QtWidgets.QLabel(text, banner)
        lbl.setGeometry(15, 0, 380, 38)
        lbl.setStyleSheet(f'color: {fg}; font-size: 12px; background: transparent; border: none;')
        lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        lbl.setTextFormat(Qt.RichText)

        if (n_pending + n_due_soon + n_overdue) > 0:
            banner.setCursor(Qt.PointingHandCursor)
            lbl.setCursor(Qt.PointingHandCursor)
            banner.setToolTip(f'{tip} — click để vào trang Bài tập')

            def _click(ev):
                if ev.button() == Qt.LeftButton:
                    # btnAssign idx 4 trong PAGES
                    self._on_nav(4)
            banner.mousePressEvent = _click
            lbl.mousePressEvent = _click
        banner.show()

    def _render_pending_payment_banner_hv(self, page):
        """Banner alert "Co X lop cho thanh toan, tong N d".

        Dat o row 2 (y=292) full width neu co lop pending. An han neu khong co.
        Caller phai set self._stu_pending_pay = (n, total_fee) truoc khi goi.
        """
        # Cleanup banner cu
        cleanup_banner(page, 'pendingPayBanner')

        n_pending, total_fee = getattr(self, '_stu_pending_pay', (0, 0))
        if n_pending <= 0:
            # Khong co pending -> _layout_dashboard_extras_hv se reset/recompute tf
            return

        banner = QtWidgets.QFrame(page)
        banner.setObjectName('pendingPayBanner')
        banner.setGeometry(25, 292, 820, 38)
        banner.setStyleSheet(
            'QFrame#pendingPayBanner { background: #fef3c7; border: 1px solid #d97706; '
            'border-left: 4px solid #c05621; border-radius: 8px; }'
        )
        banner.setCursor(Qt.PointingHandCursor)
        banner.setToolTip('Liên hệ nhân viên để thanh toán học phí. Click để xem chi tiết bảng dưới.')

        text = (f'💳  Bạn có <b>{n_pending}</b> lớp <b>chờ thanh toán</b>  ·  '
                f'tổng <b style="color:#9a3412;">{fmt_vnd(total_fee, suffix="đ")}</b>'
                f'  ·  liên hệ Nhân viên để thanh toán')

        lbl = QtWidgets.QLabel(text, banner)
        lbl.setGeometry(15, 0, 800, 38)
        lbl.setStyleSheet('color: #9a3412; font-size: 12px; background: transparent; border: none;')
        lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        lbl.setTextFormat(Qt.RichText)
        lbl.setCursor(Qt.PointingHandCursor)

        # Click → scroll xuong tableFrame de nhin chi tiet (gioi han: chi co `tblCourses`)
        def _click(ev):
            if ev.button() == Qt.LeftButton:
                tf = page.findChild(QtWidgets.QFrame, 'tableFrame')
                if tf:
                    tbl = tf.findChild(QtWidgets.QTableWidget, 'tblCourses')
                    if tbl:
                        # Highlight first pending row
                        for r in range(tbl.rowCount()):
                            it = tbl.item(r, 5)
                            if it and 'chờ' in it.text().lower():
                                tbl.selectRow(r)
                                tbl.scrollToItem(it, QtWidgets.QAbstractItemView.PositionAtCenter)
                                tbl.setFocus()
                                break
        banner.mousePressEvent = _click
        lbl.mousePressEvent = _click
        banner.show()

    def _render_exam_alert_banner_hv(self, page):
        """Banner alert "Co N mon thi sap toi" (≤7 ngay) tren HV dashboard.

        Tu dong xep o vi tri Row 2 (y=292) neu khong co pendingPayBanner,
        hoac Row 3 (y=336) neu co pendingPay. An han neu khong co exam upcoming.
        """
        from datetime import date as _date
        # Cleanup banner cu
        cleanup_banner(page, 'examAlertBanner')

        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        n_today = n_3 = n_7 = 0
        if DB_AVAILABLE and hv_id and ExamService:
            try:
                today_d = _date.today()
                rows = ExamService.get_for_student(hv_id) or []
                for r in rows:
                    ngay_d = parse_iso_date(r.get('ngay_thi') or r.get('ngay', ''))
                    if not ngay_d:
                        continue
                    dl = (ngay_d - today_d).days
                    if dl == 0: n_today += 1
                    elif 1 <= dl <= 3: n_3 += 1
                    elif 4 <= dl <= 7: n_7 += 1
            except Exception as e:
                print(f'[STU_DASH_EXAM] loi: {e}')

        n_total = n_today + n_3 + n_7
        if n_total <= 0:
            self._layout_dashboard_extras_hv(page)
            return

        banner = QtWidgets.QFrame(page)
        banner.setObjectName('examAlertBanner')
        # Position quyet dinh boi _layout_dashboard_extras_hv
        banner.setGeometry(25, 336, 820, 38)

        if n_today > 0:
            bg, left, fg = '#fef3c7', '#c05621', '#9a3412'
        elif n_3 > 0:
            bg, left, fg = '#fee2e2', '#dc2626', '#991b1b'
        else:
            bg, left, fg = '#fef9e7', '#d97706', '#92400e'
        banner.setStyleSheet(
            f'QFrame#examAlertBanner {{ background: {bg}; border: 1px solid {left}; '
            f'border-left: 4px solid {left}; border-radius: 8px; }}'
        )
        banner.setCursor(Qt.PointingHandCursor)

        parts = []
        if n_today > 0:
            parts.append(f'<b>{n_today}</b> môn <b style="color:#9a3412;">HÔM NAY</b>')
        if n_3 > 0:
            parts.append(f'<b>{n_3}</b> môn ≤3 ngày')
        if n_7 > 0:
            parts.append(f'<b>{n_7}</b> môn 4-7 ngày')
        text_html = f'📝 Lịch thi sắp tới: {" · ".join(parts)} — <span style="color:#1e3a8a;">click để xem</span>'

        lbl = QtWidgets.QLabel(text_html, banner)
        lbl.setGeometry(15, 0, 800, 38)
        lbl.setStyleSheet(f'color: {fg}; font-size: 12px; background: transparent; border: none;')
        lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        lbl.setTextFormat(Qt.RichText)
        lbl.setCursor(Qt.PointingHandCursor)
        banner.setToolTip(f'{n_total} môn thi sắp tới — click vào trang Lịch thi')

        def _click(ev):
            if ev.button() == Qt.LeftButton:
                self._on_nav(2)  # btnExam idx 2
        banner.mousePressEvent = _click
        lbl.mousePressEvent = _click
        banner.show()
        self._layout_dashboard_extras_hv(page)

    def _layout_dashboard_extras_hv(self, page):
        """Recompute Y positions cho cac extra banners + tableFrame."""
        # Row 1 (today + asg) o y=248-286
        # Row extras start o y=292
        y = 292
        for name in ('pendingPayBanner', 'examAlertBanner'):
            b = page.findChild(QtWidgets.QFrame, name)
            if b:
                g = b.geometry()
                if g.y() != y:
                    b.setGeometry(g.x(), y, g.width(), g.height())
                y += 44
        # Push tableFrame
        tf = page.findChild(QtWidgets.QFrame, 'tableFrame')
        if tf:
            g = tf.geometry()
            new_y = max(296, y + 4)
            if g.y() != new_y:
                new_h = max(g.height() - (new_y - g.y()), 200)
                tf.setGeometry(g.x(), new_y, g.width(), new_h)

    def _fill_schedule(self):
        page = self.page_widgets[1]

        # Header bar phai resize de khong overflow ra ngoai contentArea (870 wide)
        hb = page.findChild(QtWidgets.QFrame, 'headerBar')
        if hb:
            hb.setGeometry(0, 0, 870, 56)
            # Combo "Loc lop" - de loc lich theo 1 lop cu the
            if not hb.findChild(QtWidgets.QComboBox, 'cboSchedFilter'):
                lbl_f = QtWidgets.QLabel('Lọc:', hb)
                lbl_f.setObjectName('lblSchedFilter')
                lbl_f.setGeometry(245, 18, 38, 24)
                lbl_f.setStyleSheet('color: #4a5568; font-size: 12px; font-weight: bold; background: transparent;')
                lbl_f.show()
                cbo = QtWidgets.QComboBox(hb)
                cbo.setObjectName('cboSchedFilter')
                cbo.setGeometry(285, 12, 280, 32)
                cbo.setCursor(Qt.PointingHandCursor)
                cbo.setStyleSheet('QComboBox { background: white; border: 1px solid #d2d6dc; '
                                   'border-radius: 6px; padding: 4px 10px; font-size: 12px; } '
                                   'QComboBox:hover { border-color: #002060; } '
                                   'QComboBox::drop-down { border: none; padding-right: 6px; }')
                cbo.show()
            # Them nut "In lich tuan PDF" - shift trai cho cho combo filter
            if not hb.findChild(QtWidgets.QPushButton, 'btnPrintSchedHV'):
                btn_pdf = QtWidgets.QPushButton('🖨 In tuần PDF', hb)
                btn_pdf.setObjectName('btnPrintSchedHV')
                btn_pdf.setGeometry(580, 12, 130, 32)
                btn_pdf.setCursor(Qt.PointingHandCursor)
                btn_pdf.setToolTip('In lịch tuần đang xem ra PDF để mang theo')
                btn_pdf.setStyleSheet(
                    'QPushButton { background: #c05621; color: white; border: none; '
                    'border-radius: 6px; font-size: 12px; font-weight: bold; } '
                    'QPushButton:hover { background: #9c4419; }'
                )
                btn_pdf.clicked.connect(self._stu_export_schedule_week_pdf)
                btn_pdf.show()
            # Them nut "Xuat lich (.ics)" 1 lan
            if not hb.findChild(QtWidgets.QPushButton, 'btnExportICS'):
                btn_ics = QtWidgets.QPushButton('📅 Xuất .ics', hb)
                btn_ics.setObjectName('btnExportICS')
                btn_ics.setGeometry(720, 12, 130, 32)
                btn_ics.setCursor(Qt.PointingHandCursor)
                btn_ics.setToolTip('Xuất lịch học sang file .ics để import vào Google/Apple Calendar')
                btn_ics.setStyleSheet(
                    f'QPushButton {{ background: {COLORS["green"]}; color: white; border: none; '
                    f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                    f'QPushButton:hover {{ background: {COLORS["green_hover"]}; }}'
                )
                btn_ics.clicked.connect(self._stu_export_ics)
                btn_ics.show()

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

            # Nut chon ngay tuy y -> jump tuan chua ngay do
            btn_goto = QtWidgets.QPushButton('📅 Chọn ngày...', cf)
            btn_goto.setObjectName('btnGotoWeek')
            btn_goto.setGeometry(15, 170, 195, 30)
            btn_goto.setStyleSheet('QPushButton { background: white; color: #c05621; border: 1px solid #c05621; border-radius: 6px; font-size: 11px; font-weight: bold; } QPushButton:hover { background: #fef5f0; }')
            btn_goto.setCursor(Qt.PointingHandCursor)
            btn_goto.setToolTip('Mở lịch để chọn 1 ngày bất kỳ - tự động nhảy đến tuần chứa ngày đó')
            btn_goto.show()

            hint = QtWidgets.QLabel('Click "Chọn ngày..." để xem tuần xa', cf)
            hint.setObjectName('lblNavHint')
            hint.setGeometry(15, 207, 195, 18)
            hint.setStyleSheet('color: #a0aec0; font-size: 9px; background: transparent;')
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
                near_d = parse_iso_date(near)
                if near_d:
                    self._stu_current_monday = QDate(near_d.year, near_d.month, near_d.day)
            except Exception as e:
                print(f'[STU_SCHED] nearest_week loi: {e}')
        self._load_student_schedule_week(page, tbl, self._stu_current_monday, hours, days_vn)

        # Wire prev/next/today buttons
        btn_prev = cf.findChild(QtWidgets.QPushButton, 'btnPrevWeek') if cf else None
        btn_next = cf.findChild(QtWidgets.QPushButton, 'btnNextWeek') if cf else None
        btn_today = cf.findChild(QtWidgets.QPushButton, 'btnTodayWeek') if cf else None
        nav_btns = [b for b in (btn_prev, btn_next, btn_today) if b]

        def _reload_with_debounce(new_monday):
            """Disable nut nav khi dang load -> re-enable sau, chong spam click."""
            self._stu_current_monday = new_monday
            for b in nav_btns:
                b.setEnabled(False)
            QtWidgets.QApplication.processEvents()
            try:
                self._load_student_schedule_week(page, tbl, self._stu_current_monday, hours, days_vn)
            finally:
                for b in nav_btns:
                    b.setEnabled(True)

        if btn_prev:
            btn_prev.clicked.connect(lambda: _reload_with_debounce(self._stu_current_monday.addDays(-7)))
        if btn_next:
            btn_next.clicked.connect(lambda: _reload_with_debounce(self._stu_current_monday.addDays(7)))
        if btn_today:
            btn_today.clicked.connect(lambda: _reload_with_debounce(
                QDate.currentDate().addDays(-(QDate.currentDate().dayOfWeek() - 1))
            ))

        # Wire nut "Chon ngay..." -> mo dialog -> jump
        btn_goto = cf.findChild(QtWidgets.QPushButton, 'btnGotoWeek') if cf else None
        if btn_goto:
            def _on_goto():
                picked = pick_week_jumper_dialog(self, self._stu_current_monday)
                if picked:
                    new_mon = picked.addDays(-(picked.dayOfWeek() - 1))
                    _reload_with_debounce(new_mon)
            btn_goto.clicked.connect(_on_goto)

        # Populate combo loc lop + wire change
        cbo_filter = hb.findChild(QtWidgets.QComboBox, 'cboSchedFilter') if hb else None
        if cbo_filter is not None and cbo_filter.count() == 0:
            cbo_filter.blockSignals(True)
            cbo_filter.addItem('Tất cả lớp', None)
            if DB_AVAILABLE and hv_id:
                try:
                    my_classes = CourseService.get_classes_by_student(hv_id) or []
                    seen = set()
                    for r in my_classes:
                        ma = r.get('ma_lop')
                        if ma and ma not in seen:
                            seen.add(ma)
                            ten = r.get('ten_mon', '') or ''
                            label = f'{ma} · {ten}' if ten else ma
                            cbo_filter.addItem(label, ma)
                except Exception as e:
                    print(f'[STU_SCHED] populate filter loi: {e}')
            cbo_filter.blockSignals(False)
            # Wire 1 lan
            cbo_filter.currentIndexChanged.connect(
                lambda idx: (
                    setattr(self, '_stu_sched_filter', cbo_filter.itemData(idx)),
                    self._load_student_schedule_week(page, tbl, self._stu_current_monday, hours, days_vn),
                )
            )

    def _load_student_schedule_week(self, page, tbl, monday, hours, days_vn):
        """Reload lich hoc HV cho tuan bat dau bang `monday` (QDate)."""
        # Update header cot ngay + label tuan; highlight cot HOM NAY mau xanh
        today = QDate.currentDate()
        for i in range(6):
            d = monday.addDays(i)
            hi = tbl.horizontalHeaderItem(i+1)
            if hi:
                is_today = (d == today)
                prefix = '● ' if is_today else ''
                hi.setText(f'{prefix}{d.toString("dd/MM/yyyy")}\n{days_vn[i]}')
                # Set foreground color: today = navy bold, khac = default
                if is_today:
                    hi.setForeground(QColor('#002060'))
                    f = hi.font(); f.setBold(True); hi.setFont(f)
                else:
                    hi.setForeground(QColor('#4a5568'))
                    f = hi.font(); f.setBold(False); hi.setFont(f)
        wr_lbl = page.findChild(QtWidgets.QLabel, 'lblWeekRange')
        if wr_lbl:
            # Set format=RichText 1 lan o day - sau setText voi HTML moi parse dung
            wr_lbl.setTextFormat(Qt.RichText)
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

        def mk_card(ma_lop, ten_mon, ts, phong, gv, color, ngay_str='', sched_row=None):
            f = QtWidgets.QFrame()
            f.setStyleSheet(f'QFrame {{ background: white; border: 1px solid #d2d6dc; border-radius: 4px; border-top: 3px solid {color}; margin: 1px; }}')
            f.setCursor(Qt.PointingHandCursor)
            # Tooltip rich HTML voi day du info (hover show full detail)
            # Skip prefix 'P. ' khi phong = '—' (placeholder cho 'chua co phong')
            phong_low = (phong or '').lower()
            if not phong or phong == '—':
                phong_disp = '—'
            elif phong_low.startswith(('p.', 'p ', 'phòng', 'phong')):
                phong_disp = phong
            else:
                phong_disp = f'P. {phong}'
            tip = (
                f'<b style="color:{color};">{ma_lop}</b><br>'
                f'<b>{ten_mon}</b><br>'
                f'<span style="color:#718096;">━━━━━━━━━━━━</span><br>'
                f'🕒 <b>{ts}</b>{("<br>📅 " + ngay_str) if ngay_str else ""}<br>'
                f'📍 {phong_disp}<br>'
                f'👨‍🏫 {gv or "—"}<br>'
                f'<span style="color:#a0aec0; font-size:10px;">━━━ Click để xem chi tiết ━━━</span>'
            )
            f.setToolTip(tip)
            # Click vao card -> popup chi tiet buoi hoc
            if sched_row is not None:
                def _click(ev, _r=sched_row):
                    if ev.button() == Qt.LeftButton:
                        self._show_session_detail(_r, role='hv')
                f.mousePressEvent = _click
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
                # Filter neu user da chon 1 lop trong combo cboSchedFilter
                sel_lop = getattr(self, '_stu_sched_filter', None)
                if sel_lop:
                    rows = [r for r in rows if r.get('lop_id') == sel_lop]
                color_palette = ['#002060', '#c68a1e', '#276749', '#c53030', '#3182ce']
                color_by_lop = {}
                from datetime import date as _date
                for r in rows:
                    try:
                        d = parse_iso_date(r.get('ngay'))
                        if d is None:
                            continue
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
                            d.strftime('%d/%m/%Y') if hasattr(d, 'strftime') else str(d),
                            r,  # raw row de show detail dialog khi click
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
            for rs, span, col, ma_lop, ten_mon, ts, phong, gv, color, ngay_str, raw in sched:
                tbl.setCellWidget(rs, col, mk_card(ma_lop, ten_mon, ts, phong, gv, color, ngay_str, raw))
                tbl.setSpan(rs, col, span, 1)

        # Update lblWeekRange voi count "X buoi · Y lop"
        if wr_lbl:
            n_sessions = len(sched)
            n_lops = len({tup[3] for tup in sched if len(tup) > 3 and tup[3]})
            base = f'Tuần: {monday.toString("dd/MM/yyyy")} → {monday.addDays(5).toString("dd/MM/yyyy")}'
            # textFormat=RichText da set o tren khi findChild
            if n_sessions > 0:
                wr_lbl.setText(f'{base}  ·  <b style="color:#002060;">{n_sessions}</b> buổi'
                                 f'  ·  <b style="color:#c05621;">{n_lops}</b> lớp')
            else:
                wr_lbl.setText(f'{base}  ·  <span style="color:#a0aec0;">không có buổi</span>')

        # Update legend frame voi cac lop dang hien thi
        self._update_schedule_legend(page, sched)

    def _update_schedule_legend(self, page, sched):
        """Update legend1-5 + legendTxt1-5 trong legendFrame theo cac lop trong sched.

        sched: list tuple voi format (..., ma_lop, ten_mon, ..., color, ...)
        """
        lf = page.findChild(QtWidgets.QFrame, 'legendFrame')
        if not lf:
            return
        # Build map ma_lop -> (color, ten_mon) tu sched (giu thu tu xuat hien)
        seen = {}
        for tup in sched or []:
            try:
                ma_lop = tup[3]
                ten_mon = tup[4]
                color = tup[8]
            except (IndexError, TypeError):
                continue
            if ma_lop and ma_lop not in seen:
                seen[ma_lop] = (color, ten_mon)
        items = list(seen.items())[:5]  # legend chi co 5 row
        # Update tung row legend1-5
        for i in range(1, 6):
            chip = lf.findChild(QtWidgets.QLabel, f'legend{i}')
            txt = lf.findChild(QtWidgets.QLabel, f'legendTxt{i}')
            if i <= len(items):
                ma_lop, (color, ten_mon) = items[i - 1]
                if chip:
                    chip.setStyleSheet(f'background: {color}; border-radius: 2px;')
                    chip.show()
                if txt:
                    label = f'{ma_lop}'
                    if ten_mon:
                        # Truncate ten_mon neu qua dai
                        ten_short = ten_mon if len(ten_mon) <= 18 else ten_mon[:16] + '…'
                        label = f'{ma_lop} · {ten_short}'
                    txt.setText(label)
                    txt.setToolTip(f'{ma_lop} — {ten_mon}' if ten_mon else ma_lop)
                    txt.show()
            else:
                # Khong du items -> hide row
                if chip: chip.hide()
                if txt: txt.hide()
        # Update title
        lbl_title = lf.findChild(QtWidgets.QLabel, 'lblLegendTitle')
        if lbl_title:
            n = len(items)
            if n == 0:
                lbl_title.setText('Chú thích (chưa có lớp)')
            elif n < len(seen):
                lbl_title.setText(f'Chú thích ({n}/{len(seen)} lớp)')
            else:
                lbl_title.setText(f'Chú thích ({n} lớp)')

    def _fill_exam(self):
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblExam')
        if not tbl:
            return

        # Them nut "In PDF" vao headerBar 1 lan
        hb = page.findChild(QtWidgets.QFrame, 'headerBar')
        if hb and not hb.findChild(QtWidgets.QPushButton, 'btnPrintExam'):
            btn_pdf = QtWidgets.QPushButton('🖨 In PDF', hb)
            btn_pdf.setObjectName('btnPrintExam')
            btn_pdf.setGeometry(470, 12, 120, 32)
            btn_pdf.setCursor(Qt.PointingHandCursor)
            btn_pdf.setToolTip('In danh sách lịch thi ra PDF')
            btn_pdf.setStyleSheet(
                'QPushButton { background: #c05621; color: white; border: none; '
                'border-radius: 6px; font-size: 12px; font-weight: bold; } '
                'QPushButton:hover { background: #9c4419; }'
            )
            btn_pdf.clicked.connect(self._stu_export_exam_pdf)
            btn_pdf.show()

        # Load exams cua HV tu API + luu semester_id de filter
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        data = []
        self._exam_sem_ids = []  # song song voi data, luu sem_id de filter
        # Cache full rows de _stu_export_exam_pdf re-use khong query lai
        self._stu_exam_rows_cache = []
        if DB_AVAILABLE and hv_id and ExamService:
            try:
                rows = ExamService.get_for_student(hv_id) or []
                self._stu_exam_rows_cache = rows
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
                    self._exam_sem_ids.append(r.get('semester_id') or '')
            except Exception as e:
                print(f'[STU_EXAM] API loi: {e}')

        # Summary banner: dem so mon thi <=7 ngay
        n_today = n_soon_3 = n_soon_7 = 0
        first_upcoming_row = None  # de scroll khi click banner

        if not data:
            set_table_empty_state(
                tbl, 'Chưa có lịch thi nào',
                icon='📝',
                cta_text='📅 Xem lịch học',
                cta_callback=lambda: self._on_nav(1))
        else:
            tbl.setRowCount(len(data))
            from datetime import date as _date
            today = _date.today()
            for r, row in enumerate(data):
                # Tinh days_left tu raw row (cache)
                days_left = None
                ngay_d = None
                if r < len(self._stu_exam_rows_cache):
                    raw = self._stu_exam_rows_cache[r]
                    ngay_d = parse_iso_date(raw.get('ngay_thi') or raw.get('ngay', ''))
                    if ngay_d:
                        days_left = (ngay_d - today).days

                # Color row theo days_left
                #  HOM NAY     -> nen vang dam, text do
                #  1-3 ngay    -> nen do nhat, text do, bold
                #  4-7 ngay    -> nen vang nhat, text cam
                #  da thi      -> nen xam nhat, text gray italic
                #  binh thuong -> default
                bg_color = None
                fg_color = None
                bold = False
                italic = False
                if days_left is None:
                    pass
                elif days_left == 0:
                    bg_color = '#fef3c7'   # yellow 100
                    fg_color = '#9a3412'   # orange 800
                    bold = True
                    n_today += 1
                    if first_upcoming_row is None:
                        first_upcoming_row = r
                elif 1 <= days_left <= 3:
                    bg_color = '#fee2e2'   # red 100
                    fg_color = '#991b1b'   # red 800
                    bold = True
                    n_soon_3 += 1
                    if first_upcoming_row is None:
                        first_upcoming_row = r
                elif 4 <= days_left <= 7:
                    bg_color = '#fef9e7'   # yellow 50
                    fg_color = '#92400e'   # amber 800
                    n_soon_7 += 1
                    if first_upcoming_row is None:
                        first_upcoming_row = r
                elif days_left < 0:
                    bg_color = '#f7fafc'
                    fg_color = '#9ca3af'
                    italic = True

                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    if bg_color:
                        item.setBackground(QColor(bg_color))
                    if fg_color:
                        item.setForeground(QColor(fg_color))
                    if bold or italic:
                        f = item.font()
                        if bold: f.setBold(True)
                        if italic: f.setItalic(True)
                        item.setFont(f)
                    tbl.setItem(r, c, item)

                # Append countdown text vao cell Phong (cot 5) hoac Ngay (cot 3)
                # Show "HÔM NAY!" hoac "Còn N ngày" o cell Ca thi (cot 4)
                if days_left is not None and days_left >= 0 and days_left <= 7:
                    ca_item = tbl.item(r, 4)
                    if ca_item:
                        old_txt = ca_item.text()
                        if days_left == 0:
                            badge = '\n⚠ HÔM NAY!'
                        else:
                            badge = f'\nCòn {days_left} ngày'
                        ca_item.setText(old_txt + badge)
                # Tooltip cho ca row
                if days_left is not None and tbl.item(r, 0):
                    if days_left > 0:
                        tip = f'Còn {days_left} ngày nữa thi'
                    elif days_left == 0:
                        tip = 'Thi hôm nay - chuẩn bị sẵn!'
                    else:
                        tip = f'Đã thi cách đây {-days_left} ngày'
                    for c in range(7):
                        if tbl.item(r, c):
                            tbl.item(r, c).setToolTip(tip)

            # Row height: 52 cho row co badge "Hom nay/Con N ngay", 40 cho row binh thuong
            for r in range(len(data)):
                ca_item = tbl.item(r, 4)
                has_badge = ca_item and ('\n' in ca_item.text())
                tbl.setRowHeight(r, 52 if has_badge else 40)
            # Tooltip nhac user double-click
            for r in range(len(data)):
                for c in range(min(7, tbl.columnCount())):
                    it = tbl.item(r, c)
                    if it and not it.toolTip():
                        it.setToolTip('Double-click để xem chi tiết ca thi')
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, w in enumerate([30, 65, 140, 85, 135, 80]):
            tbl.setColumnWidth(c, w)
        tbl.verticalHeader().setVisible(False)

        # Wire double-click row -> popup detail (1 lan)
        if not getattr(self, '_stu_exam_dblclick_wired', False):
            tbl.cellDoubleClicked.connect(self._stu_on_exam_dblclick)
            self._stu_exam_dblclick_wired = True

        # === Banner summary mon thi sap toi (≤7 ngay) ===
        # Cleanup banner cu (truoc khi tao moi)
        cleanup_banner(page, 'examTodayBanner')

        n_total_soon = n_today + n_soon_3 + n_soon_7
        if n_total_soon > 0:
            banner = QtWidgets.QFrame(page)
            banner.setObjectName('examTodayBanner')
            banner.setGeometry(25, 60, 820, 38)
            # Mau theo do gan
            if n_today > 0:
                bg = '#fef3c7'; left = '#c05621'; text_clr = '#9a3412'
            elif n_soon_3 > 0:
                bg = '#fee2e2'; left = '#dc2626'; text_clr = '#991b1b'
            else:
                bg = '#fef9e7'; left = '#d97706'; text_clr = '#92400e'
            banner.setStyleSheet(
                f'QFrame#examTodayBanner {{ background: {bg}; border: 1px solid {left}; '
                f'border-left: 4px solid {left}; border-radius: 8px; }}'
            )
            banner.setCursor(Qt.PointingHandCursor)

            # Build text
            parts = []
            if n_today > 0:
                parts.append(f'<b>{n_today}</b> môn thi <b style="color:#9a3412;">HÔM NAY</b>')
            if n_soon_3 > 0:
                parts.append(f'<b>{n_soon_3}</b> môn trong 3 ngày')
            if n_soon_7 > 0:
                parts.append(f'<b>{n_soon_7}</b> môn trong 4-7 ngày')
            text_html = f'🔔 Bạn có {" · ".join(parts)} — <span style="color:#1e3a8a;">click để xem ngay</span>'

            lbl = QtWidgets.QLabel(text_html, banner)
            lbl.setGeometry(15, 0, 800, 38)
            lbl.setStyleSheet(f'color: {text_clr}; font-size: 12px; background: transparent; border: none;')
            lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            lbl.setTextFormat(Qt.RichText)
            banner.setToolTip(f'{n_total_soon} môn thi sắp tới — click để jump tới mục đầu tiên')
            # Click banner -> scroll to first upcoming row
            target_row = first_upcoming_row
            def _click(ev, _r=target_row):
                if ev.button() == Qt.LeftButton and _r is not None:
                    tbl.selectRow(_r)
                    tbl.scrollToItem(tbl.item(_r, 0), QtWidgets.QAbstractItemView.PositionAtCenter)
                    tbl.setFocus()
            banner.mousePressEvent = _click
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.mousePressEvent = _click
            banner.show()

            # Day examFrame xuong de chua banner
            ef = page.findChild(QtWidgets.QFrame, 'examFrame')
            if ef:
                g = ef.geometry()
                new_y = 104
                if g.y() != new_y:
                    new_h = max(g.height() - (new_y - g.y()), 200)
                    ef.setGeometry(g.x(), new_y, g.width(), new_h)
                    # Resize tbl ben trong (height giam tuong ung)
                    tg = tbl.geometry()
                    tbl.setGeometry(tg.x(), tg.y(), tg.width(), max(tg.height() - 32, 200))
        else:
            # Reset examFrame ve geometry mac dinh neu khong co banner
            ef = page.findChild(QtWidgets.QFrame, 'examFrame')
            if ef:
                g = ef.geometry()
                if g.y() != 72:
                    ef.setGeometry(g.x(), 72, g.width(), g.height() + (g.y() - 72))

        # Load combo semester dynamic + filter theo sem_id thuc
        cbo = page.findChild(QtWidgets.QComboBox, 'cboSemester')
        if cbo:
            cbo.clear()
            cbo.addItem('Tất cả khóa học')
            sem_map = {0: None}
            if DB_AVAILABLE and SemesterService:
                try:
                    sems = SemesterService.get_all() or []
                    for i, s in enumerate(sems, start=1):
                        nm = s.get('ten') or s.get('id', '')
                        nh = s.get('nam_hoc', '')
                        cbo.addItem(f'{nm} - {nh}' if nh else nm)
                        sem_map[i] = s.get('id', '')
                except Exception as e:
                    print(f'[HV_EXAM_SEM] loi: {e}')
            safe_connect(cbo.currentIndexChanged, lambda idx: self._filter_exam_sem(sem_map.get(idx)))

    def _filter_exam_sem(self, sem_id):
        """Filter bang lich thi theo semester_id thuc. None = tat ca."""
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblExam')
        if not tbl:
            return
        for r in range(tbl.rowCount()):
            if sem_id is None:
                tbl.setRowHidden(r, False)
            elif r < len(self._exam_sem_ids):
                tbl.setRowHidden(r, self._exam_sem_ids[r] != sem_id)

    def _stu_on_exam_dblclick(self, row, col):
        """HV double-click 1 row tbl Lich thi -> popup chi tiet ca thi."""
        cache = getattr(self, '_stu_exam_rows_cache', [])
        if row < 0 or row >= len(cache):
            return
        show_exam_detail_dialog(self, cache[row], role='hv')

    def _fill_grades(self):
        page = self.page_widgets[3]
        # lay tu DB truoc neu co
        self._student_grades_by_sem = {}
        # Cache so buoi + completed cho stat cards
        self._grades_total_buoi = 0
        self._grades_completed = 0
        if DB_AVAILABLE:
            try:
                hv_id = MOCK_USER.get('id')
                if hv_id:
                    rows = GradeService.get_grades_by_student(hv_id)
                    # group theo semester_id (lay 1 lan tu API classes)
                    from collections import defaultdict
                    by_sem = defaultdict(list)
                    # Cache class so_buoi + semester_id de tranh N+1 query
                    sem_cache = {}
                    sobuoi_cache = {}
                    try:
                        all_classes = CourseService.get_all_classes() or []
                        for c in all_classes:
                            sem_cache[c.get('ma_lop')] = c.get('semester_id') or '_unknown'
                            sobuoi_cache[c.get('ma_lop')] = int(c.get('so_buoi') or 0)
                    except Exception as _e:
                        pass
                    for g in rows:
                        sid = sem_cache.get(g['lop_id'], '_unknown')
                        sb = sobuoi_cache.get(g['lop_id'], 0)
                        by_sem[sid].append([
                            g['ma_mon'], g['ten_mon'],
                            str(sb) if sb else '—',
                            f"{float(g['diem_qt']):.1f}" if g.get('diem_qt') else '',
                            f"{float(g['diem_thi']):.1f}" if g.get('diem_thi') else '',
                            f"{float(g['tong_ket']):.1f}" if g.get('tong_ket') else '',
                            g.get('xep_loai', '') or '',
                        ])
                        # Tinh stat: so_buoi tich luy + so khoa hoan thanh (co tong_ket >= 4 = pass)
                        self._grades_total_buoi += sb
                        try:
                            if float(g.get('tong_ket') or 0) >= 4.0:
                                self._grades_completed += 1
                        except (ValueError, TypeError):
                            pass
                    self._student_grades_by_sem = dict(by_sem)
            except Exception as e:
                print(f'[GRADES] DB loi: {e}')
        # khong co du lieu -> de trong, ham render se hien bang rong
        # them mot dong placeholder de bao "Chua co du lieu diem"
        # _render_student_grades() da xu ly empty state -> khong can dup nua
        self._render_student_grades(None)

        # Stat cards: Diem TB (he 10) / So khoa hoan thanh / So buoi tich luy
        # Khoa ngoai khoa khong dung GPA he 4, dung diem he 10 voi xep loai A+...F
        gpa_he10 = 0.0
        if DB_AVAILABLE:
            try:
                hv_id = MOCK_USER.get('id')
                if hv_id:
                    stats = GradeService.get_gpa_stats(hv_id) or {}
                    gpa_he10 = float(stats.get('gpa') or 0.0)
            except Exception as e:
                print(f'[GPA] loi: {e}')

        for attr, val, color in [
            ('lblGpa', f'{gpa_he10:.2f}' if gpa_he10 > 0 else '—', COLORS['navy']),
            ('lblGpaSem', str(self._grades_completed) if self._grades_completed else '—', COLORS['green']),
            ('lblTotalCredits', str(self._grades_total_buoi) if self._grades_total_buoi else '—', COLORS['gold']),
        ]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setText(val)
                w.setStyleSheet(f'color: {color}; font-size: 22px; font-weight: bold; background: transparent;')
        # Header: them nut "Xuat PDF bang diem" + cboSemester
        header = page.findChild(QtWidgets.QFrame, 'headerBar')
        if header:
            # Cleanup nut cu (neu co)
            for old_name in ('btnProgressCT',):
                old = header.findChild(QtWidgets.QPushButton, old_name)
                if old:
                    old.deleteLater()
            # Add or reuse PDF export button (idempotent re-fill)
            btn_pdf = header.findChild(QtWidgets.QPushButton, 'btnExportPDF')
            if not btn_pdf:
                btn_pdf = QtWidgets.QPushButton('🖨 Xuất PDF', header)
                btn_pdf.setObjectName('btnExportPDF')
                btn_pdf.setGeometry(720, 12, 130, 32)
                btn_pdf.setCursor(Qt.PointingHandCursor)
                btn_pdf.setStyleSheet(
                    f'QPushButton {{ background: {COLORS["gold"]}; color: white; border: none; '
                    f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                    f'QPushButton:hover {{ background: {COLORS["gold_hover"]}; }}'
                )
                btn_pdf.show()
            safe_connect(btn_pdf.clicked, self._stu_export_grades_pdf)
        # cboSemester nho hon de fit nut PDF
        cbo_sem = page.findChild(QtWidgets.QComboBox, 'cboSemester')
        if cbo_sem:
            cbo_sem.setGeometry(470, 12, 240, 32)

        # combo loc - load dynamic tu API. Khoa ngoai khoa: filter theo dot
        # khai giang (semester_id) hoac "Tat ca khoa hoc"
        cbo = cbo_sem
        if cbo:
            cbo.clear()
            cbo.addItem('Tất cả khóa học')
            sem_map = {0: None}
            if DB_AVAILABLE and SemesterService:
                try:
                    sems = SemesterService.get_all() or []
                    for i, s in enumerate(sems, start=1):
                        nm = s.get('ten') or s.get('id', '')
                        nh = s.get('nam_hoc', '')
                        cbo.addItem(f'{nm} - {nh}' if nh else nm)
                        sem_map[i] = s.get('id', '')
                except Exception as e:
                    print(f'[HV_GRADES_SEM] loi: {e}')
            safe_connect(cbo.currentIndexChanged, lambda idx: self._render_student_grades(sem_map.get(idx)))

    def _stu_export_grades_pdf(self):
        """Xuat bang diem PDF cho HV - dung QPrinter + HTML template chinh quy."""
        try:
            from PyQt5.QtPrintSupport import QPrinter
            from PyQt5.QtGui import QTextDocument
        except ImportError:
            msg_warn(self, 'Lỗi', 'PyQt5.QtPrintSupport không có sẵn.')
            return
        if not self._student_grades_by_sem:
            msg_warn(self, 'Trống', 'Bạn chưa có điểm để xuất PDF.')
            return
        msv = MOCK_USER.get('msv', 'N/A')
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Xuất bảng điểm PDF',
            os.path.join(os.path.expanduser('~'), 'Desktop', f'BangDiem_{msv}.pdf'),
            'PDF Files (*.pdf)'
        )
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'

        # Compute aggregated stats
        from datetime import datetime
        all_rows = []
        for rows in self._student_grades_by_sem.values():
            all_rows.extend(rows)
        # Get GPA + completed count
        gpa_he10 = 0.0
        try:
            hv_id = MOCK_USER.get('id')
            if hv_id and DB_AVAILABLE:
                stats = GradeService.get_gpa_stats(hv_id) or {}
                gpa_he10 = float(stats.get('gpa') or 0.0)
        except Exception:
            pass

        # Build HTML
        u = MOCK_USER
        rows_html = []
        for i, row in enumerate(all_rows, 1):
            ma_kh, ten, sb, qt, thi, tk, xl = row
            # Color theo xep loai
            xl_color = '#166534' if xl in ('A+', 'A') else (
                '#1e3a8a' if xl in ('B+', 'B') else (
                    '#92400e' if xl in ('C+', 'C') else '#991b1b'
                )
            )
            tk_color = '#166534' if (tk and tk != '' and float(tk) >= 8) else '#1a1a2e'
            rows_html.append(f'''
                <tr style="background: {'#f7fafc' if i % 2 == 0 else 'white'};">
                    <td style="text-align: center; padding: 8px; border: 1px solid #e2e8f0;">{i}</td>
                    <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">{ma_kh}</td>
                    <td style="padding: 8px; border: 1px solid #e2e8f0;">{ten}</td>
                    <td style="text-align: center; padding: 8px; border: 1px solid #e2e8f0;">{sb}</td>
                    <td style="text-align: center; padding: 8px; border: 1px solid #e2e8f0;">{qt or '—'}</td>
                    <td style="text-align: center; padding: 8px; border: 1px solid #e2e8f0;">{thi or '—'}</td>
                    <td style="text-align: center; padding: 8px; border: 1px solid #e2e8f0; color: {tk_color}; font-weight: bold;">{tk or '—'}</td>
                    <td style="text-align: center; padding: 8px; border: 1px solid #e2e8f0; color: {xl_color}; font-weight: bold; font-size: 13px;">{xl or '—'}</td>
                </tr>
            ''')
        html = f'''
        <html><head><meta charset="utf-8"></head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e;">
        <div style="text-align: center; border-bottom: 3px solid #002060; padding-bottom: 12px; margin-bottom: 20px;">
            <h1 style="color: #002060; margin: 0; font-size: 22px;">TRUNG TÂM NGOẠI KHÓA EAUT</h1>
            <p style="margin: 4px 0; color: #4a5568; font-size: 11px;">
                Km 23, QL5, Trưng Trắc, Văn Lâm, Hưng Yên · Hotline: 024.3999.1111
            </p>
        </div>

        <h2 style="text-align: center; color: #c05621; margin: 0 0 4px 0; letter-spacing: 1px;">BẢNG ĐIỂM HỌC VIÊN</h2>
        <p style="text-align: center; color: #718096; font-size: 11px; margin: 0 0 18px 0;">
            Cập nhật: <b>{datetime.now().strftime('%d/%m/%Y %H:%M')}</b>
        </p>

        <table cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 16px;">
            <tr style="background: #edf2f7;">
                <td style="width: 25%; color: #4a5568; padding: 8px;">Họ và tên</td>
                <td style="padding: 8px;"><b>{u.get('name', '—')}</b></td>
                <td style="width: 18%; color: #4a5568; padding: 8px;">Mã số HV</td>
                <td style="padding: 8px;"><b>{u.get('msv', '—')}</b></td>
            </tr>
            <tr>
                <td style="color: #4a5568; padding: 8px;">Ngày sinh</td>
                <td style="padding: 8px;">{u.get('ngaysinh', '—')}</td>
                <td style="color: #4a5568; padding: 8px;">Giới tính</td>
                <td style="padding: 8px;">{u.get('gioitinh', '—')}</td>
            </tr>
        </table>

        <table cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 11px;">
            <thead>
                <tr style="background: #002060; color: white;">
                    <th style="padding: 8px; border: 1px solid #002060; width: 4%;">#</th>
                    <th style="padding: 8px; border: 1px solid #002060; width: 12%;">Mã KH</th>
                    <th style="padding: 8px; border: 1px solid #002060;">Tên khóa học</th>
                    <th style="padding: 8px; border: 1px solid #002060; width: 8%;">Số buổi</th>
                    <th style="padding: 8px; border: 1px solid #002060; width: 8%;">QT</th>
                    <th style="padding: 8px; border: 1px solid #002060; width: 8%;">Thi</th>
                    <th style="padding: 8px; border: 1px solid #002060; width: 10%;">TK</th>
                    <th style="padding: 8px; border: 1px solid #002060; width: 10%;">Xếp loại</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html) if rows_html else '<tr><td colspan="8" style="text-align: center; padding: 20px; color: #a0aec0;">(Chưa có điểm)</td></tr>'}
            </tbody>
        </table>

        <div style="margin-top: 18px; padding: 12px; background: #f7fafc; border-left: 4px solid #002060; border-radius: 4px;">
            <p style="margin: 4px 0; font-size: 12px;"><b style="color: #002060;">Tổng kết:</b></p>
            <p style="margin: 4px 0; font-size: 13px;">
                · Điểm trung bình hệ 10: <b style="color: #c05621;">{gpa_he10:.2f}</b><br>
                · Số khóa học hoàn thành: <b>{self._grades_completed}</b><br>
                · Tổng số buổi học: <b>{self._grades_total_buoi}</b>
            </p>
        </div>

        <div style="margin-top: 40px; display: flex; justify-content: flex-end;">
            <div style="text-align: center; width: 40%;">
                <p style="color: #4a5568; font-size: 11px;">Hà Nội, ngày {datetime.now().day} tháng {datetime.now().month} năm {datetime.now().year}</p>
                <p style="margin-top: 4px; color: #4a5568;"><b>Trưởng phòng đào tạo</b></p>
                <p style="font-size: 10px; color: #718096; font-style: italic;">(ký tên, đóng dấu)</p>
            </div>
        </div>

        <p style="text-align: center; color: #718096; font-size: 10px; margin-top: 30px; font-style: italic;">
            Bảng điểm này có giá trị tham khảo. Bản chính thức cấp tại văn phòng Trung tâm.
        </p>
        </body></html>
        '''
        try:
            doc = _make_vn_textdoc(html)
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
            doc.print_(printer)
            msg_info(self, 'Đã xuất PDF', f'Bảng điểm đã lưu:\n{path}')
        except Exception as e:
            print(f'[STU_PDF] loi: {e}')
            msg_warn(self, 'Lỗi xuất PDF', f'Không xuất được:\n{e}')

    def _render_student_grades(self, sem_id):
        """Render bang diem cua HV. sem_id=None = tat ca khoa hoc.
        Khoa ngoai khoa: bo cot 'Hoc ky' (khong phan ky), giu so_buoi tu class detail.
        """
        page = self.page_widgets[3]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblGrades')
        if not tbl:
            return
        # Gop tat ca diem - khong them cot HK
        all_rows = []
        if sem_id and sem_id in self._student_grades_by_sem:
            all_rows = list(self._student_grades_by_sem[sem_id])
        else:
            for s_id, rows in self._student_grades_by_sem.items():
                all_rows.extend(rows)

        tbl.setColumnCount(7)
        headers = ['Mã KH', 'Tên khóa học', 'Số buổi', 'Điểm QT', 'Điểm thi', 'Tổng kết', 'Xếp loại']
        for c, h in enumerate(headers):
            tbl.setHorizontalHeaderItem(c, QtWidgets.QTableWidgetItem(h))

        if not all_rows:
            set_table_empty_state(
                tbl, 'Chưa có dữ liệu điểm - GV chưa nhập điểm hoặc bạn chưa hoàn thành lớp nào.',
                icon='⭐',
                cta_text='📚 Xem lớp đã đăng ký',
                cta_callback=lambda: self._on_nav(0))
        else:
            tbl.setRowCount(len(all_rows))
            for r, row in enumerate(all_rows):
                # Row 40px - du cho chu xep loai (khong pill nua)
                tbl.setRowHeight(r, 40)
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter if c != 1 else Qt.AlignLeft | Qt.AlignVCenter)
                    if c == 5:  # tong ket - color text theo nguong diem
                        try:
                            s = float(val)
                            item.setForeground(QColor(COLORS['green'] if s >= 8 else COLORS['navy'] if s >= 6.5 else COLORS['orange']))
                        except ValueError:
                            pass
                    elif c == 6 and val:  # xep loai - mau bold theo grade
                        style_status_item(item, val)
                    tbl.setItem(r, c, item)
        # Stretch col 1 (Ten khoa hoc) - cot dai nhat - cot khac fix
        tbl.setColumnWidth(0, 70)    # Ma KH
        tbl.setColumnWidth(1, 200)   # Ten khoa (stretch)
        tbl.setColumnWidth(2, 70)    # So buoi
        tbl.setColumnWidth(3, 70)    # Diem QT
        tbl.setColumnWidth(4, 70)    # Diem thi
        tbl.setColumnWidth(5, 80)    # Tong ket
        tbl.setColumnWidth(6, 95)    # Xep loai badge - vua du fit B+/A+
        tbl.horizontalHeader().setStretchLastSection(False)
        tbl.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        tbl.verticalHeader().setVisible(False)

    # ===== STUDENT ASSIGNMENTS PAGE =====

    def _fill_assignments(self):
        """Trang Bai tap cua HV - xem ds bai cho lop minh, nop bai, xem feedback."""
        page = self.page_widgets[4]
        if not getattr(page, '_built', False):
            self._build_stu_assignments_ui(page)
            page._built = True
        self._reload_stu_assignments(page)

    def _build_stu_assignments_ui(self, page):
        """Build UI 1 lan: header + bang ds bai tap can lam."""
        hb = QtWidgets.QFrame(page)
        hb.setObjectName('headerBar')
        hb.setGeometry(0, 0, 870, 56)
        hb.setStyleSheet('QFrame#headerBar { background: white; border-bottom: 1px solid #d2d6dc; }')
        title = QtWidgets.QLabel('Bài tập', hb)
        title.setGeometry(25, 4, 200, 24)
        title.setStyleSheet('color: #1a1a2e; font-size: 16px; font-weight: bold; background: transparent;')
        sub = QtWidgets.QLabel('Bấm "Nộp" để gửi bài, "Xem góp ý" để xem feedback.', hb)
        sub.setGeometry(25, 30, 440, 16)
        sub.setStyleSheet('color: #718096; font-size: 10px; background: transparent;')

        # Search box
        txt_s = QtWidgets.QLineEdit(hb)
        txt_s.setObjectName('txtStuAsgSearch')
        txt_s.setGeometry(470, 12, 220, 32)
        txt_s.setPlaceholderText('🔍 Tìm tiêu đề / lớp / khóa...')
        txt_s.setClearButtonEnabled(True)
        txt_s.setStyleSheet('QLineEdit { background: white; border: 1px solid #d2d6dc; '
                             'border-radius: 6px; padding: 4px 10px; font-size: 12px; } '
                             'QLineEdit:focus { border-color: #002060; }')

        # Filter combo trang thai
        cbo = QtWidgets.QComboBox(hb)
        cbo.setObjectName('cboStuAsgStatus')
        cbo.setGeometry(700, 12, 150, 32)
        cbo.setCursor(Qt.PointingHandCursor)
        cbo.addItem('Tất cả trạng thái', None)
        cbo.addItem('🔵 Chưa nộp', 'pending')
        cbo.addItem('🟢 Đã nộp', 'submitted')
        cbo.addItem('⭐ Đã chấm', 'graded')
        cbo.addItem('🔴 Quá hạn', 'overdue')
        cbo.setStyleSheet('QComboBox { background: white; border: 1px solid #d2d6dc; '
                           'border-radius: 6px; padding: 4px 8px; font-size: 11px; } '
                           'QComboBox:hover { border-color: #002060; } '
                           'QComboBox::drop-down { border: none; padding-right: 4px; }')

        tbl = QtWidgets.QTableWidget(page)
        tbl.setObjectName('tblStuAssignments')
        tbl.setGeometry(15, 70, 840, 615)
        tbl.setColumnCount(7)
        tbl.setHorizontalHeaderLabels(['#', 'Tiêu đề', 'Khóa học', 'Hạn nộp',
                                        'Trạng thái', 'Điểm', 'Thao tác'])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # Header padding 14x10 + min-height 46 dong nhat voi adm sched + bai nop dialog
        tbl.setStyleSheet(
            'QTableWidget { background: white; border: 1px solid #d2d6dc; '
            'border-radius: 6px; gridline-color: #edf2f7; font-size: 12px; } '
            'QHeaderView::section { background: #f7fafc; color: #4a5568; '
            'padding: 14px 10px; border: none; border-bottom: 1px solid #d2d6dc; '
            'font-family: "Segoe UI", "Inter", sans-serif; '
            'font-weight: bold; font-size: 11px; }'
        )
        tbl.horizontalHeader().setMinimumHeight(46)
        tbl.show()

    def _reload_stu_assignments(self, page):
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblStuAssignments')
        if not tbl:
            return
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        rows = []
        if DB_AVAILABLE and hv_id:
            try:
                rows = AssignmentService.get_pending(hv_id) or []
            except Exception as e:
                print(f'[STU_ASG] loi: {e}')

        if not rows:
            set_table_empty_state(
                tbl, 'Chưa có bài tập nào - GV chưa giao bài, hoặc bạn chưa đăng ký lớp.',
                icon='📝',
                cta_text='📚 Xem lớp đã đăng ký',
                cta_callback=lambda: self._on_nav(0))
        else:
            from datetime import datetime
            now = datetime.now()
            tbl.setRowCount(len(rows))
            for r, row in enumerate(rows):
                tbl.setRowHeight(r, 44)
                han_str = '—'
                han_overdue = False
                if row.get('han_nop'):
                    han_dt = parse_iso_datetime(row['han_nop'])
                    if han_dt:
                        han_str = han_dt.strftime('%d/%m/%Y %H:%M')
                        han_overdue = han_dt < now
                    else:
                        han_str = str(row['han_nop'])

                has_sub = row.get('submission_id') is not None
                graded = row.get('diem') is not None
                if graded:
                    status = 'Đã chấm'
                elif has_sub:
                    status = 'Đã nộp'
                elif han_overdue:
                    status = 'Quá hạn'
                else:
                    status = 'Chưa nộp'
                diem_disp = f"{float(row['diem']):.1f}/{row.get('diem_toi_da', 10)}" if graded else '—'

                items = [str(r + 1), row.get('tieu_de', ''),
                         f"{row.get('lop_id', '')} ({row.get('ten_mon', '')})",
                         han_str, status, diem_disp]
                for c, val in enumerate(items):
                    item = QtWidgets.QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter if c in (0, 3, 5) else Qt.AlignLeft | Qt.AlignVCenter)
                    if c == 4:  # status badge
                        style_status_item(item, status)
                    if c == 3 and han_overdue and not graded:
                        item.setForeground(QColor(COLORS['red']))
                    tbl.setItem(r, c, item)
                # Action: Nop / Sua / Xem gop y
                if graded:
                    btns_spec = [('Xem góp ý', 'navy')]
                elif has_sub:
                    btns_spec = [('Sửa nộp', 'orange')]
                else:
                    btns_spec = [('Nộp bài', 'green')]
                cell, (btn,) = make_action_cell(btns_spec)
                tbl.setCellWidget(r, 6, cell)
                btn.clicked.connect(lambda ch, asg=dict(row): self._stu_dialog_submit(asg))
        # Tong width 35+220+180+130+100+75+100 = 840 (vua khit table 840px)
        for c, w in enumerate([35, 220, 180, 130, 100, 75, 100]):
            tbl.setColumnWidth(c, w)
        tbl.horizontalHeader().setStretchLastSection(False)

        # Wire search + filter (1 lan, idempotent)
        txt_s = page.findChild(QtWidgets.QLineEdit, 'txtStuAsgSearch')
        cbo = page.findChild(QtWidgets.QComboBox, 'cboStuAsgStatus')
        if txt_s and not getattr(self, '_stu_asg_filter_wired', False):
            txt_s.textChanged.connect(lambda _t: self._stu_filter_assignments())
            if cbo:
                cbo.currentIndexChanged.connect(lambda _i: self._stu_filter_assignments())
            self._stu_asg_filter_wired = True

    def _stu_filter_assignments(self):
        """Apply search + status filter len tblStuAssignments."""
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblStuAssignments')
        txt_s = page.findChild(QtWidgets.QLineEdit, 'txtStuAsgSearch')
        cbo = page.findChild(QtWidgets.QComboBox, 'cboStuAsgStatus')
        if not tbl:
            return
        # Search via norm() de bo dau - user go 'cham' match 'Đã chấm' / 'Bai tap' match 'Bài tập'
        kw = norm(txt_s.text() if txt_s else '')
        sel_status = cbo.itemData(cbo.currentIndex()) if cbo else None
        # Map filter id -> trang thai VN
        status_map_vn = {
            'pending': 'chưa nộp',
            'submitted': 'đã nộp',
            'graded': 'đã chấm',
            'overdue': 'quá hạn',
        }
        target_st = status_map_vn.get(sel_status) if sel_status else None
        for r in range(tbl.rowCount()):
            show = True
            # Search keyword (col 1=title, col 2=lớp+khóa) via norm
            if kw:
                hit = False
                for c in (1, 2):
                    it = tbl.item(r, c)
                    if it and kw in norm(it.text()):
                        hit = True; break
                if not hit:
                    show = False
            # Status filter (col 4)
            if show and target_st:
                it = tbl.item(r, 4)
                if it and target_st not in it.text().lower():
                    show = False
            tbl.setRowHidden(r, not show)

    def _stu_dialog_submit(self, asg):
        """Dialog HV nop bai (hoac xem feedback neu da cham)."""
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle(f'Bài tập: {asg.get("tieu_de", "")}')
        dlg.setFixedSize(640, 620)
        v = QtWidgets.QVBoxLayout(dlg)

        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        # Load chi tiet bai + bai HV da nop (neu co)
        full_asg = None
        my_sub = None
        try:
            full_asg = AssignmentService.get(asg['id']) or {}
            my_sub = AssignmentService.get_my_submission(asg['id'], hv_id)
        except Exception as e:
            print(f'[STU_ASG] load loi: {e}')
            full_asg = asg
            my_sub = None

        # Header info
        han_str = fmt_date(full_asg.get('han_nop'), fmt='%d/%m/%Y %H:%M', default='Không hạn')
        head = QtWidgets.QLabel(
            f'<b style="font-size:14px;">{full_asg.get("tieu_de", "")}</b><br>'
            f'<span style="color:#718096;">Lớp {full_asg.get("lop_id", "")} · '
            f'GV: {full_asg.get("ten_gv", "")} · Hạn: {han_str} · '
            f'Tối đa {full_asg.get("diem_toi_da", 10)} điểm</span>'
        )
        head.setStyleSheet('color: #2d3748; padding: 8px; background: #f7fafc; '
                           'border: 1px solid #e2e8f0; border-radius: 6px;')
        head.setWordWrap(True)
        v.addWidget(head)

        # Mo ta bai
        v.addWidget(QtWidgets.QLabel('<b>Đề bài:</b>'))
        desc = QtWidgets.QTextEdit()
        desc.setPlainText(full_asg.get('mo_ta', '') or '(GV chưa thêm mô tả)')
        desc.setReadOnly(True)
        desc.setFixedHeight(120)
        desc.setStyleSheet('background: #f7fafc;')
        v.addWidget(desc)

        # Bai cua HV
        v.addWidget(QtWidgets.QLabel('<b>Bài làm của bạn:</b>'))
        my_text = QtWidgets.QTextEdit()
        my_text.setPlaceholderText('Nhập bài làm vào đây (text). Sau này có thể upload file.')
        my_text.setFixedHeight(150)
        if my_sub and my_sub.get('noi_dung'):
            my_text.setPlainText(my_sub['noi_dung'])
        v.addWidget(my_text)

        # Feedback GV (neu co)
        graded = my_sub and my_sub.get('diem') is not None
        if graded:
            fb_box = QtWidgets.QFrame()
            fb_box.setStyleSheet('QFrame { background: #f0fdf4; border: 1px solid #86efac; border-radius: 6px; padding: 6px; }')
            fbv = QtWidgets.QVBoxLayout(fb_box)
            fbv.setContentsMargins(8, 6, 8, 6)
            diem_lbl = QtWidgets.QLabel(
                f'<b style="color:#166534;">✓ Điểm: {float(my_sub["diem"]):.1f} / {full_asg.get("diem_toi_da", 10)}</b>'
            )
            diem_lbl.setStyleSheet('background: transparent; border: none;')
            fbv.addWidget(diem_lbl)
            nx = my_sub.get('nhan_xet', '') or '(GV chưa ghi nhận xét)'
            nx_lbl = QtWidgets.QLabel(f'<b>Nhận xét:</b> {nx}')
            nx_lbl.setStyleSheet('color: #166534; background: transparent; border: none;')
            nx_lbl.setWordWrap(True)
            fbv.addWidget(nx_lbl)
            v.addWidget(fb_box)

        # Buttons
        btns = QtWidgets.QDialogButtonBox()
        if graded:
            btn_close = btns.addButton('Đóng', QtWidgets.QDialogButtonBox.RejectRole)
            btn_close.clicked.connect(dlg.reject)
            my_text.setReadOnly(True)
        else:
            btn_save = btns.addButton('Nộp bài', QtWidgets.QDialogButtonBox.AcceptRole)
            btn_cancel = btns.addButton('Huỷ', QtWidgets.QDialogButtonBox.RejectRole)
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
        v.addWidget(btns)

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        # Submit
        noi_dung = my_text.toPlainText().strip()
        if not noi_dung:
            msg_warn(self, 'Trống', 'Bài làm không được để trống.')
            return
        try:
            AssignmentService.submit(asg['id'], hv_id, noi_dung)
        except Exception as e:
            msg_warn(self, 'Lỗi nộp', api_error_msg(e))
            return
        msg_info(self, 'Thành công', f'Đã nộp bài "{full_asg.get("tieu_de", "")}". GV sẽ chấm sớm.')
        self._reload_stu_assignments(self.page_widgets[4])

    def _fill_review(self):
        # Sau khi them btnAssign vao PAGES idx 4, btnReview chuyen sang idx 5
        page = self.page_widgets[5]
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
            if not data:
                set_table_empty_state(
                    tbl, 'Chưa có dữ liệu giảng viên',
                    icon='⭐',
                    cta_text='📚 Xem khóa học',
                    cta_callback=lambda: self._on_nav(0))
            else:
                tbl.setRowCount(len(data))
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
                    cell, (btn,) = make_action_cell([('Đánh giá', 'navy')])
                    tbl.setCellWidget(r, 5, cell)
            for c, cw in enumerate([40, 195, 115, 80, 90, 120]):
                tbl.setColumnWidth(c, cw)
            tbl.horizontalHeader().setStretchLastSection(False)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)
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
        # search + filter - safe_connect tranh accumulation khi page reload
        # (truoc moi lan _fill_review chay them 1 handler -> nav qua lai N lan
        # se trigger filter N lan moi text change -> lag UI)
        txt_s = page.findChild(QtWidgets.QLineEdit, 'txtSearchReview')
        if txt_s:
            safe_connect(txt_s.textChanged,
                         lambda t: table_filter(tbl, t, cols=[1, 2]) if tbl else None)
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboDept')
        if cbo_d:
            safe_connect(cbo_d.currentIndexChanged, lambda: self._apply_review_filter())
        cbo_s = page.findChild(QtWidgets.QComboBox, 'cboSubject')
        if cbo_s:
            safe_connect(cbo_s.currentIndexChanged, lambda: self._apply_review_filter())

    def _apply_review_filter(self):
        page = self.page_widgets[5]  # btnReview moved to idx 5 sau khi insert btnAssign
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
            msg_warn(self, 'Đánh giá', f'Lưu đánh giá thất bại:\n{api_error_msg(e)}')

    def _fill_notifications(self):
        """Load notifs vao cache + render lan dau. Render thuc trong _render_notifications."""
        page = self.page_widgets[6]  # btnNotice moved to idx 6 sau khi insert btnAssign

        # Add search + filter controls vao headerBar 1 lan
        hb = page.findChild(QtWidgets.QFrame, 'headerBar')
        if hb and not hb.findChild(QtWidgets.QLineEdit, 'txtNotifSearch'):
            search = QtWidgets.QLineEdit(hb)
            search.setObjectName('txtNotifSearch')
            search.setGeometry(250, 12, 280, 32)
            search.setPlaceholderText('🔍 Tìm theo tiêu đề / nội dung...')
            search.setStyleSheet('QLineEdit { background: white; border: 1px solid #d2d6dc; '
                                  'border-radius: 6px; padding: 4px 12px; font-size: 12px; } '
                                  'QLineEdit:focus { border-color: #002060; }')
            search.show()
            search.textChanged.connect(lambda _t: self._render_notifications())

            cbo = QtWidgets.QComboBox(hb)
            cbo.setObjectName('cboNotifFilter')
            cbo.setGeometry(550, 12, 180, 32)
            cbo.setCursor(Qt.PointingHandCursor)
            cbo.addItem('Tất cả loại', None)
            cbo.addItem('🔴 Khẩn cấp', 'urgent')
            cbo.addItem('🟠 Cảnh báo', 'warning')
            cbo.addItem('🔵 Thông tin', 'info')
            cbo.setStyleSheet('QComboBox { background: white; border: 1px solid #d2d6dc; '
                               'border-radius: 6px; padding: 4px 10px; font-size: 12px; } '
                               'QComboBox:hover { border-color: #002060; } '
                               'QComboBox::drop-down { border: none; padding-right: 6px; }')
            cbo.show()
            cbo.currentIndexChanged.connect(lambda _i: self._render_notifications())

            # Counter label "X / Y thông báo" - shrink để chừa chỗ nut bulk delete
            lbl_cnt = QtWidgets.QLabel('— / —', hb)
            lbl_cnt.setObjectName('lblNotifCount')
            lbl_cnt.setGeometry(745, 18, 65, 24)
            lbl_cnt.setStyleSheet('color: #4a5568; font-size: 11px; font-weight: bold; '
                                   'background: #f7fafc; border: 1px solid #e2e8f0; '
                                   'border-radius: 6px; padding: 2px 4px;')
            lbl_cnt.setAlignment(Qt.AlignCenter)
            lbl_cnt.show()

            # Nut "Xoa tat ca" icon-only o goc phai
            btn_clear_all = QtWidgets.QPushButton('🗑', hb)
            btn_clear_all.setObjectName('btnClearAllNotif')
            btn_clear_all.setGeometry(820, 14, 38, 32)
            btn_clear_all.setCursor(Qt.PointingHandCursor)
            btn_clear_all.setToolTip('Xóa tất cả thông báo (chỉ xóa các thông báo đang hiển thị sau filter)')
            btn_clear_all.setStyleSheet(
                'QPushButton { background: white; color: #c53030; border: 1px solid #c53030; '
                'border-radius: 6px; font-size: 14px; font-weight: bold; } '
                'QPushButton:hover { background: #c53030; color: white; }'
            )
            btn_clear_all.clicked.connect(self._clear_all_notif)
            btn_clear_all.show()

        # An 6 card hardcode cua .ui (dung lam template thoi)
        for i in range(1, 7):
            c = page.findChild(QtWidgets.QFrame, f'card{i}')
            if c:
                c.hide()

        # Lay notifs tu API + cache. Filter notif HV da dismiss UI-only
        # (xem _delete_notif: khong goi API DELETE de tranh xoa broadcast notif)
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        self._stu_notif_cache = []
        if DB_AVAILABLE and hv_id:
            try:
                rows = NotificationService.get_for_student(hv_id) or []
                dismissed = getattr(self, '_stu_notif_dismissed', set())
                self._stu_notif_cache = [n for n in rows if n.get('id') not in dismissed]
            except Exception as e:
                print(f'[STU_NOTIF] API loi: {e}')

        self._render_notifications()

    def _render_notifications(self):
        """Re-render danh sach notif tu cache, ap dung search + filter."""
        page = self.page_widgets[6]
        sc = page.findChild(QtWidgets.QWidget, 'scrollContent')
        if not sc:
            return
        notifs = getattr(self, '_stu_notif_cache', []) or []

        # Apply filter loai
        page_hb = page.findChild(QtWidgets.QFrame, 'headerBar')
        cbo = page_hb.findChild(QtWidgets.QComboBox, 'cboNotifFilter') if page_hb else None
        sel_loai = cbo.itemData(cbo.currentIndex()) if cbo else None
        if sel_loai:
            notifs = [n for n in notifs if (n.get('loai') or 'info') == sel_loai]

        # Apply search keyword - dung norm() bo dau de user go 'thong bao' tim duoc
        # 'Thông báo' (truoc lower() khong strip dau -> miss diacritic match)
        search = page_hb.findChild(QtWidgets.QLineEdit, 'txtNotifSearch') if page_hb else None
        kw_raw = search.text().strip() if search else ''
        kw = norm(kw_raw)
        if kw:
            notifs = [n for n in notifs
                      if kw in norm(n.get('tieu_de', '') or '')
                      or kw in norm(n.get('noi_dung', '') or '')]

        # Update counter
        total = len(getattr(self, '_stu_notif_cache', []) or [])
        lbl_cnt = page_hb.findChild(QtWidgets.QLabel, 'lblNotifCount') if page_hb else None
        if lbl_cnt:
            lbl_cnt.setText(f'{len(notifs)} / {total}')

        # Xoa cac card dynamic + empty cu
        for old in sc.findChildren(QtWidgets.QFrame):
            if old.objectName().startswith('dynNotifCard'):
                old.setParent(None); old.deleteLater()
        old_empty = sc.findChild(QtWidgets.QLabel, 'lblNoNotif')
        if old_empty:
            old_empty.setParent(None); old_empty.deleteLater()

        if not notifs:
            empty = QtWidgets.QLabel('Không có thông báo phù hợp' if (kw or sel_loai)
                                       else 'Không có thông báo nào', sc)
            empty.setObjectName('lblNoNotif')
            empty.setGeometry(25, 20, 820, 80)
            empty.setStyleSheet(f'color: {COLORS["text_light"]}; font-size: 13px; padding: 20px; '
                                 f'background: white; border: 1px dashed #cbd5e0; border-radius: 8px;')
            empty.setAlignment(Qt.AlignCenter)
            empty.show()
            sc.setMinimumHeight(120)
            return

        color_map = {'urgent': '#c53030', 'warning': '#e8710a', 'info': '#002060'}
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

            # Title shrink width de chua chỗ cho nut Xoa o goc phai
            title_lbl = QtWidgets.QLabel(n.get('tieu_de', '') or '(Không tiêu đề)', card)
            title_lbl.setGeometry(20, 14, 720, 22)
            title_lbl.setStyleSheet('color: #1a1a2e; font-size: 14px; font-weight: bold; background: transparent; border: none;')
            title_lbl.show()

            # Nut An (X) o goc phai card - dismiss UI-only, khong xoa DB
            notif_id = n.get('id')
            if notif_id is not None:
                btn_del = QtWidgets.QPushButton('🗑', card)
                btn_del.setObjectName(f'btnDelNotif{i}')
                btn_del.setGeometry(card_w - 42, 12, 26, 26)
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setToolTip('Ẩn thông báo này khỏi danh sách (HV khác vẫn nhận được)')
                btn_del.setStyleSheet(
                    'QPushButton { background: transparent; border: 1px solid transparent; '
                    'border-radius: 4px; font-size: 13px; color: #a0aec0; } '
                    'QPushButton:hover { background: #fee2e2; border-color: #c53030; color: #c53030; }'
                )
                btn_del.clicked.connect(
                    lambda ch, _id=notif_id, _td=n.get('tieu_de', ''): self._delete_notif(_id, _td)
                )
                btn_del.show()

            date_lbl = QtWidgets.QLabel(card)
            date_str = fmt_relative_date(n.get('ngay_tao'))
            full_ts = fmt_date(n.get('ngay_tao'), fmt='%d/%m/%Y %H:%M')
            src = n.get('tu_ten') or 'Hệ thống'
            date_lbl.setText(f'{date_str} • {src}')
            date_lbl.setToolTip(full_ts)
            date_lbl.setGeometry(20, 40, 400, 16)
            date_lbl.setStyleSheet('color: #718096; font-size: 11px; background: transparent; border: none;')
            date_lbl.show()

            content_lbl = QtWidgets.QLabel(n.get('noi_dung', '') or '', card)
            content_lbl.setGeometry(20, 62, 780, 32)
            content_lbl.setStyleSheet('color: #4a5568; font-size: 12px; background: transparent; border: none;')
            content_lbl.setWordWrap(True)
            content_lbl.show()

            card.show()
            y += card_h + gap

        sc.setMinimumHeight(y + 20)

    def _clear_all_notif(self):
        """Xoa tat ca thong bao dang hien thi (sau filter) - bulk delete."""
        # Lay danh sach notif sau filter (giong _render_notifications)
        page = self.page_widgets[6]
        page_hb = page.findChild(QtWidgets.QFrame, 'headerBar')
        cbo = page_hb.findChild(QtWidgets.QComboBox, 'cboNotifFilter') if page_hb else None
        sel_loai = cbo.itemData(cbo.currentIndex()) if cbo else None
        search = page_hb.findChild(QtWidgets.QLineEdit, 'txtNotifSearch') if page_hb else None
        # Dung norm() bo dau de target khop voi visible danh sach (deu render qua norm)
        kw = norm(search.text() if search else '')

        cache = getattr(self, '_stu_notif_cache', []) or []
        target = list(cache)
        if sel_loai:
            target = [n for n in target if (n.get('loai') or 'info') == sel_loai]
        if kw:
            target = [n for n in target
                      if kw in norm(n.get('tieu_de', '') or '')
                      or kw in norm(n.get('noi_dung', '') or '')]

        if not target:
            msg_warn(self, 'Không có gì để ẩn', 'Danh sách hiện tại đang trống.')
            return

        # Confirm voi count - msg dung 'an' (dismiss UI-only) thay vi 'xoa'
        # vi behavior la ẩn local, khong DELETE DB. Ẩn co the reset khi reload window.
        if not msg_confirm(self, 'Xác nhận ẩn tất cả',
                           f'Bạn có chắc muốn ẩn <b>{len(target)}</b> thông báo đang hiển thị?\n\n'
                           f'Thông báo sẽ ẩn khỏi danh sách của bạn (không xóa khỏi DB nên HV khác vẫn nhận được).'):
            return

        # Bulk dismiss UI-only (KHONG goi API DELETE - tranh xoa notif broadcast
        # khoi DB lam HV khac mat). Track set _stu_notif_dismissed cho reload.
        if not hasattr(self, '_stu_notif_dismissed'):
            self._stu_notif_dismissed = set()
        delete_ids = set()
        for n in target:
            nid = n.get('id')
            if not nid:
                continue
            self._stu_notif_dismissed.add(nid)
            delete_ids.add(nid)

        # Update cache
        self._stu_notif_cache = [n for n in cache if n.get('id') not in delete_ids]
        self._render_notifications()
        if hasattr(self, '_update_notif_badge'):
            self._update_notif_badge()

        msg_info(self, 'Đã ẩn', f'✓ Đã ẩn <b>{len(delete_ids)}</b> thông báo khỏi danh sách (không xóa khỏi DB).')

    def _delete_notif(self, notif_id, tieu_de=''):
        """An 1 thong bao khoi danh sach cua HV nay - dismiss UI-only.

        QUAN TRONG: Khong goi API delete vi notification la BROADCAST
        (GV/Admin gui den toan lop hoac toan he thong). Neu HV1 xoa thi
        DB DELETE -> HV2 mat luon notif chua doc -> bug.

        Chi xoa khoi cache local (_stu_notif_cache) + persist set 'da an'
        vao instance attr de re-fetch khong hien lai. Refresh page (F5)
        se reset. De-luu permanent can them bang notification_reads voi
        FK (notif_id, hv_id) - chua implement.
        """
        # Confirm bang msg_confirm thuong (khong dung msg_confirm_delete vi
        # text 'XOA' va 'KHONG THE HOAN TAC' khong dung voi dismiss UI-only)
        title_short = tieu_de[:40] if tieu_de else f'#{notif_id}'
        if not msg_confirm(self, 'Xác nhận ẩn',
                           f'Ẩn thông báo <b>"{title_short}"</b> khỏi danh sách của bạn?\n\n'
                           f'<i>Chỉ ẩn UI - HV khác vẫn nhận được thông báo này.</i>'):
            return
        # Track ID da dismiss trong session (reset khi reload)
        if not hasattr(self, '_stu_notif_dismissed'):
            self._stu_notif_dismissed = set()
        self._stu_notif_dismissed.add(notif_id)
        # Update cache local + re-render
        cache = getattr(self, '_stu_notif_cache', []) or []
        self._stu_notif_cache = [n for n in cache if n.get('id') != notif_id]
        self._render_notifications()
        if hasattr(self, '_update_notif_badge'):
            self._update_notif_badge()

    def _fill_profile(self):
        page = self.page_widgets[7]  # btnProfile moved to idx 7 sau khi insert btnAssign
        u = MOCK_USER
        # Dung .get() de tranh KeyError sau clear_session_state() (logout xoa het keys)
        # Bo cac field 'lop'/'khoa'/'nienkhoa'/'hedt' - khong relevant cho khoa ngoai khoa
        # (HV co the dang ky nhieu lop khac nhau, khong thuoc khoa nao co dinh)
        for attr, val in [('lblProfileName', u.get('name', '')),
                          ('lblProfileRole', 'Học viên'),
                          ('lblProfileAvatar', u.get('initials', '?')),
                          ('valMaSV', u.get('msv', '')),
                          ('valHoTen', u.get('name', '')),
                          ('valNgaySinh', u.get('ngaysinh', '')),
                          ('valGioiTinh', u.get('gioitinh', '')),
                          ('valLop', '—'),       # khong dung field nay nua
                          ('valKhoa', '—'),       # khong dung field nay nua
                          ('valNienKhoa', '—'),   # khong dung field nay nua
                          ('valHeDT', 'Khoá ngoại khoá')]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setText('' if val is None else str(val))
        for attr, val in [('txtEmail', u.get('email', '')),
                          ('txtPhone', u.get('sdt', '')),
                          ('txtAddress', u.get('diachi', ''))]:
            w = page.findChild(QtWidgets.QLineEdit, attr)
            if w:
                w.setText('' if val is None else str(val))

        btn_save = page.findChild(QtWidgets.QPushButton, 'btnSave')
        if btn_save:
            safe_connect(btn_save.clicked, self._save_profile)
        btn_cp = page.findChild(QtWidgets.QPushButton, 'btnChangePass')
        if btn_cp:
            safe_connect(btn_cp.clicked, self._change_pass)

        # Build/refresh card "Thong ke hoc tap" duoi contactCard (1 lan)
        self._build_stu_profile_stats(page)

    def _build_stu_profile_stats(self, page):
        """Card 'Thong ke hoc tap' o phia duoi profile (4 stat: lop / hoan thanh / hoc phi / GPA)."""
        # Cleanup old (de re-fill voi data moi neu user vao lai page)
        cleanup_banner(page, 'profileStatsCard')

        # Lay du lieu: classes + grades
        hv_id = MOCK_USER.get('id') or MOCK_USER.get('user_id')
        n_total = 0
        n_done = 0
        total_fee = 0
        gpa_list = []
        if DB_AVAILABLE and hv_id:
            try:
                cls = CourseService.get_classes_by_student(hv_id) or []
                for c in cls:
                    st = c.get('reg_status') or c.get('trang_thai') or ''
                    if st in ('paid', 'completed'):
                        n_total += 1
                        try:
                            total_fee += int(c.get('gia') or 0)
                        except (TypeError, ValueError):
                            pass
                    if st == 'completed':
                        n_done += 1
            except Exception as e:
                print(f'[STU_PROFILE] stats lop loi: {e}')
            try:
                grades = GradeService.get_grades_by_student(hv_id) or []
                for g in grades:
                    tk = g.get('tong_ket')
                    if tk is not None:
                        try:
                            gpa_list.append(float(tk))
                        except (TypeError, ValueError):
                            pass
            except Exception as e:
                print(f'[STU_PROFILE] stats GPA loi: {e}')
        gpa = (sum(gpa_list) / len(gpa_list)) if gpa_list else 0.0

        # Card
        card = QtWidgets.QFrame(page)
        card.setObjectName('profileStatsCard')
        card.setGeometry(445, 560, 400, 130)
        card.setStyleSheet('QFrame#profileStatsCard { background: white; '
                            'border: 1px solid #d2d6dc; border-radius: 10px; }')

        # Title
        lbl_t = QtWidgets.QLabel('📊 Thống kê học tập', card)
        lbl_t.setGeometry(20, 12, 360, 22)
        lbl_t.setStyleSheet('color: #1a1a2e; font-size: 14px; font-weight: bold; '
                             'background: transparent; border: none;')

        # 4 stat boxes (2x2)
        # Hang 1: y=42-78
        # Hang 2: y=85-121
        stats = [
            (20, 42, '📚 Lớp đăng ký', f'{n_total}', '#002060'),
            (210, 42, '✅ Hoàn thành', f'{n_done}', '#166534'),
            (20, 85, '💰 Tổng học phí', fmt_vnd(total_fee, suffix='đ'), '#c05621'),
            (210, 85, '⭐ Điểm TB', f'{gpa:.2f}/10' if gpa_list else '—', '#7c3aed'),
        ]
        for x, y, label, val, color in stats:
            cap = QtWidgets.QLabel(label, card)
            cap.setGeometry(x, y, 170, 14)
            cap.setStyleSheet(f'color: #4a5568; font-size: 10px; '
                               'background: transparent; border: none;')
            v = QtWidgets.QLabel(val, card)
            v.setGeometry(x, y + 14, 170, 22)
            v.setStyleSheet(f'color: {color}; font-size: 16px; font-weight: bold; '
                             'background: transparent; border: none;')

    def _save_profile(self):
        page = self.page_widgets[7]  # btnProfile idx 7
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
            msg_warn(self, 'Sai định dạng',
                     'Số điện thoại không hợp lệ. Phải bắt đầu 0 (10 số) hoặc +84 (11 số).')
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

    def _change_pass(self):
        show_change_password_dialog(self, MOCK_USER, lambda: MOCK_USER.get('id'))


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

        # F5/Ctrl+R: refresh trang hien tai
        install_refresh_shortcut(self)
        # Badge sidebar: pending DK qua han + lop chua co GV
        self._update_adm_badges()

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
        add_reload_button(sidebar, self)

        sep = QtWidgets.QFrame(sidebar)
        sep.setGeometry(15, 74, 200, 1)
        sep.setStyleSheet(f'background: {COLORS["border"]};')

        y = 86
        for i, (btn_name, icon_name, icon_file, label) in enumerate(ADMIN_MENU):
            btn = QtWidgets.QPushButton(label, sidebar)
            btn.setObjectName(btn_name)
            btn.setGeometry(10, y, 210, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(SIDEBAR_NORMAL)
            if i < 9:
                btn.setToolTip(f'{label}  ·  Ctrl+{i + 1}')
            else:
                btn.setToolTip(label)
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

        # Hop "Hom nay + Dot" - context-aware UX
        add_sidebar_context_widget(sidebar)

        sep2 = QtWidgets.QFrame(sidebar)
        sep2.setGeometry(15, 610, 200, 1)
        sep2.setStyleSheet(f'background: {COLORS["border"]};')

        adm_init = MOCK_ADMIN.get('initials') or 'AD'
        lbl_av = QtWidgets.QLabel(adm_init, sidebar)
        lbl_av.setGeometry(15, 625, 38, 38)
        lbl_av.setAlignment(Qt.AlignCenter)
        lbl_av.setStyleSheet(avatar_style(adm_init))

        lbl_name = QtWidgets.QLabel(MOCK_ADMIN.get('name') or 'Admin', sidebar)
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

        # Nut "Doi mat khau" cho admin (admin khong co page Profile)
        btn_chpw = QtWidgets.QPushButton('🔑 Đổi mật khẩu', sidebar)
        btn_chpw.setObjectName('btnAdmChangePass')
        btn_chpw.setGeometry(15, 670, 200, 24)
        btn_chpw.setCursor(Qt.PointingHandCursor)
        btn_chpw.setToolTip('Mở dialog đổi mật khẩu')
        btn_chpw.setStyleSheet(
            'QPushButton { background: transparent; color: #4a5568; border: 1px solid #d2d6dc; '
            'border-radius: 4px; font-size: 10px; font-weight: bold; } '
            'QPushButton:hover { background: #edf2f7; color: #002060; border-color: #002060; }'
        )
        btn_chpw.clicked.connect(self._adm_change_pass)

        # Badge "DK pending qua han" - nam o goc btnAdminStudent (idx 3)
        stu_idx = next((i for i, (n, _) in enumerate(ADMIN_PAGES) if n == 'btnAdminStudent'), 3)
        stu_y = 86 + stu_idx * 38
        self.lblAdmRegBadge = QtWidgets.QLabel('', sidebar)
        self.lblAdmRegBadge.setObjectName('lblAdmRegBadge')
        self.lblAdmRegBadge.setGeometry(192, stu_y + 4, 22, 18)
        self.lblAdmRegBadge.setAlignment(Qt.AlignCenter)
        self.lblAdmRegBadge.setStyleSheet(
            'QLabel { background: #c53030; color: white; border-radius: 9px; '
            'font-size: 10px; font-weight: bold; padding: 0px 4px; }'
        )
        self.lblAdmRegBadge.setToolTip('So dang ky pending qua 7 ngay - can xu ly')
        self.lblAdmRegBadge.hide()

        # Badge "Lop chua co GV" - nam o goc btnAdminClasses (idx 2)
        cls_idx = next((i for i, (n, _) in enumerate(ADMIN_PAGES) if n == 'btnAdminClasses'), 2)
        cls_y = 86 + cls_idx * 38
        self.lblAdmClsBadge = QtWidgets.QLabel('', sidebar)
        self.lblAdmClsBadge.setObjectName('lblAdmClsBadge')
        self.lblAdmClsBadge.setGeometry(192, cls_y + 4, 22, 18)
        self.lblAdmClsBadge.setAlignment(Qt.AlignCenter)
        self.lblAdmClsBadge.setStyleSheet(
            'QLabel { background: #d97706; color: white; border-radius: 9px; '
            'font-size: 10px; font-weight: bold; padding: 0px 4px; }'
        )
        self.lblAdmClsBadge.setToolTip('So lop chua phan cong giang vien')
        self.lblAdmClsBadge.hide()

        return sidebar

    def _adm_change_pass(self):
        """Dialog admin doi mat khau (admin khong co page profile rieng)."""
        def _resolve_id():
            return ((getattr(self, 'current_user', None) and self.current_user.id)
                    or MOCK_ADMIN.get('user_id') or MOCK_ADMIN.get('id'))
        show_change_password_dialog(self, MOCK_ADMIN, _resolve_id)

    def _load_page(self, ui_file):
        # ui_file=None -> tao QFrame trong de fill bang code (cho Quan ly lich hoc)
        if ui_file is None:
            content = QtWidgets.QFrame()
            content.setObjectName('contentArea')
            content.setFixedSize(1020, 720)
            content.setStyleSheet('QFrame#contentArea { background: #edf2f7; }')
            return content
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
                    self._fill_admin_schedule,  # NEW idx 8
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
        if not msg_confirm(self, 'Đăng xuất', 'Bạn có chắc muốn đăng xuất?'):
            return
        clear_session_state()
        self.close()
        self.app_ref.show_login()

    def _update_adm_badges(self):
        """Update sidebar Admin: dem DK pending qua han + lop chua co GV."""
        # Badge 1: pending DK qua 7 ngay
        if hasattr(self, 'lblAdmRegBadge'):
            set_sidebar_badge(self.lblAdmRegBadge, count_overdue_pending_registrations())

        # Badge 2: lop chua co GV (gv_id IS NULL) - chi dem lop o dot open/upcoming
        # de admin khong bi spam boi cac lop dot da closed
        n_no_gv = 0
        if DB_AVAILABLE and CourseService and hasattr(self, 'lblAdmClsBadge'):
            try:
                rows = CourseService.get_all_classes() or []
                active_sems = {sid for sid, st in MOCK_SEM_STATUS.items()
                                if st in ('open', 'upcoming')}
                for r in rows:
                    if r.get('gv_id'):
                        continue
                    sid = r.get('semester_id') or ''
                    # Khong sem hoac sem trong active set -> dem
                    if not sid or not MOCK_SEM_STATUS or sid in active_sems:
                        n_no_gv += 1
            except Exception as e:
                print(f'[ADM_CLS_BADGE] loi: {e}')
            set_sidebar_badge(self.lblAdmClsBadge, n_no_gv)

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
        # Update title voi greeting time-aware (truoc chi "Tong quan")
        title = page.findChild(QtWidgets.QLabel, 'lblPageTitle')
        if title:
            title.setText(f'Tổng quan · {time_greeting()}')

        # Them nut "Xuat tong ket PDF" o header (idempotent)
        header = page.findChild(QtWidgets.QFrame, 'headerBar')
        if header is not None and not header.findChild(QtWidgets.QPushButton, 'btnAdmExportSummary'):
            btn_pdf = QtWidgets.QPushButton('🖨 Xuất tổng kết', header)
            btn_pdf.setObjectName('btnAdmExportSummary')
            btn_pdf.setGeometry(835, 12, 160, 32)
            btn_pdf.setCursor(Qt.PointingHandCursor)
            btn_pdf.setToolTip('Xuất báo cáo tổng kết trung tâm ra PDF (4 stats + top classes + recent activity)')
            btn_pdf.setStyleSheet(
                f'QPushButton {{ background: {COLORS["gold"]}; color: white; border: none; '
                f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                f'QPushButton:hover {{ background: {COLORS["gold_hover"]}; }}'
            )
            btn_pdf.clicked.connect(self._adm_export_summary_pdf)
            btn_pdf.show()
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
                    val = stat_card_data.get(key)
                    # Cho lblStat4: lookup ten dep + canh bao neu khong co dot open
                    if lbl_name == 'lblStat4':
                        if val:
                            try:
                                sem = SemesterService.get(val) if SemesterService else None
                                if sem:
                                    val = sem.get('ten') or val
                            except Exception:
                                pass
                            w.setText(str(val))
                            w.setStyleSheet('')  # reset style neu truoc do bi cnh bao
                            # Reset font-size bi backend overide neu can
                        else:
                            # Khong co dot open -> canh bao
                            w.setText('Chưa mở')
                            w.setStyleSheet('color: #c05621; font-weight: bold; font-size: 18px;')
                    else:
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
                    t_str = fmt_relative_date(a.get('thoi_gian'))
                    color = COLORS['green'] if a.get('loai') == 'reg' else COLORS['gold']
                    recent_data.append((t_str, a.get('noi_dung', ''), color))
            except Exception as e:
                print(f'[STATS] recent loi: {e}')

        # top courses voi progress bar (visual chart - QProgressBar thay cho text %)
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblTopCourses')
        if tbl:
            data = top_data if top_data else []
            if not data:
                set_table_empty_state(tbl, 'Chưa có dữ liệu')
            else:
                tbl.setRowCount(len(data))
                tbl.clearSpans()
                for r, (name, cur, mx) in enumerate(data):
                    tbl.setItem(r, 0, QtWidgets.QTableWidgetItem(name))
                    item_ss = QtWidgets.QTableWidgetItem(f'{cur}/{mx}')
                    item_ss.setTextAlignment(Qt.AlignCenter)
                    tbl.setItem(r, 1, item_ss)
                    # Cot 2: QProgressBar thay text % (visual chart bar)
                    pct = int(cur / mx * 100) if mx else 0
                    color = COLORS['red'] if pct >= 90 else COLORS['gold'] if pct >= 60 else COLORS['green']
                    bar = QtWidgets.QProgressBar()
                    bar.setRange(0, 100)
                    bar.setValue(min(pct, 100))
                    bar.setFormat(f'{pct}%')
                    bar.setAlignment(Qt.AlignCenter)
                    bar.setStyleSheet(
                        f'QProgressBar {{ background: #edf2f7; border: 1px solid #d2d6dc; '
                        f'border-radius: 4px; height: 18px; text-align: center; '
                        f'color: #1a1a2e; font-size: 10px; font-weight: bold; }} '
                        f'QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}'
                    )
                    tbl.setCellWidget(r, 2, bar)
                for r in range(len(data)):
                    tbl.setRowHeight(r, 34)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setColumnWidth(0, 200)  # tang width cot ten cho de doc
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
            if not data:
                set_table_empty_state(tbl3, 'Chưa có dữ liệu')
            else:
                tbl3.setRowCount(len(data))
                for r, row in enumerate(data):
                    for c, val in enumerate(row):
                        item = QtWidgets.QTableWidgetItem(val)
                        item.setTextAlignment(Qt.AlignCenter if c > 0 else Qt.AlignLeft | Qt.AlignVCenter)
                        tbl3.setItem(r, c, item)
            tbl3.horizontalHeader().setStretchLastSection(True)
            for c, w in enumerate([200, 80, 80, 80]):
                tbl3.setColumnWidth(c, w)
            tbl3.verticalHeader().setVisible(False)

        # === 4 stat cards clickable -> jump to detail page (1 lan) ===
        # statCard1=HV idx 3, statCard2=Lop idx 2, statCard3=Audit idx 9, statCard4=Semester idx 6
        if not getattr(self, '_adm_stat_cards_wired', False):
            stat_to_idx = {
                'statCard1': (3, 'Đi đến trang Học viên'),
                'statCard2': (2, 'Đi đến trang Lớp'),
                'statCard3': (9, 'Đi đến trang Nhật ký hệ thống'),
                'statCard4': (6, 'Đi đến trang Đợt đăng ký'),
            }
            base_style = 'QFrame#{name} {{ background: white; border: 1px solid #d2d6dc; border-radius: 10px; }} QFrame#{name}:hover {{ border: 2px solid #002060; background: #f0f7ff; }}'
            for name, (idx, tip) in stat_to_idx.items():
                card = page.findChild(QtWidgets.QFrame, name)
                if not card:
                    continue
                card.setCursor(Qt.PointingHandCursor)
                card.setStyleSheet(base_style.format(name=name))
                card.setToolTip(tip)
                # Override mousePressEvent
                def _make_click(_idx):
                    def _click(ev):
                        if ev.button() == Qt.LeftButton:
                            self._on_nav(_idx)
                    return _click
                card.mousePressEvent = _make_click(idx)
            self._adm_stat_cards_wired = True

        # Render banner alert "Lop chua co GV"
        self._render_no_teacher_banner_admin(page)

    def _render_no_teacher_banner_admin(self, page):
        """Banner alert "X lop chua co GV" tren Admin dashboard.

        Dat o y=156 (giua stat cards va frames). Push topCoursesFrame + recentFrame
        xuong 42px neu show, reset neu khong.
        """
        # Cleanup banner cu
        cleanup_banner(page, 'noTeacherBannerAdmin')

        n_no_gv = 0
        sample_lops = []  # vài mã lớp đầu tiên de show trong tooltip
        if DB_AVAILABLE and CourseService:
            try:
                rows = CourseService.get_all_classes() or []
                # Chi dem lop dot open/upcoming - dot closed thi GV cu da xong, khong can canh bao
                active_sems = {sid for sid, st in MOCK_SEM_STATUS.items()
                                if st in ('open', 'upcoming')}
                for r in rows:
                    gv_id = r.get('gv_id')
                    ten_gv = r.get('ten_gv')
                    if gv_id is not None or ten_gv:
                        continue
                    sid = r.get('semester_id') or ''
                    if sid and MOCK_SEM_STATUS and sid not in active_sems:
                        continue  # dot da closed -> bo qua
                    n_no_gv += 1
                    if len(sample_lops) < 5:
                        sample_lops.append(r.get('ma_lop', '?'))
            except Exception as e:
                print(f'[ADM_DASH_NOGV] loi: {e}')

        # Helper push frames
        def _push_frames(shift_y):
            for fname in ('topCoursesFrame', 'recentFrame'):
                fr = page.findChild(QtWidgets.QFrame, fname)
                if fr:
                    g = fr.geometry()
                    new_y = 168 + shift_y
                    new_h = max(260 - shift_y, 140)
                    if g.y() != new_y or g.height() != new_h:
                        fr.setGeometry(g.x(), new_y, g.width(), new_h)

        if n_no_gv <= 0:
            _push_frames(0)
            return

        banner = QtWidgets.QFrame(page)
        banner.setObjectName('noTeacherBannerAdmin')
        banner.setGeometry(25, 156, 970, 38)
        banner.setStyleSheet(
            'QFrame#noTeacherBannerAdmin { background: #fef3c7; border: 1px solid #d97706; '
            'border-left: 4px solid #c05621; border-radius: 8px; }'
        )
        banner.setCursor(Qt.PointingHandCursor)

        sample_str = ', '.join(sample_lops[:3])
        if len(sample_lops) > 3:
            sample_str += f' +{n_no_gv - 3}'

        text = (f'⚠  <b>{n_no_gv}</b> lớp <b>chưa có giảng viên</b>'
                f'  ·  {sample_str}'
                f'  ·  <span style="color:#1e3a8a;">click để gán GV</span>')

        lbl = QtWidgets.QLabel(banner)
        lbl.setTextFormat(Qt.RichText)  # set TRUOC setText cho HTML parse dung
        lbl.setText(text)
        lbl.setGeometry(15, 0, 950, 38)
        lbl.setStyleSheet('color: #9a3412; font-size: 12px; background: transparent; border: none;')
        lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        lbl.setCursor(Qt.PointingHandCursor)
        banner.setToolTip(f'{n_no_gv} lớp chưa gán GV — click để vào trang Quản lý lớp')

        def _click(ev):
            if ev.button() == Qt.LeftButton:
                # btnAdminClasses idx 2
                self._on_nav(2)
        banner.mousePressEvent = _click
        lbl.mousePressEvent = _click
        banner.show()
        _push_frames(42)

    def _adm_export_summary_pdf(self):
        """Xuat bao cao tong ket trung tam PDF: 4 stats + top classes + recent activity."""
        try:
            from PyQt5.QtPrintSupport import QPrinter
            from PyQt5.QtGui import QTextDocument
        except ImportError:
            msg_warn(self, 'Lỗi', 'PyQt5.QtPrintSupport không có sẵn.')
            return
        if not (DB_AVAILABLE and StatsService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống.')
            return
        # Fetch all data
        try:
            overview = StatsService.admin_overview() or {}
            top_classes = StatsService.top_classes(limit=10) or []
            recent_acts = StatsService.recent_activity(limit=15) or []
            by_course = StatsService.by_course() or []
        except Exception as e:
            msg_warn(self, 'Lỗi tải', api_error_msg(e))
            return

        from datetime import datetime as _dt
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Xuất báo cáo tổng kết PDF',
            os.path.join(os.path.expanduser('~'), 'Desktop',
                         f'BaoCaoTongKet_EAUT_{_dt.now().strftime("%Y%m%d")}.pdf'),
            'PDF Files (*.pdf)'
        )
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'

        # Get current semester name
        cur_sem_id = overview.get('current_semester')
        cur_sem_name = '—'
        if cur_sem_id:
            try:
                sem = SemesterService.get(cur_sem_id) if SemesterService else None
                if sem:
                    cur_sem_name = sem.get('ten') or cur_sem_id
                else:
                    cur_sem_name = cur_sem_id
            except Exception:
                cur_sem_name = cur_sem_id

        # Build top classes rows
        top_rows = []
        for i, c in enumerate(top_classes, 1):
            zebra = '#f7fafc' if i % 2 == 0 else 'white'
            siso_cur = c.get('siso_hien_tai', 0)
            siso_max = c.get('siso_max', 0)
            ty_le = int(c.get('ty_le', 0) or 0)
            color = '#991b1b' if ty_le >= 95 else ('#92400e' if ty_le >= 70 else '#166534')
            top_rows.append(f'''
                <tr style="background: {zebra};">
                    <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center;">{i}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0; font-weight: bold;">{c.get('ma_lop', '—')}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0;">{c.get('ten_mon', '—')}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center;">{siso_cur}/{siso_max}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center; color: {color}; font-weight: bold;">{ty_le}%</td>
                </tr>
            ''')

        # Build recent activity rows
        act_rows = []
        for i, a in enumerate(recent_acts, 1):
            zebra = '#f7fafc' if i % 2 == 0 else 'white'
            ngay = fmt_date(a.get('thoi_gian'), fmt='%d/%m/%Y %H:%M')
            loai = a.get('loai', '')
            loai_label = 'Đăng ký' if loai == 'reg' else ('Thanh toán' if loai == 'pay' else loai)
            loai_color = '#1e3a8a' if loai == 'reg' else '#166534'
            act_rows.append(f'''
                <tr style="background: {zebra};">
                    <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center;">{i}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center;">{ngay}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0; color: {loai_color}; font-weight: bold;">{loai_label}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0;">{a.get('noi_dung', '—')}</td>
                </tr>
            ''')

        # Build by_course rows (top 10)
        course_rows = []
        for i, c in enumerate(by_course[:10], 1):
            zebra = '#f7fafc' if i % 2 == 0 else 'white'
            course_rows.append(f'''
                <tr style="background: {zebra};">
                    <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center;">{i}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0; font-weight: bold;">{c.get('ma_mon', '—')}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0;">{c.get('ten_mon', '—')}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center;">{c.get('so_lop', 0)}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center; font-weight: bold; color: #c05621;">{c.get('tong_hv', 0)}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center;">{c.get('so_dang_ky', 0)}</td>
                </tr>
            ''')

        admin_name = MOCK_ADMIN.get('name', '—')

        html = f'''
        <html><head><meta charset="utf-8"></head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e;">
        <div style="text-align: center; border-bottom: 3px solid #002060; padding-bottom: 12px; margin-bottom: 16px;">
            <h1 style="color: #002060; margin: 0; font-size: 22px;">TRUNG TÂM NGOẠI KHÓA EAUT</h1>
            <p style="margin: 4px 0; color: #4a5568; font-size: 11px;">
                Km 23, QL5, Trưng Trắc, Văn Lâm, Hưng Yên · Hotline: 024.3999.1111
            </p>
        </div>

        <h2 style="text-align: center; color: #c05621; margin: 0 0 4px 0;">BÁO CÁO TỔNG KẾT TRUNG TÂM</h2>
        <p style="text-align: center; color: #4a5568; font-size: 12px; margin: 0 0 16px 0;">
            Đợt hiện tại: <b>{cur_sem_name}</b> · Cập nhật: <b>{_dt.now().strftime('%d/%m/%Y %H:%M')}</b>
        </p>

        <h3 style="color: #002060; margin: 12px 0 6px 0;">📊 Tổng quan</h3>
        <table cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 16px;">
            <tr style="background: #002060; color: white; text-align: center;">
                <th style="padding: 12px; border: 1px solid #002060;">Tổng học viên</th>
                <th style="padding: 12px; border: 1px solid #002060;">Tổng lớp</th>
                <th style="padding: 12px; border: 1px solid #002060;">Tổng đăng ký</th>
                <th style="padding: 12px; border: 1px solid #002060;">Đợt hiện tại</th>
            </tr>
            <tr style="text-align: center;">
                <td style="padding: 14px; border: 1px solid #e2e8f0; font-size: 22px; color: #002060; font-weight: bold;">{overview.get('total_students', 0)}</td>
                <td style="padding: 14px; border: 1px solid #e2e8f0; font-size: 22px; color: #166534; font-weight: bold;">{overview.get('total_classes', 0)}</td>
                <td style="padding: 14px; border: 1px solid #e2e8f0; font-size: 22px; color: #c05621; font-weight: bold;">{overview.get('total_registrations', 0)}</td>
                <td style="padding: 14px; border: 1px solid #e2e8f0; font-size: 16px; color: #1a4480;"><b>{cur_sem_name}</b></td>
            </tr>
        </table>

        <h3 style="color: #002060; margin: 12px 0 6px 0;">🏆 Top {len(top_classes)} lớp đông học viên nhất</h3>
        <table cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 16px;">
            <thead><tr style="background: #002060; color: white;">
                <th style="padding: 6px; border: 1px solid #002060; width: 5%;">#</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 14%;">Mã lớp</th>
                <th style="padding: 6px; border: 1px solid #002060;">Khóa học</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 14%;">Sĩ số</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 12%;">Tỷ lệ</th>
            </tr></thead>
            <tbody>{''.join(top_rows) if top_rows else '<tr><td colspan="5" style="text-align:center; padding: 12px; color: #a0aec0;">(không có)</td></tr>'}</tbody>
        </table>

        <h3 style="color: #002060; margin: 12px 0 6px 0;">📚 Phân bổ theo khóa học</h3>
        <table cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 16px;">
            <thead><tr style="background: #002060; color: white;">
                <th style="padding: 6px; border: 1px solid #002060; width: 5%;">#</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 12%;">Mã KH</th>
                <th style="padding: 6px; border: 1px solid #002060;">Tên khóa học</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 10%;">Số lớp</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 12%;">Tổng HV</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 12%;">Đăng ký</th>
            </tr></thead>
            <tbody>{''.join(course_rows) if course_rows else '<tr><td colspan="6" style="text-align:center; padding: 12px; color: #a0aec0;">(không có)</td></tr>'}</tbody>
        </table>

        <h3 style="color: #002060; margin: 12px 0 6px 0;">📋 Hoạt động gần đây ({len(recent_acts)} dòng)</h3>
        <table cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 10px;">
            <thead><tr style="background: #002060; color: white;">
                <th style="padding: 6px; border: 1px solid #002060; width: 5%;">#</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 18%;">Thời gian</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 14%;">Loại</th>
                <th style="padding: 6px; border: 1px solid #002060;">Nội dung</th>
            </tr></thead>
            <tbody>{''.join(act_rows) if act_rows else '<tr><td colspan="4" style="text-align:center; padding: 12px; color: #a0aec0;">(không có)</td></tr>'}</tbody>
        </table>

        <div style="margin-top: 30px; display: flex; justify-content: flex-end;">
            <div style="text-align: center; width: 40%;">
                <p style="color: #4a5568; font-size: 11px;">Hà Nội, ngày {_dt.now().day}/{_dt.now().month}/{_dt.now().year}</p>
                <p style="margin-top: 4px;"><b>Quản trị viên</b></p>
                <p style="font-size: 10px; color: #718096; font-style: italic;">(ký, họ tên)</p>
                <p style="margin-top: 50px;"><b>{admin_name}</b></p>
            </div>
        </div>
        </body></html>
        '''
        try:
            doc = _make_vn_textdoc(html)
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
            doc.print_(printer)
            msg_info(self, 'Đã xuất PDF', f'Báo cáo tổng kết đã lưu:\n{path}')
        except Exception as e:
            print(f'[ADM_SUMMARY] loi: {e}')
            msg_warn(self, 'Lỗi xuất PDF', f'Không xuất được:\n{e}')

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
                    a = agg_by_ma_mon.setdefault(ma, {'cur': 0, 'mx': 0, 'n': 0,
                                                      'gv': set(), 'lich': set(),
                                                      'buoi': set()})
                    a['cur'] += int(cls.get('siso_hien_tai') or 0)
                    a['mx'] += int(cls.get('siso_max') or 0)
                    a['n'] += 1
                    if cls.get('ten_gv'): a['gv'].add(cls['ten_gv'])
                    if cls.get('lich'): a['lich'].add(cls['lich'])
                    sb = int(cls.get('so_buoi') or 0)
                    if sb > 0: a['buoi'].add(sb)
                data = []
                for c in courses:
                    a = agg_by_ma_mon.get(c['ma_mon'], {})
                    # so_buoi: neu cac lop cua mon co cung so_buoi -> hien so do.
                    # Khac nhau -> hien khoang (vd '20-24'). Khong co lop -> '—'
                    buoi_set = a.get('buoi', set())
                    if not buoi_set:
                        sb_disp = '—'
                    elif len(buoi_set) == 1:
                        sb_disp = str(next(iter(buoi_set)))
                    else:
                        sb_disp = f'{min(buoi_set)}-{max(buoi_set)}'
                    data.append([
                        c['ma_mon'], c['ten_mon'], sb_disp,
                        ', '.join(sorted(a.get('gv', set()))) or '—',
                        ', '.join(sorted(a.get('lich', set()))) or '—',
                        a.get('cur', 0), a.get('mx', 40) or 40,
                        c.get('mo_ta', '') or '',  # idx 7: mo_ta cho tooltip
                    ])
            except Exception as e:
                print(f'[ADMIN_COURSES] API loi: {e}')
        if not data:
            data = []  # khong co data -> empty table
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdminCourses')
        if tbl:
            tbl.setRowCount(len(data))
            for r, row in enumerate(data):
                # row[7] = mo_ta (cho tooltip)
                mo_ta = row[7] if len(row) > 7 else ''
                tooltip = f'<b>{row[1]}</b><br>{mo_ta}' if mo_ta else None
                for c in range(5):
                    item = QtWidgets.QTableWidgetItem(str(row[c]))
                    # Cot 0 (Ma KH) + cot 2 (So buoi) center align
                    if c in (0, 2):
                        item.setTextAlignment(Qt.AlignCenter)
                    if tooltip:
                        item.setToolTip(tooltip)
                    tbl.setItem(r, c, item)
                # si so = text mau
                cur, mx = row[5], row[6]
                pct = int(cur / mx * 100) if mx else 0
                item_ss = QtWidgets.QTableWidgetItem(f'{cur}/{mx}')
                item_ss.setTextAlignment(Qt.AlignCenter)
                color = COLORS['red'] if pct >= 90 else COLORS['gold'] if pct >= 60 else COLORS['green']
                item_ss.setForeground(QColor(color))
                if tooltip: item_ss.setToolTip(tooltip)
                tbl.setItem(r, 5, item_ss)
                # thao tac - pattern chuan
                cell, (btn_edit, btn_del) = make_action_cell([('Sửa', 'navy'), ('Xóa', 'red')])
                tbl.setCellWidget(r, 6, cell)
                btn_edit.clicked.connect(lambda ch, ma=row[0], nm=row[1]: self._admin_edit_course(ma, nm))
                btn_del.clicked.connect(lambda ch, ma=row[0], nm=row[1], t=tbl: self._admin_del_row(t, ma, nm, 'khóa học'))
            tbl.horizontalHeader().setStretchLastSection(True)
            # Col 2 (So buoi) tang 30 -> 75: header 'Số buổi' co dau khong vua 30px
            for c, cw in enumerate([70, 180, 75, 140, 130, 110, 150]):
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
        # Them nut Bulk import Khoa hoc CSV (idempotent)
        if not page.findChild(QtWidgets.QPushButton, 'btnImportCoursesCSV'):
            btn_imp = QtWidgets.QPushButton('📥 Import CSV', page)
            btn_imp.setObjectName('btnImportCoursesCSV')
            if btn_add:
                geo = btn_add.geometry()
                btn_imp.setGeometry(geo.x() - 145, geo.y(), 135, geo.height())
            else:
                btn_imp.setGeometry(700, 18, 135, 32)
            btn_imp.setCursor(Qt.PointingHandCursor)
            btn_imp.setToolTip('Import nhiều Khóa học từ file CSV (cột: ma_mon,ten_mon,mo_ta)')
            btn_imp.setStyleSheet(
                f'QPushButton {{ background: white; color: {COLORS["navy"]}; border: 1px solid {COLORS["navy"]}; '
                f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                f'QPushButton:hover {{ background: {COLORS["navy"]}; color: white; }}'
            )
            btn_imp.clicked.connect(self._admin_import_courses_csv)
            btn_imp.show()

    def _admin_import_courses_csv(self):
        """Import nhieu Khoa hoc tu CSV. Header: ma_mon,ten_mon,mo_ta"""
        import csv as _csv
        path, _ext = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Chọn file CSV danh sách khóa học',
            os.path.join(os.path.expanduser('~'), 'Desktop'),
            'CSV Files (*.csv)'
        )
        if not path:
            return
        rows = []
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = _csv.DictReader(f)
                for r in reader:
                    rows.append({k.strip(): (v or '').strip() for k, v in r.items()})
        except Exception as e:
            msg_warn(self, 'Lỗi đọc file', f'Không đọc được CSV:\n{e}')
            return
        if not rows:
            msg_warn(self, 'Trống', 'File CSV không có dòng nào (cần header dòng đầu).')
            return
        required = {'ma_mon', 'ten_mon'}
        missing = required - set(rows[0].keys())
        if missing:
            msg_warn(self, 'Thiếu cột',
                     f'Thiếu cột bắt buộc: {missing}.\n\nHeader chuẩn: ma_mon,ten_mon,mo_ta')
            return

        # Preview dialog
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle(f'Import khóa học - {len(rows)} dòng')
        dlg.setFixedSize(820, 500)
        v = QtWidgets.QVBoxLayout(dlg)
        head = QtWidgets.QLabel(
            f'<b>File:</b> {os.path.basename(path)}<br>'
            f'<b>Số dòng:</b> {len(rows)} khóa · Bấm <b>Import</b> để bắt đầu.<br>'
            f'<i style="color:#718096; font-size:11px;">Khóa nào lỗi (vd ma_mon trùng) sẽ skip + báo cuối.</i>'
        )
        head.setWordWrap(True)
        head.setStyleSheet('background:#edf2f7; padding:10px; border-radius:6px; font-size:12px;')
        v.addWidget(head)

        tbl = QtWidgets.QTableWidget()
        cols = ['#', 'Mã môn', 'Tên môn', 'Mô tả']
        tbl.setColumnCount(len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setRowCount(min(len(rows), 100))
        for r, row in enumerate(rows[:100]):
            items = [str(r + 1), row.get('ma_mon', ''), row.get('ten_mon', ''),
                     row.get('mo_ta', '') or '—']
            for c, val in enumerate(items):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(str(val)))
        for c, w in enumerate([35, 100, 200, 440]):
            tbl.setColumnWidth(c, w)
        if len(rows) > 100:
            head.setText(head.text() + f'<br><b style="color:#c05621;">⚠ Hiển thị 100/{len(rows)} dòng đầu</b>')
        v.addWidget(tbl)

        btns = QtWidgets.QDialogButtonBox()
        btns.addButton(f'⬆ Import {len(rows)} khóa', QtWidgets.QDialogButtonBox.AcceptRole)
        btns.addButton('Huỷ', QtWidgets.QDialogButtonBox.RejectRole)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        v.addWidget(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        if not (DB_AVAILABLE and CourseService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống.')
            return

        # Bulk loop
        success = 0
        failed = []
        for i, row in enumerate(rows, 1):
            try:
                ma_mon = row.get('ma_mon', '').strip()
                ten_mon = row.get('ten_mon', '').strip()
                if not ma_mon or not ten_mon:
                    raise ValueError('ma_mon / ten_mon trống')
                CourseService.create_course(
                    ma_mon=ma_mon,
                    ten_mon=ten_mon,
                    mo_ta=row.get('mo_ta') or '',
                )
                success += 1
            except Exception as e:
                err_msg = str(e)
                if '\n' in err_msg:
                    err_msg = err_msg.split('\n')[-1].strip() or err_msg[:200]
                failed.append({'row': i, 'ma_mon': row.get('ma_mon', '?'), 'error': err_msg[:200]})

        # Refresh + reload
        try:
            _refresh_cache()
        except Exception:
            pass
        self.pages_filled[1] = False
        self._fill_admin_courses()

        if not failed:
            msg_info(self, 'Thành công',
                     f'✓ Đã import <b>{success}/{len(rows)}</b> khóa học thành công!')
        else:
            err_lines = [f'• Dòng {f["row"]} (môn {f["ma_mon"]}): {f["error"]}' for f in failed[:15]]
            extra = '' if len(failed) <= 15 else f'\n... và {len(failed)-15} lỗi nữa'
            msg_warn(self, 'Hoàn tất với lỗi',
                     f'Thành công: <b>{success}/{len(rows)}</b><br>'
                     f'Lỗi: <b>{len(failed)}</b><br><br>'
                     f'<pre style="font-size:10px;">' + '\n'.join(err_lines) + extra + '</pre>')

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
        dlg.setWindowTitle('Thêm khóa học')
        dlg.setFixedSize(440, 380)
        form = QtWidgets.QFormLayout(dlg)
        txt_code = QtWidgets.QLineEdit()
        txt_code.setPlaceholderText('VD: IT001')
        txt_name = QtWidgets.QLineEdit()
        txt_name.setPlaceholderText('VD: Lập trình Python cơ bản')
        txt_tc = QtWidgets.QLineEdit('3')
        txt_gv = QtWidgets.QLineEdit()
        # Mo ta thuc - QTextEdit cho phep multi-line
        txt_desc = QtWidgets.QTextEdit()
        txt_desc.setFixedHeight(90)
        txt_desc.setPlaceholderText('Mô tả ngắn về khoá học (đối tượng, kỹ năng, ứng dụng)...')
        form.addRow('Mã khóa:', txt_code)
        form.addRow('Tên khóa:', txt_name)
        form.addRow('Số buổi:', txt_tc)
        form.addRow('GV phụ trách:', txt_gv)
        form.addRow('Mô tả:', txt_desc)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        txt_code.setFocus()  # auto-focus first field
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not txt_code.text().strip() or not txt_name.text().strip():
            msg_warn(self, 'Thiếu', 'Mã khóa và tên môn không được trống')
            return
        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        new_code = txt_code.text().upper().strip()
        new_name = txt_name.text().strip()
        # Mo ta: dung text user nhap (multi-line). Fallback format cu neu rong.
        desc_text = txt_desc.toPlainText().strip()
        if not desc_text:
            desc_text = f'Số buổi: {txt_tc.text() or 3}'
            if txt_gv.text().strip():
                desc_text += f'. GV: {txt_gv.text().strip()}'
        # Goi API TRUOC khi update UI
        try:
            CourseService.create_course(
                ma_mon=new_code,
                ten_mon=new_name,
                mo_ta=desc_text,
            )
        except Exception as e:
            print(f'[ADM_ADD_COURSE] DB loi: {e}')
            msg_warn(self, 'Không thêm được', api_error_msg(e))
            return
        # DB OK -> refresh cache + re-fill bang. Truoc append + insertRow manual
        # voi vals khong dong nhat (txt_tc/txt_gv chi dung trong mo_ta fallback,
        # khong phai field thuc cua course) -> bang hien sai sau add
        _refresh_cache()
        self.pages_filled[1] = False
        self._fill_admin_courses()
        self.pages_filled[1] = True
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

        # Fetch mo_ta hien tai tu API (table chi luu 4 col, mo_ta o DB)
        cur_mo_ta = ''
        if DB_AVAILABLE:
            try:
                course_full = CourseService.get_course(ma) or {}
                cur_mo_ta = course_full.get('mo_ta', '') or ''
            except Exception as e:
                print(f'[ADM_EDIT_COURSE] fetch loi: {e}')

        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle(f'Sửa khóa học - {ma}')
        dlg.setFixedSize(440, 440)
        form = QtWidgets.QFormLayout(dlg)
        txt_code = QtWidgets.QLineEdit(tbl.item(target_row, 0).text() if tbl.item(target_row, 0) else ma)
        txt_code.setReadOnly(True)  # Khong cho sua ma_mon (la PK)
        txt_code.setStyleSheet('background: #f7fafc; color: #718096;')
        txt_name = QtWidgets.QLineEdit(tbl.item(target_row, 1).text() if tbl.item(target_row, 1) else nm)
        txt_tc = QtWidgets.QLineEdit(tbl.item(target_row, 2).text() if tbl.item(target_row, 2) else '3')
        txt_gv = QtWidgets.QLineEdit(tbl.item(target_row, 3).text() if tbl.item(target_row, 3) else '')
        txt_lich = QtWidgets.QLineEdit(tbl.item(target_row, 4).text() if tbl.item(target_row, 4) else '')
        # Mo ta: pre-fill tu DB
        txt_desc = QtWidgets.QTextEdit()
        txt_desc.setFixedHeight(100)
        txt_desc.setPlainText(cur_mo_ta)
        txt_desc.setPlaceholderText('Mô tả khoá học...')
        form.addRow('Mã khóa:', txt_code)
        form.addRow('Tên khóa:', txt_name)
        form.addRow('Số buổi:', txt_tc)
        form.addRow('GV phụ trách:', txt_gv)
        form.addRow('Lịch học:', txt_lich)
        form.addRow('Mô tả:', txt_desc)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        txt_name.setFocus()  # focus ten (ma_mon read-only)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not txt_name.text().strip():
            msg_warn(self, 'Thiếu', 'Tên khoá học không được trống')
            return
        new_name = txt_name.text().strip()

        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # mo_ta: dung text user nhap, fallback metadata neu rong
        new_desc = txt_desc.toPlainText().strip()
        if not new_desc:
            new_desc = f'Số buổi: {txt_tc.text() or 3}'
            if txt_gv.text().strip():
                new_desc += f'. GV: {txt_gv.text().strip()}'
            if txt_lich.text().strip():
                new_desc += f'. Lịch: {txt_lich.text().strip()}'
        try:
            CourseService.update_course(ma, ten_mon=new_name, mo_ta=new_desc)
        except Exception as e:
            print(f'[ADM_EDIT_COURSE] loi: {e}')
            msg_warn(self, 'Không lưu được', api_error_msg(e))
            return

        # DB OK -> refresh cache + re-fill bang (truoc setItem manual khong update
        # cot 'So buoi' aggregate tu cac lop -> bang hien stale)
        _refresh_cache()
        self.pages_filled[1] = False
        self._fill_admin_courses()
        self.pages_filled[1] = True
        msg_info(self, 'Đã cập nhật', f'Đã lưu thay đổi cho {ma}')

    def _admin_del_row(self, tbl, ma, nm, loai):
        # Pre-check: lookup so item lien quan de canh bao truoc khi xoa
        related = ''
        try:
            if loai == 'khóa học' and DB_AVAILABLE:
                # Khoa hoc co bao nhieu lop?
                classes = CourseService.get_all_classes() or []
                cnt = sum(1 for c in classes if c.get('ma_mon') == ma)
                if cnt > 0:
                    related = f'⚠ Khóa học này hiện có {cnt} lớp tham chiếu. Xóa sẽ thất bại nếu chưa xóa các lớp.'
            elif loai == 'lớp' and DB_AVAILABLE:
                # Lop co bao nhieu HV dang ky?
                cls = CourseService.get_class(ma) or {}
                siso = int(cls.get('siso_hien_tai') or 0)
                if siso > 0:
                    related = f'⚠ Lớp này đang có {siso} học viên đăng ký. Xóa sẽ ảnh hưởng dữ liệu của họ.'
            elif loai in ('học viên', 'giảng viên', 'nhân viên'):
                related = '⚠ Tất cả dữ liệu liên quan (đăng ký, điểm, đánh giá...) sẽ bị xóa cascade.'
        except Exception:
            pass  # Pre-check fail thi van cho confirm thuong

        if not msg_confirm_delete(self, loai, ma, nm, related):
            return
        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # Ghi DB - PHAI thanh cong moi xoa UI. Khong silent catch nua.
        try:
            if loai == 'khóa học':
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

        # DB delete OK - refresh cache neu xoa khoa/lop (anh huong MOCK_COURSES/CLASSES)
        # Cac places khac (vd Adm add_class combo) doc tu cache nay - neu khong refresh
        # se hien khoa/lop da xoa
        if loai in ('khóa học', 'lớp'):
            _refresh_cache()
        # xoa UI
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
            # Col 6 (Thao tac) 150 -> 160 cho 'Chi tiết' (85px) + 'Xóa' (55px) + spacing 6
            for c, cw in enumerate([75, 140, 100, 95, 90, 100, 160]):
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
        # cbo_d (Khoa): bo loc theo khoa vi students table KHONG co cot khoa
        # (khoa la field cua teachers/employees). Truoc cho admin chon
        # 'CNTT'/'Toán'/'Ngoại ngữ' nhung col 3 cua row la hardcode '—' ->
        # filter khong bao gio match -> chon khoa thi an HET hv.
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboFilterDeptSt')
        if cbo_d:
            cbo_d.hide()  # An hoan toan thay vi hien filter ma khong work
        # Lop combo: populate tu cac lop thuc te HV dang ky (khong hardcode
        # 'CNTT-K20A'). Lay unique tu cot 2 (cac_lop) cua data.
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboFilterClass')
        if cbo_c:
            cbo_c.clear()
            cbo_c.addItem('Tất cả lớp')
            # Lay danh sach lop tu MOCK_CLASSES (chuan, da pop tu API)
            for cls in MOCK_CLASSES:
                cbo_c.addItem(cls[0])  # ma_lop
            safe_connect(cbo_c.currentIndexChanged, lambda: self._admin_filter_students())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddStudent')
        if btn_add:
            safe_connect(btn_add.clicked, self._admin_add_student)
        # Them nut Bulk import CSV (idempotent) - attach to page, place ben canh btn Add
        if not page.findChild(QtWidgets.QPushButton, 'btnImportCSV'):
            btn_import = QtWidgets.QPushButton('📥 Import CSV', page)
            btn_import.setObjectName('btnImportCSV')
            # Tinh vi tri ben canh btn_add (cung row)
            if btn_add:
                geo = btn_add.geometry()
                btn_import.setGeometry(geo.x() - 145, geo.y(), 135, geo.height())
            else:
                btn_import.setGeometry(700, 18, 135, 32)
            btn_import.setCursor(Qt.PointingHandCursor)
            btn_import.setToolTip('Import nhiều HV cùng lúc từ file CSV (cột: username,password,full_name,msv,...)')
            btn_import.setStyleSheet(
                f'QPushButton {{ background: white; color: {COLORS["navy"]}; border: 1px solid {COLORS["navy"]}; '
                f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                f'QPushButton:hover {{ background: {COLORS["navy"]}; color: white; }}'
            )
            btn_import.clicked.connect(self._admin_import_students_csv)
            btn_import.show()

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
        if not tbl:
            return
        # Strip dau khi so sanh - cac_lop la chuoi 'IT001-A, IT002-B' nen
        # check substring de khop ma_lop. Bo cbo_d (khoa) - student khong co
        # khoa col, filter cu luon hide het rows
        lop_sel = _status_normalize(cbo_c.currentText()) if cbo_c and cbo_c.currentIndex() > 0 else None
        for r in range(tbl.rowCount()):
            it_lop = tbl.item(r, 2)
            show = True
            if lop_sel and it_lop and lop_sel not in _status_normalize(it_lop.text()):
                show = False
            tbl.setRowHidden(r, not show)

    def _admin_import_students_csv(self):
        """Dialog Admin import nhieu HV cung luc tu file CSV.

        Format CSV (header bat buoc): username,password,full_name,msv,email,sdt,gioitinh,ngaysinh,diachi
        Encoding: utf-8 hoac utf-8-sig (Excel save)
        """
        # Step 1: chon file
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Chọn file CSV để import', os.path.expanduser('~/Desktop'),
            'CSV Files (*.csv)'
        )
        if not path:
            return

        # Step 2: parse CSV
        try:
            import csv
            with open(path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            msg_warn(self, 'Lỗi đọc file', f'Không đọc được CSV:\n{e}')
            return
        if not rows:
            msg_warn(self, 'Trống', 'File CSV không có dữ liệu.')
            return
        # Validate required cols
        required = {'username', 'password', 'full_name', 'msv'}
        missing = required - set(rows[0].keys())
        if missing:
            msg_warn(self, 'Thiếu cột',
                     f'CSV thiếu cột bắt buộc: {", ".join(sorted(missing))}\n\n'
                     'Header CSV chuẩn:\n'
                     'username,password,full_name,msv,email,sdt,gioitinh,ngaysinh,diachi')
            return

        # Step 3: dialog preview + confirm
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle(f'Import CSV - {len(rows)} dòng')
        dlg.setFixedSize(880, 540)
        v = QtWidgets.QVBoxLayout(dlg)

        head = QtWidgets.QLabel(
            f'<b>File:</b> {os.path.basename(path)}<br>'
            f'<b>Số dòng:</b> {len(rows)} học viên · Bấm <b>Import</b> để bắt đầu.<br>'
            f'<i style="color:#718096; font-size:11px;">'
            f'Hệ thống sẽ tạo từng tài khoản, dòng nào lỗi (vd MSV trùng) sẽ skip + báo cuối.'
            f'</i>'
        )
        head.setWordWrap(True)
        head.setStyleSheet('background:#edf2f7; padding:10px; border-radius:6px; font-size:12px;')
        v.addWidget(head)

        # Preview table
        tbl = QtWidgets.QTableWidget()
        cols = ['#', 'MSV', 'Họ tên', 'Username', 'Email', 'SĐT', 'Giới tính']
        tbl.setColumnCount(len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setRowCount(min(len(rows), 100))  # cap preview 100 dong
        for r, row in enumerate(rows[:100]):
            items = [str(r + 1), row.get('msv', ''), row.get('full_name', ''),
                     row.get('username', ''), row.get('email', '') or '—',
                     row.get('sdt', '') or '—', row.get('gioitinh', '') or '—']
            for c, val in enumerate(items):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(str(val)))
        for c, w in enumerate([35, 100, 200, 130, 180, 100, 80]):
            tbl.setColumnWidth(c, w)
        if len(rows) > 100:
            head.setText(head.text() + f'<br><b style="color:#c05621;">⚠ Hiển thị 100/{len(rows)} dòng đầu (toàn bộ {len(rows)} sẽ được import)</b>')
        v.addWidget(tbl)

        btns = QtWidgets.QDialogButtonBox()
        btn_import = btns.addButton(f'⬆ Import {len(rows)} HV', QtWidgets.QDialogButtonBox.AcceptRole)
        btns.addButton('Huỷ', QtWidgets.QDialogButtonBox.RejectRole)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        v.addWidget(btns)

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        # Step 4: bulk import
        if not (DB_AVAILABLE and StudentService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống.')
            return
        # Build payload (clean rows - strip whitespace + handle empty)
        # Lowercase username dong bo voi single-add + login flow (DB
        # WHERE username=%s case-sensitive)
        payload = []
        for row in rows:
            d = {
                'username': (row.get('username') or '').strip().lower(),
                'password': (row.get('password') or '').strip() or 'pass1234',
                'full_name': (row.get('full_name') or '').strip(),
                'msv': (row.get('msv') or '').strip(),
                'email': (row.get('email') or '').strip() or None,
                'sdt': (row.get('sdt') or '').strip() or None,
                'gioitinh': (row.get('gioitinh') or '').strip() or None,
                'ngaysinh': (row.get('ngaysinh') or '').strip() or None,
                'diachi': (row.get('diachi') or '').strip() or None,
            }
            payload.append(d)
        try:
            result = StudentService.bulk_create(payload) or {}
        except Exception as e:
            msg_warn(self, 'Lỗi import', api_error_msg(e))
            return

        success = result.get('success', 0)
        failed = result.get('failed', [])
        total = result.get('total', 0)

        # Step 5: result dialog
        if not failed:
            msg_info(self, 'Thành công',
                     f'✓ Đã import <b>{success}/{total}</b> học viên thành công!')
        else:
            err_lines = [f'• Dòng {f["row"]} (MSV {f["msv"]}): {f["error"]}' for f in failed[:15]]
            extra = '' if len(failed) <= 15 else f'\n... và {len(failed)-15} lỗi nữa'
            msg_warn(self, 'Hoàn tất với lỗi',
                     f'Thành công: <b>{success}/{total}</b><br>'
                     f'Lỗi: <b>{len(failed)}</b><br><br>'
                     f'<pre style="font-size:10px;">' + '\n'.join(err_lines) + extra + '</pre>')
        # Refresh
        self.pages_filled[3] = False
        self._fill_admin_students()
        self.pages_filled[3] = True

    def _admin_add_student(self):
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Thêm học viên')
        dlg.setFixedSize(420, 320)
        form = QtWidgets.QFormLayout(dlg)
        fields = [('MSV', 'msv'), ('Họ tên', 'ten'), ('Lớp', 'lop'), ('Khoa', 'khoa'),
                  ('SDT', 'sdt'), ('Email', 'email')]
        widgets = {}
        for label, key in fields:
            w = QtWidgets.QLineEdit()
            if key == 'email':
                w.setPlaceholderText('vd: ten@example.com')
            elif key == 'sdt':
                w.setPlaceholderText('vd: 0901234567')
            form.addRow(label + ':', w)
            widgets[key] = w
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        widgets['msv'].setFocus()  # auto-focus first field
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not widgets['msv'].text().strip() or not widgets['ten'].text().strip():
            msg_warn(self, 'Thiếu', 'MSV và họ tên không được trống')
            return
        # Validate email/SDT format truoc khi POST
        sdt = widgets['sdt'].text().strip()
        email = widgets['email'].text().strip()
        if sdt and not is_valid_phone_vn(sdt):
            msg_warn(self, 'Sai định dạng', 'SDT không hợp lệ. Phải bắt đầu bằng 0 (10 số) hoặc +84 (11 số).')
            return
        if email and not is_valid_email(email):
            msg_warn(self, 'Sai định dạng', 'Email không hợp lệ (vd: ten@example.com)')
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
                sdt=sdt or None,
                email=email or None,
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
        # Card "Dot hien tai" - lay tu SemesterService.get_current()
        lbl_cur = page.findChild(QtWidgets.QLabel, 'lblCurrentSem')
        lbl_st = page.findChild(QtWidgets.QLabel, 'lblSemStatus')
        if DB_AVAILABLE and SemesterService:
            try:
                cur = SemesterService.get_current()
                if cur and lbl_cur:
                    nm = cur.get('ten') or cur.get('id', '')
                    nh = cur.get('nam_hoc', '')
                    lbl_cur.setText(f'{nm} - {nh}' if nh else nm)
                if cur and lbl_st:
                    st = cur.get('trang_thai', '')
                    if st == 'open':
                        lbl_st.setText('Đang mở đăng ký')
                        lbl_st.setStyleSheet('color: #276749; font-size: 12px; font-weight: bold; background: transparent;')
                    elif st == 'upcoming':
                        lbl_st.setText('Sắp mở')
                        lbl_st.setStyleSheet('color: #c05621; font-size: 12px; font-weight: bold; background: transparent;')
                    else:
                        lbl_st.setText('Đã đóng')
                        lbl_st.setStyleSheet('color: #718096; font-size: 12px; font-weight: bold; background: transparent;')
            except Exception as e:
                print(f'[ADM_SEM] cur loi: {e}')

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
                ['HK2-2526', 'Đợt 2', '2025-2026', '01/01/2026', '30/06/2026', 'Đang mở'],
                ['HK1-2526', 'Đợt 1', '2025-2026', '01/08/2025', '31/12/2025', 'Đã đóng'],
                ['HK2-2425', 'Đợt 2', '2024-2025', '01/01/2025', '30/06/2025', 'Đã đóng'],
                ['HK1-2425', 'Đợt 1', '2024-2025', '01/08/2024', '31/12/2024', 'Đã đóng'],
            ]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblSemesters')
        if tbl:
            tbl.setRowCount(len(data))
            for r, row in enumerate(data):
                for c in range(5):
                    tbl.setItem(r, c, QtWidgets.QTableWidgetItem(row[c]))
                # Trang thai: style item voi mau + bold (truc tiep, khong dung widget)
                is_open = 'mở' in row[5]
                item_st = QtWidgets.QTableWidgetItem(row[5])
                style_status_item(item_st, row[5])
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
        dlg.setWindowTitle('Thêm đợt khoá học')
        dlg.setFixedSize(380, 280)
        form = QtWidgets.QFormLayout(dlg)
        ma = QtWidgets.QLineEdit()
        ma.setPlaceholderText('VD: DOT1-2026')
        ten = QtWidgets.QLineEdit()
        ten.setPlaceholderText('VD: Đợt 1 năm 2026')
        nam = QtWidgets.QLineEdit('2026-2027')
        bd = QtWidgets.QLineEdit('01/08/2026')
        bd.setPlaceholderText('dd/mm/yyyy')
        kt = QtWidgets.QLineEdit('31/12/2026')
        kt.setPlaceholderText('dd/mm/yyyy')
        form.addRow('Mã đợt:', ma)
        form.addRow('Tên đợt:', ten)
        form.addRow('Năm học:', nam)
        form.addRow('Bắt đầu:', bd)
        form.addRow('Kết thúc:', kt)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        ma.setFocus()
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        # Validate input
        if not ma.text().strip() or not ten.text().strip():
            msg_warn(self, 'Thiếu', 'Mã đợt và tên không được trống')
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
        msg_info(self, 'Thành công', f'Đã thêm đợt {ma.text().strip()}')

    def _fill_admin_curriculum(self):
        page = self.page_widgets[7]
        si = page.findChild(QtWidgets.QLabel, 'iconSearchCurr')
        if si:
            si.setPixmap(QPixmap(os.path.join(ICONS, 'search.png')).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        data = None
        cur_ids = []  # song song voi data, luu DB id de update chinh xac
        if DB_AVAILABLE:
            try:
                if not CurriculumService: raise RuntimeError("CurriculumService chua co")
                rows = CurriculumService.get_all()
                # convert 'Bat buoc' tu DB -> 'Cơ bản' cho UI
                loai_map = {'Bat buoc': 'Cơ bản', 'Tu chon': 'Nâng cao', 'Dai cuong': 'Định hướng'}
                data = []
                for i, c in enumerate(rows, start=1):
                    data.append([
                        str(i), c['ma_mon'], c.get('ten_mon', '') or '',
                        str(c.get('tin_chi', 3)),
                        loai_map.get(c.get('loai', ''), c.get('loai', '')),
                        c.get('hoc_ky_de_nghi', '') or '—',
                        c.get('mon_tien_quyet') or '—',
                    ])
                    cur_ids.append(c.get('id'))
            except Exception as e:
                print(f'[ADM_CURR] DB loi: {e}')
        # Cache cur_ids vao instance attr de _admin_edit_curriculum dung
        self._curr_ids = cur_ids
        if not data:
            data = [
                ['1', 'IT001', 'Nhập môn lập trình', '3', 'Cơ bản', 'HK1', '—'],
                ['2', 'MA001', 'Giải tích 1', '3', 'Cơ bản', 'HK1', '—'],
                ['3', 'EN001', 'Tiếng Anh 1', '3', 'Định hướng', 'HK1', '—'],
                ['4', 'IT002', 'Cấu trúc dữ liệu', '3', 'Cơ bản', 'HK2', 'IT001'],
                ['5', 'MA002', 'Đại số tuyến tính', '3', 'Cơ bản', 'HK2', '—'],
                ['6', 'IT003', 'Kỹ thuật lập trình', '3', 'Cơ bản', 'HK3', 'IT002'],
                ['7', 'IT004', 'Cơ sở dữ liệu', '3', 'Cơ bản', 'HK3', 'IT002'],
                ['8', 'IT005', 'Mạng máy tính', '3', 'Cơ bản', 'HK4', '—'],
                ['9', 'IT006', 'Hệ điều hành', '3', 'Cơ bản', 'HK4', 'IT003'],
                ['10', 'IT007', 'Công nghệ phần mềm', '3', 'Cơ bản', 'HK5', 'IT003'],
                ['11', 'IT008', 'Trí tuệ nhân tạo', '3', 'Nâng cao', 'HK5', 'IT002, MA002'],
                ['12', 'IT009', 'Phát triển web', '3', 'Nâng cao', 'HK5', 'IT003'],
                ['13', 'IT010', 'An toàn thông tin', '3', 'Nâng cao', 'HK6', 'IT005'],
                ['14', 'IT011', 'Lập trình di động', '3', 'Nâng cao', 'HK6', 'IT003'],
            ]
        # tinh trang thai mo lop cho moi mon (de show "Đang mở X lớp")
        # Tinh so lop per ma_mon - lay tu cache MOCK_CLASSES (da load tu API)
        # tranh dung db.fetch_all shim (returns []) gay [WARN] khi walkthrough
        ma_mon_count = {}
        for c in MOCK_CLASSES:
            ma_mon_count[c[1]] = ma_mon_count.get(c[1], 0) + 1

        # Stats summary tren cung trang
        n_total = len(data)
        n_bb = sum(1 for r in data if r[4] == 'Cơ bản')
        n_tc = sum(1 for r in data if r[4] == 'Nâng cao')
        n_dc = sum(1 for r in data if r[4] == 'Định hướng')
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
            lbl_stats.setTextFormat(Qt.RichText)  # explicit cho HTML <b>/<span> render dung
            lbl_stats.setText(
                f'<b>{n_total}</b> môn  ·  '
                f'<span style="color:{COLORS["navy"]};"><b>{n_bb}</b> Cơ bản</span>  '
                f'<span style="color:{COLORS["green"]};"><b>{n_tc}</b> Nâng cao</span>  '
                f'<span style="color:{COLORS["gold"]};"><b>{n_dc}</b> Định hướng</span>  ·  '
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
            type_colors = {'Cơ bản': COLORS['navy'], 'Nâng cao': COLORS['green'], 'Định hướng': COLORS['gold']}
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
                btn_del.clicked.connect(lambda ch, rr=r, nm=row[2], t=tbl: self._admin_del_curriculum(rr, nm, t))
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
            cbo_l.addItems(['Tất cả loại', 'Cơ bản', 'Nâng cao', 'Định hướng'])
        cbo_h = page.findChild(QtWidgets.QComboBox, 'cboHocKy')
        if cbo_h:
            cbo_h.clear()
            cbo_h.addItem('Tất cả đợt')
            # Lay unique hoc_ky_de_nghi tu curriculum data thuc te (vd 'HK1', 'HK2', 'Dot 1'...)
            unique_dots = set()
            if DB_AVAILABLE and CurriculumService:
                try:
                    items = CurriculumService.get_all() or []
                    for it in items:
                        d = it.get('hoc_ky_de_nghi')
                        if d: unique_dots.add(str(d))
                except Exception:
                    pass
            for d in sorted(unique_dots):
                cbo_h.addItem(d)
        for nm in ('cboNganh', 'cboLoai', 'cboHocKy'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                safe_connect(cbo.currentIndexChanged, lambda idx: self._admin_filter_curriculum())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddCurr')
        if btn_add:
            safe_connect(btn_add.clicked, self._admin_add_curriculum)
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportCurr')
        if btn_exp:
            safe_connect(btn_exp.clicked, lambda: export_table_csv(self, tbl, 'lo_trinh_hoc.csv', 'Xuất lộ trình học'))

    def _admin_edit_curriculum(self, row_idx):
        page = self.page_widgets[7]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCurriculum')
        if not tbl:
            return
        cur = [tbl.item(row_idx, c).text() if tbl.item(row_idx, c) else '' for c in range(7)]

        # Lay danh sach dot hien co + dot dang chon (cho preserve)
        existing_dots = set()
        try:
            curr_items = CurriculumService.get_all() or []
            for it in curr_items:
                d = it.get('hoc_ky_de_nghi')
                if d: existing_dots.add(str(d))
        except Exception:
            pass
        if cur[5] and cur[5] != '—':
            existing_dots.add(cur[5])

        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Sửa khoá trong lộ trình học')
        dlg.setFixedSize(440, 420)
        form = QtWidgets.QFormLayout(dlg)
        txt_stt = QtWidgets.QLineEdit(cur[0]); txt_stt.setReadOnly(True)
        txt_stt.setStyleSheet('background: #f7fafc; color: #718096;')
        txt_code = QtWidgets.QLineEdit(cur[1])
        txt_name = QtWidgets.QLineEdit(cur[2])
        txt_tc = QtWidgets.QLineEdit(cur[3])
        cbo_loai = QtWidgets.QComboBox()
        cbo_loai.addItems(['Cơ bản', 'Nâng cao', 'Định hướng'])
        if cur[4] in ['Cơ bản', 'Nâng cao', 'Định hướng']:
            cbo_loai.setCurrentText(cur[4])
        # Dot: editable combo, load existing + cho admin nhap moi
        cbo_dot = QtWidgets.QComboBox()
        cbo_dot.setEditable(True)
        cbo_dot.lineEdit().setPlaceholderText('VD: Đợt 1, Mùa hè 2026...')
        for d in sorted(existing_dots):
            cbo_dot.addItem(d)
        if cur[5] and cur[5] != '—':
            cbo_dot.setCurrentText(cur[5])
        txt_prereq = QtWidgets.QLineEdit(cur[6] if cur[6] != '—' else '')
        txt_prereq.setPlaceholderText('Để trống nếu không có, cách nhau bởi dấu phẩy')
        form.addRow('STT:', txt_stt)
        form.addRow('Mã khoá:', txt_code)
        form.addRow('Tên khoá:', txt_name)
        form.addRow('Số buổi:', txt_tc)
        form.addRow('Loại:', cbo_loai)
        form.addRow('Đợt:', cbo_dot)
        form.addRow('Yêu cầu trình độ:', txt_prereq)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        txt_name.setFocus()  # auto-focus ten khoa (STT readonly, ma_khoa it cap nhat)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not txt_code.text().strip() or not txt_name.text().strip():
            msg_warn(self, 'Thiếu', 'Mã khóa và tên môn không được trống')
            return
        try:
            int(txt_tc.text())
        except ValueError:
            msg_warn(self, 'Sai dữ liệu', 'Số buổi phải là số')
            return
        type_colors = {'Cơ bản': COLORS['navy'], 'Nâng cao': COLORS['green'], 'Định hướng': COLORS['gold']}
        new_vals = [cur[0], txt_code.text().upper(), txt_name.text(), txt_tc.text(),
                    cbo_loai.currentText(), cbo_dot.currentText().strip() or '—',
                    txt_prereq.text().strip() or '—']

        # Persist via API CurriculumService.update()
        if not (DB_AVAILABLE and CurriculumService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # Lay cur_id tu cache theo row_idx (chinh xac, khong lookup by ma_mon
        # vi co the dup row trong khung CT)
        cur_ids = getattr(self, '_curr_ids', [])
        if row_idx >= len(cur_ids) or not cur_ids[row_idx]:
            msg_warn(self, 'Lỗi', 'Không xác định được id môn để cập nhật. '
                                  'Vui lòng đóng dialog, F5 lại trang rồi thử lại.')
            return
        cur_id = cur_ids[row_idx]
        try:
            type_to_db = {'Cơ bản': 'Bat buoc', 'Nâng cao': 'Tu chon', 'Định hướng': 'Dai cuong'}
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
        msg_info(self, 'Thành công', f'Đã cập nhật khoá {txt_code.text()} - {txt_name.text()}')

    def _admin_del_curriculum(self, row_idx, ten_mon, tbl):
        """Xoa muc khung CT theo cur_id (tu cache _curr_ids[row_idx]).
        Khong dung _admin_del_row vi cot 0 la STT (so), khong phai ma_mon.
        Dac biet quan trong khi co duplicate ma_mon trong khung CT."""
        cur_ids = getattr(self, '_curr_ids', [])
        if row_idx >= len(cur_ids) or not cur_ids[row_idx]:
            msg_warn(self, 'Lỗi', 'Không xác định được id môn để xóa.')
            return
        cur_id = cur_ids[row_idx]
        ma_mon_display = tbl.item(row_idx, 1).text() if tbl.item(row_idx, 1) else f'#{cur_id}'
        if not msg_confirm(self, 'Xác nhận xóa', f'Xóa môn {ma_mon_display} - {ten_mon} khỏi khung CT?'):
            return
        if not (DB_AVAILABLE and CurriculumService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        try:
            CurriculumService.delete(cur_id)
        except Exception as e:
            print(f'[ADM_DEL_CURR] id={cur_id} loi: {e}')
            msg_warn(self, 'Không xóa được', api_error_msg(e))
            return
        # DB OK -> re-fill bang
        self.pages_filled[7] = False
        self._fill_admin_curriculum()
        self.pages_filled[7] = True
        msg_info(self, 'Đã xóa', f'Đã xóa môn {ma_mon_display} - {ten_mon}')

    def _admin_add_curriculum(self):
        page = self.page_widgets[7]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCurriculum')
        if not tbl:
            return
        # Lay danh sach khoa hoc co san - curriculum.ma_mon FK ve courses.ma_mon
        try:
            courses = CourseService.get_all_courses() or []
        except Exception:
            courses = []
        if not courses:
            msg_warn(self, 'Không có khoá nào', 'Hãy thêm khoá học trước khi đưa vào lộ trình.')
            return

        # Lay unique dot tu curriculum hien co (de admin chon nhanh) hoac nhap moi
        existing_dots = set()
        try:
            curr_items = CurriculumService.get_all() or []
            for it in curr_items:
                d = it.get('hoc_ky_de_nghi')
                if d: existing_dots.add(str(d))
        except Exception:
            pass

        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Thêm khoá vào lộ trình học')
        dlg.setFixedSize(460, 380)
        form = QtWidgets.QFormLayout(dlg)
        # Combobox chon khoa (chi khoa co san trong courses)
        cbo_mon = QtWidgets.QComboBox()
        for c in courses:
            cbo_mon.addItem(f"{c['ma_mon']} - {c.get('ten_mon', '')}", c['ma_mon'])
        txt_tc = QtWidgets.QLineEdit('3')
        cbo_loai = QtWidgets.QComboBox(); cbo_loai.addItems(['Cơ bản', 'Nâng cao', 'Định hướng'])
        # Dot: editable combo - admin co the chon dot co san hoac nhap moi (vd "Mua he 2026")
        cbo_dot = QtWidgets.QComboBox()
        cbo_dot.setEditable(True)
        cbo_dot.lineEdit().setPlaceholderText('VD: Đợt 1, Mùa hè 2026...')
        for d in sorted(existing_dots):
            cbo_dot.addItem(d)
        txt_prereq = QtWidgets.QLineEdit()
        txt_prereq.setPlaceholderText('VD: IT001 (để trống nếu không có)')
        form.addRow('Khoá học:', cbo_mon)
        form.addRow('Số buổi:', txt_tc)
        form.addRow('Loại:', cbo_loai)
        form.addRow('Đợt:', cbo_dot)
        form.addRow('Yêu cầu trình độ:', txt_prereq)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        cbo_mon.setFocus()  # auto-focus first field
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        # Validate tin_chi
        try:
            tin_chi_n = int(txt_tc.text().strip())
            if tin_chi_n < 1 or tin_chi_n > 10:
                raise ValueError()
        except ValueError:
            msg_warn(self, 'Sai dữ liệu', 'Số buổi phải là số từ 1-10')
            return
        if not (DB_AVAILABLE and CurriculumService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        ma_mon_sel = cbo_mon.currentData()
        # Goi API truoc
        loai_map = {'Cơ bản': 'Bat buoc', 'Nâng cao': 'Tu chon', 'Định hướng': 'Dai cuong'}
        try:
            CurriculumService.create(
                ma_mon=ma_mon_sel,
                tin_chi=tin_chi_n,
                loai=loai_map.get(cbo_loai.currentText(), 'Bat buoc'),
                hoc_ky_de_nghi=cbo_dot.currentText().strip() or None,
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
        msg_info(self, 'Thành công', f'Đã thêm khoá {ma_mon_sel} vào lộ trình học')

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
            t_norm = norm(cbo_n.currentText())  # bo dau + lower
            # Truoc 'CNTT' in t case-sensitive + 'Toán' in t -> 'toán' lowercase miss
            if 'cntt' in t_norm or 'thong tin' in t_norm:
                nganh_prefix = 'IT'
            elif 'toan' in t_norm:
                nganh_prefix = 'MA'
            elif 'ngoai ngu' in t_norm or 'anh' in t_norm:
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

    # ===== ADMIN SCHEDULE PAGE =====

    def _fill_admin_schedule(self):
        """Trang 'Quan ly lich hoc' - Admin tao + xem + xoa schedule cho bat ky lop nao."""
        page = self.page_widgets[8]
        if not getattr(page, '_built', False):
            self._build_admin_schedule_ui(page)
            page._built = True
        self._reload_admin_schedule(page)

    def _build_admin_schedule_ui(self, page):
        """Build UI 1 lan: header + filter + table + nut tao."""
        # Header bar
        hb = QtWidgets.QFrame(page)
        hb.setObjectName('headerBar')
        hb.setGeometry(0, 0, 1020, 56)
        hb.setStyleSheet('QFrame#headerBar { background: white; border-bottom: 1px solid #d2d6dc; }')
        title = QtWidgets.QLabel('Quản lý lịch học', hb)
        title.setGeometry(25, 0, 400, 56)
        title.setStyleSheet('color: #1a1a2e; font-size: 17px; font-weight: bold; background: transparent;')

        # Nut Tao theo lich tuan (batch)
        btn_batch = QtWidgets.QPushButton('📅 Tạo theo tuần', hb)
        btn_batch.setObjectName('btnAdmBatchSched')
        btn_batch.setGeometry(700, 12, 150, 32)
        btn_batch.setCursor(Qt.PointingHandCursor)
        btn_batch.setStyleSheet(
            f'QPushButton {{ background: white; color: {COLORS["navy"]}; border: 1px solid {COLORS["navy"]}; '
            f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
            f'QPushButton:hover {{ background: {COLORS["navy"]}; color: white; }}'
        )
        btn_batch.clicked.connect(self._admin_dialog_batch_schedule)

        btn_new = QtWidgets.QPushButton('+ Tạo buổi', hb)
        btn_new.setObjectName('btnAdmNewSched')
        btn_new.setGeometry(860, 12, 140, 32)
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.setStyleSheet(
            'QPushButton { background: #002060; color: white; border: none; '
            'border-radius: 6px; font-size: 12px; font-weight: bold; } '
            'QPushButton:hover { background: #001a50; }'
        )
        btn_new.clicked.connect(self._admin_dialog_new_schedule)

        # Filter bar - sat hon header de bot empty space (truoc gap 14px qua nhieu)
        fb = QtWidgets.QFrame(page)
        fb.setObjectName('filterBar')
        fb.setGeometry(15, 62, 990, 44)
        fb.setStyleSheet('QFrame#filterBar { background: white; border: 1px solid #d2d6dc; border-radius: 8px; }')

        lbl_lop = QtWidgets.QLabel('Lọc theo lớp:', fb)
        lbl_lop.setGeometry(15, 11, 90, 22)
        lbl_lop.setStyleSheet('color: #4a5568; font-size: 12px; background: transparent;')

        cbo_lop = QtWidgets.QComboBox(fb)
        cbo_lop.setObjectName('cboAdmSchedLop')
        cbo_lop.setGeometry(110, 8, 200, 28)
        cbo_lop.setStyleSheet('QComboBox { background: white; border: 1px solid #d2d6dc; border-radius: 4px; padding: 2px 6px; font-size: 12px; }')

        lbl_count = QtWidgets.QLabel('', fb)
        lbl_count.setObjectName('lblSchedCount')
        lbl_count.setGeometry(330, 11, 350, 22)
        lbl_count.setStyleSheet('color: #718096; font-size: 11px; background: transparent;')

        # Search box loc theo ma lop / ten mon / phong / ngay
        txt_s = QtWidgets.QLineEdit(fb)
        txt_s.setObjectName('txtAdmSchedSearch')
        txt_s.setGeometry(700, 8, 275, 28)
        txt_s.setPlaceholderText('🔍 Tìm theo lớp / môn / phòng / ngày...')
        txt_s.setClearButtonEnabled(True)
        txt_s.setStyleSheet('QLineEdit { background: white; border: 1px solid #d2d6dc; '
                             'border-radius: 4px; padding: 2px 8px; font-size: 12px; } '
                             'QLineEdit:focus { border-color: #002060; }')

        # Table - gap 12px sau filter de header table khong dinh sat filter bar
        tbl = QtWidgets.QTableWidget(page)
        tbl.setObjectName('tblAdmSched')
        tbl.setGeometry(15, 118, 990, 574)
        tbl.setColumnCount(8)
        tbl.setHorizontalHeaderLabels(['#', 'Lớp', 'Khóa học', 'Ngày', 'Thứ',
                                       'Giờ học', 'Phòng', 'Thao tác'])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # Header padding tang 14px (tu 8) de chu khong dinh sat mep tren / canh
        # font Segoe UI nho hon mot chut + letter-spacing nhe cho de doc
        tbl.setStyleSheet(
            'QTableWidget { background: white; border: 1px solid #d2d6dc; '
            'border-radius: 6px; gridline-color: #edf2f7; font-size: 12px; } '
            'QHeaderView::section { background: #f7fafc; color: #4a5568; '
            'padding: 14px 10px; border: none; border-bottom: 1px solid #d2d6dc; '
            'font-family: "Segoe UI", "Inter", sans-serif; '
            'font-weight: bold; font-size: 11px; }'
        )
        # Tang chieu cao header de them lasting hon
        tbl.horizontalHeader().setMinimumHeight(46)
        tbl.show()

        # Wire combo filter
        cbo_lop.currentIndexChanged.connect(lambda: self._reload_admin_schedule(page))
        # Wire search box: filter visible rows ngay bang table_filter (khong cần reload)
        txt_s.textChanged.connect(
            lambda s, _t=tbl: table_filter(_t, s, cols=[1, 2, 3, 6])
        )

    def _reload_admin_schedule(self, page):
        """Load lai du lieu schedule (theo filter lop neu co)."""
        cbo_lop = page.findChild(QtWidgets.QComboBox, 'cboAdmSchedLop')
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmSched')
        lbl_count = page.findChild(QtWidgets.QLabel, 'lblSchedCount')
        # CHU Y: bool(empty QComboBox) = False trong PyQt5 -> phai dung `is None`
        if cbo_lop is None or tbl is None:
            return

        # Refresh combo lop neu rong
        if cbo_lop.count() == 0:
            cbo_lop.blockSignals(True)
            cbo_lop.addItem('-- Tất cả lớp --', None)
            for cls in MOCK_CLASSES:
                cbo_lop.addItem(f"{cls[0]} - {cls[2]}", cls[0])
            cbo_lop.blockSignals(False)

        sel_lop = cbo_lop.currentData()
        rows = []
        if DB_AVAILABLE and ScheduleService:
            try:
                if sel_lop:
                    rows = ScheduleService.get_for_class(sel_lop) or []
                else:
                    # Lay 1 tuan rong: 12 tuan tu hom nay -> tat ca lich gan day
                    from datetime import date as _date, timedelta as _td
                    today = _date.today()
                    monday_4w_back = today - _td(days=today.weekday() + 28)
                    rows = ScheduleService.get_by_week(monday_4w_back.isoformat()) or []
                    # Get more weeks
                    for w in range(1, 12):
                        more = ScheduleService.get_by_week(
                            (monday_4w_back + _td(weeks=w)).isoformat()
                        ) or []
                        rows.extend(more)
            except Exception as e:
                print(f'[ADM_SCHED] loi: {e}')

        if lbl_count:
            lbl_count.setText(f'Tổng: {len(rows)} buổi học')

        days_vn = {2: 'Thứ 2', 3: 'Thứ 3', 4: 'Thứ 4', 5: 'Thứ 5',
                   6: 'Thứ 6', 7: 'Thứ 7', 8: 'CN', 1: 'CN'}

        if not rows:
            set_table_empty_state(
                tbl, 'Chưa có buổi học nào',
                icon='📅',
                cta_text='+ Tạo buổi học',
                cta_callback=self._admin_dialog_new_schedule)
        else:
            tbl.setRowCount(len(rows))
            for r, row in enumerate(rows):
                # Row 44 de cum nut Sua/Xoa (24+padding) khong bi crop chu co dau tieng Viet
                tbl.setRowHeight(r, 44)
                ngay = fmt_date(row.get('ngay'))
                gio_bd = str(row.get('gio_bat_dau', ''))[:5]
                gio_kt = str(row.get('gio_ket_thuc', ''))[:5]
                gio = f'{gio_bd}-{gio_kt}' if gio_bd and gio_kt else '—'
                thu_n = row.get('thu')
                thu_str = days_vn.get(thu_n, '—') if thu_n else '—'
                items = [str(r + 1), row.get('lop_id', ''),
                         row.get('ten_mon', '') or '—',
                         ngay, thu_str, gio, row.get('phong', '') or '—']
                for c, val in enumerate(items):
                    item = QtWidgets.QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter if c != 2 else Qt.AlignLeft | Qt.AlignVCenter)
                    tbl.setItem(r, c, item)
                # Action: Sua + Xoa - dong nhat 'Xóa' (4 chars) thay vi 'Xoá' (3 chars)
                cell, (btn_edit, btn_del) = make_action_cell(
                    [('Sửa', 'navy'), ('Xóa', 'red')], spacing=8
                )
                tbl.setCellWidget(r, 7, cell)
                btn_edit.clicked.connect(lambda ch, sid=row.get('id'):
                                         self._admin_dialog_schedule(sched_id=sid))
                btn_del.clicked.connect(lambda ch, sid=row.get('id'),
                                        lop=row.get('lop_id', ''), d=ngay:
                                        self._admin_delete_schedule(sid, lop, d))
        # Column widths total 990 - shrink Thao tac (270 qua rong cho 2 nut)
        # va tang col 'Khoa hoc' (200 -> 240) cho ten khoa hoc dai
        for c, w in enumerate([35, 85, 240, 95, 70, 125, 130, 210]):
            tbl.setColumnWidth(c, w)
        tbl.horizontalHeader().setStretchLastSection(False)

    def _admin_dialog_new_schedule(self):
        """Wrapper: tao buoi hoc moi (sched_id=None)."""
        self._admin_dialog_schedule(sched_id=None)

    def _admin_dialog_batch_schedule(self):
        """Dialog tao bulk buoi hoc theo pattern: cac thu trong tuan + N tuan."""
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Tạo lịch học theo tuần (Bulk)')
        dlg.setFixedSize(540, 580)
        v = QtWidgets.QVBoxLayout(dlg)

        # Header info
        info = QtWidgets.QLabel(
            '<b>Tạo nhiều buổi học cùng lúc</b> - chọn lớp + các thứ trong tuần + số tuần.<br>'
            '<i style="color:#718096; font-size:11px;">Ví dụ: T2 và T5, từ tuần 5/5/2026, 12 tuần → 24 buổi học.</i>'
        )
        info.setWordWrap(True)
        info.setStyleSheet('background: #edf2f7; padding: 10px; border-radius: 6px; font-size: 12px;')
        v.addWidget(info)

        form = QtWidgets.QFormLayout()
        form.setSpacing(10)

        # Lop combo
        cbo_lop = QtWidgets.QComboBox()
        cbo_lop.addItem('-- Chọn lớp --', None)
        for cls in MOCK_CLASSES:
            cbo_lop.addItem(f"{cls[0]} - {cls[2]}", cls[0])

        # Days of week (checkboxes)
        days_widget = QtWidgets.QWidget()
        days_h = QtWidgets.QHBoxLayout(days_widget)
        days_h.setContentsMargins(0, 0, 0, 0)
        days_h.setSpacing(8)
        cbx_days = []
        for day_label, day_num in [('T2', 2), ('T3', 3), ('T4', 4), ('T5', 5),
                                    ('T6', 6), ('T7', 7), ('CN', 8)]:
            cbx = QtWidgets.QCheckBox(day_label)
            cbx.setProperty('day_num', day_num)
            cbx.setStyleSheet('QCheckBox { font-size: 12px; padding: 2px 4px; }')
            cbx_days.append(cbx)
            days_h.addWidget(cbx)
        days_h.addStretch()

        from PyQt5.QtCore import QDate, QTime
        # Start date
        dt_start = QtWidgets.QDateEdit()
        dt_start.setCalendarPopup(True)
        # Default Monday tuần này
        today = QDate.currentDate()
        monday = today.addDays(-(today.dayOfWeek() - 1))
        dt_start.setDate(monday)
        dt_start.setDisplayFormat('dd/MM/yyyy')

        # Num weeks
        spin_weeks = QtWidgets.QSpinBox()
        spin_weeks.setRange(1, 52)
        spin_weeks.setValue(12)
        spin_weeks.setSuffix(' tuần')

        # Times
        time_bd = QtWidgets.QTimeEdit(QTime(7, 0))
        time_bd.setDisplayFormat('HH:mm')
        time_kt = QtWidgets.QTimeEdit(QTime(9, 30))
        time_kt.setDisplayFormat('HH:mm')

        # Phong
        txt_phong = QtWidgets.QLineEdit()
        txt_phong.setPlaceholderText('Để trống = phòng mặc định của lớp')

        # Start buoi so
        spin_buoi = QtWidgets.QSpinBox()
        spin_buoi.setRange(1, 200)
        spin_buoi.setValue(1)
        spin_buoi.setPrefix('Bắt đầu từ buổi #')

        # Preview label - explicit RichText format de <b> render dung
        lbl_preview = QtWidgets.QLabel('Chọn lớp + thứ + tuần để xem preview')
        lbl_preview.setTextFormat(Qt.RichText)
        lbl_preview.setStyleSheet('color: #c05621; font-weight: bold; font-size: 12px; padding: 6px; background: #fff7ed; border-radius: 4px;')

        def update_preview():
            n_days = sum(1 for c in cbx_days if c.isChecked())
            n_total = n_days * spin_weeks.value()
            if n_days == 0 or cbo_lop.currentIndex() == 0:
                lbl_preview.setText('Chưa đủ dữ liệu để preview')
            else:
                lop = cbo_lop.currentData()
                day_names = [c.text() for c in cbx_days if c.isChecked()]
                lbl_preview.setText(
                    f'→ Sẽ tạo <b>{n_total}</b> buổi học cho lớp <b>{lop}</b> '
                    f'({", ".join(day_names)} × {spin_weeks.value()} tuần)'
                )
        for c in cbx_days:
            c.stateChanged.connect(update_preview)
        spin_weeks.valueChanged.connect(update_preview)
        cbo_lop.currentIndexChanged.connect(update_preview)

        form.addRow('Lớp (*):', cbo_lop)
        form.addRow('Thứ trong tuần (*):', days_widget)
        form.addRow('Tuần bắt đầu:', dt_start)
        form.addRow('Số tuần:', spin_weeks)
        form.addRow('Giờ bắt đầu:', time_bd)
        form.addRow('Giờ kết thúc:', time_kt)
        form.addRow('Phòng:', txt_phong)
        form.addRow('Buổi số:', spin_buoi)
        v.addLayout(form)
        v.addWidget(lbl_preview)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        v.addWidget(btns)
        cbo_lop.setFocus()
        update_preview()

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if cbo_lop.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn lớp')
            return
        days = [c.property('day_num') for c in cbx_days if c.isChecked()]
        if not days:
            msg_warn(self, 'Thiếu', 'Hãy chọn ít nhất 1 thứ trong tuần')
            return
        if time_kt.time() <= time_bd.time():
            msg_warn(self, 'Sai giờ', 'Giờ kết thúc phải sau giờ bắt đầu')
            return
        if not (DB_AVAILABLE and ScheduleService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống')
            return
        try:
            result = ScheduleService.create_batch(
                lop_id=cbo_lop.currentData(),
                days_of_week=days,
                start_date=dt_start.date().toString('yyyy-MM-dd'),
                num_weeks=spin_weeks.value(),
                gio_bat_dau=time_bd.time().toString('HH:mm:ss'),
                gio_ket_thuc=time_kt.time().toString('HH:mm:ss'),
                phong=txt_phong.text().strip() or None,
                start_buoi_so=spin_buoi.value(),
            )
            count = result.get('count', 0) if isinstance(result, dict) else 0
        except Exception as e:
            print(f'[ADM_BATCH] loi: {e}')
            msg_warn(self, 'Lỗi', api_error_msg(e))
            return
        msg_info(self, 'Thành công',
                 f'Đã tạo <b>{count}</b> buổi học cho lớp {cbo_lop.currentData()}!')
        self._reload_admin_schedule(self.page_widgets[8])

    def _admin_dialog_schedule(self, sched_id=None):
        """Dialog Admin tao moi (sched_id=None) hoac sua (sched_id=N) buoi hoc."""
        is_edit = sched_id is not None
        existing = None
        if is_edit:
            try:
                existing = ScheduleService.get(sched_id) or {}
            except Exception as e:
                msg_warn(self, 'Lỗi', f'Không load được buổi học: {api_error_msg(e)}')
                return

        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle(f'Sửa buổi học #{sched_id}' if is_edit else 'Tạo buổi học mới (Admin)')
        dlg.setFixedSize(500, 480)
        form = QtWidgets.QFormLayout(dlg)

        cbo_lop = QtWidgets.QComboBox()
        cbo_lop.addItem('-- Chọn lớp --', None)
        for cls in MOCK_CLASSES:
            cbo_lop.addItem(f"{cls[0]} - {cls[2]} ({cls[3] or 'chưa GV'})", cls[0])
        if is_edit and existing.get('lop_id'):
            for i in range(cbo_lop.count()):
                if cbo_lop.itemData(i) == existing['lop_id']:
                    cbo_lop.setCurrentIndex(i)
                    break
            cbo_lop.setEnabled(False)  # khong cho doi lop khi edit

        from PyQt5.QtCore import QDate, QTime
        dt_ngay = QtWidgets.QDateEdit()
        dt_ngay.setCalendarPopup(True)
        dt_ngay.setDisplayFormat('dd/MM/yyyy')
        if is_edit and existing.get('ngay'):
            ngay_v = existing['ngay']
            if hasattr(ngay_v, 'year'):
                dt_ngay.setDate(QDate(ngay_v.year, ngay_v.month, ngay_v.day))
            elif isinstance(ngay_v, str):
                dt_ngay.setDate(QDate.fromString(ngay_v[:10], 'yyyy-MM-dd'))
        else:
            dt_ngay.setDate(QDate.currentDate().addDays(1))

        time_bd = QtWidgets.QTimeEdit(QTime(7, 0))
        time_bd.setDisplayFormat('HH:mm')
        time_kt = QtWidgets.QTimeEdit(QTime(9, 30))
        time_kt.setDisplayFormat('HH:mm')
        if is_edit:
            for tw, key in [(time_bd, 'gio_bat_dau'), (time_kt, 'gio_ket_thuc')]:
                v = existing.get(key)
                if v:
                    s = str(v)[:5]
                    try:
                        h, m = map(int, s.split(':'))
                        tw.setTime(QTime(h, m))
                    except Exception:
                        pass

        txt_phong = QtWidgets.QLineEdit()
        txt_phong.setPlaceholderText('Để trống = dùng phòng mặc định của lớp')
        if is_edit and existing.get('phong'):
            txt_phong.setText(existing['phong'])

        spin_buoi = QtWidgets.QSpinBox()
        spin_buoi.setRange(1, 200)
        spin_buoi.setValue(int(existing.get('buoi_so') or 1) if is_edit else 1)
        spin_buoi.setPrefix('Buổi #')

        txt_nd = QtWidgets.QTextEdit()
        txt_nd.setPlaceholderText('Nội dung buổi học (chương/bài/chủ đề)')
        txt_nd.setFixedHeight(80)
        if is_edit and existing.get('noi_dung'):
            txt_nd.setPlainText(existing['noi_dung'])

        form.addRow('Lớp (*):', cbo_lop)
        form.addRow('Ngày (*):', dt_ngay)
        form.addRow('Giờ bắt đầu:', time_bd)
        form.addRow('Giờ kết thúc:', time_kt)
        form.addRow('Phòng:', txt_phong)
        form.addRow('Buổi số:', spin_buoi)
        form.addRow('Nội dung:', txt_nd)

        btn_label = QtWidgets.QDialogButtonBox.Save if is_edit else QtWidgets.QDialogButtonBox.Ok
        btns = QtWidgets.QDialogButtonBox(btn_label | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if not is_edit:
            cbo_lop.setFocus()
        else:
            txt_nd.setFocus()

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if cbo_lop.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn lớp')
            return
        if time_kt.time() <= time_bd.time():
            msg_warn(self, 'Sai giờ', 'Giờ kết thúc phải sau giờ bắt đầu')
            return
        if not (DB_AVAILABLE and ScheduleService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống')
            return
        # CHECK CONFLICT truoc khi save
        ngay_str = dt_ngay.date().toString('yyyy-MM-dd')
        gio_bd_str = time_bd.time().toString('HH:mm:ss')
        gio_kt_str = time_kt.time().toString('HH:mm:ss')
        phong_val = txt_phong.text().strip() or None
        # Lay phong default cua lop neu user khong nhap
        if not phong_val:
            for cls in MOCK_CLASSES:
                if cls[0] == cbo_lop.currentData():
                    phong_val = cls[5] or None
                    break
        if not check_schedule_conflict_warn(
            self, ngay_str, gio_bd_str, gio_kt_str,
            phong=phong_val, lop_id=cbo_lop.currentData(),
            exclude_id=sched_id if is_edit else None
        ):
            return  # User cancel
        try:
            kwargs = dict(
                lop_id=cbo_lop.currentData(),
                ngay=ngay_str,
                gio_bat_dau=gio_bd_str,
                gio_ket_thuc=gio_kt_str,
                phong=txt_phong.text().strip() or None,
                buoi_so=spin_buoi.value(),
                noi_dung=txt_nd.toPlainText().strip() or None,
            )
            if is_edit:
                kwargs.pop('lop_id', None)  # khong gui lop_id
                ScheduleService.update(sched_id, **kwargs)
            else:
                ScheduleService.create(**kwargs)
        except Exception as e:
            print(f'[ADM_SCHED] save loi: {e}')
            msg_warn(self, 'Lỗi lưu', api_error_msg(e))
            return
        action = 'cập nhật' if is_edit else 'tạo'
        msg_info(self, 'Thành công',
                 f'Đã {action} buổi học '
                 f'ngày {dt_ngay.date().toString("dd/MM/yyyy")}')
        self._reload_admin_schedule(self.page_widgets[8])

    def _admin_delete_schedule(self, sched_id, lop, ngay):
        if not msg_confirm_delete(self, 'buổi học', str(sched_id),
                                  item_name=f'{lop} ngày {ngay}'):
            return
        if not (DB_AVAILABLE and ScheduleService):
            return
        try:
            ScheduleService.delete(sched_id)
        except Exception as e:
            msg_warn(self, 'Lỗi xoá', api_error_msg(e))
            return
        msg_info(self, 'Đã xoá', f'Đã xoá buổi học #{sched_id}')
        self._reload_admin_schedule(self.page_widgets[8])

    def _fill_admin_audit(self):
        page = self.page_widgets[9]  # shifted +1 sau khi insert btnAdminSchedule idx 8
        si = page.findChild(QtWidgets.QLabel, 'iconSearchAudit')
        if si:
            si.setPixmap(QPixmap(os.path.join(ICONS, 'search.png')).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        data = None
        if DB_AVAILABLE:
            try:
                if not AuditService: raise RuntimeError("AuditService chua co")
                rows = AuditService.get_all(limit=50)
                role_map = {'admin': 'QTV', 'teacher': 'GV', 'employee': 'NV', 'student': 'HV'}
                # Map action code (tu DB trigger + auth_service.log_login) -> ten thao tac
                # than thien tieng Viet. Truoc 'login'/'login_failed' khong trong map ->
                # hien raw 'login' -> filter 'Đăng nhập' khong match
                action_map = {
                    'create_registrations': 'Tạo đăng ký',
                    'update_registrations': 'Cập nhật ĐK',
                    'delete_registrations': 'Huỷ đăng ký',
                    'create_payments': 'Thanh toán',
                    'update_payments': 'Cập nhật TT',
                    'delete_payments': 'Hoàn tiền',
                    'create_grades': 'Nhập điểm',
                    'update_grades': 'Sửa điểm',
                    'delete_grades': 'Xoá điểm',
                    'create_attendance': 'Điểm danh',
                    'update_attendance': 'Sửa điểm danh',
                    'login': 'Đăng nhập',
                    'login_failed': 'Đăng nhập thất bại',
                    'logout': 'Đăng xuất',
                }
                data = []
                for l in rows:
                    ts = fmt_date(l.get('created_at'), fmt='%d/%m/%Y %H:%M:%S')
                    # Action tu DB trigger (no user) -> hien 'Hệ thống' / 'Tự động' thay vi '—'
                    username = l.get('username')
                    role = l.get('role')
                    if not username and not role:
                        username_display = 'Hệ thống'
                        role_display = 'Tự động'
                    else:
                        username_display = username or '—'
                        role_display = role_map.get(role, role or '—')
                    raw_action = l.get('action', '')
                    action_display = action_map.get(raw_action, raw_action)
                    data.append([
                        ts, username_display, role_display,
                        action_display,
                        l.get('description') or '',
                        l.get('ip_address') or '—',
                    ])
            except Exception as e:
                print(f'[ADM_AUDIT] DB loi: {e}')
        if not data:
            data = [
                ['17/04/2026 08:12:34', 'admin', 'QTV', 'Đăng nhập', 'Đăng nhập thành công', '192.168.1.10'],
                ['17/04/2026 08:15:02', 'admin', 'QTV', 'Mở đăng ký', 'Mở đăng ký HK2-2526', '192.168.1.10'],
                ['17/04/2026 08:30:11', '2024001', 'HV', 'Đăng nhập', 'Đăng nhập thành công', '10.0.0.55'],
                ['17/04/2026 08:31:45', '2024001', 'HV', 'Đăng ký', 'Đăng ký IT004 - Trí tuệ nhân tạo', '10.0.0.55'],
                ['17/04/2026 08:32:10', '2024001', 'HV', 'Đăng ký', 'Đăng ký IT005 - Phát triển web', '10.0.0.55'],
                ['17/04/2026 08:45:30', '2024002', 'HV', 'Đăng nhập', 'Đăng nhập thành công', '10.0.0.87'],
                ['17/04/2026 08:46:12', '2024002', 'HV', 'Hủy ĐK', 'Hủy đăng ký MA002 - Xác suất TK', '10.0.0.87'],
                ['17/04/2026 09:00:05', '2024003', 'HV', 'Đăng nhập', 'Đăng nhập thất bại (sai MK)', '10.0.0.42'],
                ['17/04/2026 09:00:15', '2024003', 'HV', 'Đăng nhập', 'Đăng nhập thất bại (sai MK)', '10.0.0.42'],
                ['17/04/2026 09:00:25', '2024003', 'HV', 'Cảnh báo', 'Khóa tài khoản 15 phút (3 lần sai)', '10.0.0.42'],
                ['17/04/2026 09:15:30', 'admin', 'QTV', 'Cập nhật', 'Sửa sĩ số IT001 từ 35 → 40', '192.168.1.10'],
                ['17/04/2026 09:30:00', '2024010', 'HV', 'Thanh toán', 'Thanh toán 9,000,000 đ - HK2', '10.0.0.91'],
            ]
        action_colors = {
            'Đăng nhập': COLORS['green'], 'Đăng nhập thất bại': COLORS['red'],
            'Đăng xuất': COLORS['text_mid'],
            'Đăng ký': COLORS['navy'],
            'Tạo đăng ký': COLORS['navy'], 'Huỷ đăng ký': COLORS['orange'],
            'Cập nhật ĐK': COLORS['text_mid'],
            'Thanh toán': COLORS['gold'], 'Hoàn tiền': COLORS['orange'],
            'Cập nhật TT': COLORS['text_mid'],
            'Nhập điểm': COLORS['navy'], 'Sửa điểm': COLORS['text_mid'], 'Xoá điểm': COLORS['red'],
            'Điểm danh': COLORS['green'], 'Sửa điểm danh': COLORS['text_mid'],
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
        # search + filter - safe_connect tranh accumulation
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchAudit')
        if txt:
            safe_connect(txt.textChanged, lambda s: table_filter(tbl, s, cols=[1, 3, 4]))
        cbo_u = page.findChild(QtWidgets.QComboBox, 'cboAuditUser')
        if cbo_u:
            cbo_u.clear()
            cbo_u.addItems(['Tất cả người dùng', 'QTV', 'GV', 'NV', 'HV'])
        cbo_a = page.findChild(QtWidgets.QComboBox, 'cboAuditAction')
        if cbo_a:
            cbo_a.clear()
            # Cac muc filter phai khop voi nhan o cot 3 (action_map): 'Huy DK' khong
            # match 'Huỷ đăng ký' substring. Cap nhat de filter chay dung
            cbo_a.addItems(['Tất cả hành động', 'Đăng nhập', 'Tạo đăng ký', 'Huỷ đăng ký',
                            'Thanh toán', 'Hoàn tiền', 'Nhập điểm', 'Sửa điểm',
                            'Điểm danh', 'Mở đăng ký', 'Cảnh báo'])
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboAuditDate')
        if cbo_d:
            cbo_d.clear()
            cbo_d.addItems(['Tất cả thời gian', 'Hôm nay', '7 ngày qua', '30 ngày qua'])
        for nm in ('cboAuditUser', 'cboAuditAction', 'cboAuditDate'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                safe_connect(cbo.currentIndexChanged, lambda: self._admin_filter_audit())
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportAudit')
        if btn_exp:
            safe_connect(btn_exp.clicked, lambda: export_table_csv(self, tbl, 'nhat_ky_he_thong.csv', 'Xuất nhật ký hệ thống'))

    def _admin_filter_audit(self):
        page = self.page_widgets[9]  # audit shifted +1
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
                    # Parse ngay tu cell text "dd/mm/yyyy HH:MM..." hoac "dd/mm/yyyy"
                    from datetime import date as _date, datetime as _dt, timedelta as _td
                    today = _date.today()
                    row_date = None
                    txt = it.text().strip()
                    # Try cac format pho bien
                    for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y',
                                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                        try:
                            row_date = _dt.strptime(txt[:len(fmt) + 5], fmt).date()
                            break
                        except (ValueError, TypeError):
                            continue
                    if row_date is None:
                        # Khong parse duoc -> giu hien thi (an toan)
                        pass
                    else:
                        ds_low = date_sel.lower()
                        if 'hôm nay' in ds_low or 'today' in ds_low:
                            show = show and (row_date == today)
                        elif '7 ngày' in ds_low or '7 ngay' in ds_low:
                            show = show and (row_date >= today - _td(days=7))
                        elif '30 ngày' in ds_low or '30 ngay' in ds_low:
                            show = show and (row_date >= today - _td(days=30))
            tbl.setRowHidden(r, not show)

    def _fill_admin_stats(self):
        # Populate cbo voi danh sach hoc ky tu API
        page = self.page_widgets[10]  # stats shifted +1 sau khi insert btnAdminSchedule idx 8
        cbo = page.findChild(QtWidgets.QComboBox, 'cboStatSemester')
        self._stats_sem_ids = []
        default_idx = 0
        # CHU Y: PyQt5 QComboBox bool() = False khi empty -> phai dung `is not None`
        if cbo is not None:
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
        page = self.page_widgets[10]  # stats shifted +1
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
                                f"{float(c['gpa']):.1f}" if c.get('gpa') else '—',
                                fmt_vnd(c.get('doanh_thu'), suffix='')]
                               for c in stat.get('class_stats', [])]
            except Exception as e:
                print(f'[ADM_STATS] semester {sem_id} loi: {e}')

        def _render_table_with_empty(tbl, data, fill_func, col_widths):
            """Helper render table voi placeholder empty state - dung set_table_empty_state."""
            if not data:
                set_table_empty_state(tbl, 'Chưa có dữ liệu')
            else:
                tbl.setRowCount(len(data))
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
            ma, mmon, tmon, gv, lich, phong, smax, siso, gia, *_ = cls
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
            gia_item = QtWidgets.QTableWidgetItem(fmt_vnd(gia))
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
            cbo_c.addItem('Tất cả khóa học')
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
        # Them nut Bulk import CSV (idempotent) - canh nut Add
        if not page.findChild(QtWidgets.QPushButton, 'btnImportClassesCSV'):
            btn_imp = QtWidgets.QPushButton('📥 Import CSV', page)
            btn_imp.setObjectName('btnImportClassesCSV')
            if btn_add:
                geo = btn_add.geometry()
                btn_imp.setGeometry(geo.x() - 145, geo.y(), 135, geo.height())
            else:
                btn_imp.setGeometry(700, 18, 135, 32)
            btn_imp.setCursor(Qt.PointingHandCursor)
            btn_imp.setToolTip('Import nhiều lớp cùng lúc từ file CSV (cột: ma_lop,ma_mon,gv_id,lich,phong,siso_max,gia,semester_id,so_buoi)')
            btn_imp.setStyleSheet(
                f'QPushButton {{ background: white; color: {COLORS["navy"]}; border: 1px solid {COLORS["navy"]}; '
                f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                f'QPushButton:hover {{ background: {COLORS["navy"]}; color: white; }}'
            )
            btn_imp.clicked.connect(self._admin_import_classes_csv)
            btn_imp.show()

    def _admin_import_classes_csv(self):
        """Dialog Admin import nhieu lop cung luc tu file CSV.

        Format header bat buoc: ma_lop,ma_mon,gv_id,lich,phong,siso_max,gia,semester_id,so_buoi
        gv_id co the de trong (None). Encoding: utf-8 / utf-8-sig.
        """
        import csv as _csv
        path, _ext = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Chọn file CSV danh sách lớp',
            os.path.join(os.path.expanduser('~'), 'Desktop'),
            'CSV Files (*.csv)'
        )
        if not path:
            return
        rows = []
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = _csv.DictReader(f)
                for r in reader:
                    rows.append({k.strip(): (v or '').strip() for k, v in r.items()})
        except Exception as e:
            msg_warn(self, 'Lỗi đọc file', f'Không đọc được CSV:\n{e}')
            return
        if not rows:
            msg_warn(self, 'Trống', 'File CSV không có dòng nào (cần header dòng đầu).')
            return
        required = {'ma_lop', 'ma_mon'}
        missing = required - set(rows[0].keys())
        if missing:
            msg_warn(self, 'Thiếu cột',
                     f'Thiếu cột bắt buộc: {missing}.\n\n'
                     'Header chuẩn: ma_lop,ma_mon,gv_id,lich,phong,siso_max,gia,semester_id,so_buoi')
            return

        # Preview dialog
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle(f'Import lớp - {len(rows)} dòng')
        dlg.setFixedSize(880, 500)
        v = QtWidgets.QVBoxLayout(dlg)
        head = QtWidgets.QLabel(
            f'<b>File:</b> {os.path.basename(path)}<br>'
            f'<b>Số dòng:</b> {len(rows)} lớp · Bấm <b>Import</b> để bắt đầu.<br>'
            f'<i style="color:#718096; font-size:11px;">Lớp nào lỗi (vd ma_lop trùng) sẽ skip + báo cuối.</i>'
        )
        head.setWordWrap(True)
        head.setStyleSheet('background:#edf2f7; padding:10px; border-radius:6px; font-size:12px;')
        v.addWidget(head)

        tbl = QtWidgets.QTableWidget()
        cols = ['#', 'Mã lớp', 'Mã môn', 'GV ID', 'Lịch', 'Phòng', 'Sĩ số max', 'Học phí']
        tbl.setColumnCount(len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setRowCount(min(len(rows), 100))
        for r, row in enumerate(rows[:100]):
            items = [str(r + 1), row.get('ma_lop', ''), row.get('ma_mon', ''),
                     row.get('gv_id', '') or '—', row.get('lich', '') or '—',
                     row.get('phong', '') or '—', row.get('siso_max', '40'),
                     fmt_vnd(row.get('gia', 0) or 0, suffix='đ')]
            for c, val in enumerate(items):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(str(val)))
        for c, w in enumerate([35, 90, 80, 70, 130, 80, 80, 130]):
            tbl.setColumnWidth(c, w)
        if len(rows) > 100:
            head.setText(head.text() + f'<br><b style="color:#c05621;">⚠ Hiển thị 100/{len(rows)} dòng đầu</b>')
        v.addWidget(tbl)

        btns = QtWidgets.QDialogButtonBox()
        btns.addButton(f'⬆ Import {len(rows)} lớp', QtWidgets.QDialogButtonBox.AcceptRole)
        btns.addButton('Huỷ', QtWidgets.QDialogButtonBox.RejectRole)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        v.addWidget(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        if not (DB_AVAILABLE and CourseService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống.')
            return

        # Bulk loop (no bulk endpoint -> goi tung cai)
        success = 0
        failed = []
        for i, row in enumerate(rows, 1):
            try:
                ma_lop = row.get('ma_lop', '').strip()
                ma_mon = row.get('ma_mon', '').strip()
                if not ma_lop or not ma_mon:
                    raise ValueError('ma_lop / ma_mon trống')
                gv_id_raw = (row.get('gv_id') or '').strip()
                gv_id = int(gv_id_raw) if gv_id_raw else None
                CourseService.create_class(
                    ma_lop=ma_lop,
                    ma_mon=ma_mon,
                    gv_id=gv_id,
                    lich=row.get('lich') or '',
                    phong=row.get('phong') or '',
                    siso_max=int(row.get('siso_max') or 40),
                    gia=int(row.get('gia') or 0),
                    semester_id=row.get('semester_id') or None,
                    so_buoi=int(row.get('so_buoi') or 24),
                )
                success += 1
            except Exception as e:
                err_msg = str(e)
                if '\n' in err_msg:
                    err_msg = err_msg.split('\n')[-1].strip() or err_msg[:200]
                failed.append({'row': i, 'ma_lop': row.get('ma_lop', '?'), 'error': err_msg[:200]})

        # Refresh cache + reload bang
        try:
            _refresh_cache()
        except Exception:
            pass
        self.pages_filled[2] = False
        self._fill_admin_classes()

        if not failed:
            msg_info(self, 'Thành công',
                     f'✓ Đã import <b>{success}/{len(rows)}</b> lớp thành công!')
        else:
            err_lines = [f'• Dòng {f["row"]} (lớp {f["ma_lop"]}): {f["error"]}' for f in failed[:15]]
            extra = '' if len(failed) <= 15 else f'\n... và {len(failed)-15} lỗi nữa'
            msg_warn(self, 'Hoàn tất với lỗi',
                     f'Thành công: <b>{success}/{len(rows)}</b><br>'
                     f'Lỗi: <b>{len(failed)}</b><br><br>'
                     f'<pre style="font-size:10px;">' + '\n'.join(err_lines) + extra + '</pre>')

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
        _, mmon, tmon, gv, lich, phong, smax, siso, gia, *_ = cur

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
        # Sĩ số hiện tại = read-only (auto-sync qua DB trigger khi register/cancel)
        txt_siso = QtWidgets.QLineEdit(str(siso))
        txt_siso.setReadOnly(True)
        txt_siso.setStyleSheet('background: #f7fafc; color: #718096;')
        txt_siso.setToolTip('Tự động cập nhật khi có học viên đăng ký - không sửa thủ công')
        # Hoc phi: dung QSpinBox co thousand separator (dong bo voi add dialog)
        gia_spin = QtWidgets.QSpinBox()
        gia_spin.setRange(0, 100_000_000)
        gia_spin.setSingleStep(100_000)
        gia_spin.setValue(int(gia or 0))
        gia_spin.setSuffix(' đ')
        gia_spin.setGroupSeparatorShown(True)  # 2.500.000 đ
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
        form.addRow('Học phí:', gia_spin)
        form.addRow('Số buổi:', txt_buoi)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        try:
            smax_n = int(txt_smax.text())
            siso_n = int(txt_siso.text())  # readonly, giu giu giu nguyen
            gia_n = int(gia_spin.value())
            buoi_n = int(txt_buoi.text())
        except ValueError:
            msg_warn(self, 'Sai dữ liệu', 'Sĩ số tối đa và số buổi phải là số')
            return
        if siso_n > smax_n:
            msg_warn(self, 'Sai dữ liệu',
                     f'Hiện đang có {siso_n} HV đăng ký. Không thể đặt sĩ số tối đa < {siso_n}.\n'
                     'Hãy huỷ bớt đăng ký trước khi giảm sĩ số tối đa.')
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

        # Goi API - KHONG gui siso_hien_tai (trigger DB tu sync)
        try:
            CourseService.update_class(ma_lop,
                ma_mon=ma_mon_new,
                gv_id=gv_id_new,
                lich=txt_lich.text(), phong=txt_phong.text(),
                siso_max=smax_n, gia=gia_n,
                so_buoi=buoi_n,
            )
        except Exception as e:
            print(f'[ADM_EDIT_CLS] DB loi: {e}')
            msg_warn(self, 'Không lưu được', api_error_msg(e))
            return

        # DB OK -> refresh cache (giu sem_id field) + re-fill bang. Truoc replace
        # MOCK_CLASSES[idx] manual voi 9 fields (thieu sem_id) -> is_class_active()
        # khong nhan duoc trang thai dot
        _refresh_cache()
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
        # GV combo: load tu TeacherService de dam bao co GV moi (chua co lop)
        # Truoc lay tu MOCK_CLASSES -> GV chua duoc gan lop nao se khong xuat hien
        # -> admin khong them duoc lop cho GV moi cho den khi co lop khac roi
        cbo_gv = QtWidgets.QComboBox()
        cbo_gv.addItem('-- Chọn giảng viên --', None)
        try:
            for t in (TeacherService.get_all() or []):
                tid = t.get('id') or t.get('user_id')
                ten = (t.get('full_name') or '').strip()
                if tid and ten:
                    cbo_gv.addItem(ten, userData=tid)
        except Exception as e:
            print(f'[ADM_ADD_CLS] load teachers loi: {e}')
        lich = QtWidgets.QLineEdit('T2 (7:00-9:30)')
        phong = QtWidgets.QLineEdit('P.?')
        smax = QtWidgets.QSpinBox(); smax.setRange(10, 100); smax.setValue(40)
        gia = QtWidgets.QSpinBox(); gia.setRange(500000, 10000000); gia.setSingleStep(100000); gia.setValue(2000000)
        gia.setSuffix(' đ'); gia.setGroupSeparatorShown(True)
        so_buoi = QtWidgets.QSpinBox(); so_buoi.setRange(4, 60); so_buoi.setValue(24)

        form.addRow('Mã lớp (*):', ma)
        form.addRow('Khóa học (*):', cbo_mon)
        form.addRow('Giảng viên (*):', cbo_gv)
        form.addRow('Lịch học:', lich)
        form.addRow('Phòng:', phong)
        form.addRow('Sĩ số tối đa:', smax)
        form.addRow('Học phí:', gia)
        form.addRow('Số buổi:', so_buoi)
        # Note: Si so hien tai = 0 mac dinh, se tu dong update qua DB trigger khi co dang ky

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        ma.setFocus()  # auto-focus first field
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not ma.text().strip():
            msg_warn(self, 'Thiếu', 'Mã lớp không được trống')
            return
        if cbo_mon.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn khóa học')
            return
        if cbo_gv.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn giảng viên')
            return

        mon_code, mon_name = cbo_mon.currentData()
        gv_id = cbo_gv.currentData()  # userData = teacher_id (set khi build combo)
        gv_name = cbo_gv.currentText()
        ma_lop = ma.text().upper().strip()

        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        if not gv_id:
            msg_warn(self, 'Lỗi', f'Không xác định được giảng viên "{gv_name}".')
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
                semester_id=sem_id, siso_hien_tai=0,  # Trigger DB tu update khi co dang ky
                so_buoi=so_buoi.value(),
            )
        except Exception as e:
            print(f'[ADM_ADD_CLS] DB loi: {e}')
            msg_warn(self, 'Không thêm được', api_error_msg(e))
            return

        # DB OK -> refresh cache + reload UI (truoc append manual missing sem_id idx 9
        # khien is_class_active() khong nhan thay sem_id -> mis-detect)
        _refresh_cache()
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
        # Col 7 (Thao tac) 140 -> 160 cho 'Chi tiết' (85px) + 'Xóa' (55px) + spacing
        for c, cw in enumerate([75, 170, 140, 110, 115, 70, 90, 160]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 44)

        widen_search(page, 'txtSearchTea', 300, ['cboTeaKhoa', 'cboTeaHocVi'])
        # search / filter / add - safe_connect tranh accumulation
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchTea')
        if txt:
            safe_connect(txt.textChanged, lambda s: table_filter(tbl, s, cols=[0, 1]))
        # Populate cbo dynamic tu data thuc te thay vi hardcode (truoc cbo co
        # 'Cử nhân'/'Ngoại ngữ' nhung DB khong co GV nao co value do -> chon
        # filter hien rong, gay UX bad. Lay unique tu cot 2 (khoa) + cot 3 (hoc_vi))
        cbo_k = page.findChild(QtWidgets.QComboBox, 'cboTeaKhoa')
        if cbo_k:
            cbo_k.clear()
            cbo_k.addItem('Tất cả khoa')
            seen_k = set()
            for row in data:
                if len(row) > 2 and row[2] and row[2] not in seen_k:
                    seen_k.add(row[2]); cbo_k.addItem(row[2])
        cbo_hv = page.findChild(QtWidgets.QComboBox, 'cboTeaHocVi')
        if cbo_hv:
            cbo_hv.clear()
            cbo_hv.addItem('Tất cả học vị')
            seen_hv = set()
            for row in data:
                if len(row) > 3 and row[3] and row[3] not in seen_hv:
                    seen_hv.add(row[3]); cbo_hv.addItem(row[3])
        for nm in ('cboTeaKhoa', 'cboTeaHocVi'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                safe_connect(cbo.currentIndexChanged, lambda: self._admin_filter_teachers())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddTeacher')
        if btn_add:
            safe_connect(btn_add.clicked, lambda: self._admin_add_user('giảng viên', 4, 'tblAdmTeachers',
                                                                       ['Mã GV', 'Họ tên', 'Khoa', 'Học vị', 'SDT']))
        # Them nut Bulk import GV CSV (idempotent)
        if not page.findChild(QtWidgets.QPushButton, 'btnImportTeachersCSV'):
            btn_imp = QtWidgets.QPushButton('📥 Import CSV', page)
            btn_imp.setObjectName('btnImportTeachersCSV')
            if btn_add:
                geo = btn_add.geometry()
                btn_imp.setGeometry(geo.x() - 145, geo.y(), 135, geo.height())
            else:
                btn_imp.setGeometry(700, 18, 135, 32)
            btn_imp.setCursor(Qt.PointingHandCursor)
            btn_imp.setToolTip('Import nhiều GV từ file CSV (cột: username,password,full_name,ma_gv,email,sdt,hoc_vi,khoa,chuyen_nganh,tham_nien)')
            btn_imp.setStyleSheet(
                f'QPushButton {{ background: white; color: {COLORS["navy"]}; border: 1px solid {COLORS["navy"]}; '
                f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                f'QPushButton:hover {{ background: {COLORS["navy"]}; color: white; }}'
            )
            btn_imp.clicked.connect(self._admin_import_teachers_csv)
            btn_imp.show()

    def _admin_filter_teachers(self):
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmTeachers')
        if not tbl:
            return
        cbo_k = page.findChild(QtWidgets.QComboBox, 'cboTeaKhoa')
        cbo_hv = page.findChild(QtWidgets.QComboBox, 'cboTeaHocVi')
        # Strip dau (NFD) khi so sanh - DB seed luu khong dau ('Tien si', 'Toan')
        # nhung combo UI hien co dau ('Tiến sĩ', 'Toán'). Khong normalize -> filter
        # khong khop -> tat ca rows bi an
        khoa_sel = _status_normalize(cbo_k.currentText()) if cbo_k and cbo_k.currentIndex() > 0 else None
        hv_sel = _status_normalize(cbo_hv.currentText()) if cbo_hv and cbo_hv.currentIndex() > 0 else None
        for r in range(tbl.rowCount()):
            show = True
            if khoa_sel:
                it = tbl.item(r, 2)
                if it and khoa_sel not in _status_normalize(it.text()):
                    show = False
            if hv_sel:
                it = tbl.item(r, 3)
                if it and hv_sel not in _status_normalize(it.text()):
                    show = False
            tbl.setRowHidden(r, not show)

    def _admin_filter_employees(self):
        page = self.page_widgets[5]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmEmployees')
        if not tbl:
            return
        cbo_r = page.findChild(QtWidgets.QComboBox, 'cboEmpRole')
        cbo_s = page.findChild(QtWidgets.QComboBox, 'cboEmpStatus')
        # Strip dau khi so sanh - DB co the chua data khong dau ('Nhan vien dang ky')
        # nhung combo UI co dau ('Nhân viên đăng ký')
        role_sel = _status_normalize(cbo_r.currentText()) if cbo_r and cbo_r.currentIndex() > 0 else None
        status_sel = _status_normalize(cbo_s.currentText()) if cbo_s and cbo_s.currentIndex() > 0 else None
        for r in range(tbl.rowCount()):
            show = True
            if role_sel:
                it = tbl.item(r, 2)
                if it and role_sel not in _status_normalize(it.text()):
                    show = False
            if status_sel:
                it = tbl.item(r, 5)
                if it and status_sel not in _status_normalize(it.text()):
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
            # Placeholder gioi thieu cho cac field email/sdt
            if 'mail' in label.lower():
                w.setPlaceholderText('vd: ten@example.com')
            elif 'SDT' in label or 'điện thoại' in label.lower():
                w.setPlaceholderText('vd: 0901234567')
            form.addRow(label + ':', w)
            widgets.append(w)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if widgets:
            widgets[0].setFocus()  # auto-focus first field
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not widgets[0].text().strip() or not widgets[1].text().strip():
            msg_warn(self, 'Thiếu', f'{fields[0]} và {fields[1]} không được trống')
            return
        # Validate email/SDT format truoc khi POST
        for label, w in zip(fields, widgets):
            val = w.text().strip()
            if not val:
                continue
            if 'mail' in label.lower() and not is_valid_email(val):
                msg_warn(self, 'Sai định dạng', f'{label} không hợp lệ (vd: ten@example.com)')
                return
            if ('SDT' in label or 'điện thoại' in label.lower()) and not is_valid_phone_vn(val):
                msg_warn(self, 'Sai định dạng', f'{label} phải có 10-11 chữ số')
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
        # Col 6 (Thao tac) 140 -> 160 cho 'Chi tiết' (85px) + 'Xóa' (55px) + spacing
        for c, cw in enumerate([75, 170, 170, 115, 195, 90, 160]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 44)

        widen_search(page, 'txtSearchEmp', 300, ['cboEmpRole', 'cboEmpStatus'])
        # search / filter / add - safe_connect
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchEmp')
        if txt:
            safe_connect(txt.textChanged, lambda s: table_filter(tbl, s, cols=[0, 1]))
        # Populate cbo dynamic tu data thuc te (truoc cbo_s co 'Nghỉ phép' nhung
        # FE chi map is_active -> 'Đang làm'/'Đã nghỉ' -> filter 'Nghỉ phép' empty)
        cbo_r = page.findChild(QtWidgets.QComboBox, 'cboEmpRole')
        if cbo_r:
            cbo_r.clear()
            cbo_r.addItem('Tất cả chức vụ')
            seen_r = set()
            for row in data:
                if len(row) > 2 and row[2] and row[2] != '—' and row[2] not in seen_r:
                    seen_r.add(row[2]); cbo_r.addItem(row[2])
        cbo_s = page.findChild(QtWidgets.QComboBox, 'cboEmpStatus')
        if cbo_s:
            cbo_s.clear()
            cbo_s.addItem('Tất cả trạng thái')
            seen_s = set()
            for row in data:
                if len(row) > 5 and row[5] and row[5] not in seen_s:
                    seen_s.add(row[5]); cbo_s.addItem(row[5])
        for nm in ('cboEmpRole', 'cboEmpStatus'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                safe_connect(cbo.currentIndexChanged, lambda: self._admin_filter_employees())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddEmp')
        if btn_add:
            safe_connect(btn_add.clicked, lambda: self._admin_add_user('nhân viên', 5, 'tblAdmEmployees',
                                                                       ['Mã NV', 'Họ tên', 'Chức vụ', 'SDT', 'Email']))
        # Them nut Bulk import NV CSV (idempotent)
        if not page.findChild(QtWidgets.QPushButton, 'btnImportEmpsCSV'):
            btn_imp = QtWidgets.QPushButton('📥 Import CSV', page)
            btn_imp.setObjectName('btnImportEmpsCSV')
            if btn_add:
                geo = btn_add.geometry()
                btn_imp.setGeometry(geo.x() - 145, geo.y(), 135, geo.height())
            else:
                btn_imp.setGeometry(700, 18, 135, 32)
            btn_imp.setCursor(Qt.PointingHandCursor)
            btn_imp.setToolTip('Import nhiều NV từ file CSV (cột: username,password,full_name,ma_nv,email,sdt,chuc_vu,phong_ban,ngay_vao_lam)')
            btn_imp.setStyleSheet(
                f'QPushButton {{ background: white; color: {COLORS["navy"]}; border: 1px solid {COLORS["navy"]}; '
                f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                f'QPushButton:hover {{ background: {COLORS["navy"]}; color: white; }}'
            )
            btn_imp.clicked.connect(self._admin_import_employees_csv)
            btn_imp.show()

    def _admin_import_teachers_csv(self):
        """Import nhieu GV cung luc tu CSV. Header: username,password,full_name,ma_gv,..."""
        self._admin_bulk_import_user_csv(
            user_type='giảng viên',
            required={'username', 'ma_gv', 'full_name'},
            preview_cols=['#', 'Mã GV', 'Họ tên', 'Username', 'Khoa', 'Học vị', 'SDT'],
            preview_keys=['ma_gv', 'full_name', 'username', 'khoa', 'hoc_vi', 'sdt'],
            preview_widths=[35, 90, 200, 130, 150, 100, 100],
            create_fn=lambda d: TeacherService.create(
                # Lowercase username dong bo voi single-add + login flow
                username=(d.get('username') or '').strip().lower(),
                password=d.get('password') or 'pass1234',
                full_name=d.get('full_name'), ma_gv=d.get('ma_gv'),
                email=d.get('email') or None, sdt=d.get('sdt') or None,
                hoc_vi=d.get('hoc_vi') or None, khoa=d.get('khoa') or None,
                chuyen_nganh=d.get('chuyen_nganh') or None,
                tham_nien=int(d.get('tham_nien') or 0),
            ),
            row_id_key='ma_gv',
            reload_idx=4,
            reload_fn=self._fill_admin_teachers,
        )

    def _admin_import_employees_csv(self):
        """Import nhieu NV cung luc tu CSV. Header: username,password,full_name,ma_nv,..."""
        self._admin_bulk_import_user_csv(
            user_type='nhân viên',
            required={'username', 'ma_nv', 'full_name'},
            preview_cols=['#', 'Mã NV', 'Họ tên', 'Username', 'Chức vụ', 'Phòng ban', 'SDT'],
            preview_keys=['ma_nv', 'full_name', 'username', 'chuc_vu', 'phong_ban', 'sdt'],
            preview_widths=[35, 90, 200, 130, 130, 130, 100],
            create_fn=lambda d: EmployeeService.create(
                # Lowercase username dong bo voi single-add + login flow
                username=(d.get('username') or '').strip().lower(),
                password=d.get('password') or 'pass1234',
                full_name=d.get('full_name'), ma_nv=d.get('ma_nv'),
                email=d.get('email') or None, sdt=d.get('sdt') or None,
                chuc_vu=d.get('chuc_vu') or None, phong_ban=d.get('phong_ban') or None,
                ngay_vao_lam=d.get('ngay_vao_lam') or None,
            ),
            row_id_key='ma_nv',
            reload_idx=5,
            reload_fn=self._fill_admin_employees,
        )

    def _admin_bulk_import_user_csv(self, user_type, required, preview_cols, preview_keys,
                                     preview_widths, create_fn, row_id_key, reload_idx, reload_fn):
        """Generic helper: pick CSV -> preview -> bulk loop create -> report.
        Reuse cho cả GV (TeacherService.create) lan NV (EmployeeService.create).
        """
        import csv as _csv
        path, _ext = QtWidgets.QFileDialog.getOpenFileName(
            self, f'Chọn file CSV danh sách {user_type}',
            os.path.join(os.path.expanduser('~'), 'Desktop'),
            'CSV Files (*.csv)'
        )
        if not path:
            return
        rows = []
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = _csv.DictReader(f)
                for r in reader:
                    rows.append({k.strip(): (v or '').strip() for k, v in r.items()})
        except Exception as e:
            msg_warn(self, 'Lỗi đọc file', f'Không đọc được CSV:\n{e}')
            return
        if not rows:
            msg_warn(self, 'Trống', 'File CSV không có dòng nào (cần header dòng đầu).')
            return
        missing = required - set(rows[0].keys())
        if missing:
            msg_warn(self, 'Thiếu cột', f'Thiếu cột bắt buộc: {missing}')
            return

        # Preview dialog
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle(f'Import {user_type} - {len(rows)} dòng')
        dlg.setFixedSize(880, 500)
        v = QtWidgets.QVBoxLayout(dlg)
        head = QtWidgets.QLabel(
            f'<b>File:</b> {os.path.basename(path)}<br>'
            f'<b>Số dòng:</b> {len(rows)} {user_type} · Bấm <b>Import</b> để bắt đầu.<br>'
            f'<i style="color:#718096; font-size:11px;">Dòng nào lỗi (vd mã trùng) sẽ skip + báo cuối.</i>'
        )
        head.setWordWrap(True)
        head.setStyleSheet('background:#edf2f7; padding:10px; border-radius:6px; font-size:12px;')
        v.addWidget(head)

        tbl = QtWidgets.QTableWidget()
        tbl.setColumnCount(len(preview_cols))
        tbl.setHorizontalHeaderLabels(preview_cols)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setRowCount(min(len(rows), 100))
        for r, row in enumerate(rows[:100]):
            items = [str(r + 1)] + [row.get(k, '') or '—' for k in preview_keys]
            for c, val in enumerate(items):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(str(val)))
        for c, w in enumerate(preview_widths):
            tbl.setColumnWidth(c, w)
        if len(rows) > 100:
            head.setText(head.text() + f'<br><b style="color:#c05621;">⚠ Hiển thị 100/{len(rows)} dòng đầu</b>')
        v.addWidget(tbl)

        btns = QtWidgets.QDialogButtonBox()
        btns.addButton(f'⬆ Import {len(rows)}', QtWidgets.QDialogButtonBox.AcceptRole)
        btns.addButton('Huỷ', QtWidgets.QDialogButtonBox.RejectRole)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        v.addWidget(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        if not DB_AVAILABLE:
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống.')
            return

        success = 0
        failed = []
        for i, row in enumerate(rows, 1):
            try:
                create_fn(row)
                success += 1
            except Exception as e:
                err_msg = str(e)
                if '\n' in err_msg:
                    err_msg = err_msg.split('\n')[-1].strip() or err_msg[:200]
                failed.append({'row': i, 'id': row.get(row_id_key, '?'), 'error': err_msg[:200]})

        # Reload
        try:
            self.pages_filled[reload_idx] = False
            reload_fn()
        except Exception:
            pass

        if not failed:
            msg_info(self, 'Thành công', f'✓ Đã import <b>{success}/{len(rows)}</b> {user_type} thành công!')
        else:
            err_lines = [f'• Dòng {f["row"]} ({f["id"]}): {f["error"]}' for f in failed[:15]]
            extra = '' if len(failed) <= 15 else f'\n... và {len(failed)-15} lỗi nữa'
            msg_warn(self, 'Hoàn tất với lỗi',
                     f'Thành công: <b>{success}/{len(rows)}</b><br>'
                     f'Lỗi: <b>{len(failed)}</b><br><br>'
                     f'<pre style="font-size:10px;">' + '\n'.join(err_lines) + extra + '</pre>')


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

        # F5/Ctrl+R: refresh trang hien tai
        install_refresh_shortcut(self)

        # Update sidebar badges initially
        self._update_tea_badges()

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
        add_reload_button(sidebar, self)

        sep = QtWidgets.QFrame(sidebar)
        sep.setGeometry(15, 74, 200, 1)
        sep.setStyleSheet(f'background: {COLORS["border"]};')

        y = 86
        for i, (btn_name, icon_name, icon_file, label) in enumerate(TEACHER_MENU):
            btn = QtWidgets.QPushButton(label, sidebar)
            btn.setObjectName(btn_name)
            btn.setGeometry(10, y, 210, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(SIDEBAR_NORMAL)
            if i < 9:
                btn.setToolTip(f'{label}  ·  Ctrl+{i + 1}')
            else:
                btn.setToolTip(label)
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

        # Hop "Hom nay + Dot" - context-aware UX
        add_sidebar_context_widget(sidebar)

        sep2 = QtWidgets.QFrame(sidebar)
        sep2.setGeometry(15, 610, 200, 1)
        sep2.setStyleSheet(f'background: {COLORS["border"]};')

        lbl_av = QtWidgets.QLabel(MOCK_TEACHER['initials'], sidebar)
        lbl_av.setGeometry(15, 625, 38, 38)
        lbl_av.setAlignment(Qt.AlignCenter)
        lbl_av.setStyleSheet(avatar_style(MOCK_TEACHER['initials']))

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

        # Badge "Bai tap chua cham" - nam o goc btnTeaAssign (idx 7)
        asg_idx = next((i for i, (n, _) in enumerate(TEACHER_PAGES) if n == 'btnTeaAssign'), 7)
        asg_y = 86 + asg_idx * 38
        self.lblTeaAsgBadge = QtWidgets.QLabel('', sidebar)
        self.lblTeaAsgBadge.setObjectName('lblTeaAsgBadge')
        self.lblTeaAsgBadge.setGeometry(192, asg_y + 4, 22, 18)
        self.lblTeaAsgBadge.setAlignment(Qt.AlignCenter)
        self.lblTeaAsgBadge.setStyleSheet(
            'QLabel { background: #d97706; color: white; border-radius: 9px; '
            'font-size: 10px; font-weight: bold; padding: 0px 4px; }'
        )
        self.lblTeaAsgBadge.hide()

        return sidebar

    def _update_tea_badges(self):
        """Update sidebar GV badges - count bai tap chua cham."""
        if not hasattr(self, 'lblTeaAsgBadge'):
            return
        gv_id = MOCK_TEACHER.get('user_id')
        n_to_grade = 0
        if DB_AVAILABLE and gv_id and AssignmentService:
            try:
                rows = AssignmentService.get_by_teacher(gv_id) or []
                for r in rows:
                    so_nop = int(r.get('so_nop', 0) or 0)
                    so_cham = int(r.get('so_cham', 0) or 0)
                    if so_nop > so_cham:
                        n_to_grade += (so_nop - so_cham)
            except Exception as e:
                print(f'[TEA_BADGE] loi: {e}')
        set_sidebar_badge(self.lblTeaAsgBadge, n_to_grade)

    def _load_page(self, ui_file):
        # ui_file=None -> tao QFrame trong de fill bang code (cho trang Bai tap)
        if ui_file is None:
            content = QtWidgets.QFrame()
            content.setObjectName('contentArea')
            content.setFixedSize(870, 700)
            content.setStyleSheet('QFrame#contentArea { background: #edf2f7; }')
            return content
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
                    self._fill_tea_assignments, self._fill_tea_exams,
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

        # Them search box trong attendFrame 1 lan (loc HV theo MSV/ten)
        af = page.findChild(QtWidgets.QFrame, 'attendFrame')
        if af and not af.findChild(QtWidgets.QLineEdit, 'txtAttendSearch'):
            # Shrink title + stats de chừa chỗ search
            lbl_t = af.findChild(QtWidgets.QLabel, 'lblAttendTitle')
            if lbl_t:
                lbl_t.setGeometry(22, 14, 180, 22)
            lbl_st = af.findChild(QtWidgets.QLabel, 'lblAttendStats')
            if lbl_st:
                lbl_st.setGeometry(450, 14, 350, 22)
            txt_s = QtWidgets.QLineEdit(af)
            txt_s.setObjectName('txtAttendSearch')
            txt_s.setGeometry(220, 11, 220, 28)
            txt_s.setPlaceholderText('🔍 Tìm MSV / tên HV...')
            txt_s.setClearButtonEnabled(True)
            txt_s.setStyleSheet('QLineEdit { background: white; border: 1px solid #d2d6dc; '
                                 'border-radius: 4px; padding: 2px 8px; font-size: 12px; } '
                                 'QLineEdit:focus { border-color: #002060; }')
            txt_s.show()
            # Wire 1 lan
            tbl_inner = af.findChild(QtWidgets.QTableWidget, 'tblAttendance')
            if tbl_inner:
                txt_s.textChanged.connect(
                    lambda s, _t=tbl_inner: table_filter(_t, s, cols=[1, 2])
                )

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
                    # Truoc: ScheduleService.create + re-query GET /class/{ma_lop}
                    # roi matched[-1] de lay id - fragile khi co nhieu buoi cung
                    # ngay (ORDER BY ngay nhung khong specify ASC/DESC -> id thu
                    # tu khong dam bao). Backend tra ve {'id': sid} -> dung
                    # truc tiep
                    resp = ScheduleService.create(
                        ma_lop, ngay_val, gio_bd, gio_kt,
                        trang_thai='completed'
                    )
                    buoi_id = resp.get('id') if isinstance(resp, dict) else None
                    if buoi_id:
                        print(f'[TEA_ATTEND] Tao schedule moi cho {ma_lop}, id={buoi_id}')
                    if not buoi_id or buoi_id <= 0:
                        msg_warn(self, 'Lỗi', 'Đã tạo buổi học nhưng không lấy được mã. Vui lòng thử lại.')
                        return
                except Exception as e:
                    print(f'[TEA_ATTEND] Khong tao duoc schedule: {e}')
                    msg_warn(self, 'Lỗi tạo buổi', f'Không thể tạo buổi học mới:\n{api_error_msg(e)}')
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
        if not msg_confirm(self, 'Đăng xuất', 'Bạn có chắc muốn đăng xuất?'):
            return
        clear_session_state()
        self.close()
        self.app_ref.show_login()

    # === TEACHER DATA FILL ===

    def _fill_tea_dashboard(self):
        page = self.page_widgets[0]
        w = page.findChild(QtWidgets.QLabel, 'lblWelcome')
        if w:
            # Hoc vi prefix neu co - map ten day du sang viet tat
            # (DB seed luu 'Tiến sĩ' -> 'TS.' thay vi 'Tiến sĩ.' awkward)
            hv = (MOCK_TEACHER.get('hocvi') or '').strip()
            _HV_MAP = {
                'tien si': 'TS.', 'thac si': 'ThS.',
                'pho giao su': 'PGS.', 'giao su': 'GS.',
                'cu nhan': 'CN.', 'ky su': 'KS.',
            }
            hv_norm = _status_normalize(hv)
            prefix = _HV_MAP.get(hv_norm, f"{hv}. " if hv else '') or "Thầy/Cô "
            if not prefix.endswith(' '):
                prefix += ' '
            w.setText(f"{time_greeting()}, {prefix}{MOCK_TEACHER.get('name', '')}")

        # Header semester label - lay tu DB thay vi hardcode HK
        lbl_sem = page.findChild(QtWidgets.QLabel, 'lblSemester')
        if lbl_sem and DB_AVAILABLE:
            try:
                cur_sem = SemesterService.get_current() if SemesterService else None
                if cur_sem:
                    nm = cur_sem.get('ten') or cur_sem.get('id', '')
                    nh = cur_sem.get('nam_hoc', '')
                    lbl_sem.setText(f'{nm} - Năm {nh}' if nh else nm)
                else:
                    lbl_sem.setText('Khóa học ngoại khoá EAUT')
            except Exception:
                lbl_sem.setText('Khóa học ngoại khoá EAUT')

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
            from datetime import datetime as _dt, time as _time
            data = []
            today_raw = []  # raw rows de double-click hien dialog
            now_t = _dt.now().time()

            def _parse_t(s):
                try:
                    parts = str(s)[:8].split(':')
                    return _time(int(parts[0]), int(parts[1]))
                except Exception:
                    return None

            if DB_AVAILABLE and gv_id and ScheduleService:
                try:
                    today_rows = ScheduleService.get_today() or []
                    for r in today_rows:
                        # filter buoi cua gv hien tai
                        if r.get('gv_id') and r.get('gv_id') != gv_id:
                            continue
                        today_raw.append(r)
                        gio_bd = str(r.get('gio_bat_dau', ''))[:5]
                        gio_kt = str(r.get('gio_ket_thuc', ''))[:5]
                        time_str = f'{gio_bd}-{gio_kt}' if gio_bd else '—'
                        # Status badge dua tren now
                        t_bd = _parse_t(r.get('gio_bat_dau', ''))
                        t_kt = _parse_t(r.get('gio_ket_thuc', ''))
                        status = ''   # '', 'now', 'soon', 'past'
                        badge = ''
                        if t_bd and t_kt:
                            if t_bd <= now_t <= t_kt:
                                status = 'now'
                                badge = '\n🟢 Đang dạy'
                            elif now_t < t_bd:
                                # Tinh phut den buoi
                                bd_min = t_bd.hour * 60 + t_bd.minute
                                now_min = now_t.hour * 60 + now_t.minute
                                left_min = bd_min - now_min
                                if left_min <= 60:
                                    status = 'soon'
                                    badge = f'\n⏳ Còn {left_min} phút'
                                else:
                                    h = left_min // 60
                                    m = left_min % 60
                                    status = 'soon'
                                    badge = f'\n⏳ Còn {h}h{m:02d}'
                            else:
                                status = 'past'
                                badge = '\n✓ Đã dạy'
                        ma_lop = r.get('lop_id', '')
                        ten_mon = r.get('ten_mon', '')
                        data.append([
                            time_str + badge,
                            f'{ma_lop} ({ten_mon})' if ten_mon else ma_lop,
                            r.get('phong', '') or '—',
                            status,  # extra meta - khong hien
                        ])
                except Exception as e:
                    print(f'[TEA_DASH] today loi: {e}')
            # Cache de double-click reuse
            self._tea_today_cache = today_raw

            if not data:
                set_table_empty_state(
                    tbl, 'Hôm nay không có buổi dạy',
                    icon='✓',
                    cta_text='📅 Xem lịch dạy tuần',
                    cta_callback=lambda: self._on_nav(1))
            else:
                tbl.setRowCount(len(data))
                # Status -> background color
                bg_map = {'now': '#dcfce7',    # green 100
                          'soon': '#fef3c7',   # yellow 100
                          'past': '#f7fafc'}   # gray
                fg_map = {'now': '#166534',
                          'soon': '#92400e',
                          'past': '#9ca3af'}
                for r, row in enumerate(data):
                    status = row[3]
                    bg = bg_map.get(status)
                    fg = fg_map.get(status)
                    italic = (status == 'past')
                    bold = (status == 'now')
                    for c in range(3):
                        item = QtWidgets.QTableWidgetItem(row[c])
                        item.setTextAlignment(Qt.AlignCenter if c != 1 else Qt.AlignLeft | Qt.AlignVCenter)
                        if bg:
                            item.setBackground(QColor(bg))
                        if fg:
                            item.setForeground(QColor(fg))
                        if italic or bold:
                            f = item.font()
                            if bold: f.setBold(True)
                            if italic: f.setItalic(True)
                            item.setFont(f)
                        tbl.setItem(r, c, item)
                for r in range(len(data)):
                    has_badge = '\n' in data[r][0]
                    tbl.setRowHeight(r, 50 if has_badge else 38)

                # Wire double-click row -> popup show all today sessions (1 lan)
                if not getattr(self, '_tea_today_dblclick_wired', False):
                    tbl.cellDoubleClicked.connect(
                        lambda *_: show_today_sessions_dialog(
                            self, getattr(self, '_tea_today_cache', []), role='gv'
                        )
                    )
                    self._tea_today_dblclick_wired = True
                # Tooltip hint user
                for r in range(len(data)):
                    if tbl.item(r, 0):
                        tbl.item(r, 0).setToolTip('Double-click để xem chi tiết tất cả buổi dạy hôm nay')
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setColumnWidth(0, 110)
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
                        t_str = fmt_relative_date(n.get('ngay_tao'))
                        # Target priority: HV cu the > lop > broadcast
                        if n.get('den_hv_id'):
                            target = f"HV {n.get('ten_hv_dich') or '?'}"
                        elif n.get('den_lop'):
                            target = n['den_lop']
                        else:
                            target = 'Tất cả'
                        data.append((t_str, f"Đã gửi '{n.get('tieu_de', '')}' đến {target}"))
                except Exception as e:
                    print(f'[TEA_DASH] activity loi: {e}')
            if not data:
                set_table_empty_state(tbl2, 'Chưa có hoạt động')
            else:
                tbl2.setRowCount(len(data))
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

        # === 3 stat cards clickable -> jump to detail page (1 lan) ===
        # statCard4 = Diem danh gia -> khong co page tuong ung -> bo qua
        if not getattr(self, '_tea_stat_cards_wired', False):
            stat_to_idx = {
                'statCard1': (2, 'Đi đến trang Lớp của tôi'),
                'statCard2': (3, 'Đi đến trang Học viên'),
                'statCard3': (1, 'Đi đến trang Lịch dạy'),
            }
            base_style = ('QFrame#{name} {{ background: white; border: 1px solid #d2d6dc; border-radius: 10px; }} '
                          'QFrame#{name}:hover {{ border: 2px solid #002060; background: #f0f7ff; }}')
            for name, (idx, tip) in stat_to_idx.items():
                card = page.findChild(QtWidgets.QFrame, name)
                if not card:
                    continue
                card.setCursor(Qt.PointingHandCursor)
                card.setStyleSheet(base_style.format(name=name))
                card.setToolTip(tip)
                def _make_click(_idx):
                    def _click(ev):
                        if ev.button() == Qt.LeftButton:
                            self._on_nav(_idx)
                    return _click
                card.mousePressEvent = _make_click(idx)
            self._tea_stat_cards_wired = True

        # Render banner "Bai tap chua cham" o giua stat cards va todayFrame
        self._render_grade_alert_banner_gv(page)

    def _render_grade_alert_banner_gv(self, page):
        """Banner alert "X bai tap can cham" tren GV dashboard.

        Dat o y=242 (giua stat cards va todayFrame). Push todayFrame + activityFrame
        xuong 36px neu show, reset neu khong.
        """
        # Cleanup banner cu
        cleanup_banner(page, 'gradeAlertBannerGV')

        gv_id = MOCK_TEACHER.get('user_id')
        n_to_grade = 0
        n_total_pending = 0  # tong submission chua cham (bao gom da co diem nhung sua = 0)
        if DB_AVAILABLE and gv_id and AssignmentService:
            try:
                rows = AssignmentService.get_by_teacher(gv_id) or []
                for r in rows:
                    so_nop = int(r.get('so_nop', 0) or 0)
                    so_cham = int(r.get('so_cham', 0) or 0)
                    diff = max(0, so_nop - so_cham)
                    if diff > 0:
                        n_to_grade += 1
                        n_total_pending += diff
            except Exception as e:
                print(f'[TEA_DASH_GRADE] loi: {e}')

        # Helper push frames + reset
        def _push_frames(shift_y):
            for fname in ('todayFrame', 'activityFrame'):
                fr = page.findChild(QtWidgets.QFrame, fname)
                if fr:
                    g = fr.geometry()
                    new_y = 254 + shift_y
                    new_h = max(420 - shift_y, 200)
                    if g.y() != new_y or g.height() != new_h:
                        fr.setGeometry(g.x(), new_y, g.width(), new_h)
                    # tblToday + tblActivity inside frame: keep children y
                    # Recompute: original tbl y=44 -> stays 44 (relative)

        if n_to_grade <= 0:
            _push_frames(0)
            return

        banner = QtWidgets.QFrame(page)
        banner.setObjectName('gradeAlertBannerGV')
        banner.setGeometry(25, 242, 820, 38)
        banner.setStyleSheet(
            'QFrame#gradeAlertBannerGV { background: #fef3c7; border: 1px solid #d97706; '
            'border-left: 4px solid #c05621; border-radius: 8px; }'
        )
        banner.setCursor(Qt.PointingHandCursor)

        text = (f'📝  Bạn có <b>{n_to_grade}</b> bài tập có HV nộp chưa chấm  ·  '
                f'tổng <b style="color:#9a3412;">{n_total_pending}</b> bài cần xử lý'
                f'  ·  <span style="color:#1e3a8a;">click để chấm ngay</span>')

        lbl = QtWidgets.QLabel(text, banner)
        lbl.setGeometry(15, 0, 800, 38)
        lbl.setStyleSheet('color: #9a3412; font-size: 12px; background: transparent; border: none;')
        lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        lbl.setTextFormat(Qt.RichText)
        lbl.setCursor(Qt.PointingHandCursor)
        banner.setToolTip(f'{n_total_pending} bài tập cần chấm — click để vào trang Bài tập')

        def _click(ev):
            if ev.button() == Qt.LeftButton:
                # btnTeaAssign idx 7 trong TEACHER_PAGES
                self._on_nav(7)
        banner.mousePressEvent = _click
        lbl.mousePressEvent = _click
        banner.show()

        # Push 2 frames xuong
        _push_frames(36)

    def _fill_tea_schedule(self):
        # tái sử dụng schedule.ui giống HV nhưng lịch của GV
        page = self.page_widgets[1]

        hb = page.findChild(QtWidgets.QFrame, 'headerBar')
        if hb:
            hb.setGeometry(0, 0, 870, 56)
            # Sua title "Lich hoc" -> "Lich day" cho GV (UI .ui dung chung voi HV)
            title_lbl = hb.findChild(QtWidgets.QLabel, 'lblPageTitle')
            if title_lbl and title_lbl.text().strip() == 'Lịch học':
                title_lbl.setText('Lịch dạy')
            # An lblWeekRange (overlap voi cum Loc + cboFilter, info nay co o panel ben phai roi)
            wr_old = page.findChild(QtWidgets.QLabel, 'lblWeekRange')
            if wr_old:
                wr_old.hide()
            # Combo loc lop - dat truoc cum nut
            if not hb.findChild(QtWidgets.QComboBox, 'cboTeaSchedFilter'):
                lbl_f = QtWidgets.QLabel('Lọc:', hb)
                lbl_f.setObjectName('lblTeaSchedFilter')
                lbl_f.setGeometry(170, 18, 38, 24)
                lbl_f.setStyleSheet('color: #4a5568; font-size: 12px; font-weight: bold; background: transparent;')
                lbl_f.show()
                cbo = QtWidgets.QComboBox(hb)
                cbo.setObjectName('cboTeaSchedFilter')
                cbo.setGeometry(210, 12, 220, 32)
                cbo.setCursor(Qt.PointingHandCursor)
                cbo.setStyleSheet('QComboBox { background: white; border: 1px solid #d2d6dc; '
                                   'border-radius: 6px; padding: 4px 10px; font-size: 12px; } '
                                   'QComboBox:hover { border-color: #002060; } '
                                   'QComboBox::drop-down { border: none; padding-right: 6px; }')
                cbo.show()
            # Them nut "In tuan PDF" - dat truoc cum nut export
            if not hb.findChild(QtWidgets.QPushButton, 'btnTeaPrintSched'):
                btn_pdf = QtWidgets.QPushButton('🖨 In tuần', hb)
                btn_pdf.setObjectName('btnTeaPrintSched')
                btn_pdf.setGeometry(440, 12, 110, 32)
                btn_pdf.setCursor(Qt.PointingHandCursor)
                btn_pdf.setToolTip('In lịch dạy tuần đang xem ra PDF')
                btn_pdf.setStyleSheet(
                    'QPushButton { background: #c05621; color: white; border: none; '
                    'border-radius: 6px; font-size: 12px; font-weight: bold; } '
                    'QPushButton:hover { background: #9c4419; }'
                )
                btn_pdf.clicked.connect(self._tea_export_schedule_week_pdf)
                btn_pdf.show()
            # Them nut "Xuat lich .ics" 1 lan
            if not hb.findChild(QtWidgets.QPushButton, 'btnTeaExportICS'):
                btn_ics = QtWidgets.QPushButton('📅 Xuất .ics', hb)
                btn_ics.setObjectName('btnTeaExportICS')
                btn_ics.setGeometry(560, 12, 130, 32)
                btn_ics.setCursor(Qt.PointingHandCursor)
                btn_ics.setToolTip('Xuất lịch dạy sang .ics để import vào Google/Apple Calendar')
                btn_ics.setStyleSheet(
                    f'QPushButton {{ background: {COLORS["green"]}; color: white; border: none; '
                    f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                    f'QPushButton:hover {{ background: {COLORS["green_hover"]}; }}'
                )
                btn_ics.clicked.connect(self._tea_export_ics)
                btn_ics.show()
            # Them nut "+ Tao buoi hoc" o header (1 lan, tranh duplicate)
            if not hb.findChild(QtWidgets.QPushButton, 'btnNewSched'):
                btn_new = QtWidgets.QPushButton('+ Tạo buổi học', hb)
                btn_new.setObjectName('btnNewSched')
                btn_new.setGeometry(710, 12, 140, 32)
                btn_new.setCursor(Qt.PointingHandCursor)
                btn_new.setStyleSheet(
                    'QPushButton { background: #002060; color: white; border: none; '
                    'border-radius: 6px; font-size: 12px; font-weight: bold; } '
                    'QPushButton:hover { background: #001a50; }'
                )
                btn_new.clicked.connect(self._tea_dialog_new_schedule)
                btn_new.show()
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

            # Nut chon ngay tuy y -> jump tuan chua ngay do
            btn_goto = QtWidgets.QPushButton('📅 Chọn ngày...', cf)
            btn_goto.setObjectName('btnGotoWeek')
            btn_goto.setGeometry(15, 170, 195, 30)
            btn_goto.setStyleSheet('QPushButton { background: white; color: #c05621; border: 1px solid #c05621; border-radius: 6px; font-size: 11px; font-weight: bold; } QPushButton:hover { background: #fef5f0; }')
            btn_goto.setCursor(Qt.PointingHandCursor)
            btn_goto.setToolTip('Mở lịch để chọn 1 ngày bất kỳ - tự động nhảy đến tuần chứa ngày đó')
            btn_goto.show()

            hint = QtWidgets.QLabel('Click "Chọn ngày..." để xem tuần xa', cf)
            hint.setObjectName('lblNavHint')
            hint.setGeometry(15, 207, 195, 18)
            hint.setStyleSheet('color: #a0aec0; font-size: 9px; background: transparent;')
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

        # KHONG tao lblWeekRange cho GV - thong tin tuan da co o "Dieu huong tuan" panel ben phai
        # (truoc day se overlap voi cboTeaSchedFilter + nut In tuan/Xuat ics/Tao buoi hoc)

        today = QDate.currentDate()
        self._tea_current_monday = today.addDays(-(today.dayOfWeek() - 1))
        gv_id = MOCK_TEACHER.get('user_id')
        if DB_AVAILABLE and gv_id:
            try:
                near = ScheduleService.nearest_week_for_teacher(gv_id, today.toPyDate())
                near_d = parse_iso_date(near)
                if near_d:
                    self._tea_current_monday = QDate(near_d.year, near_d.month, near_d.day)
            except Exception as e:
                print(f'[TEA_SCHED] nearest_week loi: {e}')
        self._load_teacher_schedule_week(page, tbl, self._tea_current_monday, hours, days_vn)

        # Wire prev/next/today buttons (debounce: disable nut khi dang load chong spam)
        btn_prev = cf.findChild(QtWidgets.QPushButton, 'btnPrevWeek') if cf else None
        btn_next = cf.findChild(QtWidgets.QPushButton, 'btnNextWeek') if cf else None
        btn_today = cf.findChild(QtWidgets.QPushButton, 'btnTodayWeek') if cf else None
        nav_btns = [b for b in (btn_prev, btn_next, btn_today) if b]

        def _reload_with_debounce(new_monday):
            self._tea_current_monday = new_monday
            for b in nav_btns:
                b.setEnabled(False)
            QtWidgets.QApplication.processEvents()
            try:
                self._load_teacher_schedule_week(page, tbl, self._tea_current_monday, hours, days_vn)
            finally:
                for b in nav_btns:
                    b.setEnabled(True)

        if btn_prev:
            btn_prev.clicked.connect(lambda: _reload_with_debounce(self._tea_current_monday.addDays(-7)))
        if btn_next:
            btn_next.clicked.connect(lambda: _reload_with_debounce(self._tea_current_monday.addDays(7)))
        if btn_today:
            btn_today.clicked.connect(lambda: _reload_with_debounce(
                QDate.currentDate().addDays(-(QDate.currentDate().dayOfWeek() - 1))
            ))

        # Wire nut "Chon ngay..." GV -> mo dialog -> jump
        btn_goto = cf.findChild(QtWidgets.QPushButton, 'btnGotoWeek') if cf else None
        if btn_goto:
            def _on_tea_goto():
                picked = pick_week_jumper_dialog(self, self._tea_current_monday)
                if picked:
                    new_mon = picked.addDays(-(picked.dayOfWeek() - 1))
                    _reload_with_debounce(new_mon)
            btn_goto.clicked.connect(_on_tea_goto)

        # Populate combo loc lop GV
        cbo_filter = hb.findChild(QtWidgets.QComboBox, 'cboTeaSchedFilter') if hb else None
        if cbo_filter is not None and cbo_filter.count() == 0:
            cbo_filter.blockSignals(True)
            cbo_filter.addItem('Tất cả lớp', None)
            if DB_AVAILABLE and gv_id and CourseService:
                try:
                    my_classes = CourseService.get_classes_by_teacher(gv_id) or []
                    seen = set()
                    for r in my_classes:
                        ma = r.get('ma_lop')
                        if ma and ma not in seen:
                            seen.add(ma)
                            ten = r.get('ten_mon', '') or ''
                            label = f'{ma} · {ten}' if ten else ma
                            cbo_filter.addItem(label, ma)
                except Exception as e:
                    print(f'[TEA_SCHED] populate filter loi: {e}')
            cbo_filter.blockSignals(False)
            cbo_filter.currentIndexChanged.connect(
                lambda idx: (
                    setattr(self, '_tea_sched_filter', cbo_filter.itemData(idx)),
                    self._load_teacher_schedule_week(page, tbl, self._tea_current_monday, hours, days_vn),
                )
            )

    def _load_teacher_schedule_week(self, page, tbl, monday, hours, days_vn):
        """Reload lich day GV cho tuan bat dau bang `monday` (QDate)."""
        # Highlight cot HOM NAY (đồng nhất với HV schedule)
        today = QDate.currentDate()
        for i in range(6):
            d = monday.addDays(i)
            hi = tbl.horizontalHeaderItem(i+1)
            if hi:
                is_today = (d == today)
                prefix = '● ' if is_today else ''
                hi.setText(f'{prefix}{d.toString("dd/MM/yyyy")}\n{days_vn[i]}')
                if is_today:
                    hi.setForeground(QColor('#002060'))
                    f = hi.font(); f.setBold(True); hi.setFont(f)
                else:
                    hi.setForeground(QColor('#4a5568'))
                    f = hi.font(); f.setBold(False); hi.setFont(f)
        wr_lbl = page.findChild(QtWidgets.QLabel, 'lblWeekRange')
        if wr_lbl:
            # Set format=RichText 1 lan o day - sau setText voi HTML moi parse dung
            wr_lbl.setTextFormat(Qt.RichText)
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

        def mk(ma_lop, ten_mon, ts, phong, ss, color, ngay_str='', sched_row=None):
            f = QtWidgets.QFrame()
            f.setStyleSheet(f'QFrame {{ background: white; border: 1px solid #d2d6dc; border-radius: 4px; border-top: 3px solid {color}; margin: 1px; }}')
            f.setCursor(Qt.PointingHandCursor)
            # Skip prefix 'P. ' khi phong = '—' (placeholder); avoid 'P. —' awkward
            phong_low = (phong or '').lower()
            if not phong or phong == '—':
                phong_disp = '—'
            elif phong_low.startswith(('p.', 'p ', 'phòng', 'phong')):
                phong_disp = phong
            else:
                phong_disp = f'P. {phong}'
            tip = (
                f'<b style="color:{color};">{ma_lop}</b><br>'
                f'<b>{ten_mon}</b><br>'
                f'<span style="color:#718096;">━━━━━━━━━━━━</span><br>'
                f'🕒 <b>{ts}</b>{("<br>📅 " + ngay_str) if ngay_str else ""}<br>'
                f'📍 {phong_disp}<br>'
                f'👥 {ss}<br>'
                f'<span style="color:#a0aec0; font-size:10px;">━━━ Click để xem chi tiết ━━━</span>'
            )
            f.setToolTip(tip)
            # Click vao card -> popup chi tiet buoi day
            if sched_row is not None:
                def _click(ev, _r=sched_row):
                    if ev.button() == Qt.LeftButton:
                        self._tea_show_session_detail(_r)
                f.mousePressEvent = _click
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
                # Filter neu user da chon 1 lop trong combo cboTeaSchedFilter
                sel_lop = getattr(self, '_tea_sched_filter', None)
                if sel_lop:
                    rows = [r for r in rows if r.get('lop_id') == sel_lop]
                colors = ['#002060', '#c68a1e', '#276749', '#c53030', '#3182ce']
                color_by_lop = {}
                from datetime import date as _date
                for r in rows:
                    try:
                        d = parse_iso_date(r.get('ngay'))
                        if d is None: continue
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
                            d.strftime('%d/%m/%Y') if hasattr(d, 'strftime') else str(d),
                            r,  # raw row de show detail dialog
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
            for rs, span, col, ma_lop, ten_mon, ts, phong, ss, color, ngay_str, raw in sched:
                tbl.setCellWidget(rs, col, mk(ma_lop, ten_mon, ts, phong, ss, color, ngay_str, raw))
                tbl.setSpan(rs, col, span, 1)

        # Update lblWeekRange GV voi count buoi + so lop
        wr_lbl_gv = page.findChild(QtWidgets.QLabel, 'lblWeekRange')
        if wr_lbl_gv:
            n_sessions = len(sched)
            n_lops = len({tup[3] for tup in sched if len(tup) > 3 and tup[3]})
            base = f'Tuần: {monday.toString("dd/MM/yyyy")} → {monday.addDays(5).toString("dd/MM/yyyy")}'
            # textFormat=RichText da set o tren khi findChild
            if n_sessions > 0:
                wr_lbl_gv.setText(f'{base}  ·  <b style="color:#002060;">{n_sessions}</b> buổi'
                                    f'  ·  <b style="color:#c05621;">{n_lops}</b> lớp')
            else:
                wr_lbl_gv.setText(f'{base}  ·  <span style="color:#a0aec0;">không có buổi</span>')

        # Update legend frame voi cac lop dang day
        self._update_tea_schedule_legend(page, sched)

    def _update_tea_schedule_legend(self, page, sched):
        """Update legend1-5 + legendTxt1-5 trong legendFrame GV.
        Sched format GV: (..., ma_lop, ten_mon, ts, phong, ss, color, ngay_str, raw)
        """
        lf = page.findChild(QtWidgets.QFrame, 'legendFrame')
        if not lf:
            return
        seen = {}
        for tup in sched or []:
            try:
                ma_lop = tup[3]
                ten_mon = tup[4]
                color = tup[8]
            except (IndexError, TypeError):
                continue
            if ma_lop and ma_lop not in seen:
                seen[ma_lop] = (color, ten_mon)
        items = list(seen.items())[:5]
        for i in range(1, 6):
            chip = lf.findChild(QtWidgets.QLabel, f'legend{i}')
            txt = lf.findChild(QtWidgets.QLabel, f'legendTxt{i}')
            if i <= len(items):
                ma_lop, (color, ten_mon) = items[i - 1]
                if chip:
                    chip.setStyleSheet(f'background: {color}; border-radius: 2px;')
                    chip.show()
                if txt:
                    label = ma_lop
                    if ten_mon:
                        ten_short = ten_mon if len(ten_mon) <= 18 else ten_mon[:16] + '…'
                        label = f'{ma_lop} · {ten_short}'
                    txt.setText(label)
                    txt.setToolTip(f'{ma_lop} — {ten_mon}' if ten_mon else ma_lop)
                    txt.show()
            else:
                if chip: chip.hide()
                if txt: txt.hide()
        lbl_title = lf.findChild(QtWidgets.QLabel, 'lblLegendTitle')
        if lbl_title:
            n = len(items)
            if n == 0:
                lbl_title.setText('Chú thích (chưa có lớp)')
            elif n < len(seen):
                lbl_title.setText(f'Chú thích ({n}/{len(seen)} lớp)')
            else:
                lbl_title.setText(f'Chú thích ({n} lớp)')

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
            ma, mmon, tmon, gv, lich, phong, smax, siso, gia, *_ = cls
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
            gia_item = QtWidgets.QTableWidgetItem(fmt_vnd(gia))
            gia_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            gia_item.setForeground(QColor(COLORS['gold']))
            tbl.setItem(r, 5, gia_item)
            # action: 3 nut text-only - emoji 📅/🖨 trong text gay font fallback (Segoe UI Emoji)
            # khong khop QPushButton font 'Segoe UI' bold -> chu trong nut nhin sai font.
            # Doi sang 'Lịch' / 'In DS' text-only + emoji vao tooltip
            cell, (btn_detail, btn_sched, btn_print) = make_action_cell(
                [('Chi tiết', 'navy'), ('Lịch', 'green'), ('In DS', 'gold')], spacing=4
            )
            tbl.setCellWidget(r, 6, cell)
            btn_detail.clicked.connect(lambda ch, m=ma, n=tmon, s=siso, mx=smax, p=phong, l=lich, g=gia:
                show_detail_dialog(self, 'Chi tiết lớp', [
                    ('Mã lớp', m), ('Khóa học', n), ('Giảng viên', MOCK_TEACHER['name']),
                    ('Lịch học', l), ('Phòng', p),
                    ('Sĩ số', f'{s}/{mx}'),
                    ('Học phí', fmt_vnd(g)),
                ], avatar_text=m, subtitle=n))
            btn_sched.setToolTip(f'📅 Xem toàn bộ lịch của lớp {ma}')
            btn_sched.clicked.connect(lambda ch, m=ma, n=tmon: self._tea_show_class_full_schedule(m, n))
            btn_print.setToolTip(f'🖨 In danh sách học viên lớp {ma} ra PDF')
            btn_print.clicked.connect(lambda ch, m=ma: self._tea_print_class_roster(m))
        # Tang col 6 (Thao tac) cho fit 3 nut text-only (Chi tiết 85 + Lịch 65 + In DS 65 + 2*spacing 4 = 223)
        for c, cw in enumerate([70, 145, 65, 105, 55, 95, 230]):
            tbl.setColumnWidth(c, cw)
        tbl.horizontalHeader().setStretchLastSection(False)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(my_classes)):
            tbl.setRowHeight(r, 44)

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
                    # Map trang thai DB -> tieng Viet hien thi (truoc chi check 'paid'
                    # -> 'completed' bi nham hien 'Cho TT' -> GV thay HV da hoan thanh
                    # van bao 'cho thanh toan' -> confusing)
                    _ST_VN = {
                        'paid': 'Đang học',
                        'pending_payment': 'Chờ TT',
                        'completed': 'Hoàn thành',
                    }
                    data = []
                    for i, s in enumerate(rows, start=1):
                        st_raw = s.get('trang_thai', '')
                        status = _ST_VN.get(st_raw, st_raw or '—')
                        data.append([str(i), s['msv'], s['full_name'],
                                     s.get('lop_id', ''), s.get('sdt') or '—', status])
            except Exception as e:
                print(f'[TEA_STU] DB loi: {e}')
        if not data:
            data = []
        tbl.setRowCount(len(data))
        for r, row in enumerate(data):
            # Row 44px - du cho chu trang thai (khong pill nua)
            tbl.setRowHeight(r, 44)
            for c, val in enumerate(row[:5]):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c in (0, 3) else Qt.AlignLeft | Qt.AlignVCenter)
                tbl.setItem(r, c, item)
            # Cot Trang thai: style item voi mau + bold (truc tiep, khong widget)
            item_st = QtWidgets.QTableWidgetItem(row[5])
            style_status_item(item_st, row[5])
            tbl.setItem(r, 5, item_st)
        tbl.horizontalHeader().setStretchLastSection(True)
        # Cot 5 (Trang thai badge "Đang học"/"Chờ TT"): vua du fit pill
        for c, cw in enumerate([45, 100, 200, 90, 130, 130]):
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
        if cbo is not None:
            cbo.clear()
            cbo.addItem('📢 Tất cả lớp đang dạy', None)  # userData=None -> broadcast
            # Lay lop GV dang day - uu tien API, fallback theo ten
            gv_id = MOCK_TEACHER.get('user_id')
            classes_loaded = []
            if DB_AVAILABLE and gv_id:
                try:
                    rows = CourseService.get_classes_by_teacher(gv_id)
                    for r in rows:
                        cbo.addItem(f"📚 Lớp {r['ma_lop']}", r['ma_lop'])  # userData=lop_id (str)
                        classes_loaded.append(r['ma_lop'])
                except Exception as e:
                    print(f'[TEA_NOTICE] DB loi lop: {e}')
            if not classes_loaded:
                gv_name = MOCK_TEACHER.get('name', '')
                for cls in MOCK_CLASSES:
                    if cls[3] == gv_name:
                        cbo.addItem(f'📚 Lớp {cls[0]}', cls[0])
                        classes_loaded.append(cls[0])

            # Them tung HV cua tat ca lop GV day -> gui thong bao rieng
            if DB_AVAILABLE and gv_id and classes_loaded:
                try:
                    students = CourseService.get_students_by_teacher(gv_id) or []
                    if students:
                        # Separator
                        cbo.insertSeparator(cbo.count())
                        # De-dup HV (1 HV co the o nhieu lop GV day)
                        seen = set()
                        for s in students:
                            uid = s.get('user_id') or s.get('hv_id')
                            if uid in seen:
                                continue
                            seen.add(uid)
                            label = f"👤 {s.get('full_name', '?')} ({s.get('msv', '?')})"
                            cbo.addItem(label, uid)  # userData=hv_user_id (int)
                except Exception as e:
                    print(f'[TEA_NOTICE] DB loi HV: {e}')

        # Sent panel: them search box + counter, push scroll xuong de chua
        sf = page.findChild(QtWidgets.QFrame, 'sentFrame')
        if sf and not sf.findChild(QtWidgets.QLineEdit, 'txtSentSearch'):
            # Update title gon hon
            lbl_t = sf.findChild(QtWidgets.QLabel, 'lblSentTitle')
            if lbl_t:
                lbl_t.setText('Đã gửi')
                lbl_t.setGeometry(22, 14, 80, 22)
            # Counter "X/Y" canh ben title
            lbl_cnt = QtWidgets.QLabel('— / —', sf)
            lbl_cnt.setObjectName('lblTeaSentCount')
            lbl_cnt.setGeometry(110, 16, 70, 18)
            lbl_cnt.setStyleSheet('color: #4a5568; font-size: 10px; font-weight: bold; '
                                   'background: #f7fafc; border: 1px solid #e2e8f0; '
                                   'border-radius: 4px; padding: 1px 6px;')
            lbl_cnt.setAlignment(Qt.AlignCenter)
            # Nut "Xoa tat ca" icon-only o goc phai title row
            btn_clr = QtWidgets.QPushButton('🗑', sf)
            btn_clr.setObjectName('btnTeaClearAllSent')
            btn_clr.setGeometry(245, 12, 38, 26)
            btn_clr.setCursor(Qt.PointingHandCursor)
            btn_clr.setToolTip('Xóa tất cả thông báo đã gửi (sau filter)')
            btn_clr.setStyleSheet(
                'QPushButton { background: white; color: #c53030; border: 1px solid #c53030; '
                'border-radius: 4px; font-size: 12px; font-weight: bold; } '
                'QPushButton:hover { background: #c53030; color: white; }'
            )
            btn_clr.clicked.connect(self._tea_clear_all_sent_notice)
            btn_clr.show()
            # Search box
            txt_s = QtWidgets.QLineEdit(sf)
            txt_s.setObjectName('txtSentSearch')
            txt_s.setGeometry(22, 42, 260, 28)
            txt_s.setPlaceholderText('🔍 Tìm tiêu đề / nội dung / lớp...')
            txt_s.setClearButtonEnabled(True)
            txt_s.setStyleSheet('QLineEdit { background: white; border: 1px solid #d2d6dc; '
                                 'border-radius: 4px; padding: 2px 8px; font-size: 11px; } '
                                 'QLineEdit:focus { border-color: #002060; }')
            txt_s.show()
            # Push scroll area xuong duoi search
            ss = sf.findChild(QtWidgets.QScrollArea, 'sentScroll')
            if ss:
                g = ss.geometry()
                ss.setGeometry(g.x(), 78, g.width(), max(g.height() - 34, 250))
            # Wire search -> re-render
            txt_s.textChanged.connect(lambda _t: self._render_tea_sent_notices())

        # Populate sent list - lay tu API NotificationService.get_sent_by_teacher()
        sc = page.findChild(QtWidgets.QWidget, 'sentContent')
        if sc:
            sc.setMinimumHeight(500)
            if sc.layout() is None:
                vlay = QtWidgets.QVBoxLayout(sc)
                vlay.setContentsMargins(4, 4, 4, 4)
                vlay.setSpacing(8)
            else:
                vlay = sc.layout()
            self._tea_notice_layout = vlay

            self._tea_sent_cache = []
            gv_id = MOCK_TEACHER.get('user_id')
            if DB_AVAILABLE and gv_id:
                try:
                    # Tang limit tu 10 -> 100 de search xuyen suot history
                    rows = NotificationService.get_sent_by_teacher(gv_id, limit=100) or []
                    self._tea_sent_cache = rows
                except Exception as e:
                    print(f'[TEA_NOTICE] sent loi: {e}')

            self._render_tea_sent_notices()

        # Style cho txtSubject + txtContent - .ui khong co styleSheet -> inherit
        # default Qt khien border khong ro, user khong thay ranh gioi field + co the
        # khong biet la editable. Apply explicit border + focus + bg trang.
        txt_subj = page.findChild(QtWidgets.QLineEdit, 'txtSubject')
        if txt_subj and not txt_subj.styleSheet():
            txt_subj.setStyleSheet(
                'QLineEdit { background: white; border: 1px solid #d2d6dc; '
                'border-radius: 6px; padding: 8px 12px; font-size: 13px; '
                'color: #1a1a2e; } '
                'QLineEdit:focus { border-color: #002060; }'
            )
        txt_ct = page.findChild(QtWidgets.QTextEdit, 'txtContent')
        if txt_ct and not txt_ct.styleSheet():
            txt_ct.setStyleSheet(
                'QTextEdit { background: white; border: 1px solid #d2d6dc; '
                'border-radius: 6px; padding: 8px 12px; font-size: 13px; '
                'color: #1a1a2e; } '
                'QTextEdit:focus { border: 1px solid #002060; }'
            )
            txt_ct.setReadOnly(False)  # explicit - tranh truong hop bi inherit readonly
            txt_ct.setEnabled(True)

        # nut gui / clear - safe_connect tranh accumulation
        btn_send = page.findChild(QtWidgets.QPushButton, 'btnSendNotice')
        if btn_send:
            safe_connect(btn_send.clicked, self._tea_send_notice)
        btn_clear = page.findChild(QtWidgets.QPushButton, 'btnClearNotice')
        if btn_clear:
            safe_connect(btn_clear.clicked, self._tea_clear_notice)

    def _make_notice_card(self, to, subj, t, notif_id=None):
        card = QtWidgets.QFrame()
        card.setFixedHeight(82)
        card.setStyleSheet('QFrame { background: #f7fafc; border-radius: 6px; border-left: 3px solid #002060; }')

        # Hop chua header row (target + nut Xoa) + 2 row noi dung
        vb = QtWidgets.QVBoxLayout(card)
        vb.setContentsMargins(10, 8, 10, 8)
        vb.setSpacing(3)

        # Header row: target label (left) + delete button (right)
        hb = QtWidgets.QHBoxLayout()
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(6)
        l1 = QtWidgets.QLabel(f'→ {to}')
        l1.setStyleSheet(f'color: {COLORS["navy"]}; font-size: 11px; font-weight: bold; background: transparent; border: none;')
        hb.addWidget(l1)
        hb.addStretch(1)
        if notif_id is not None:
            btn_del = QtWidgets.QPushButton('🗑')
            btn_del.setFixedSize(22, 22)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setToolTip('Xóa thông báo này')
            btn_del.setStyleSheet(
                'QPushButton { background: transparent; border: 1px solid transparent; '
                'border-radius: 4px; font-size: 11px; color: #a0aec0; padding: 0; } '
                'QPushButton:hover { background: #fee2e2; border-color: #c53030; color: #c53030; }'
            )
            btn_del.clicked.connect(
                lambda ch, _id=notif_id, _td=subj: self._tea_delete_sent_notice(_id, _td)
            )
            hb.addWidget(btn_del)
        vb.addLayout(hb)

        l2 = QtWidgets.QLabel(subj)
        l2.setStyleSheet('color: #1a1a2e; font-size: 12px; background: transparent; border: none;')
        l2.setWordWrap(True)
        l3 = QtWidgets.QLabel(t)
        l3.setStyleSheet(f'color: {COLORS["text_light"]}; font-size: 10px; background: transparent; border: none;')
        vb.addWidget(l2)
        vb.addWidget(l3)
        return card

    def _tea_delete_sent_notice(self, notif_id, tieu_de=''):
        """GV xoa 1 thong bao da gui."""
        if not msg_confirm_delete(self, 'thông báo đã gửi', str(notif_id),
                                   item_name=tieu_de[:40] if tieu_de else ''):
            return
        if not (DB_AVAILABLE and NotificationService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        try:
            NotificationService.delete(notif_id)
        except Exception as e:
            msg_warn(self, 'Không xóa được', api_error_msg(e))
            return
        # Update cache + re-render
        cache = getattr(self, '_tea_sent_cache', []) or []
        self._tea_sent_cache = [n for n in cache if n.get('id') != notif_id]
        self._render_tea_sent_notices()

    def _tea_clear_all_sent_notice(self):
        """GV bulk delete thong bao da gui sau filter."""
        page = self.page_widgets[5]
        sf = page.findChild(QtWidgets.QFrame, 'sentFrame')
        txt_s = sf.findChild(QtWidgets.QLineEdit, 'txtSentSearch') if sf else None
        # Dung norm() bo dau de match diacritic / khong dau dong nhat
        kw = norm(txt_s.text() if txt_s else '')

        cache = getattr(self, '_tea_sent_cache', []) or []
        target = list(cache)
        if kw:
            target = [n for n in target
                      if kw in norm(n.get('tieu_de', '') or '')
                      or kw in norm(n.get('noi_dung', '') or '')
                      or kw in norm(n.get('den_lop', '') or '')]

        if not target:
            msg_warn(self, 'Không có gì để xóa', 'Danh sách hiện tại đang trống.')
            return

        if not msg_confirm(self, 'Xác nhận xóa tất cả',
                           f'Bạn có chắc muốn xóa <b>{len(target)}</b> thông báo đã gửi?\n\n'
                           f'Hành động này KHÔNG thể hoàn tác. HV sẽ không nhận được nữa.'):
            return
        if not (DB_AVAILABLE and NotificationService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return

        deleted = 0
        failed = 0
        delete_ids = set()
        for n in target:
            nid = n.get('id')
            if not nid:
                continue
            try:
                NotificationService.delete(nid)
                delete_ids.add(nid)
                deleted += 1
            except Exception as e:
                failed += 1
                print(f'[TEA_NOTIF_DEL_ALL] loi {nid}: {e}')

        self._tea_sent_cache = [n for n in cache if n.get('id') not in delete_ids]
        self._render_tea_sent_notices()
        if failed:
            msg_warn(self, 'Hoàn tất với lỗi',
                     f'Đã xóa: <b>{deleted}/{len(target)}</b><br>Lỗi: <b>{failed}</b>')
        else:
            msg_info(self, 'Đã xóa', f'✓ Đã xóa <b>{deleted}</b> thông báo.')

    def _render_tea_sent_notices(self):
        """Re-render danh sach thong bao da gui voi filter (cache + search)."""
        page = self.page_widgets[5]
        vlay = getattr(self, '_tea_notice_layout', None)
        if vlay is None:
            return
        # Clear layout cu (cache widget de tranh None sau setParent)
        while vlay.count():
            it = vlay.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        rows_all = getattr(self, '_tea_sent_cache', []) or []
        # Apply search keyword - dung norm() bo dau de tim 'thong bao' match 'Thông báo'
        sf = page.findChild(QtWidgets.QFrame, 'sentFrame')
        txt_s = sf.findChild(QtWidgets.QLineEdit, 'txtSentSearch') if sf else None
        kw = norm(txt_s.text() if txt_s else '')
        if kw:
            rows = [n for n in rows_all
                    if kw in norm(n.get('tieu_de', '') or '')
                    or kw in norm(n.get('noi_dung', '') or '')
                    or kw in norm(n.get('den_lop', '') or '')]
        else:
            rows = rows_all

        # Update counter
        lbl_cnt = sf.findChild(QtWidgets.QLabel, 'lblTeaSentCount') if sf else None
        if lbl_cnt:
            lbl_cnt.setText(f'{len(rows)} / {len(rows_all)}')

        if not rows:
            empty = QtWidgets.QLabel('Không có thông báo phù hợp' if kw else 'Chưa gửi thông báo nào')
            empty.setStyleSheet(f'color: {COLORS["text_light"]}; font-size: 13px; padding: 20px;')
            empty.setAlignment(Qt.AlignCenter)
            vlay.addWidget(empty)
        else:
            for n in rows:
                # Target priority: HV cu the > lop > broadcast
                if n.get('den_hv_id'):
                    target = f"HV: {n.get('ten_hv_dich') or '?'}"
                elif n.get('den_lop'):
                    target = n['den_lop']
                else:
                    target = 'Tất cả'
                card = self._make_notice_card(
                    target,
                    n.get('tieu_de', '') or '(không tiêu đề)',
                    fmt_relative_date(n.get('ngay_tao')),
                    notif_id=n.get('id'),
                )
                vlay.addWidget(card)
        vlay.addStretch()

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
        target_data = cbo.currentData()  # None / str (lop_id) / int (hv_user_id)
        title = subj.text().strip()
        body = content.toPlainText().strip()
        gv_user_id = MOCK_TEACHER.get('user_id')
        if not (DB_AVAILABLE and gv_user_id):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống.')
            return
        # Route theo type cua target_data: int=HV cu the, str=lop, None=broadcast
        den_lop = None
        den_hv_id = None
        if isinstance(target_data, int):
            den_hv_id = target_data
        elif isinstance(target_data, str):
            den_lop = target_data
        try:
            NotificationService.send(gv_user_id, title, body,
                                     den_lop=den_lop, den_hv_id=den_hv_id,
                                     loai='info')
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

        # Them search box trong filterBar 1 lan (de loc theo MSV/ten HV)
        fb = page.findChild(QtWidgets.QFrame, 'filterBar')
        if fb and not fb.findChild(QtWidgets.QLineEdit, 'txtTeaGradeSearch'):
            # Shrink + reposition lblStatus de chua chỗ
            lbl_st = fb.findChild(QtWidgets.QLabel, 'lblStatus')
            if lbl_st:
                lbl_st.setText('QT 30% · Thi 70% · TK = tổng kết')
                lbl_st.setGeometry(625, 16, 200, 18)
            txt_s = QtWidgets.QLineEdit(fb)
            txt_s.setObjectName('txtTeaGradeSearch')
            txt_s.setGeometry(395, 11, 220, 28)
            txt_s.setPlaceholderText('🔍 Tìm theo MSV / tên HV...')
            txt_s.setClearButtonEnabled(True)
            txt_s.setStyleSheet('QLineEdit { background: white; border: 1px solid #d2d6dc; '
                                 'border-radius: 4px; padding: 2px 8px; font-size: 12px; } '
                                 'QLineEdit:focus { border-color: #002060; }')
            txt_s.show()

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
        # safe_connect tranh accumulation khi user nav qua lai trang -> moi
        # lan _fill_tea_grades chay them 1 handler -> recalc N lan / 1 edit
        safe_connect(tbl.itemChanged, self._recalc_grade_row)
        self._grades_recalc_lock = False

        # save button - safe_connect tranh save N lan / 1 click
        btn = page.findChild(QtWidgets.QPushButton, 'btnSaveGrades')
        if btn:
            safe_connect(btn.clicked, self._save_tea_grades)

        # Wire search box -> filter row theo MSV/ten HV (1 lan, idempotent)
        if fb:
            txt_s = fb.findChild(QtWidgets.QLineEdit, 'txtTeaGradeSearch')
            if txt_s and not getattr(self, '_tea_grade_search_wired', False):
                # cols 1=MSV, 2=Ho ten
                txt_s.textChanged.connect(
                    lambda s, _t=tbl: table_filter(_t, s, cols=[1, 2])
                )
                self._tea_grade_search_wired = True
        # them nut "Cap nhat tu diem danh" + "Xuat CSV" + "PDF lop" canh nut Luu (1 lan)
        header = page.findChild(QtWidgets.QFrame, 'headerBar')
        if header and not header.findChild(QtWidgets.QPushButton, 'btnSyncAttend'):
            # nut Export PDF (in bang diem ca lop chinh quy)
            btn_pdf = QtWidgets.QPushButton('🖨 PDF', header)
            btn_pdf.setObjectName('btnExportGradesPDF')
            btn_pdf.setGeometry(355, 12, 80, 32)
            btn_pdf.setCursor(Qt.PointingHandCursor)
            btn_pdf.setToolTip('Xuất bảng điểm lớp hiện tại ra PDF chính quy (cho phòng đào tạo)')
            btn_pdf.setStyleSheet(
                f'QPushButton {{ background: white; color: {COLORS["gold"]}; border: 1px solid {COLORS["gold"]}; '
                f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                f'QPushButton:hover {{ background: {COLORS["gold"]}; color: white; }}'
            )
            def _do_export_grades_pdf():
                ma_lop = cbo.currentText() if (cbo and cbo.currentIndex() > 0) else None
                if not ma_lop:
                    msg_warn(self, 'Chưa chọn', 'Hãy chọn 1 lớp cụ thể để in bảng điểm')
                    return
                if not (DB_AVAILABLE and CourseService and GradeService):
                    msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống')
                    return
                try:
                    cls_info = CourseService.get_class(ma_lop) or {}
                    grades = GradeService.get_grades_by_class(ma_lop) or []
                except Exception as e:
                    msg_warn(self, 'Lỗi tải', api_error_msg(e))
                    return
                if not cls_info.get('ten_gv'):
                    cls_info['ten_gv'] = MOCK_TEACHER.get('name', '—')
                export_class_grades_pdf(
                    self, cls_info, grades,
                    default_filename=f'BangDiemLop_{ma_lop}.pdf'
                )
            safe_connect(btn_pdf.clicked, _do_export_grades_pdf)
            btn_pdf.show()
            # nut Export CSV
            btn_exp = QtWidgets.QPushButton('⬇ CSV', header)
            btn_exp.setObjectName('btnExportGrades')
            btn_exp.setGeometry(440, 12, 80, 32)
            btn_exp.setCursor(Qt.PointingHandCursor)
            btn_exp.setToolTip('Xuất danh sách điểm lớp hiện tại ra file CSV')
            btn_exp.setStyleSheet(
                'QPushButton { background: white; color: #1a4480; border: 1px solid #1a4480; '
                'border-radius: 6px; font-size: 12px; font-weight: bold; } '
                'QPushButton:hover { background: #1a4480; color: white; }'
            )
            def _do_export_grades():
                ma_lop = cbo.currentText() if (cbo and cbo.currentIndex() > 0) else 'tat_ca'
                fname = f'diem_{ma_lop.replace("/", "_")}.csv'
                export_table_csv(self, tbl, fname, f'Xuất điểm {ma_lop}')
            safe_connect(btn_exp.clicked, _do_export_grades)
            btn_exp.show()
            # nut Sync CC
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
            safe_connect(btn_sync.clicked, lambda: self._sync_cc_from_attendance(tbl, cbo))
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
        try:
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
        finally:
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

        # Lock cellChanged signal trong khi fill table - tranh _recalc_grade_row
        # bi trigger sai khi chua fill xong toan bo row. try/finally de release du loi
        self._grades_recalc_lock = True
        try:
            tbl.setRowCount(len(data))
            # Clear cellWidgets cu (xep loai cot 7) tranh leak khi re-render
            for r in range(tbl.rowCount()):
                tbl.removeCellWidget(r, 7)
            for r, row in enumerate(data):
                # Row 44px - du cho chu xep loai (khong pill nua)
                tbl.setRowHeight(r, 44)
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter if c != 2 else Qt.AlignLeft | Qt.AlignVCenter)
                    # cot CC (3), QT (4), Thi (5) cho edit truc tiep tren bang
                    if c not in (3, 4, 5):
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    # Cot 7 (xep loai): style mau + bold truc tiep tren item
                    if c == 7 and val:
                        style_status_item(item, val)
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
            # Cot 3 (Chuyen can): 85 de header 'Chuyên cần' co dau khong bi crop
            # Cot 7 (XL badge): 95 de fit "B+"/"A+"
            for c, cw in enumerate([40, 95, 165, 85, 70, 70, 70, 95]):
                tbl.setColumnWidth(c, cw)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                # rowHeight da set o vong loop tren - khong can set lai
                # Nut Nhap diem - dung pattern chuan
                cell, (btn_enter,) = make_action_cell([('Nhập điểm', 'navy')])
                tbl.setCellWidget(r, 8, cell)
                btn_enter.clicked.connect(lambda ch, rr=r: self._tea_grade_dialog(tbl, rr))
        finally:
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
            # Chi tinh TK + XL khi ca QT va Thi deu duoc nhap (>0). Neu thieu 1
            # truong se compute sai (vd QT=8 + Thi=0 -> TK=2.4 -> 'F') va luu
            # vao bang khien user nham. Hien preview '—' de ro la chua du
            if qt <= 0 or thi <= 0:
                lbl_preview.setText(
                    '<span style="color:#a0aec0;">Cần nhập đủ <b>QT</b> và '
                    '<b>Thi</b> để tự tính tổng kết và xếp loại</span>'
                )
                return
            total = round(qt * 0.3 + thi * 0.7, 2)
            letter = score_to_letter(total)  # khop bac thang BE
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
        # cap nhat table - dung try/finally de lock luon duoc release du co exception
        self._grades_recalc_lock = True
        try:
            qt_val = sp_qt.value()
            thi_val = sp_thi.value()
            cc_val = sp_cc.value()
            # Diem nao = 0 = user khong nhap -> de blank thay vi "0.0"
            tbl.item(row_idx, 3).setText(f'{cc_val:.1f}' if cc_val > 0 else '')
            tbl.item(row_idx, 4).setText(f'{qt_val:.2f}' if qt_val > 0 else '')
            tbl.item(row_idx, 5).setText(f'{thi_val:.2f}' if thi_val > 0 else '')
            # TK + XL: chi compute khi co ca QT va Thi (tranh truong hop QT=8 +
            # Thi=0 -> TK=2.4 -> 'F' luu vao bang khien user nham)
            if qt_val > 0 and thi_val > 0:
                total = round(qt_val * 0.3 + thi_val * 0.7, 2)
                letter = score_to_letter(total)
                it_tk = QtWidgets.QTableWidgetItem(f'{total:.1f}')
                it_tk.setTextAlignment(Qt.AlignCenter)
                it_tk.setFlags(it_tk.flags() & ~Qt.ItemIsEditable)
                tbl.setItem(row_idx, 6, it_tk)
                it_xl = QtWidgets.QTableWidgetItem(letter)
                style_status_item(it_xl, letter)
                it_xl.setFlags(it_xl.flags() & ~Qt.ItemIsEditable)
                tbl.setItem(row_idx, 7, it_xl)
                done_msg = f'Điểm của {tbl.item(row_idx,2).text()}: {total} ({letter})'
            else:
                # Clear TK + XL neu chua du diem
                it_tk = QtWidgets.QTableWidgetItem('')
                it_tk.setFlags(it_tk.flags() & ~Qt.ItemIsEditable)
                tbl.setItem(row_idx, 6, it_tk)
                it_xl = QtWidgets.QTableWidgetItem('')
                it_xl.setFlags(it_xl.flags() & ~Qt.ItemIsEditable)
                tbl.setItem(row_idx, 7, it_xl)
                done_msg = (f'Đã lưu điểm cho {tbl.item(row_idx,2).text()}. '
                            'Còn thiếu QT/Thi nên chưa tính tổng kết.')
        finally:
            self._grades_recalc_lock = False
        msg_info(self, 'Đã cập nhật', done_msg)

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
        letter = score_to_letter(total)
        self._grades_recalc_lock = True
        try:
            it_tot = QtWidgets.QTableWidgetItem(f'{total:.1f}')
            it_tot.setTextAlignment(Qt.AlignCenter)
            it_tot.setFlags(it_tot.flags() & ~Qt.ItemIsEditable)
            tbl.setItem(r, 6, it_tot)
            it_let = QtWidgets.QTableWidgetItem(letter)
            style_status_item(it_let, letter)
            it_let.setFlags(it_let.flags() & ~Qt.ItemIsEditable)
            tbl.setItem(r, 7, it_let)
        finally:
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
                qt_text = (tbl.item(r, 4).text() if tbl.item(r, 4) else '').strip().replace(',', '.')
                thi_text = (tbl.item(r, 5).text() if tbl.item(r, 5) else '').strip().replace(',', '.')
                # Cell trong -> bo qua hang nay (msg ro hon 'could not convert string')
                if not qt_text or not thi_text:
                    skipped.append((msv, 'thiếu điểm QT hoặc Thi'))
                    continue
                try:
                    qt = float(qt_text)
                    thi = float(thi_text)
                except ValueError:
                    skipped.append((msv, f'điểm không phải số: QT="{qt_text}", Thi="{thi_text}"'))
                    continue
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

    # ===== TEACHER ASSIGNMENTS PAGE =====

    def _fill_tea_assignments(self):
        """Trang 'Giao bài tập' - GV xem ds bai da giao + tao moi + xem bai HV nop."""
        page = self.page_widgets[7]
        # Build UI 1 lan (cache vao page._built)
        if not getattr(page, '_built', False):
            self._build_tea_assignments_ui(page)
            page._built = True
        self._reload_tea_assignments(page)

    def _build_tea_assignments_ui(self, page):
        """Build UI 1 lan: header + bang ds bai tap + nut tao."""
        # Header bar
        hb = QtWidgets.QFrame(page)
        hb.setObjectName('headerBar')
        hb.setGeometry(0, 0, 870, 56)
        hb.setStyleSheet('QFrame#headerBar { background: white; border-bottom: 1px solid #d2d6dc; }')
        title = QtWidgets.QLabel('Giao bài tập', hb)
        title.setGeometry(25, 0, 200, 56)
        title.setStyleSheet('color: #1a1a2e; font-size: 17px; font-weight: bold; background: transparent;')

        # Search box
        txt_s = QtWidgets.QLineEdit(hb)
        txt_s.setObjectName('txtTeaAsgSearch')
        txt_s.setGeometry(240, 12, 220, 32)
        txt_s.setPlaceholderText('🔍 Tìm tiêu đề / lớp / khóa...')
        txt_s.setClearButtonEnabled(True)
        txt_s.setStyleSheet('QLineEdit { background: white; border: 1px solid #d2d6dc; '
                             'border-radius: 6px; padding: 4px 10px; font-size: 12px; } '
                             'QLineEdit:focus { border-color: #002060; }')

        # Filter combo theo lop
        cbo = QtWidgets.QComboBox(hb)
        cbo.setObjectName('cboTeaAsgClass')
        cbo.setGeometry(470, 12, 220, 32)
        cbo.setCursor(Qt.PointingHandCursor)
        cbo.addItem('Tất cả lớp', None)
        cbo.setStyleSheet('QComboBox { background: white; border: 1px solid #d2d6dc; '
                           'border-radius: 6px; padding: 4px 10px; font-size: 11px; } '
                           'QComboBox:hover { border-color: #002060; } '
                           'QComboBox::drop-down { border: none; padding-right: 4px; }')

        btn_new = QtWidgets.QPushButton('+ Giao bài mới', hb)
        btn_new.setObjectName('btnNewAssign')
        btn_new.setGeometry(710, 12, 140, 32)
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.setStyleSheet(
            'QPushButton { background: #002060; color: white; border: none; '
            'border-radius: 6px; font-size: 12px; font-weight: bold; } '
            'QPushButton:hover { background: #001a50; }'
        )
        btn_new.clicked.connect(self._tea_dialog_new_assignment)

        # Bang ds bai tap
        tbl = QtWidgets.QTableWidget(page)
        tbl.setObjectName('tblAssignments')
        tbl.setGeometry(15, 70, 840, 615)
        tbl.setColumnCount(7)
        tbl.setHorizontalHeaderLabels(['#', 'Tiêu đề', 'Lớp', 'Khóa học',
                                       'Hạn nộp', 'Đã nộp / Đã chấm', 'Thao tác'])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # Header padding 14x10 dong nhat voi cac trang khac
        tbl.setStyleSheet(
            'QTableWidget { background: white; border: 1px solid #d2d6dc; '
            'border-radius: 6px; gridline-color: #edf2f7; font-size: 12px; } '
            'QHeaderView::section { background: #f7fafc; color: #4a5568; '
            'padding: 14px 10px; border: none; border-bottom: 1px solid #d2d6dc; '
            'font-family: "Segoe UI", "Inter", sans-serif; '
            'font-weight: bold; font-size: 11px; }'
        )
        tbl.horizontalHeader().setMinimumHeight(46)
        tbl.show()

    def _reload_tea_assignments(self, page):
        """Load lai du lieu bai tap (goi sau khi them/sua/xoa)."""
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAssignments')
        if not tbl:
            return
        gv_id = MOCK_TEACHER.get('user_id')
        rows = []
        if DB_AVAILABLE and gv_id:
            try:
                rows = AssignmentService.get_by_teacher(gv_id) or []
            except Exception as e:
                print(f'[TEA_ASG] loi load: {e}')

        # Populate combo class filter (preserve selection)
        hb = page.findChild(QtWidgets.QFrame, 'headerBar')
        cbo = hb.findChild(QtWidgets.QComboBox, 'cboTeaAsgClass') if hb else None
        if cbo is not None:
            cur_sel = cbo.currentData() if cbo.count() > 0 else None
            cbo.blockSignals(True)
            cbo.clear()
            cbo.addItem('Tất cả lớp', None)
            seen = set()
            for row in rows:
                ma = row.get('lop_id', '')
                if ma and ma not in seen:
                    seen.add(ma)
                    cbo.addItem(ma, ma)
            if cur_sel:
                idx = cbo.findData(cur_sel)
                if idx >= 0:
                    cbo.setCurrentIndex(idx)
            cbo.blockSignals(False)

        if not rows:
            set_table_empty_state(
                tbl, 'Chưa có bài tập nào',
                icon='📝',
                cta_text='+ Giao bài mới',
                cta_callback=self._tea_dialog_new_assignment)
        else:
            tbl.setRowCount(len(rows))
            for r, row in enumerate(rows):
                tbl.setRowHeight(r, 44)
                han = fmt_date(row.get('han_nop'), fmt='%d/%m/%Y %H:%M', default='Không hạn')
                so_nop = int(row.get('so_nop', 0) or 0)
                so_cham = int(row.get('so_cham', 0) or 0)
                items = [
                    str(r + 1),
                    row.get('tieu_de', ''),
                    row.get('lop_id', ''),
                    row.get('ten_mon', ''),
                    han,
                    f'{so_nop} nộp / {so_cham} chấm',
                ]
                for c, val in enumerate(items):
                    item = QtWidgets.QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter if c in (0, 2, 4, 5) else Qt.AlignLeft | Qt.AlignVCenter)
                    tbl.setItem(r, c, item)
                # Action: Xem bai nop / Xoa. 'Xoa' (3 chars) -> btn 52px qua hep
                # cho dau tieng Viet -> doi sang 'Xóa' (4 chars) de get 60px width
                cell, (btn_view, btn_del) = make_action_cell(
                    [('Xem nộp', 'navy'), ('Xóa', 'red')], spacing=10
                )
                tbl.setCellWidget(r, 6, cell)
                btn_view.clicked.connect(lambda ch, asg_id=row['id']: self._tea_dialog_submissions(asg_id))
                btn_del.clicked.connect(lambda ch, asg_id=row['id'], td=row.get('tieu_de', ''):
                                        self._tea_delete_assignment(asg_id, td))
        # Tong width 35+185+75+110+125+135+175 = 840 (vua khit table 840px)
        # Tang col 5 (Da nop/Da cham) 90->135 cho header dai khong bi crop
        # Tang col 6 (Thao tac) 165->175 cho 2 nut Xem nop/Xoa khong bi che
        for c, w in enumerate([35, 185, 75, 110, 125, 135, 175]):
            tbl.setColumnWidth(c, w)
        tbl.horizontalHeader().setStretchLastSection(False)

        # Wire search + filter (1 lan, idempotent)
        txt_s = hb.findChild(QtWidgets.QLineEdit, 'txtTeaAsgSearch') if hb else None
        if txt_s and not getattr(self, '_tea_asg_filter_wired', False):
            txt_s.textChanged.connect(lambda _t: self._tea_filter_assignments(page))
            if cbo is not None:
                cbo.currentIndexChanged.connect(lambda _i: self._tea_filter_assignments(page))
            self._tea_asg_filter_wired = True
        # Apply filter ngay (cho truong hop reload sau add/edit/delete giu nguyen filter)
        self._tea_filter_assignments(page)

    def _tea_filter_assignments(self, page):
        """Apply search + class filter len tblAssignments (GV)."""
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAssignments')
        if not tbl:
            return
        hb = page.findChild(QtWidgets.QFrame, 'headerBar')
        txt_s = hb.findChild(QtWidgets.QLineEdit, 'txtTeaAsgSearch') if hb else None
        cbo = hb.findChild(QtWidgets.QComboBox, 'cboTeaAsgClass') if hb else None
        # Dung norm() bo dau cho search nhat quan voi cac filter khac
        kw = norm(txt_s.text() if txt_s else '')
        sel_lop = cbo.currentData() if cbo else None
        for r in range(tbl.rowCount()):
            show = True
            # Search keyword (col 1=tieu de, col 2=lop, col 3=khoa hoc) qua norm
            if kw:
                hit = False
                for c in (1, 2, 3):
                    it = tbl.item(r, c)
                    if it and kw in norm(it.text()):
                        hit = True; break
                if not hit:
                    show = False
            # Filter lop (col 2)
            if show and sel_lop:
                it = tbl.item(r, 2)
                if it and it.text() != sel_lop:
                    show = False
            tbl.setRowHidden(r, not show)

    def _tea_dialog_new_assignment(self):
        """Dialog tao bai tap moi - chon lop + nhap tieu de/mo ta/han nop."""
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Giao bài tập mới')
        dlg.setFixedSize(500, 480)
        form = QtWidgets.QFormLayout(dlg)

        cbo_lop = QtWidgets.QComboBox()
        cbo_lop.addItem('-- Chọn lớp --', None)
        gv_id = MOCK_TEACHER.get('user_id')
        if DB_AVAILABLE and gv_id:
            try:
                rows = CourseService.get_classes_by_teacher(gv_id) or []
                for r in rows:
                    cbo_lop.addItem(f"{r['ma_lop']} - {r.get('ten_mon', '')}", r['ma_lop'])
            except Exception as e:
                print(f'[TEA_ASG] loi load lop: {e}')

        txt_title = QtWidgets.QLineEdit()
        txt_title.setPlaceholderText('VD: Bài tập tuần 3 - Vòng lặp')
        txt_desc = QtWidgets.QTextEdit()
        txt_desc.setPlaceholderText('Mô tả yêu cầu bài tập (có thể dán link tài liệu, ví dụ...)')
        txt_desc.setFixedHeight(140)

        dt_han = QtWidgets.QDateTimeEdit()
        dt_han.setCalendarPopup(True)
        from PyQt5.QtCore import QDateTime
        dt_han.setDateTime(QDateTime.currentDateTime().addDays(7))
        dt_han.setDisplayFormat('dd/MM/yyyy HH:mm')

        spin_diem = QtWidgets.QDoubleSpinBox()
        spin_diem.setRange(1, 100)
        spin_diem.setValue(10)
        spin_diem.setSingleStep(0.5)
        spin_diem.setSuffix(' điểm')

        form.addRow('Lớp (*):', cbo_lop)
        form.addRow('Tiêu đề (*):', txt_title)
        form.addRow('Mô tả:', txt_desc)
        form.addRow('Hạn nộp:', dt_han)
        form.addRow('Điểm tối đa:', spin_diem)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        cbo_lop.setFocus()

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if cbo_lop.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn lớp')
            return
        title = txt_title.text().strip()
        if not title:
            msg_warn(self, 'Thiếu', 'Tiêu đề không được trống')
            return
        if not (DB_AVAILABLE and AssignmentService and gv_id):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống')
            return
        try:
            han_dt = dt_han.dateTime().toPyDateTime()
            AssignmentService.create(
                lop_id=cbo_lop.currentData(),
                gv_id=gv_id,
                tieu_de=title,
                mo_ta=txt_desc.toPlainText(),
                han_nop=han_dt,
                diem_toi_da=float(spin_diem.value()),
            )
        except Exception as e:
            print(f'[TEA_ASG] create loi: {e}')
            msg_warn(self, 'Lỗi', f'Không tạo được:\n{api_error_msg(e)}')
            return
        msg_info(self, 'Thành công', f'Đã giao bài "{title}" cho lớp {cbo_lop.currentData()}')
        self._reload_tea_assignments(self.page_widgets[7])

    def _tea_delete_assignment(self, asg_id, tieu_de):
        """Xoa 1 bai tap (cascade xoa luon submissions)."""
        if not msg_confirm_delete(self, 'bài tập', str(asg_id), item_name=tieu_de,
                                  related='Tất cả bài HV đã nộp cho bài này sẽ bị xoá.'):
            return
        if not (DB_AVAILABLE and AssignmentService):
            return
        try:
            AssignmentService.delete(asg_id)
        except Exception as e:
            msg_warn(self, 'Lỗi xoá', api_error_msg(e))
            return
        msg_info(self, 'Đã xoá', f'Đã xoá bài tập "{tieu_de}"')
        self._reload_tea_assignments(self.page_widgets[7])

    def _tea_dialog_submissions(self, asg_id):
        """Dialog xem ds bai HV nop cho 1 assignment + GV cham."""
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle(f'Bài nộp - Bài tập #{asg_id}')
        dlg.setFixedSize(820, 580)
        v = QtWidgets.QVBoxLayout(dlg)
        v.setContentsMargins(0, 0, 0, 12)
        v.setSpacing(10)

        # Header banner navy - thay text tho bang banner chuyen nghiep
        banner = QtWidgets.QFrame()
        banner.setObjectName('asgBanner')
        banner.setStyleSheet(
            'QFrame#asgBanner { background: #002060; border: none; border-radius: 0px; }'
        )
        banner.setFixedHeight(78)
        bv = QtWidgets.QVBoxLayout(banner)
        bv.setContentsMargins(20, 12, 20, 12)
        bv.setSpacing(4)
        lbl_title = QtWidgets.QLabel('Đang tải...')
        lbl_title.setObjectName('lblAsgTitle')
        lbl_title.setStyleSheet('color: white; font-size: 16px; font-weight: bold; '
                                 'background: transparent;')
        bv.addWidget(lbl_title)
        lbl_meta = QtWidgets.QLabel('')
        lbl_meta.setObjectName('lblAsgMeta')
        lbl_meta.setStyleSheet('color: rgba(255,255,255,0.85); font-size: 12px; '
                                'background: transparent;')
        lbl_meta.setWordWrap(True)
        bv.addWidget(lbl_meta)
        v.addWidget(banner)

        # Wrapper de body co padding 2 ben
        body = QtWidgets.QWidget()
        body_v = QtWidgets.QVBoxLayout(body)
        body_v.setContentsMargins(16, 4, 16, 0)
        body_v.setSpacing(8)
        v.addWidget(body, 1)

        # Description (mo ta) hien rieng dong duoi banner cho de doc
        lbl_desc = QtWidgets.QLabel('')
        lbl_desc.setObjectName('lblAsgDesc')
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet('color: #4a5568; font-size: 12px; padding: 4px 2px;')
        body_v.addWidget(lbl_desc)

        # Bang ds nop - padding header thoang hon, font Segoe UI/Inter
        tbl = QtWidgets.QTableWidget()
        tbl.setColumnCount(6)
        tbl.setHorizontalHeaderLabels(['MSV', 'Họ tên', 'Trạng thái', 'Nộp lúc', 'Điểm', 'Thao tác'])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setStyleSheet(
            'QTableWidget { background: white; border: 1px solid #d2d6dc; '
            'border-radius: 6px; gridline-color: #edf2f7; font-size: 12px; } '
            'QHeaderView::section { background: #f7fafc; color: #4a5568; '
            'padding: 14px 10px; border: none; border-bottom: 1px solid #d2d6dc; '
            'font-family: "Segoe UI", "Inter", sans-serif; '
            'font-weight: bold; font-size: 11px; }'
        )
        tbl.horizontalHeader().setMinimumHeight(46)
        body_v.addWidget(tbl)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        btns.rejected.connect(dlg.reject)
        body_v.addWidget(btns)

        def reload_subs():
            try:
                asg = AssignmentService.get(asg_id) or {}
                subs = AssignmentService.get_submissions(asg_id) or []
            except Exception as e:
                msg_warn(dlg, 'Lỗi', api_error_msg(e))
                return
            han = fmt_date(asg.get('han_nop'), fmt='%d/%m/%Y %H:%M', default='Không hạn')
            lbl_title.setText(asg.get('tieu_de', '') or f'Bài tập #{asg_id}')
            lbl_meta.setText(
                f'Lớp <b>{asg.get("lop_id", "")}</b> '
                f'({asg.get("ten_mon", "")})  ·  '
                f'Hạn: <b>{han}</b>  ·  '
                f'Tối đa <b>{asg.get("diem_toi_da", 10)}</b> điểm'
            )
            lbl_desc.setText(asg.get('mo_ta', '') or '<i style="color:#a0aec0;">(không có mô tả)</i>')
            tbl.setRowCount(len(subs))
            for r, s in enumerate(subs):
                tbl.setRowHeight(r, 44)
                has_sub = s.get('submission_id') is not None
                graded = s.get('diem') is not None
                status = 'Đã chấm' if graded else ('Đã nộp' if has_sub else 'Chưa nộp')
                nop_at = fmt_date(s.get('nop_luc'), fmt='%d/%m/%Y %H:%M', default='—') if has_sub else '—'
                diem_disp = f"{float(s['diem']):.1f}" if graded else '—'
                items = [s.get('msv', ''), s.get('full_name', ''),
                         status, nop_at, diem_disp]
                for c, val in enumerate(items):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter if c != 1 else Qt.AlignLeft | Qt.AlignVCenter)
                    if c == 2:  # status
                        style_status_item(item, status)
                    tbl.setItem(r, c, item)
                # Action button - tu style cho dialog nay (font 10pt + padding rong + hover)
                if has_sub:
                    btn_text = 'Sửa điểm' if graded else 'Chấm bài'
                    cell_w = QtWidgets.QWidget()
                    hl = QtWidgets.QHBoxLayout(cell_w)
                    hl.setContentsMargins(6, 4, 6, 4)
                    hl.setAlignment(Qt.AlignCenter)
                    btn = QtWidgets.QPushButton(btn_text)
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.setFixedSize(110, 32)
                    btn.setStyleSheet(
                        'QPushButton { font-family: "Segoe UI", "Inter", sans-serif; '
                        'font-size: 13px; font-weight: bold; color: white; '
                        'background: #002060; border: none; border-radius: 4px; '
                        'padding: 6px 14px; } '
                        'QPushButton:hover { background: #1e3a8a; } '
                        'QPushButton:pressed { background: #001640; }'
                    )
                    btn.clicked.connect(lambda ch, sub=dict(s), a=dict(asg):
                                        self._tea_dialog_grade(sub, a, reload_subs))
                    hl.addWidget(btn)
                    tbl.setCellWidget(r, 5, cell_w)
                else:
                    no_lbl = QtWidgets.QLabel('—')
                    no_lbl.setAlignment(Qt.AlignCenter)
                    no_lbl.setStyleSheet('color: #a0aec0; font-size: 13px;')
                    tbl.setCellWidget(r, 5, no_lbl)
            # Tong width: 90+180+90+130+60+250 = 800 (dialog 820 - margins)
            for c, w in enumerate([90, 180, 90, 130, 60, 250]):
                tbl.setColumnWidth(c, w)
            tbl.horizontalHeader().setStretchLastSection(False)

        reload_subs()
        dlg.exec_()
        # Reload bang chinh sau khi dong dialog (so cham co the doi)
        self._reload_tea_assignments(self.page_widgets[7])

    def _tea_dialog_grade(self, sub, asg, after_save_callback):
        """Dialog cham diem 1 bai nop + nhan xet."""
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle(f'Chấm bài - {sub.get("full_name", "")}')
        dlg.setFixedSize(560, 560)
        v = QtWidgets.QVBoxLayout(dlg)
        v.setContentsMargins(0, 0, 0, 12)
        v.setSpacing(10)

        # Header banner navy - dong nhat voi dialog cha 'Bai nop'
        banner = QtWidgets.QFrame()
        banner.setStyleSheet('QFrame { background: #002060; border: none; }')
        banner.setFixedHeight(72)
        bv = QtWidgets.QVBoxLayout(banner)
        bv.setContentsMargins(20, 10, 20, 10)
        bv.setSpacing(3)
        lbl_hv = QtWidgets.QLabel(
            f'{sub.get("full_name", "") or "?"} '
            f'<span style="color: rgba(255,255,255,0.7); font-weight: normal;">'
            f'({sub.get("msv", "") or "?"})</span>'
        )
        lbl_hv.setStyleSheet('color: white; font-size: 16px; font-weight: bold; background: transparent;')
        bv.addWidget(lbl_hv)
        lbl_asg = QtWidgets.QLabel(
            f'Bài: <b>{asg.get("tieu_de", "")}</b>  ·  '
            f'Tối đa <b>{asg.get("diem_toi_da", 10)}</b> điểm'
        )
        lbl_asg.setStyleSheet('color: rgba(255,255,255,0.85); font-size: 12px; background: transparent;')
        bv.addWidget(lbl_asg)
        v.addWidget(banner)

        # Body wrapper voi padding 2 ben
        body = QtWidgets.QWidget()
        body_v = QtWidgets.QVBoxLayout(body)
        body_v.setContentsMargins(16, 4, 16, 0)
        body_v.setSpacing(6)
        v.addWidget(body, 1)

        # Bai nop
        body_v.addWidget(QtWidgets.QLabel('<b>Bài nộp:</b>'))
        sub_view = QtWidgets.QTextEdit()
        sub_view.setPlainText(sub.get('noi_dung', '') or '(HV nộp file - chưa có nội dung text)')
        sub_view.setReadOnly(True)
        sub_view.setFixedHeight(160)
        sub_view.setStyleSheet('background: #f7fafc; color: #2d3748; border: 1px solid #e2e8f0; border-radius: 6px;')
        body_v.addWidget(sub_view)

        # Diem + nhan xet
        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 4, 0, 0)
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(0, float(asg.get('diem_toi_da', 10)))
        spin.setSingleStep(0.5)
        spin.setSuffix(' điểm')
        if sub.get('diem') is not None:
            spin.setValue(float(sub['diem']))

        txt_nx = QtWidgets.QTextEdit()
        txt_nx.setPlaceholderText('Nhận xét / góp ý cho học viên...')
        txt_nx.setFixedHeight(90)
        if sub.get('nhan_xet'):
            txt_nx.setPlainText(sub['nhan_xet'])

        form.addRow('Điểm:', spin)
        form.addRow('Nhận xét:', txt_nx)
        body_v.addLayout(form)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        body_v.addWidget(btns)

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        sub_id = sub.get('submission_id')
        if not sub_id:
            return
        try:
            AssignmentService.grade(sub_id, float(spin.value()), txt_nx.toPlainText())
        except Exception as e:
            msg_warn(self, 'Lỗi chấm', api_error_msg(e))
            return
        msg_info(self, 'Đã chấm', f'Đã lưu điểm {spin.value():.1f} cho {sub.get("full_name", "")}')
        if after_save_callback:
            after_save_callback()

    # ===== TEACHER SCHEDULE CREATE =====

    def _tea_print_class_roster(self, ma_lop):
        """In danh sach HV cua 1 lop ra PDF."""
        if not (DB_AVAILABLE and CourseService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống')
            return
        try:
            # Get class info
            cls_info = CourseService.get_class(ma_lop) or {}
            students = CourseService.get_students_in_class(ma_lop) or []
        except Exception as e:
            msg_warn(self, 'Lỗi tải', api_error_msg(e))
            return
        # Ensure ten_gv is set
        if not cls_info.get('ten_gv'):
            cls_info['ten_gv'] = MOCK_TEACHER.get('name', '—')
        export_class_roster_pdf(
            self, cls_info, students,
            default_filename=f'DanhSachLop_{ma_lop}.pdf'
        )

    def _tea_show_class_full_schedule(self, ma_lop, ten_mon=''):
        """Mo dialog liet ke tat ca buoi cua 1 lop (24 buoi du kien)."""
        if not (DB_AVAILABLE and ScheduleService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống')
            return
        try:
            schedules = ScheduleService.get_for_class(ma_lop) or []
        except Exception as e:
            msg_warn(self, 'Lỗi tải', api_error_msg(e))
            return
        gv_name = MOCK_TEACHER.get('name', '') or ''
        show_class_full_schedule_dialog(self, ma_lop, ten_mon, schedules,
                                          role='gv', ten_gv=gv_name)

    def _tea_export_ics(self):
        """Xuat tat ca lich day cua GV ra .ics."""
        gv_id = MOCK_TEACHER.get('user_id')
        if not gv_id:
            msg_warn(self, 'Lỗi', 'Chưa có thông tin GV')
            return
        if not (DB_AVAILABLE and ScheduleService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống')
            return
        try:
            schedules = ScheduleService.get_all_for_teacher(gv_id) or []
        except Exception as e:
            msg_warn(self, 'Lỗi tải', api_error_msg(e))
            return
        gv_code = MOCK_TEACHER.get('id', 'GV')
        export_schedule_ics(self, schedules,
                            default_filename=f'LichDay_{gv_code}.ics',
                            calendar_name=f'Lịch dạy EAUT - {MOCK_TEACHER.get("name", "")}')

    def _tea_export_schedule_week_pdf(self):
        """In lich day tuan dang xem ra PDF."""
        gv_id = MOCK_TEACHER.get('user_id')
        if not gv_id:
            msg_warn(self, 'Lỗi', 'Chưa có thông tin GV')
            return
        monday = getattr(self, '_tea_current_monday', None)
        if monday is None:
            today = QDate.currentDate()
            monday = today.addDays(-(today.dayOfWeek() - 1))
        if not (DB_AVAILABLE and ScheduleService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống')
            return
        try:
            schedules = ScheduleService.get_for_teacher_week(gv_id, monday.toPyDate()) or []
        except Exception as e:
            msg_warn(self, 'Lỗi tải', api_error_msg(e))
            return
        gv_code = MOCK_TEACHER.get('id', 'GV')
        name = MOCK_TEACHER.get('name', '') or ''
        fname = f'LichDay_{gv_code}_{monday.toString("yyyyMMdd")}.pdf'
        export_schedule_week_pdf(self, schedules, monday,
                                  owner_role='gv', owner_name=name, owner_code=gv_code,
                                  default_filename=fname)

    def _tea_show_session_detail(self, sched_row):
        """Popup chi tiet 1 buoi day khi GV click vao card lich tuan."""
        ngay_v = sched_row.get('ngay', '')
        ngay_d = parse_iso_date(ngay_v)
        if ngay_d:
            thu_vn = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm',
                      'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật'][ngay_d.weekday()]
            ngay_str = f'{thu_vn}, {ngay_d.strftime("%d/%m/%Y")}'
        else:
            ngay_str = str(ngay_v)[:10] or '—'
        gio_bd = str(sched_row.get('gio_bat_dau', ''))[:5]
        gio_kt = str(sched_row.get('gio_ket_thuc', ''))[:5]
        gio_str = f'{gio_bd} - {gio_kt}' if gio_bd and gio_kt else '—'
        phong = sched_row.get('phong', '') or '—'
        ma_lop = sched_row.get('lop_id', '?') or '?'
        ten_mon = sched_row.get('ten_mon', '') or '—'
        siso = sched_row.get('siso_hien_tai')
        siso_max = sched_row.get('siso_max')
        if siso is not None and siso_max is not None:
            ss_str = f'{siso} / {siso_max} HV'
        elif siso is not None:
            ss_str = f'{siso} HV'
        else:
            ss_str = '—'
        buoi_so = sched_row.get('buoi_so')
        nd = sched_row.get('noi_dung', '') or ''
        trang_thai = sched_row.get('trang_thai') or 'scheduled'
        # Map khop DB CHECK schema.sql ('scheduled'/'completed'/'cancelled'/'postponed')
        st_vn = {'scheduled': 'Đã lên lịch', 'completed': 'Đã diễn ra',
                 'cancelled': 'Đã huỷ', 'postponed': 'Đã dời lịch'}
        st_label = st_vn.get(trang_thai, trang_thai)

        fields = [
            ('NGÀY DẠY', ngay_str),
            ('THỜI GIAN', gio_str),
            ('PHÒNG', phong),
            ('LỚP', ma_lop),
            ('KHÓA HỌC', ten_mon),
            ('SĨ SỐ', ss_str),
        ]
        if buoi_so:
            fields.append(('BUỔI SỐ', f'Buổi {buoi_so}'))
        if nd:
            fields.append(('NỘI DUNG BUỔI', nd))
        fields.append(('TRẠNG THÁI', st_label))

        show_detail_dialog(
            self,
            title=f'Chi tiết buổi dạy · {ma_lop}',
            fields=fields,
            avatar_text=ma_lop[:2],
            subtitle=ten_mon,
        )

    def _tea_dialog_new_schedule(self):
        """Dialog GV tao buoi hoc moi cho lop minh day."""
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Tạo buổi học mới')
        dlg.setFixedSize(480, 460)
        form = QtWidgets.QFormLayout(dlg)

        # Lop combo
        cbo_lop = QtWidgets.QComboBox()
        cbo_lop.addItem('-- Chọn lớp --', None)
        gv_id = MOCK_TEACHER.get('user_id')
        if DB_AVAILABLE and gv_id:
            try:
                rows = CourseService.get_classes_by_teacher(gv_id) or []
                for r in rows:
                    cbo_lop.addItem(f"{r['ma_lop']} - {r.get('ten_mon', '')}", r['ma_lop'])
            except Exception as e:
                print(f'[TEA_SCHED] loi load lop: {e}')

        # Ngay
        from PyQt5.QtCore import QDate, QTime
        dt_ngay = QtWidgets.QDateEdit()
        dt_ngay.setCalendarPopup(True)
        dt_ngay.setDate(QDate.currentDate().addDays(1))
        dt_ngay.setDisplayFormat('dd/MM/yyyy')

        # Gio bat dau / ket thuc
        time_bd = QtWidgets.QTimeEdit(QTime(7, 0))
        time_bd.setDisplayFormat('HH:mm')
        time_kt = QtWidgets.QTimeEdit(QTime(9, 30))
        time_kt.setDisplayFormat('HH:mm')

        # Phong (default lay tu lop)
        txt_phong = QtWidgets.QLineEdit()
        txt_phong.setPlaceholderText('Để trống = dùng phòng mặc định của lớp')

        # Buoi so
        spin_buoi = QtWidgets.QSpinBox()
        spin_buoi.setRange(1, 200)
        spin_buoi.setValue(1)
        spin_buoi.setPrefix('Buổi #')

        # Noi dung
        txt_nd = QtWidgets.QTextEdit()
        txt_nd.setPlaceholderText('Nội dung buổi học (chương/bài/chủ đề)')
        txt_nd.setFixedHeight(80)

        form.addRow('Lớp (*):', cbo_lop)
        form.addRow('Ngày (*):', dt_ngay)
        form.addRow('Giờ bắt đầu:', time_bd)
        form.addRow('Giờ kết thúc:', time_kt)
        form.addRow('Phòng:', txt_phong)
        form.addRow('Buổi số:', spin_buoi)
        form.addRow('Nội dung:', txt_nd)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        cbo_lop.setFocus()

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if cbo_lop.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn lớp')
            return
        if time_kt.time() <= time_bd.time():
            msg_warn(self, 'Sai giờ', 'Giờ kết thúc phải sau giờ bắt đầu')
            return
        if not (DB_AVAILABLE and ScheduleService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống')
            return
        # CHECK CONFLICT (cung phong/lop/GV + overlap gio)
        ngay_str = dt_ngay.date().toString('yyyy-MM-dd')
        gio_bd_str = time_bd.time().toString('HH:mm:ss')
        gio_kt_str = time_kt.time().toString('HH:mm:ss')
        phong_val = txt_phong.text().strip() or None
        if not phong_val:
            for cls in MOCK_CLASSES:
                if cls[0] == cbo_lop.currentData():
                    phong_val = cls[5] or None
                    break
        if not check_schedule_conflict_warn(
            self, ngay_str, gio_bd_str, gio_kt_str,
            phong=phong_val, lop_id=cbo_lop.currentData(),
            gv_id=MOCK_TEACHER.get('user_id')
        ):
            return
        try:
            ScheduleService.create(
                lop_id=cbo_lop.currentData(),
                ngay=ngay_str,
                gio_bat_dau=gio_bd_str,
                gio_ket_thuc=gio_kt_str,
                phong=txt_phong.text().strip() or None,
                buoi_so=spin_buoi.value(),
                noi_dung=txt_nd.toPlainText().strip() or None,
            )
        except Exception as e:
            print(f'[TEA_SCHED] create loi: {e}')
            msg_warn(self, 'Lỗi tạo', api_error_msg(e))
            return
        msg_info(self, 'Thành công',
                 f'Đã tạo buổi học cho {cbo_lop.currentData()} '
                 f'ngày {dt_ngay.date().toString("dd/MM/yyyy")}')
        # Reload tuan hien tai de thay buoi moi
        self.pages_filled[1] = False
        self._fill_tea_schedule()
        self.pages_filled[1] = True

    # ===== TEACHER EXAMS PAGE =====

    def _fill_tea_exams(self):
        """Trang 'Lich thi' - GV tao + xem lich thi cho cac lop minh day."""
        page = self.page_widgets[8]
        if not getattr(page, '_built', False):
            self._build_tea_exams_ui(page)
            page._built = True
        self._reload_tea_exams(page)

    def _build_tea_exams_ui(self, page):
        hb = QtWidgets.QFrame(page)
        hb.setObjectName('headerBar')
        hb.setGeometry(0, 0, 870, 56)
        hb.setStyleSheet('QFrame#headerBar { background: white; border-bottom: 1px solid #d2d6dc; }')
        title = QtWidgets.QLabel('Lịch thi', hb)
        title.setGeometry(25, 0, 400, 56)
        title.setStyleSheet('color: #1a1a2e; font-size: 17px; font-weight: bold; background: transparent;')

        # Combo loc theo lop - GV dang day nhieu lop -> can loc nhanh
        lbl_f = QtWidgets.QLabel('Lớp:', hb)
        lbl_f.setObjectName('lblTeaExamFilter')
        lbl_f.setGeometry(425, 18, 35, 24)
        lbl_f.setStyleSheet('color: #4a5568; font-size: 12px; font-weight: bold; background: transparent;')

        cbo_f = QtWidgets.QComboBox(hb)
        cbo_f.setObjectName('cboTeaExamFilter')
        cbo_f.setGeometry(465, 12, 85, 32)
        cbo_f.setCursor(Qt.PointingHandCursor)
        cbo_f.setStyleSheet('QComboBox { background: white; border: 1px solid #d2d6dc; '
                              'border-radius: 6px; padding: 4px 8px; font-size: 11px; } '
                              'QComboBox:hover { border-color: #002060; } '
                              'QComboBox::drop-down { border: none; padding-right: 4px; }')

        # Nut "In PDF" - de truoc nut Tao lich thi
        btn_pdf = QtWidgets.QPushButton('🖨 In PDF', hb)
        btn_pdf.setObjectName('btnTeaPrintExam')
        btn_pdf.setGeometry(560, 12, 140, 32)
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.setToolTip('In danh sách lịch thi của GV ra PDF')
        btn_pdf.setStyleSheet(
            'QPushButton { background: #c05621; color: white; border: none; '
            'border-radius: 6px; font-size: 12px; font-weight: bold; } '
            'QPushButton:hover { background: #9c4419; }'
        )
        btn_pdf.clicked.connect(self._tea_export_exam_pdf)

        btn_new = QtWidgets.QPushButton('+ Tạo lịch thi', hb)
        btn_new.setObjectName('btnNewExam')
        btn_new.setGeometry(710, 12, 140, 32)
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.setStyleSheet(
            'QPushButton { background: #002060; color: white; border: none; '
            'border-radius: 6px; font-size: 12px; font-weight: bold; } '
            'QPushButton:hover { background: #001a50; }'
        )
        btn_new.clicked.connect(self._tea_dialog_new_exam)

        tbl = QtWidgets.QTableWidget(page)
        tbl.setObjectName('tblTeaExams')
        tbl.setGeometry(15, 70, 840, 615)
        tbl.setColumnCount(8)
        tbl.setHorizontalHeaderLabels(['#', 'Lớp', 'Khóa học', 'Ngày thi',
                                       'Ca', 'Phòng', 'Hình thức', 'Thao tác'])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # Header padding 14x10 dong nhat voi cac trang khac
        tbl.setStyleSheet(
            'QTableWidget { background: white; border: 1px solid #d2d6dc; '
            'border-radius: 6px; gridline-color: #edf2f7; font-size: 12px; } '
            'QHeaderView::section { background: #f7fafc; color: #4a5568; '
            'padding: 14px 10px; border: none; border-bottom: 1px solid #d2d6dc; '
            'font-family: "Segoe UI", "Inter", sans-serif; '
            'font-weight: bold; font-size: 11px; }'
        )
        tbl.horizontalHeader().setMinimumHeight(46)
        tbl.show()

    def _reload_tea_exams(self, page):
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblTeaExams')
        if not tbl:
            return
        gv_id = MOCK_TEACHER.get('user_id')
        rows_all = []
        if DB_AVAILABLE and gv_id:
            try:
                rows_all = ExamService.get_for_teacher(gv_id) or []
            except Exception as e:
                print(f'[TEA_EXAM] loi: {e}')

        # Populate combo loc lop tu rows + wire 1 lan
        cbo_f = page.findChild(QtWidgets.QComboBox, 'cboTeaExamFilter')
        if cbo_f is not None:
            # Luu lua chon hien tai de restore sau repopulate
            cur_sel = cbo_f.currentData() if cbo_f.count() > 0 else None
            cbo_f.blockSignals(True)
            cbo_f.clear()
            cbo_f.addItem('Tất cả', None)
            seen = set()
            for r in rows_all:
                ma = r.get('lop_id', '')
                if ma and ma not in seen:
                    seen.add(ma)
                    cbo_f.addItem(ma, ma)
            # Restore sel cu neu con ton tai
            if cur_sel:
                idx = cbo_f.findData(cur_sel)
                if idx >= 0:
                    cbo_f.setCurrentIndex(idx)
            cbo_f.blockSignals(False)
            if not getattr(self, '_tea_exam_filter_wired', False):
                cbo_f.currentIndexChanged.connect(lambda _i: self._reload_tea_exams(page))
                self._tea_exam_filter_wired = True

        # Apply filter
        sel_lop = cbo_f.currentData() if cbo_f else None
        rows = [r for r in rows_all if not sel_lop or r.get('lop_id') == sel_lop]

        # Cache de double-click reuse (dung filtered rows)
        self._tea_exam_rows_cache = rows

        # Counters cho banner summary
        n_today = n_soon_3 = n_soon_7 = 0
        first_upcoming_row = None

        if not rows:
            set_table_empty_state(
                tbl, 'Chưa có lịch thi nào',
                icon='📋',
                cta_text='+ Tạo lịch thi mới',
                cta_callback=self._tea_dialog_new_exam)
        else:
            from datetime import date as _date
            today_d = _date.today()
            tbl.setRowCount(len(rows))
            for r, row in enumerate(rows):
                ngay = fmt_date(row.get('ngay_thi'))
                gio_bd = str(row.get('gio_bat_dau', ''))[:5]
                gio_kt = str(row.get('gio_ket_thuc', ''))[:5]
                ca_full = row.get('ca_thi', '')
                if gio_bd and gio_kt:
                    ca_full = f'{ca_full}\n{gio_bd}-{gio_kt}'

                # Tinh days_left
                d_parsed = parse_iso_date(row.get('ngay_thi') or row.get('ngay', ''))
                days_left = (d_parsed - today_d).days if d_parsed else None

                bg_color = None
                fg_color = None
                bold = False
                italic = False
                if days_left is not None:
                    if days_left == 0:
                        bg_color = '#fef3c7'; fg_color = '#9a3412'; bold = True
                        n_today += 1
                        if first_upcoming_row is None:
                            first_upcoming_row = r
                    elif 1 <= days_left <= 3:
                        bg_color = '#fee2e2'; fg_color = '#991b1b'; bold = True
                        n_soon_3 += 1
                        if first_upcoming_row is None:
                            first_upcoming_row = r
                    elif 4 <= days_left <= 7:
                        bg_color = '#fef9e7'; fg_color = '#92400e'
                        n_soon_7 += 1
                        if first_upcoming_row is None:
                            first_upcoming_row = r
                    elif days_left < 0:
                        bg_color = '#f7fafc'; fg_color = '#9ca3af'; italic = True

                # Append badge vao ca thi cell
                if days_left is not None and 0 <= days_left <= 7:
                    badge = '\n⚠ HÔM NAY!' if days_left == 0 else f'\nCòn {days_left} ngày'
                    ca_full = ca_full + badge

                items = [str(r + 1), row.get('lop_id', ''), row.get('ten_mon', ''),
                         ngay, ca_full, row.get('phong', '') or '—',
                         row.get('hinh_thuc', '') or '']
                for c, val in enumerate(items):
                    item = QtWidgets.QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter if c != 2 else Qt.AlignLeft | Qt.AlignVCenter)
                    if bg_color:
                        item.setBackground(QColor(bg_color))
                    if fg_color:
                        item.setForeground(QColor(fg_color))
                    if bold or italic:
                        f = item.font()
                        if bold: f.setBold(True)
                        if italic: f.setItalic(True)
                        item.setFont(f)
                    tbl.setItem(r, c, item)

                # Tooltip ca row (status + nhac dblclick)
                base_tip = ''
                if days_left is not None:
                    base_tip = (f'Còn {days_left} ngày nữa thi' if days_left > 0
                                 else 'Thi hôm nay - GV co mat som!' if days_left == 0
                                 else f'Đã diễn ra cách đây {-days_left} ngày')
                hint = ' · Double-click để xem chi tiết'
                tip = (base_tip + hint).strip(' ·') if base_tip else 'Double-click để xem chi tiết'
                for c in range(7):
                    if tbl.item(r, c):
                        tbl.item(r, c).setToolTip(tip)

                # Row height tang neu co badge
                tbl.setRowHeight(r, 56 if (days_left is not None and 0 <= days_left <= 7) else 44)

                # Action: Xoa - dong nhat 'Xóa' (4 chars 65px) thay 'Xoá' (3 chars 55px)
                cell, (btn_del,) = make_action_cell([('Xóa', 'red')])
                tbl.setCellWidget(r, 7, cell)
                btn_del.clicked.connect(lambda ch, eid=row['id'], lop=row.get('lop_id', ''),
                                        d=fmt_date(row.get('ngay_thi')):
                                        self._tea_delete_exam(eid, lop, d))
        # Tong width 35+85+170+90+130+85+105+140 = 840
        for c, w in enumerate([35, 85, 170, 90, 130, 85, 105, 140]):
            tbl.setColumnWidth(c, w)
        tbl.horizontalHeader().setStretchLastSection(False)

        # Wire double-click (chi cot 0-6, khong chan cot Thao tac 7) -> popup detail
        if not getattr(self, '_tea_exam_dblclick_wired', False):
            tbl.cellDoubleClicked.connect(self._tea_on_exam_dblclick)
            self._tea_exam_dblclick_wired = True

        # === Banner summary mon thi sap toi (≤7 ngay) ===
        cleanup_banner(page, 'examTodayBannerTea')
        n_total_soon = n_today + n_soon_3 + n_soon_7
        if n_total_soon > 0:
            banner = QtWidgets.QFrame(page)
            banner.setObjectName('examTodayBannerTea')
            banner.setGeometry(15, 60, 840, 38)
            if n_today > 0:
                bg = '#fef3c7'; left = '#c05621'; text_clr = '#9a3412'
            elif n_soon_3 > 0:
                bg = '#fee2e2'; left = '#dc2626'; text_clr = '#991b1b'
            else:
                bg = '#fef9e7'; left = '#d97706'; text_clr = '#92400e'
            banner.setStyleSheet(
                f'QFrame#examTodayBannerTea {{ background: {bg}; border: 1px solid {left}; '
                f'border-left: 4px solid {left}; border-radius: 8px; }}'
            )
            banner.setCursor(Qt.PointingHandCursor)

            parts = []
            if n_today > 0:
                parts.append(f'<b>{n_today}</b> ca thi <b style="color:#9a3412;">HÔM NAY</b>')
            if n_soon_3 > 0:
                parts.append(f'<b>{n_soon_3}</b> ca trong 3 ngày')
            if n_soon_7 > 0:
                parts.append(f'<b>{n_soon_7}</b> ca trong 4-7 ngày')
            text_html = f'🔔 Bạn có {" · ".join(parts)} — <span style="color:#1e3a8a;">click để jump tới mục đầu</span>'

            lbl = QtWidgets.QLabel(text_html, banner)
            lbl.setGeometry(15, 0, 820, 38)
            lbl.setStyleSheet(f'color: {text_clr}; font-size: 12px; background: transparent; border: none;')
            lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            lbl.setTextFormat(Qt.RichText)
            banner.setToolTip(f'{n_total_soon} ca thi sắp tới — click để jump')

            target_row = first_upcoming_row
            def _click(ev, _r=target_row):
                if ev.button() == Qt.LeftButton and _r is not None:
                    tbl.selectRow(_r)
                    tbl.scrollToItem(tbl.item(_r, 0), QtWidgets.QAbstractItemView.PositionAtCenter)
                    tbl.setFocus()
            banner.mousePressEvent = _click
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.mousePressEvent = _click
            banner.show()

            # Push tbl xuong de chua banner
            tg = tbl.geometry()
            new_y = 110
            if tg.y() != new_y:
                new_h = max(tg.height() - (new_y - tg.y()), 250)
                tbl.setGeometry(tg.x(), new_y, tg.width(), new_h)
        else:
            # Reset tbl ve geometry mac dinh neu khong co banner
            tg = tbl.geometry()
            if tg.y() != 70:
                tbl.setGeometry(tg.x(), 70, tg.width(), tg.height() + (tg.y() - 70))

    def _tea_dialog_new_exam(self):
        """Dialog GV tao lich thi moi cho lop minh day."""
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Tạo lịch thi mới')
        dlg.setFixedSize(500, 540)
        form = QtWidgets.QFormLayout(dlg)

        # Lop combo
        cbo_lop = QtWidgets.QComboBox()
        cbo_lop.addItem('-- Chọn lớp --', None)
        gv_id = MOCK_TEACHER.get('user_id')
        if DB_AVAILABLE and gv_id:
            try:
                rows = CourseService.get_classes_by_teacher(gv_id) or []
                for r in rows:
                    cbo_lop.addItem(f"{r['ma_lop']} - {r.get('ten_mon', '')}", r['ma_lop'])
            except Exception as e:
                print(f'[TEA_EXAM] loi load lop: {e}')

        # Ngay thi
        from PyQt5.QtCore import QDate, QTime
        dt_ngay = QtWidgets.QDateEdit()
        dt_ngay.setCalendarPopup(True)
        dt_ngay.setDate(QDate.currentDate().addDays(14))
        dt_ngay.setDisplayFormat('dd/MM/yyyy')

        # Ca thi (combo)
        cbo_ca = QtWidgets.QComboBox()
        cbo_ca.addItems(['Ca 1 (07:30-09:00)', 'Ca 2 (09:30-11:00)',
                         'Ca 3 (13:30-15:00)', 'Ca 4 (15:30-17:00)'])
        # Auto-update gio bat dau / gio ket thuc theo ca
        ca_times = {
            0: ('07:30', '09:00'),
            1: ('09:30', '11:00'),
            2: ('13:30', '15:00'),
            3: ('15:30', '17:00'),
        }
        time_bd = QtWidgets.QTimeEdit(QTime(7, 30))
        time_bd.setDisplayFormat('HH:mm')
        time_kt = QtWidgets.QTimeEdit(QTime(9, 0))
        time_kt.setDisplayFormat('HH:mm')

        def on_ca_changed(idx):
            t = ca_times.get(idx, ('07:30', '09:00'))
            h_bd, m_bd = map(int, t[0].split(':'))
            h_kt, m_kt = map(int, t[1].split(':'))
            time_bd.setTime(QTime(h_bd, m_bd))
            time_kt.setTime(QTime(h_kt, m_kt))
        cbo_ca.currentIndexChanged.connect(on_ca_changed)

        # Phong
        txt_phong = QtWidgets.QLineEdit('P.A301')
        txt_phong.setPlaceholderText('VD: P.A301')

        # Hinh thuc
        cbo_ht = QtWidgets.QComboBox()
        cbo_ht.addItems(['Trắc nghiệm', 'Tự luận', 'Vấn đáp', 'Thực hành'])

        # So cau (chi cho TN)
        spin_socau = QtWidgets.QSpinBox()
        spin_socau.setRange(0, 200)
        spin_socau.setValue(40)
        spin_socau.setSpecialValueText('—')  # 0 = N/A

        # Thoi gian phut
        spin_tg = QtWidgets.QSpinBox()
        spin_tg.setRange(15, 300)
        spin_tg.setValue(90)
        spin_tg.setSuffix(' phút')
        spin_tg.setSingleStep(15)

        form.addRow('Lớp (*):', cbo_lop)
        form.addRow('Ngày thi (*):', dt_ngay)
        form.addRow('Ca thi:', cbo_ca)
        form.addRow('Giờ bắt đầu:', time_bd)
        form.addRow('Giờ kết thúc:', time_kt)
        form.addRow('Phòng thi:', txt_phong)
        form.addRow('Hình thức:', cbo_ht)
        form.addRow('Số câu (TN):', spin_socau)
        form.addRow('Thời gian:', spin_tg)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        cbo_lop.setFocus()

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if cbo_lop.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn lớp')
            return
        # Map hinh thuc VN -> ASCII (DB schema dung Tu luan/Trac nghiem)
        ht_map = {'Trắc nghiệm': 'Trac nghiem', 'Tự luận': 'Tu luan',
                  'Vấn đáp': 'Van dap', 'Thực hành': 'Thuc hanh'}
        if not (DB_AVAILABLE and ExamService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối được hệ thống')
            return
        try:
            ExamService.create(
                lop_id=cbo_lop.currentData(),
                ngay_thi=dt_ngay.date().toString('yyyy-MM-dd'),
                ca_thi=cbo_ca.currentText().split(' (')[0],  # 'Ca 1'
                phong=txt_phong.text().strip() or None,
                hinh_thuc=ht_map.get(cbo_ht.currentText(), 'Tu luan'),
                gio_bat_dau=time_bd.time().toString('HH:mm:ss'),
                gio_ket_thuc=time_kt.time().toString('HH:mm:ss'),
                so_cau=spin_socau.value() or None,
                thoi_gian_phut=spin_tg.value(),
            )
        except Exception as e:
            print(f'[TEA_EXAM] create loi: {e}')
            msg_warn(self, 'Lỗi tạo', api_error_msg(e))
            return
        msg_info(self, 'Thành công',
                 f'Đã tạo lịch thi cho {cbo_lop.currentData()} '
                 f'ngày {dt_ngay.date().toString("dd/MM/yyyy")}')
        self._reload_tea_exams(self.page_widgets[8])

    def _tea_delete_exam(self, exam_id, lop, ngay):
        if not msg_confirm_delete(self, 'lịch thi', str(exam_id),
                                  item_name=f'{lop} ngày {ngay}'):
            return
        if not (DB_AVAILABLE and ExamService):
            return
        try:
            ExamService.delete(exam_id)
        except Exception as e:
            msg_warn(self, 'Lỗi xoá', api_error_msg(e))
            return
        msg_info(self, 'Đã xoá', f'Đã xoá lịch thi #{exam_id}')
        self._reload_tea_exams(self.page_widgets[8])

    def _tea_on_exam_dblclick(self, row, col):
        """GV double-click row Lich thi -> popup chi tiet (skip cot Thao tac 7)."""
        if col == 7:
            return
        cache = getattr(self, '_tea_exam_rows_cache', [])
        if row < 0 or row >= len(cache):
            return
        show_exam_detail_dialog(self, cache[row], role='gv')

    def _tea_export_exam_pdf(self):
        """In lich thi cua GV ra PDF."""
        gv_id = MOCK_TEACHER.get('user_id')
        if not gv_id:
            msg_warn(self, 'Lỗi', 'Chưa có thông tin GV')
            return
        if not (DB_AVAILABLE and ExamService):
            msg_warn(self, 'Lỗi', 'Chưa kết nối hệ thống')
            return
        try:
            rows = ExamService.get_for_teacher(gv_id) or []
        except Exception as e:
            msg_warn(self, 'Lỗi tải', api_error_msg(e))
            return
        if not rows:
            msg_warn(self, 'Trống', 'Chưa có lịch thi nào để in.')
            return
        gv_code = MOCK_TEACHER.get('id', 'GV')
        name = MOCK_TEACHER.get('name', '') or ''
        fname = f'LichThi_GV_{gv_code}.pdf'
        export_exam_schedule_pdf(self, rows, owner_role='gv',
                                  owner_name=name, owner_code=gv_code,
                                  default_filename=fname)

    def _fill_tea_profile(self):
        page = self.page_widgets[9]  # btnTeaProfile shifted to idx 9 sau khi insert btnTeaExam
        u = MOCK_TEACHER
        # Dung .get() de tranh KeyError sau clear_session_state()
        for attr, val in [('lblProfileName', u.get('name', '')),
                          ('lblProfileRole', f"Giảng viên - {u.get('khoa', '') or '—'}"),
                          ('lblProfileAvatar', u.get('initials', '?')),
                          ('valMaSV', u.get('id', '')),
                          ('valHoTen', u.get('name', '')),
                          ('valLop', u.get('hocvi', '')),
                          ('valKhoa', u.get('khoa', ''))]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setText('' if val is None else str(val))
        for attr, val in [('txtEmail', u.get('email', '')), ('txtPhone', u.get('sdt', ''))]:
            w = page.findChild(QtWidgets.QLineEdit, attr)
            if w:
                w.setText('' if val is None else str(val))

        btn_save = page.findChild(QtWidgets.QPushButton, 'btnSave')
        if btn_save:
            safe_connect(btn_save.clicked, self._save_tea_profile)
        btn_cp = page.findChild(QtWidgets.QPushButton, 'btnChangePass')
        if btn_cp:
            safe_connect(btn_cp.clicked, lambda: self._tea_change_pass())

        # Build/refresh card "Thong ke giang day"
        self._build_tea_profile_stats(page)

    def _build_tea_profile_stats(self, page):
        """Card 'Thong ke giang day' GV (4 stat: lop / HV / so buoi / diem TB review)."""
        cleanup_banner(page, 'profileTeaStatsCard')

        gv_id = MOCK_TEACHER.get('user_id')
        n_classes = 0
        n_students = 0
        n_sessions = 0
        avg_review = 0.0
        n_reviews = 0
        if DB_AVAILABLE and gv_id:
            try:
                # Lop dang day
                cls = CourseService.get_classes_by_teacher(gv_id) or []
                n_classes = len(cls)
                # Tong HV (de-dup tu tat ca lop)
                seen = set()
                if CourseService:
                    students = CourseService.get_students_by_teacher(gv_id) or []
                    for s in students:
                        uid = s.get('user_id') or s.get('hv_id')
                        if uid:
                            seen.add(uid)
                    n_students = len(seen)
                # So buoi day (count tat ca schedules cua GV)
                if ScheduleService:
                    try:
                        sessions = ScheduleService.get_all_for_teacher(gv_id) or []
                        n_sessions = len(sessions)
                    except Exception as _e:
                        pass
            except Exception as e:
                print(f'[TEA_PROFILE] stats lop loi: {e}')
            # Diem danh gia trung binh - lay tu TeacherService.get_for_review (co avg_rating)
            try:
                if TeacherService:
                    all_gv = TeacherService.get_for_review() or []
                    for r in all_gv:
                        rid = r.get('gv_id') or r.get('user_id') or r.get('id')
                        if rid == gv_id:
                            try:
                                avg_review = float(r.get('avg_rating') or r.get('diem_tb') or 0)
                                n_reviews = int(r.get('review_count') or r.get('so_dg') or 0)
                            except (TypeError, ValueError):
                                pass
                            break
            except Exception as e:
                print(f'[TEA_PROFILE] stats review loi: {e}')

        card = QtWidgets.QFrame(page)
        card.setObjectName('profileTeaStatsCard')
        card.setGeometry(445, 560, 400, 130)
        card.setStyleSheet('QFrame#profileTeaStatsCard { background: white; '
                            'border: 1px solid #d2d6dc; border-radius: 10px; }')

        lbl_t = QtWidgets.QLabel('📊 Thống kê giảng dạy', card)
        lbl_t.setGeometry(20, 12, 360, 22)
        lbl_t.setStyleSheet('color: #1a1a2e; font-size: 14px; font-weight: bold; '
                             'background: transparent; border: none;')

        review_str = (f'{avg_review:.1f}/5  ({n_reviews} đg)' if n_reviews > 0 else '—')
        stats = [
            (20, 42, '📚 Lớp đang dạy', f'{n_classes}', '#002060'),
            (210, 42, '👥 Tổng HV', f'{n_students}', '#166534'),
            (20, 85, '📅 Tổng buổi dạy', f'{n_sessions}', '#c05621'),
            (210, 85, '⭐ Đánh giá TB', review_str, '#7c3aed'),
        ]
        for x, y, label, val, color in stats:
            cap = QtWidgets.QLabel(label, card)
            cap.setGeometry(x, y, 180, 14)
            cap.setStyleSheet(f'color: #4a5568; font-size: 10px; '
                               'background: transparent; border: none;')
            v = QtWidgets.QLabel(val, card)
            v.setGeometry(x, y + 14, 180, 22)
            v.setStyleSheet(f'color: {color}; font-size: 16px; font-weight: bold; '
                             'background: transparent; border: none;')

    def _save_tea_profile(self):
        page = self.page_widgets[9]  # btnTeaProfile idx 9
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
            msg_warn(self, 'Sai định dạng',
                     'Số điện thoại không hợp lệ. Phải bắt đầu 0 (10 số) hoặc +84 (11 số).')
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
        show_change_password_dialog(self, MOCK_TEACHER, lambda: MOCK_TEACHER.get('user_id'))


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

        # F5/Ctrl+R: refresh trang hien tai
        install_refresh_shortcut(self)

        # Update sidebar badges initially
        self._update_emp_badges()

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
        add_reload_button(sidebar, self)

        sep = QtWidgets.QFrame(sidebar)
        sep.setGeometry(15, 74, 200, 1)
        sep.setStyleSheet(f'background: {COLORS["border"]};')

        y = 86
        for i, (btn_name, icon_name, icon_file, label) in enumerate(EMPLOYEE_MENU):
            btn = QtWidgets.QPushButton(label, sidebar)
            btn.setObjectName(btn_name)
            btn.setGeometry(10, y, 210, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(SIDEBAR_NORMAL)
            if i < 9:
                btn.setToolTip(f'{label}  ·  Ctrl+{i + 1}')
            else:
                btn.setToolTip(label)
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

        # Hop "Hom nay + Dot" - context-aware UX
        add_sidebar_context_widget(sidebar)

        sep2 = QtWidgets.QFrame(sidebar)
        sep2.setGeometry(15, 610, 200, 1)
        sep2.setStyleSheet(f'background: {COLORS["border"]};')

        lbl_av = QtWidgets.QLabel(MOCK_EMPLOYEE['initials'], sidebar)
        lbl_av.setGeometry(15, 625, 38, 38)
        lbl_av.setAlignment(Qt.AlignCenter)
        lbl_av.setStyleSheet(avatar_style(MOCK_EMPLOYEE['initials']))

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

        # Badge "DK qua han thanh toan" - nam o goc btnEmpPay (idx 3)
        pay_idx = next((i for i, (n, _) in enumerate(EMPLOYEE_PAGES) if n == 'btnEmpPay'), 3)
        pay_y = 86 + pay_idx * 38
        self.lblEmpPayBadge = QtWidgets.QLabel('', sidebar)
        self.lblEmpPayBadge.setObjectName('lblEmpPayBadge')
        self.lblEmpPayBadge.setGeometry(192, pay_y + 4, 22, 18)
        self.lblEmpPayBadge.setAlignment(Qt.AlignCenter)
        self.lblEmpPayBadge.setStyleSheet(
            'QLabel { background: #c53030; color: white; border-radius: 9px; '
            'font-size: 10px; font-weight: bold; padding: 0px 4px; }'
        )
        self.lblEmpPayBadge.hide()

        return sidebar

    def _update_emp_badges(self):
        """Update sidebar NV badges - count DK pending_payment qua 7 ngay."""
        if not hasattr(self, 'lblEmpPayBadge'):
            return
        set_sidebar_badge(self.lblEmpPayBadge, count_overdue_pending_registrations())

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
        if not msg_confirm(self, 'Đăng xuất', 'Bạn có chắc muốn đăng xuất?'):
            return
        clear_session_state()
        self.close()
        self.app_ref.show_login()

    # === EMPLOYEE DATA FILL ===

    def _fill_emp_dashboard(self):
        page = self.page_widgets[0]
        emp_id = MOCK_EMPLOYEE.get('user_id')

        # Cap nhat label hom nay theo ngay he thong (truoc hardcode 18/04/2026)
        lbl_today = page.findChild(QtWidgets.QLabel, 'lblToday')
        if lbl_today:
            from datetime import date as _date
            # them greeting time-aware truoc 'Hom nay: <date>'
            greet = time_greeting()
            lbl_today.setText(f'{greet} · Hôm nay: {_date.today().strftime("%d/%m/%Y")}')

        # Them nut "Bao cao doanh thu PDF" o header (1 lan, idempotent).
        # Header rong 870, lblToday o (600,0,245,56) ending x=845. Truoc nut o
        # x=720 width 170 ending 890 -> overflow header 20px + che lblToday.
        # Fix: chuyen lblToday sang trai (x=440 w=190) + nut o phai (x=640 w=160)
        header = page.findChild(QtWidgets.QFrame, 'headerBar')
        if header is not None and not header.findChild(QtWidgets.QPushButton, 'btnEmpReport'):
            # Resize lblToday sang trai de chua nut bao cao
            lbl_t2 = header.findChild(QtWidgets.QLabel, 'lblToday')
            if lbl_t2:
                lbl_t2.setGeometry(420, 0, 210, 56)
            btn_rpt = QtWidgets.QPushButton('🖨 Báo cáo doanh thu', header)
            btn_rpt.setObjectName('btnEmpReport')
            btn_rpt.setGeometry(640, 12, 200, 32)  # ends at 840 - fit 870 header
            btn_rpt.setCursor(Qt.PointingHandCursor)
            btn_rpt.setStyleSheet(
                f'QPushButton {{ background: {COLORS["gold"]}; color: white; border: none; '
                f'border-radius: 6px; font-size: 12px; font-weight: bold; }} '
                f'QPushButton:hover {{ background: {COLORS["gold_hover"]}; }}'
            )
            btn_rpt.clicked.connect(self._emp_dialog_revenue_report)
            btn_rpt.show()

        # Stat cards: today reg / paid / revenue / pending - tu API
        if DB_AVAILABLE and emp_id:
            try:
                stat = StatsService.employee_today(emp_id) or {}
                for attr, key, fmt in [
                    ('lblStatRegToday', 'today_reg', str),
                    ('lblStatPaidToday', 'today_paid', str),
                    ('lblStatRevenueToday', 'today_revenue',
                     lambda v: fmt_vnd(v)),
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
            if not data:
                set_table_empty_state(
                    tbl, 'Chưa có đăng ký chờ xử lý',
                    icon='📭',
                    cta_text='+ Đăng ký mới cho HV',
                    cta_callback=lambda: self._on_nav(1))
            else:
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
                    data = [(fmt_relative_date(a.get('thoi_gian')), a.get('noi_dung', '')) for a in acts]
                except Exception as e:
                    print(f'[EMP_DASH] activity loi: {e}')
            if not data:
                set_table_empty_state(tbl2, 'Chưa có hoạt động')
            else:
                tbl2.setRowCount(len(data))
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

        # === 4 stat cards clickable -> jump to detail page (1 lan) ===
        if not getattr(self, '_emp_stat_cards_wired', False):
            stat_to_idx = {
                'empStatCard1': (2, 'Đi đến trang Quản lý đăng ký'),
                'empStatCard2': (3, 'Đi đến trang Thanh toán'),
                'empStatCard3': (3, 'Đi đến trang Thanh toán (chờ TT)'),
                'empStatCard4': (3, 'Đi đến trang Thanh toán (doanh thu)'),
            }
            base_style = ('QFrame#{name} {{ background: white; border: 1px solid #d2d6dc; border-radius: 10px; }} '
                          'QFrame#{name}:hover {{ border: 2px solid #002060; background: #f0f7ff; }}')
            for name, (idx, tip) in stat_to_idx.items():
                card = page.findChild(QtWidgets.QFrame, name)
                if not card:
                    continue
                card.setCursor(Qt.PointingHandCursor)
                card.setStyleSheet(base_style.format(name=name))
                card.setToolTip(tip)
                def _make_click(_idx):
                    def _click(ev):
                        if ev.button() == Qt.LeftButton:
                            self._on_nav(_idx)
                    return _click
                card.mousePressEvent = _make_click(idx)
            self._emp_stat_cards_wired = True

        # Render banner alert "Dang ky qua han thanh toan"
        self._render_overdue_pay_banner_emp(page)

    def _render_overdue_pay_banner_emp(self, page):
        """Banner alert "X dang ky cho thanh toan qua N ngay" tren NV dashboard.

        Dat o y=156 (giua stat cards va pendingFrame). Push 2 frames xuong 42px
        neu show, reset neu khong.
        """
        from datetime import date as _date
        # Cleanup banner cu
        cleanup_banner(page, 'overduePayBannerEmp')

        # Đếm: pending_payment + ngay_dk > 7 ngay truoc
        n_overdue = 0
        oldest_days = 0
        if DB_AVAILABLE and RegistrationService:
            try:
                rows = RegistrationService.get_all_registrations(limit=500) or []
                today_d = _date.today()
                for r in rows:
                    if r.get('trang_thai') != 'pending_payment':
                        continue
                    ng = parse_iso_date(r.get('ngay_dk'))
                    if ng is None:
                        continue
                    days = (today_d - ng).days
                    if days > 7:
                        n_overdue += 1
                        oldest_days = max(oldest_days, days)
            except Exception as e:
                print(f'[EMP_DASH_OVERDUE] loi: {e}')

        # Push frames helper
        def _push_frames(shift_y):
            for fname in ('pendingFrame', 'activityEmpFrame'):
                fr = page.findChild(QtWidgets.QFrame, fname)
                if fr:
                    g = fr.geometry()
                    new_y = 168 + shift_y
                    new_h = max(506 - shift_y, 200)
                    if g.y() != new_y or g.height() != new_h:
                        fr.setGeometry(g.x(), new_y, g.width(), new_h)

        if n_overdue <= 0:
            _push_frames(0)
            return

        banner = QtWidgets.QFrame(page)
        banner.setObjectName('overduePayBannerEmp')
        banner.setGeometry(25, 156, 820, 38)

        # Style theo do gay gat (>14 ngay = do, 8-14 = vang)
        if oldest_days > 14:
            bg, left, fg = '#fee2e2', '#dc2626', '#991b1b'
            severity = 'NGHIÊM TRỌNG'
        else:
            bg, left, fg = '#fef3c7', '#d97706', '#9a3412'
            severity = 'CẦN XỬ LÝ'

        banner.setStyleSheet(
            f'QFrame#overduePayBannerEmp {{ background: {bg}; border: 1px solid {left}; '
            f'border-left: 4px solid {left}; border-radius: 8px; }}'
        )
        banner.setCursor(Qt.PointingHandCursor)

        text = (f'⏰  <b>{n_overdue}</b> đăng ký chờ thanh toán <b>quá 7 ngày</b>'
                f'  ·  cũ nhất: <b>{oldest_days}</b> ngày <b>({severity})</b>'
                f'  ·  <span style="color:#1e3a8a;">click để xử lý</span>')

        lbl = QtWidgets.QLabel(text, banner)
        lbl.setGeometry(15, 0, 800, 38)
        lbl.setStyleSheet(f'color: {fg}; font-size: 12px; background: transparent; border: none;')
        lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        lbl.setTextFormat(Qt.RichText)
        lbl.setCursor(Qt.PointingHandCursor)
        banner.setToolTip(f'{n_overdue} HV chờ TT >7 ngày — click để vào trang Thanh toán')

        def _click(ev):
            if ev.button() == Qt.LeftButton:
                # btnEmpPay idx 3
                self._on_nav(3)
        banner.mousePressEvent = _click
        lbl.mousePressEvent = _click
        banner.show()
        _push_frames(42)

    def _fill_emp_register(self):
        page = self.page_widgets[1]
        # Refresh sem status moi lan vao trang nay (admin co the vua toggle)
        _load_sem_status()
        # Loc CHI lop thuoc dot dang OPEN - dot closed khong cho register nua
        active_classes = [c for c in MOCK_CLASSES if is_class_active(c)]

        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboCourse')
        if cbo_c is not None:
            cbo_c.clear()
            cbo_c.addItem('-- Chọn khóa học --')
            # Chi list nhung khoa hoc co LOP active (avoid course rong)
            active_courses_codes = {c[1] for c in active_classes}
            for code, name in MOCK_COURSES:
                if code in active_courses_codes:
                    cbo_c.addItem(f'{code} - {name}')
            safe_connect(cbo_c.currentIndexChanged, self._emp_filter_classes)
        cbo_cls = page.findChild(QtWidgets.QComboBox, 'cboClassEmp')
        if cbo_cls is not None:
            cbo_cls.clear()
            cbo_cls.addItem('-- Chọn lớp --')
            if not active_classes:
                # Tat ca dot dang closed -> NV biet ngay khong register dc
                cbo_cls.addItem('⚠ Hiện không có đợt nào đang mở đăng ký')
            for cls in active_classes:
                try:
                    smax_c, scur_c = int(cls[6] or 0), int(cls[7] or 0)
                except (TypeError, ValueError):
                    smax_c, scur_c = 0, 0
                is_full = (smax_c > 0 and scur_c >= smax_c)
                cho_trong = max(0, smax_c - scur_c) if smax_c else 0
                if is_full:
                    suffix = '  ⛔ ĐÃ ĐẦY'
                else:
                    suffix = f'  ({cho_trong} chỗ trống)' if cho_trong > 0 else ''
                cbo_cls.addItem(f'{cls[0]} — {cls[3]} ({fmt_vnd(cls[8], suffix="đ")}){suffix}')
                # Disable item neu lop day -> NV khong the chon
                if is_full:
                    last_idx = cbo_cls.count() - 1
                    item = cbo_cls.model().item(last_idx)
                    if item:
                        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                        item.setForeground(QColor('#9ca3af'))
            # Khi chon lop -> hien info chi tiet vao lblClassDetails
            safe_connect(cbo_cls.currentIndexChanged, self._emp_show_class_info)

        # Banner cảnh báo nếu không có đợt mở
        lbl_warn = page.findChild(QtWidgets.QLabel, 'lblClassDetails')
        if lbl_warn is not None and not active_classes:
            lbl_warn.setText(
                '<span style="color:#c53030; font-weight:bold;">⚠ Hiện chưa có đợt đăng ký nào đang mở.</span><br>'
                '<span style="color:#718096;">Liên hệ Quản trị viên để mở đợt mới.</span>'
            )

        # buttons - safe_connect tranh accumulation moi lan re-fill
        btn_lk = page.findChild(QtWidgets.QPushButton, 'btnLookup')
        if btn_lk:
            safe_connect(btn_lk.clicked, self._emp_lookup_student)
        btn_rg = page.findChild(QtWidgets.QPushButton, 'btnConfirmReg')
        if btn_rg:
            safe_connect(btn_rg.clicked, self._emp_do_register)
        btn_rs = page.findChild(QtWidgets.QPushButton, 'btnResetReg')
        if btn_rs:
            safe_connect(btn_rs.clicked, self._emp_reset_form)

    def _emp_filter_classes(self, idx):
        page = self.page_widgets[1]
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboCourse')
        cbo_cls = page.findChild(QtWidgets.QComboBox, 'cboClassEmp')
        if cbo_c is None or cbo_cls is None:
            return
        # Helper add 1 cls vao cbo + disable neu day - dong bo voi _fill_emp_register
        def _add_cls(cls):
            try:
                smax_c, scur_c = int(cls[6] or 0), int(cls[7] or 0)
            except (TypeError, ValueError):
                smax_c, scur_c = 0, 0
            is_full = (smax_c > 0 and scur_c >= smax_c)
            cho_trong = max(0, smax_c - scur_c) if smax_c else 0
            if is_full:
                suffix = '  ⛔ ĐÃ ĐẦY'
            else:
                suffix = f'  ({cho_trong} chỗ trống)' if cho_trong > 0 else ''
            cbo_cls.addItem(f'{cls[0]} — {cls[3]} ({fmt_vnd(cls[8], suffix="đ")}){suffix}')
            if is_full:
                last_idx = cbo_cls.count() - 1
                item = cbo_cls.model().item(last_idx)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                    item.setForeground(QColor('#9ca3af'))
        # Chi xet active classes (thuoc dot OPEN)
        active_classes = [c for c in MOCK_CLASSES if is_class_active(c)]
        cbo_cls.clear()
        cbo_cls.addItem('-- Chọn lớp --')
        if idx == 0:
            for cls in active_classes:
                _add_cls(cls)
            return
        # cboCourse text format: "MA - Ten" -> parse ma_mon
        cur_text = cbo_c.currentText()
        mon_code = cur_text.split(' - ')[0] if ' - ' in cur_text else None
        for cls in active_classes:
            if cls[1] == mon_code:
                _add_cls(cls)

    def _emp_show_class_info(self, idx):
        """Khi NV chon lop trong cbo -> hien chi tiet (GV, Lich, Phong, Si so, Hoc phi)."""
        page = self.page_widgets[1]
        lbl = page.findChild(QtWidgets.QLabel, 'lblClassDetails')
        if not lbl:
            return
        if idx <= 0:
            lbl.setText('Vui lòng chọn môn và lớp để xem thông tin chi tiết')
            return
        cbo = page.findChild(QtWidgets.QComboBox, 'cboClassEmp')
        if not cbo:
            return
        # Parse ma_lop tu text "MA_LOP — Ten GV (gia)" -> lay ma_lop dau
        txt = cbo.currentText()
        ma_lop = txt.split('—')[0].strip() if '—' in txt else txt.split()[0]
        # Tim trong cache MOCK_CLASSES (ma_lop, ma_mon, ten_mon, ten_gv, lich, phong, smax, scur, gia)
        cls = next((c for c in MOCK_CLASSES if c[0] == ma_lop), None)
        if not cls:
            lbl.setText(f'Không tìm thấy thông tin lớp {ma_lop}')
            return
        _, _, ten_mon, gv, lich, phong, smax, scur, gia, *_ = cls
        try:
            smax_i = int(smax or 0); scur_i = int(scur or 0)
        except (TypeError, ValueError):
            smax_i, scur_i = 0, 0
        cho_trong = max(0, smax_i - scur_i)
        is_full = (smax_i > 0 and scur_i >= smax_i)
        # Style cho status si so: do bold neu day, cam neu sap day (≥80%), xanh neu con nhieu
        if is_full:
            siso_html = f'<span style="color:#c53030; font-weight:bold;">⛔ ĐÃ ĐẦY ({scur_i}/{smax_i})</span>'
        elif smax_i > 0 and scur_i / smax_i >= 0.8:
            siso_html = f'<span style="color:#c05621; font-weight:bold;">{cho_trong}/{smax_i} chỗ (sắp đầy)</span>'
        else:
            siso_html = f'<span style="color:#166534;">{cho_trong}/{smax_i} chỗ trống</span>'
        info = (
            f'<b>Khóa:</b> {ten_mon}<br>'
            f'<b>Giảng viên:</b> {gv or "—"}<br>'
            f'<b>Lịch học:</b> {lich or "—"}  ·  <b>Phòng:</b> {phong or "—"}<br>'
            f'<b>Sĩ số:</b> {siso_html}  ·  '
            f'<b>Học phí:</b> <span style="color:#c05621;">{fmt_vnd(gia, suffix="đ")}</span>'
        )
        lbl.setText(info)

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
            msg_warn(self, 'Thiếu', 'Hãy chọn khóa học')
            return
        if cbo_cls.currentIndex() == 0:
            msg_warn(self, 'Thiếu', 'Hãy chọn lớp')
            return
        # === CHECK MON TIEN QUYET tu khung CT ===
        lop_code = cbo_cls.currentText().split()[0]
        ma_mon_lop = MOCK_COURSES[cbo_c.currentIndex() - 1][0] if cbo_c.currentIndex() > 0 else None
        # === CHECK DUPLICATE: HV da dang ky lop nay chua? ===
        # Map status code -> tieng Viet de message UX-friendly
        _ST_VN = {
            'pending_payment': 'Chờ thanh toán',
            'paid': 'Đã thanh toán',
            'completed': 'Hoàn thành',
            'cancelled': 'Đã huỷ',
        }
        if DB_AVAILABLE:
            try:
                hv_check = StudentService.get_by_msv(msv.text().strip())
                if hv_check:
                    hv_uid_check = hv_check.get('user_id') or hv_check.get('id')
                    existing = CourseService.get_classes_by_student(hv_uid_check) or []
                    for cls in existing:
                        if cls.get('ma_lop') == lop_code and cls.get('reg_status') in ('pending_payment', 'paid', 'completed'):
                            st_raw = cls.get('reg_status', '')
                            st_vn = _ST_VN.get(st_raw, st_raw)
                            msg_warn(self, 'Đã đăng ký',
                                     f'Học viên {msv.text().strip()} đã đăng ký lớp {lop_code} rồi.\n'
                                     f'Trạng thái hiện tại: {st_vn}.\n'
                                     'Không thể đăng ký lại - mỗi học viên chỉ đăng ký 1 lần / lớp.')
                            return
            except Exception as e:
                print(f'[REG] check duplicate loi: {e}')
        # Khoa hoc ngoai khoa: KHONG check tien quyet/lo trinh hoc.
        # NV chi can xac nhan dang ky + thu tien, HV tu chiu trach nhiem ve trinh do.

        # === CHECK FULL: lop da day si so chua? ===
        # Lay tu MOCK_CLASSES cache (vua _refresh_cache sau register/cancel)
        # Tuple co 10 fields: ma_lop, ma_mon, ten_mon, ten_gv, lich, phong,
        #                     smax, scur, gia, sem_id -> dung *_ tranh ValueError
        cls_info = next((c for c in MOCK_CLASSES if c[0] == lop_code), None)
        if cls_info:
            try:
                smax_chk = int(cls_info[6] or 0)
                scur_chk = int(cls_info[7] or 0)
            except (TypeError, ValueError, IndexError):
                smax_chk, scur_chk = 0, 0
            if smax_chk > 0 and scur_chk >= smax_chk:
                msg_warn(self, 'Lớp đã đầy',
                         f'Lớp {lop_code} đã đủ sĩ số tối đa ({scur_chk}/{smax_chk}).\n'
                         'Không thể đăng ký thêm. Hãy chọn lớp khác cùng môn hoặc chờ admin tăng sĩ số.')
                return

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
                msg_warn(self, 'Lỗi', f'Đăng ký thất bại:\n{api_error_msg(e)}')
                return
        if saved_id:
            # Refresh cache MOCK_CLASSES de siso_hien_tai update (DB trigger da update)
            _refresh_cache()
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
                    gia = fmt_vnd(r.get('gia'), suffix='')
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
            # Row 44px - du cho chu trang thai (khong pill nua)
            tbl.setRowHeight(r, 44)
            for c, val in enumerate(row[:5]):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c in (0, 1, 3) else
                                       Qt.AlignRight | Qt.AlignVCenter if c == 4 else
                                       Qt.AlignLeft | Qt.AlignVCenter)
                tbl.setItem(r, c, item)
            # trang thai - uu tien paid_dks de sync giua 2 trang
            st = 'Đã thanh toán' if row[0] in self._paid_dks else row[5]
            # Style mau + bold truc tiep tren item (KHONG dung widget de tranh double text)
            item_st = QtWidgets.QTableWidgetItem(st)
            style_status_item(item_st, st)
            tbl.setItem(r, 5, item_st)
            # action - 2 nut Xem (navy) / Huy (red) cach nhau 12px
            cell, (btn_view, btn_cancel) = make_action_cell([('Xem', 'navy'), ('Hủy', 'red')], spacing=12)
            tbl.setCellWidget(r, 6, cell)
            btn_view.clicked.connect(lambda ch, rdata=row: show_detail_dialog(
                self, 'Chi tiết đăng ký',
                [('Mã đăng ký', rdata[0]), ('Ngày đăng ký', rdata[1]),
                 ('Học viên', rdata[2]), ('Lớp', rdata[3]),
                 ('Học phí', f'{rdata[4]} đ'), ('Trạng thái', rdata[5])],
                avatar_text='DK', subtitle=rdata[2]))
            # An nut huy neu trang thai khong cho phep
            cur_status = 'Đã thanh toán' if row[0] in self._paid_dks else row[5]
            can_cancel = cur_status == 'Chờ thanh toán'
            if can_cancel:
                btn_cancel.clicked.connect(lambda ch, ma_dk=row[0], hv=row[2], lop=row[3], t=tbl: self._emp_cancel_reg(t, ma_dk, hv, lop))
            else:
                btn_cancel.setEnabled(False)
                btn_cancel.setStyleSheet(
                    'QPushButton { background: #e2e8f0; color: #a0aec0; border: none; '
                    'border-radius: 4px; font-size: 11px; font-weight: bold; }'
                )
                btn_cancel.setToolTip(f'Không thể hủy ở trạng thái "{cur_status}"')
        tbl.horizontalHeader().setStretchLastSection(True)
        # Cot 5 (Trang thai badge) tang 125->240 fit "Chờ thanh toán" 230px pill
        # Redistribute: shrink HV name + lớp + ngày de cho rong cho badge
        # Col 6 (Thao tac) 110 -> 135 cho 'Xem' (55) + spacing 12 + 'Hủy' (55) = 122 + slack
        # Total 795 vua khit table 796px
        for c, cw in enumerate([55, 75, 145, 70, 90, 225, 135]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 44)

        widen_search(page, 'txtSearchReg', 300, ['cboRegStatus', 'cboRegDate'])
        # search + filter + export - safe_connect tranh accumulation
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchReg')
        if txt:
            safe_connect(txt.textChanged, lambda t: table_filter(tbl, t, cols=[0, 2, 3]))
        cbo_st = page.findChild(QtWidgets.QComboBox, 'cboRegStatus')
        if cbo_st:
            cbo_st.clear()
            # 4 trang thai khop voi DB CHECK: pending_payment/paid/cancelled/completed
            # Truoc thieu 'Hoan thanh' -> NV khong loc duoc reg da hoc xong
            cbo_st.addItems(['Tất cả trạng thái', 'Đã thanh toán', 'Chờ thanh toán',
                             'Đã hủy', 'Hoàn thành'])
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboRegDate')
        if cbo_d:
            cbo_d.clear()
            cbo_d.addItems(['Tất cả thời gian', 'Hôm nay', '7 ngày qua', '30 ngày qua'])
        for nm in ('cboRegStatus', 'cboRegDate'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                safe_connect(cbo.currentIndexChanged, lambda idx, n=nm: self._emp_filter_reg(n))
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportReg')
        if btn_exp:
            safe_connect(btn_exp.clicked, lambda: export_table_csv(self, tbl, 'danh_sach_dang_ky.csv', 'Xuất danh sách đăng ký'))

    def _emp_filter_reg(self, which):
        """Apply ca 2 filter status + date len tblRegistrations.
        cboRegStatus: idx 0 = Tat ca, > 0 = trang thai cu the.
        cboRegDate: idx 0 = Tat ca, 1 = Hom nay, 2 = 7 ngay qua, 3 = 30 ngay qua.
        """
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblRegistrations')
        cbo_st = page.findChild(QtWidgets.QComboBox, 'cboRegStatus')
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboRegDate')
        if not tbl:
            return

        from datetime import date as _date, timedelta as _td
        today = _date.today()

        st_text = (cbo_st.currentText() if cbo_st and cbo_st.currentIndex() > 0 else None)
        date_idx = cbo_d.currentIndex() if cbo_d else 0
        # Khoang ngay duoc chap nhan: rd >= threshold (hoac == today neu Hom nay)
        date_threshold = None
        if date_idx == 1:    # Hom nay
            date_threshold = today
        elif date_idx == 2:  # 7 ngay qua
            date_threshold = today - _td(days=7)
        elif date_idx == 3:  # 30 ngay qua
            date_threshold = today - _td(days=30)

        for r in range(tbl.rowCount()):
            show = True
            # Filter status (col 5)
            if st_text:
                it_s = tbl.item(r, 5)
                if it_s and st_text.lower() not in it_s.text().lower():
                    show = False
            # Filter date (col 1, format dd/MM/yyyy)
            if show and date_threshold:
                it_d = tbl.item(r, 1)
                if it_d:
                    try:
                        parts = it_d.text().split('/')
                        rd = _date(int(parts[2]), int(parts[1]), int(parts[0]))
                        if date_idx == 1:
                            if rd != today:
                                show = False
                        else:
                            if rd < date_threshold:
                                show = False
                    except (ValueError, IndexError):
                        pass  # parse loi -> giu nguyen show=True
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
        # DB OK -> refresh cache (DB trigger da update siso) + re-fill bang
        _refresh_cache()
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
                         fmt_vnd(r.get('gia'), suffix='')] for r in rows]
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
        # Format VND so co cham ngan: 2500000 -> '2.500.000 đ'. Truoc raw '{gia} đ'
        # khien bien lai hien '2500000 đ' nhin xau + kho doc
        try:
            gia_disp = fmt_vnd(int(gia)) if str(gia).strip() else '0 đ'
        except (ValueError, TypeError):
            gia_disp = f'{gia} đ'
        form = QtWidgets.QFormLayout()
        form.setSpacing(8)
        for label, val in [
            ('Số biên lai:', receipt_no),
            ('Ngày thu:', now.strftime('%d/%m/%Y %H:%M')),
            ('Mã đăng ký:', ma),
            ('Học viên:', ten),
            ('Lớp:', lop),
            ('Số tiền:', gia_disp),
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
        btn_save = QtWidgets.QPushButton('💾 Lưu (.txt)')
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; padding: 8px 12px; border-radius: 4px; font-weight: bold; }}')
        btn_save.clicked.connect(lambda: self._emp_save_receipt_file(receipt_no, ma, ten, lop, gia, method, ghi_chu, now))

        btn_copy = QtWidgets.QPushButton('📋 Sao chép')
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setStyleSheet(f'QPushButton {{ background: {COLORS["green"]}; color: white; border: none; padding: 8px 12px; border-radius: 4px; font-weight: bold; }}')

        def _do_copy():
            content = self._emp_build_receipt_content(receipt_no, ma, ten, lop, gia, method, ghi_chu, now)
            QtWidgets.QApplication.clipboard().setText(content)
            btn_copy.setText('✓ Đã sao chép')
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1500, lambda: btn_copy.setText('📋 Sao chép'))

        btn_copy.clicked.connect(_do_copy)

        # PDF export - dung QPrinter + QTextDocument (built-in PyQt5, khong dep moi)
        btn_pdf = QtWidgets.QPushButton('🖨 Xuất PDF')
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.setStyleSheet(f'QPushButton {{ background: {COLORS["gold"]}; color: white; border: none; padding: 8px 12px; border-radius: 4px; font-weight: bold; }}')
        btn_pdf.clicked.connect(lambda: self._emp_export_receipt_pdf(
            receipt_no, ma, ten, lop, gia, method, ghi_chu, now))

        btn_close = QtWidgets.QPushButton('Đóng')
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet('QPushButton { background: #edf2f7; color: #4a5568; border: 1px solid #d2d6dc; padding: 8px 12px; border-radius: 4px; }')
        btn_close.clicked.connect(dlg.accept)
        btns.addWidget(btn_save)
        btns.addWidget(btn_copy)
        btns.addWidget(btn_pdf)
        btns.addWidget(btn_close)
        lay.addLayout(btns)

        dlg.exec_()

    def _emp_build_receipt_content(self, receipt_no, ma, ten, lop, gia, method, ghi_chu, dt) -> str:
        """Build noi dung text bien lai - dung cho ca Save va Copy clipboard."""
        try:
            gia_disp = fmt_vnd(int(gia), suffix=' d') if str(gia).strip() else '0 d'
        except (ValueError, TypeError):
            gia_disp = f'{gia} d'
        return (
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
            f'So tien:      {gia_disp}\n'
            f'Hinh thuc:    {method}\n'
            f'Ghi chu:      {ghi_chu or "(khong)"}\n'
            f'Nhan vien:    {MOCK_EMPLOYEE["name"]}\n'
            '--------------------------------------\n'
            '--- Cam on quy hoc vien ---\n'
        )

    def _emp_save_receipt_file(self, receipt_no, ma, ten, lop, gia, method, ghi_chu, dt):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Lưu biên lai',
            os.path.join(os.path.expanduser('~'), 'Desktop', f'{receipt_no}.txt'),
            'Text (*.txt)'
        )
        if not path:
            return
        content = self._emp_build_receipt_content(receipt_no, ma, ten, lop, gia, method, ghi_chu, dt)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            msg_info(self, 'Đã lưu', f'Biên lai đã được lưu:\n{path}')
        except Exception as e:
            msg_warn(self, 'Lỗi', f'Không lưu được:\n{e}')

    def _emp_build_receipt_html(self, receipt_no, ma, ten, lop, gia, method, ghi_chu, dt) -> str:
        """Build noi dung HTML bien lai - dung cho PDF export (formatted dep)."""
        nv_name = MOCK_EMPLOYEE.get('name', '—')
        try:
            gia_disp = fmt_vnd(int(gia)) if str(gia).strip() else '0 đ'
        except (ValueError, TypeError):
            gia_disp = f'{gia} đ'
        return f'''
        <html><head><meta charset="utf-8"></head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e;">
        <div style="text-align: center; border-bottom: 3px solid #002060; padding-bottom: 12px; margin-bottom: 20px;">
            <h1 style="color: #002060; margin: 0; font-size: 22px;">TRUNG TÂM NGOẠI KHÓA EAUT</h1>
            <p style="margin: 4px 0; color: #4a5568; font-size: 11px;">
                Km 23, QL5, Trưng Trắc, Văn Lâm, Hưng Yên<br>
                Hotline: 024.3999.1111 · Email: info@eaut.edu.vn
            </p>
        </div>

        <h2 style="text-align: center; color: #c05621; margin: 0 0 4px 0; letter-spacing: 2px;">BIÊN LAI THU TIỀN</h2>
        <p style="text-align: center; color: #718096; font-size: 11px; margin: 0 0 20px 0;">
            Số biên lai: <b>{receipt_no}</b> · Ngày: <b>{dt.strftime('%d/%m/%Y %H:%M')}</b>
        </p>

        <table cellpadding="8" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px;">
            <tr style="background: #f7fafc;">
                <td style="width: 35%; color: #4a5568; border-bottom: 1px solid #e2e8f0;">Mã đăng ký</td>
                <td style="border-bottom: 1px solid #e2e8f0;"><b>{ma}</b></td>
            </tr>
            <tr>
                <td style="color: #4a5568; border-bottom: 1px solid #e2e8f0;">Học viên</td>
                <td style="border-bottom: 1px solid #e2e8f0;"><b>{ten}</b></td>
            </tr>
            <tr style="background: #f7fafc;">
                <td style="color: #4a5568; border-bottom: 1px solid #e2e8f0;">Lớp đăng ký</td>
                <td style="border-bottom: 1px solid #e2e8f0;"><b>{lop}</b></td>
            </tr>
            <tr>
                <td style="color: #4a5568; border-bottom: 1px solid #e2e8f0;">Số tiền</td>
                <td style="border-bottom: 1px solid #e2e8f0; color: #c05621;"><b style="font-size: 16px;">{gia_disp}</b></td>
            </tr>
            <tr style="background: #f7fafc;">
                <td style="color: #4a5568; border-bottom: 1px solid #e2e8f0;">Hình thức</td>
                <td style="border-bottom: 1px solid #e2e8f0;">{method}</td>
            </tr>
            <tr>
                <td style="color: #4a5568; border-bottom: 1px solid #e2e8f0;">Ghi chú</td>
                <td style="border-bottom: 1px solid #e2e8f0;">{ghi_chu or '<i style="color:#a0aec0;">(không có)</i>'}</td>
            </tr>
            <tr style="background: #f7fafc;">
                <td style="color: #4a5568;">Nhân viên thu</td>
                <td><b>{nv_name}</b></td>
            </tr>
        </table>

        <div style="margin-top: 40px; display: flex; justify-content: space-between;">
            <div style="text-align: center; width: 45%;">
                <p style="border-top: 1px solid #4a5568; padding-top: 8px; color: #4a5568;">Người nộp tiền</p>
            </div>
            <div style="text-align: center; width: 45%;">
                <p style="border-top: 1px solid #4a5568; padding-top: 8px; color: #4a5568;">
                    Người thu tiền<br><i style="font-size: 10px;">(ký, họ tên)</i>
                </p>
            </div>
        </div>

        <p style="text-align: center; color: #718096; font-size: 10px; margin-top: 30px; font-style: italic;">
            Cảm ơn quý học viên đã tin tưởng EAUT! · Biên lai có giá trị xác nhận thanh toán.
        </p>
        </body></html>
        '''

    def _emp_export_receipt_pdf(self, receipt_no, ma, ten, lop, gia, method, ghi_chu, dt):
        """Xuat bien lai sang PDF dung QPrinter + QTextDocument (built-in PyQt5)."""
        try:
            from PyQt5.QtPrintSupport import QPrinter
            from PyQt5.QtGui import QTextDocument
        except ImportError:
            msg_warn(self, 'Lỗi', 'PyQt5.QtPrintSupport không có sẵn. Cần cài thêm: pip install PyQt5-tools')
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Xuất biên lai PDF',
            os.path.join(os.path.expanduser('~'), 'Desktop', f'{receipt_no}.pdf'),
            'PDF Files (*.pdf)'
        )
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'
        try:
            html = self._emp_build_receipt_html(receipt_no, ma, ten, lop, gia, method, ghi_chu, dt)
            doc = _make_vn_textdoc(html)
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            printer.setPageSize(QPrinter.A5)  # bien lai nho gon
            printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
            doc.print_(printer)
            msg_info(self, 'Đã xuất PDF', f'Biên lai đã lưu:\n{path}')
        except Exception as e:
            print(f'[EMP_PDF] loi: {e}')
            msg_warn(self, 'Lỗi xuất PDF', f'Không xuất được:\n{e}')

    def _emp_dialog_revenue_report(self):
        """Dialog NV chon date range -> xem preview + xuat PDF bao cao doanh thu."""
        dlg = QtWidgets.QDialog(self)
        style_dialog(dlg)
        dlg.setWindowTitle('Báo cáo doanh thu')
        dlg.setFixedSize(580, 540)
        v = QtWidgets.QVBoxLayout(dlg)

        head = QtWidgets.QLabel(
            '<b>Chọn khoảng thời gian</b> - hệ thống sẽ tổng hợp tất cả thanh toán '
            'bạn đã thu trong khoảng đó.'
        )
        head.setStyleSheet('background: #edf2f7; padding: 10px; border-radius: 6px; font-size: 12px;')
        head.setWordWrap(True)
        v.addWidget(head)

        # Quick range buttons
        h_quick = QtWidgets.QHBoxLayout()
        from PyQt5.QtCore import QDate
        today = QDate.currentDate()
        dt_from = QtWidgets.QDateEdit(today)
        dt_to = QtWidgets.QDateEdit(today)
        for d in (dt_from, dt_to):
            d.setCalendarPopup(True)
            d.setDisplayFormat('dd/MM/yyyy')

        def set_range(start_date, end_date):
            dt_from.setDate(start_date)
            dt_to.setDate(end_date)
            update_preview()

        for label, days_back in [('Hôm nay', 0), ('7 ngày', 7),
                                  ('30 ngày', 30), ('Tháng này', -1)]:
            btn = QtWidgets.QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet('QPushButton { background: white; color: #002060; border: 1px solid #002060; border-radius: 4px; padding: 4px 12px; font-size: 11px; } QPushButton:hover { background: #002060; color: white; }')
            if days_back == -1:  # Thang nay
                btn.clicked.connect(lambda _,
                                    s=QDate(today.year(), today.month(), 1),
                                    e=today: set_range(s, e))
            else:
                btn.clicked.connect(lambda _, db_=days_back:
                                     set_range(today.addDays(-db_), today))
            h_quick.addWidget(btn)
        h_quick.addStretch()
        v.addLayout(h_quick)

        # Date range form
        form = QtWidgets.QFormLayout()
        form.addRow('Từ ngày:', dt_from)
        form.addRow('Đến ngày:', dt_to)
        v.addLayout(form)

        # Preview area
        preview = QtWidgets.QTextEdit()
        preview.setReadOnly(True)
        preview.setStyleSheet('background: white; border: 1px solid #d2d6dc; border-radius: 6px; font-family: "Segoe UI";')
        preview.setMinimumHeight(280)
        v.addWidget(preview)

        report_data = [None]  # mutable container

        def update_preview():
            if dt_to.date() < dt_from.date():
                preview.setHtml('<p style="color: #c53030;">⚠ Đến ngày phải sau từ ngày</p>')
                report_data[0] = None
                return
            emp_id = MOCK_EMPLOYEE.get('user_id')
            if not (DB_AVAILABLE and emp_id):
                preview.setHtml('<p style="color:#c53030;">Chưa kết nối hệ thống</p>')
                return
            try:
                data = StatsService.employee_revenue_report(
                    emp_id,
                    dt_from.date().toString('yyyy-MM-dd'),
                    dt_to.date().toString('yyyy-MM-dd')
                ) or {}
            except Exception as e:
                preview.setHtml(f'<p style="color:#c53030;">Lỗi tải: {api_error_msg(e)}</p>')
                report_data[0] = None
                return
            report_data[0] = data
            so_lan = data.get('so_lan', 0)
            tong = data.get('tong_tien', 0)
            payments = data.get('payments', [])
            bd = data.get('breakdown_by_method', [])
            html_parts = [
                f'<h3 style="color:#002060; margin: 4px 0;">Tổng kết</h3>',
                f'<p>Số lần thu: <b>{so_lan}</b> · Tổng tiền: <b style="color:#c05621;">{fmt_vnd(tong)}</b></p>',
            ]
            if bd:
                html_parts.append('<p><b>Phân bổ theo hình thức:</b></p><ul>')
                for b in bd:
                    html_parts.append(f'<li>{b["hinh_thuc"]}: <b>{b["so_lan"]}</b> lần · {fmt_vnd(int(b["tong"] or 0))}</li>')
                html_parts.append('</ul>')
            if payments:
                html_parts.append(f'<p><b>Chi tiết {len(payments)} thanh toán:</b></p>')
                html_parts.append('<table cellpadding="4" cellspacing="0" border="1" bordercolor="#e2e8f0" style="border-collapse: collapse; font-size: 11px; width: 100%;">')
                html_parts.append('<tr style="background: #f7fafc;"><th>Ngày</th><th>HV</th><th>Lớp</th><th>Tiền</th><th>HT</th></tr>')
                for p in payments[:50]:  # cap 50 dong preview
                    ngay = fmt_date(p.get('ngay_thu'), fmt='%d/%m %H:%M')
                    html_parts.append(
                        f'<tr><td>{ngay}</td><td>{p.get("ten_hv","")}</td>'
                        f'<td>{p.get("lop_id","")}</td>'
                        f'<td style="text-align:right;">{fmt_vnd(int(p.get("so_tien", 0) or 0))}</td>'
                        f'<td>{p.get("hinh_thuc","")}</td></tr>'
                    )
                html_parts.append('</table>')
                if len(payments) > 50:
                    html_parts.append(f'<p style="color:#718096; font-style:italic;">(... còn {len(payments)-50} dòng nữa, sẽ có đủ trong PDF)</p>')
            else:
                html_parts.append('<p style="color:#718096; font-style:italic;">Không có thanh toán nào trong khoảng này.</p>')
            preview.setHtml(''.join(html_parts))

        dt_from.dateChanged.connect(update_preview)
        dt_to.dateChanged.connect(update_preview)
        update_preview()

        # Buttons
        btns = QtWidgets.QDialogButtonBox()
        btn_pdf = btns.addButton('🖨 Xuất PDF', QtWidgets.QDialogButtonBox.AcceptRole)
        btn_close = btns.addButton('Đóng', QtWidgets.QDialogButtonBox.RejectRole)
        btn_close.clicked.connect(dlg.reject)
        v.addWidget(btns)

        def do_export():
            if not report_data[0]:
                msg_warn(dlg, 'Lỗi', 'Không có dữ liệu để xuất')
                return
            self._emp_export_revenue_pdf(
                report_data[0],
                dt_from.date().toString('dd/MM/yyyy'),
                dt_to.date().toString('dd/MM/yyyy')
            )
            dlg.accept()
        btn_pdf.clicked.connect(do_export)

        dlg.exec_()

    def _emp_export_revenue_pdf(self, data, from_str, to_str):
        """Xuat bao cao doanh thu PDF day du chi tiet."""
        try:
            from PyQt5.QtPrintSupport import QPrinter
            from PyQt5.QtGui import QTextDocument
        except ImportError:
            msg_warn(self, 'Lỗi', 'PyQt5.QtPrintSupport không có sẵn')
            return
        nv_name = MOCK_EMPLOYEE.get('name', '—')
        nv_id_disp = MOCK_EMPLOYEE.get('id', '—')
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Xuất báo cáo PDF',
            os.path.join(os.path.expanduser('~'), 'Desktop',
                         f'BaoCaoDoanhThu_{nv_id_disp}_{from_str.replace("/", "")}-{to_str.replace("/", "")}.pdf'),
            'PDF Files (*.pdf)'
        )
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'

        from datetime import datetime
        so_lan = data.get('so_lan', 0)
        tong = data.get('tong_tien', 0)
        payments = data.get('payments', [])
        bd = data.get('breakdown_by_method', [])

        # Build payment rows
        pay_rows = []
        for i, p in enumerate(payments, 1):
            ngay = fmt_date(p.get('ngay_thu'), fmt='%d/%m/%Y %H:%M')
            zebra = '#f7fafc' if i % 2 == 0 else 'white'
            pay_rows.append(f'''
                <tr style="background: {zebra};">
                    <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: center;">{i}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0;">{ngay}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0;">{p.get("ten_hv", "")}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0;">{p.get("msv", "")}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0;">{p.get("lop_id", "")}</td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0; text-align: right; color: #c05621;"><b>{fmt_vnd(int(p.get("so_tien", 0) or 0))}</b></td>
                    <td style="padding: 5px; border: 1px solid #e2e8f0;">{p.get("hinh_thuc", "")}</td>
                </tr>
            ''')

        bd_rows = []
        for b in bd:
            bd_rows.append(f'''
                <tr>
                    <td style="padding: 6px; border: 1px solid #e2e8f0;">{b["hinh_thuc"]}</td>
                    <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: center;">{b["so_lan"]}</td>
                    <td style="padding: 6px; border: 1px solid #e2e8f0; text-align: right; color: #c05621;"><b>{fmt_vnd(int(b["tong"] or 0))}</b></td>
                </tr>
            ''')

        html = f'''
        <html><head><meta charset="utf-8"></head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e;">
        <div style="text-align: center; border-bottom: 3px solid #002060; padding-bottom: 12px; margin-bottom: 16px;">
            <h1 style="color: #002060; margin: 0; font-size: 22px;">TRUNG TÂM NGOẠI KHÓA EAUT</h1>
            <p style="margin: 4px 0; color: #4a5568; font-size: 11px;">
                Km 23, QL5, Trưng Trắc, Văn Lâm, Hưng Yên · Hotline: 024.3999.1111
            </p>
        </div>

        <h2 style="text-align: center; color: #c05621; margin: 0 0 4px 0;">BÁO CÁO DOANH THU</h2>
        <p style="text-align: center; color: #4a5568; font-size: 12px; margin: 0 0 16px 0;">
            Từ ngày <b>{from_str}</b> đến <b>{to_str}</b>
        </p>

        <table cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 16px;">
            <tr style="background: #edf2f7;">
                <td style="width: 30%; padding: 8px;">Nhân viên thu:</td>
                <td style="padding: 8px;"><b>{nv_name}</b> ({nv_id_disp})</td>
            </tr>
            <tr>
                <td style="padding: 8px;">Số lần thu:</td>
                <td style="padding: 8px;"><b>{so_lan}</b></td>
            </tr>
            <tr style="background: #edf2f7;">
                <td style="padding: 8px;">Tổng doanh thu:</td>
                <td style="padding: 8px; color: #c05621; font-size: 16px;"><b>{fmt_vnd(tong)}</b></td>
            </tr>
        </table>

        <h3 style="color: #002060; margin: 12px 0 6px 0;">Phân bổ theo hình thức</h3>
        <table cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 16px;">
            <thead><tr style="background: #002060; color: white;">
                <th style="padding: 6px; border: 1px solid #002060;">Hình thức</th>
                <th style="padding: 6px; border: 1px solid #002060;">Số lần</th>
                <th style="padding: 6px; border: 1px solid #002060;">Tổng tiền</th>
            </tr></thead>
            <tbody>
                {''.join(bd_rows) if bd_rows else '<tr><td colspan="3" style="text-align: center; padding: 12px; color: #a0aec0;">(không có)</td></tr>'}
            </tbody>
        </table>

        <h3 style="color: #002060; margin: 12px 0 6px 0;">Chi tiết thanh toán ({len(payments)} dòng)</h3>
        <table cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 10px;">
            <thead><tr style="background: #002060; color: white;">
                <th style="padding: 6px; border: 1px solid #002060; width: 4%;">#</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 14%;">Ngày giờ</th>
                <th style="padding: 6px; border: 1px solid #002060;">Học viên</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 11%;">MSV</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 12%;">Lớp</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 13%;">Số tiền</th>
                <th style="padding: 6px; border: 1px solid #002060; width: 12%;">HT</th>
            </tr></thead>
            <tbody>
                {''.join(pay_rows) if pay_rows else '<tr><td colspan="7" style="text-align: center; padding: 12px; color: #a0aec0;">(không có thanh toán)</td></tr>'}
            </tbody>
        </table>

        <div style="margin-top: 30px; display: flex; justify-content: flex-end;">
            <div style="text-align: center; width: 40%;">
                <p style="color: #4a5568; font-size: 11px;">Hà Nội, ngày {datetime.now().day}/{datetime.now().month}/{datetime.now().year}</p>
                <p style="margin-top: 4px;"><b>Người lập báo cáo</b></p>
                <p style="font-size: 10px; color: #718096; font-style: italic;">(ký, họ tên)</p>
                <p style="margin-top: 50px;"><b>{nv_name}</b></p>
            </div>
        </div>
        </body></html>
        '''
        try:
            doc = _make_vn_textdoc(html)
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
            doc.print_(printer)
            msg_info(self, 'Đã xuất PDF', f'Báo cáo đã lưu:\n{path}')
        except Exception as e:
            print(f'[EMP_REPORT] loi: {e}')
            msg_warn(self, 'Lỗi xuất PDF', f'Không xuất được:\n{e}')

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
            set_table_empty_state(tbl, 'Chưa có dữ liệu')
        else:
            tbl.setRowCount(len(cls_list))
            for r, cls in enumerate(cls_list):
                ma, mmon, tmon, gv, lich, phong, smax, siso, gia, *_ = cls
                for c, val in enumerate([ma, tmon, gv, lich]):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter if c == 0 else Qt.AlignLeft | Qt.AlignVCenter)
                    tbl.setItem(r, c, item)
                siso_item = QtWidgets.QTableWidgetItem(f'{siso}/{smax}')
                siso_item.setTextAlignment(Qt.AlignCenter)
                pct = int(siso / smax * 100) if smax else 0
                siso_item.setForeground(QColor(COLORS['red'] if pct >= 95 else COLORS['gold'] if pct >= 70 else COLORS['green']))
                tbl.setItem(r, 4, siso_item)
                gia_item = QtWidgets.QTableWidgetItem(fmt_vnd(gia))
                gia_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                gia_item.setForeground(QColor(COLORS['gold']))
                tbl.setItem(r, 5, gia_item)
                trang_thai = 'Đầy' if pct >= 100 else 'Còn chỗ'
                item_tt = QtWidgets.QTableWidgetItem(trang_thai)
                item_tt.setTextAlignment(Qt.AlignCenter)
                item_tt.setForeground(QColor(COLORS['red'] if trang_thai == 'Đầy' else COLORS['green']))
                tbl.setItem(r, 6, item_tt)
                # nut chi tiet lop - dung pattern chuan
                cell, (btn_detail,) = make_action_cell([('Xem', 'navy')])
                tbl.setCellWidget(r, 7, cell)
                btn_detail.clicked.connect(lambda ch, cls_data=cls: show_detail_dialog(
                    self, 'Chi tiết lớp',
                    [('Mã lớp', cls_data[0]), ('Khóa học', cls_data[2]),
                     ('Giảng viên', cls_data[3]), ('Lịch học', cls_data[4]),
                     ('Phòng', cls_data[5]),
                     ('Sĩ số', f'{cls_data[7]}/{cls_data[6]}'),
                     ('Học phí', fmt_vnd(cls_data[8])),
                     ('Trạng thái', 'Đầy' if cls_data[7] >= cls_data[6] else 'Còn chỗ')],
                    avatar_text=cls_data[0][:2], subtitle=cls_data[2]))
            for r in range(len(cls_list)):
                tbl.setRowHeight(r, 44)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([78, 150, 125, 140, 68, 100, 85, 90]):
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
            cbo_c.addItem('Tất cả khóa học')
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
        # Cast moi value sang str de tranh crash khi gap int/None (vd id la int khi chua sync)
        for attr, val in [('lblProfileName', u['name']), ('lblProfileRole', f"Nhân viên - {u['chucvu']}"),
                          ('lblProfileAvatar', u['initials']), ('valMaSV', u['id']), ('valHoTen', u['name']),
                          ('valLop', u['chucvu'])]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setText('' if val is None else str(val))
        for attr, val in [('txtEmail', u['email']), ('txtPhone', u['sdt'])]:
            w = page.findChild(QtWidgets.QLineEdit, attr)
            if w:
                w.setText('' if val is None else str(val))

        btn_save = page.findChild(QtWidgets.QPushButton, 'btnSave')
        if btn_save:
            safe_connect(btn_save.clicked, self._save_emp_profile)
        btn_cp = page.findChild(QtWidgets.QPushButton, 'btnChangePass')
        if btn_cp:
            safe_connect(btn_cp.clicked, lambda: self._emp_change_pass())

        # Build/refresh card "Thong ke cong viec"
        self._build_emp_profile_stats(page)

    def _build_emp_profile_stats(self, page):
        """Card 'Thong ke cong viec' NV (4 stat: don dang ky / TT xac nhan / tong thu / TB/ngay)."""
        cleanup_banner(page, 'profileEmpStatsCard')

        emp_id = MOCK_EMPLOYEE.get('user_id') or MOCK_EMPLOYEE.get('id')
        n_reg = 0
        n_pay = 0
        total_rev = 0
        avg_per_day = 0.0
        if DB_AVAILABLE and emp_id and isinstance(emp_id, int):
            # Lay tu employee_revenue_report (range 1 nam ngược lại để cover du)
            try:
                if StatsService:
                    from datetime import date as _date, timedelta as _td
                    today = _date.today()
                    fr = (today - _td(days=365)).isoformat()
                    to = today.isoformat()
                    rep = StatsService.employee_revenue_report(emp_id, fr, to) or {}
                    n_pay = int(rep.get('so_lan', 0) or 0)
                    total_rev = int(rep.get('tong_tien', 0) or 0)
                    # Lay so registration tu RegistrationService neu co (count theo nv_id)
                    try:
                        if RegistrationService:
                            all_regs = RegistrationService.get_all_registrations(limit=1000) or []
                            n_reg = sum(1 for r in all_regs if r.get('nv_id') == emp_id)
                    except Exception:
                        pass
                    if n_pay > 0:
                        # TB / ngay = tong / so ngay (gioi han 30 ngay gan day cho realistic)
                        days = max(1, min(30, (today - (today - _td(days=30))).days))
                        avg_per_day = total_rev / days
            except Exception as e:
                print(f'[EMP_PROFILE] stats loi: {e}')

        card = QtWidgets.QFrame(page)
        card.setObjectName('profileEmpStatsCard')
        card.setGeometry(445, 560, 400, 130)
        card.setStyleSheet('QFrame#profileEmpStatsCard { background: white; '
                            'border: 1px solid #d2d6dc; border-radius: 10px; }')

        lbl_t = QtWidgets.QLabel('📊 Thống kê công việc (12 tháng qua)', card)
        lbl_t.setGeometry(20, 12, 360, 22)
        lbl_t.setStyleSheet('color: #1a1a2e; font-size: 14px; font-weight: bold; '
                             'background: transparent; border: none;')

        avg_str = (fmt_vnd(int(avg_per_day), suffix='đ/ngày') if avg_per_day > 0 else '—')
        stats = [
            (20, 42, '📝 Đăng ký xử lý', f'{n_reg}', '#002060'),
            (210, 42, '💵 TT đã xác nhận', f'{n_pay}', '#166534'),
            (20, 85, '💰 Tổng thu', fmt_vnd(total_rev, suffix='đ'), '#c05621'),
            (210, 85, '📈 TB 30 ngày', avg_str, '#7c3aed'),
        ]
        for x, y, label, val, color in stats:
            cap = QtWidgets.QLabel(label, card)
            cap.setGeometry(x, y, 180, 14)
            cap.setStyleSheet(f'color: #4a5568; font-size: 10px; '
                               'background: transparent; border: none;')
            v = QtWidgets.QLabel(val, card)
            v.setGeometry(x, y + 14, 180, 22)
            v.setStyleSheet(f'color: {color}; font-size: 14px; font-weight: bold; '
                             'background: transparent; border: none;')

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
            msg_warn(self, 'Sai định dạng',
                     'Số điện thoại không hợp lệ. Phải bắt đầu 0 (10 số) hoặc +84 (11 số).')
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
        show_change_password_dialog(self, MOCK_EMPLOYEE, lambda: MOCK_EMPLOYEE.get('user_id'))


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

        # Remember username: tu dien lan dang nhap truoc va focus vao password
        last_user = load_last_username()
        if last_user:
            self.login_win.txtUsername.setText(last_user)
            self.login_win.txtPassword.setFocus()

        # Show/hide password toggle button (overlay goc phai txtPassword)
        pw_field = self.login_win.txtPassword
        pw_geo = pw_field.geometry()
        btn_eye = QtWidgets.QPushButton('👁', pw_field.parent())
        btn_eye.setObjectName('btnTogglePw')
        btn_eye.setGeometry(pw_geo.x() + pw_geo.width() - 38, pw_geo.y() + 6, 32, 30)
        btn_eye.setCursor(Qt.PointingHandCursor)
        btn_eye.setToolTip('Hiện/ẩn mật khẩu')
        btn_eye.setStyleSheet(
            'QPushButton { background: transparent; border: none; '
            'font-size: 16px; color: #718096; } '
            'QPushButton:hover { color: #002060; }'
        )

        def _toggle_pw():
            if pw_field.echoMode() == QtWidgets.QLineEdit.Password:
                pw_field.setEchoMode(QtWidgets.QLineEdit.Normal)
                btn_eye.setText('🙈')
            else:
                pw_field.setEchoMode(QtWidgets.QLineEdit.Password)
                btn_eye.setText('👁')

        btn_eye.clicked.connect(_toggle_pw)
        btn_eye.show()

        # "Quen mat khau?" link - dat ben phai duoi password field
        btn_forgot = QtWidgets.QPushButton('Quên mật khẩu?', pw_field.parent())
        btn_forgot.setObjectName('btnForgotPw')
        btn_forgot.setGeometry(pw_geo.x() + pw_geo.width() - 130, pw_geo.y() + pw_geo.height() + 4, 130, 20)
        btn_forgot.setCursor(Qt.PointingHandCursor)
        btn_forgot.setStyleSheet(
            'QPushButton { background: transparent; color: #002060; border: none; '
            'font-size: 11px; font-weight: bold; text-align: right; padding: 0 4px; } '
            'QPushButton:hover { color: #c05621; text-decoration: underline; }'
        )

        def _show_forgot():
            msg_info(self.login_win, 'Quên mật khẩu',
                     'Để được cấp lại mật khẩu, vui lòng liên hệ:\n\n'
                     '📧 Email: admin@eaut.edu.vn\n'
                     '☎ Hotline: 024.3999.1111\n'
                     '📍 Trực tiếp tại Văn phòng Trung tâm\n\n'
                     'Vui lòng cung cấp MSV/Mã GV/Mã NV để nhân viên xác minh.')
        btn_forgot.clicked.connect(_show_forgot)
        btn_forgot.show()

        # "Tai khoan test" link - dat ben trai (đối xứng forgot pw)
        btn_test = QtWidgets.QPushButton('🔧 Tài khoản test', pw_field.parent())
        btn_test.setObjectName('btnTestAccounts')
        btn_test.setGeometry(pw_geo.x(), pw_geo.y() + pw_geo.height() + 4, 130, 20)
        btn_test.setCursor(Qt.PointingHandCursor)
        btn_test.setStyleSheet(
            'QPushButton { background: transparent; color: #718096; border: none; '
            'font-size: 11px; font-weight: bold; text-align: left; padding: 0 4px; } '
            'QPushButton:hover { color: #002060; text-decoration: underline; }'
        )

        def _show_test_accounts():
            """Dialog liet ke 4 tai khoan test + click-to-fill."""
            dlg = QtWidgets.QDialog(self.login_win)
            dlg.setWindowTitle('Tài khoản test')
            dlg.setFixedSize(420, 360)
            dlg.setStyleSheet('QDialog { background: white; }')
            v = QtWidgets.QVBoxLayout(dlg)
            v.setContentsMargins(20, 18, 20, 16)
            v.setSpacing(10)

            head = QtWidgets.QLabel('🔧  Tài khoản test - 4 vai trò')
            head.setStyleSheet('color: #002060; font-size: 14px; font-weight: bold;')
            v.addWidget(head)

            sub = QtWidgets.QLabel('Click vào dòng để tự động điền vào form đăng nhập:')
            sub.setStyleSheet('color: #718096; font-size: 11px; padding-bottom: 6px;')
            v.addWidget(sub)

            accounts = [
                ('👨‍🎓 Học viên', 'user', 'passuser', '#002060'),
                ('👨‍🏫 Giảng viên', 'gv1', 'passgv1', '#276749'),
                ('💼 Nhân viên', 'nv1', 'passnv1', '#c05621'),
                ('🛠 Quản trị viên', 'admin', 'passadmin', '#c53030'),
            ]
            for label, uname, pwd, color in accounts:
                btn = QtWidgets.QPushButton(f'  {label}\n  Username: {uname}  ·  Password: {pwd}')
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(
                    f'QPushButton {{ background: white; color: #1a1a2e; border: 1px solid #d2d6dc; '
                    f'border-left: 4px solid {color}; border-radius: 6px; '
                    f'padding: 8px 12px; font-size: 12px; text-align: left; }} '
                    f'QPushButton:hover {{ background: #f7fafc; border-color: {color}; }}'
                )
                def _fill(_u=uname, _p=pwd):
                    self.login_win.txtUsername.setText(_u)
                    self.login_win.txtPassword.setText(_p)
                    dlg.accept()
                btn.clicked.connect(_fill)
                v.addWidget(btn)

            v.addStretch(1)
            note = QtWidgets.QLabel(
                '<i style="color:#a0aec0; font-size:10px;">Lưu ý: chỉ dùng để demo / test. '
                'Trên môi trường production hãy đổi mật khẩu mặc định.</i>'
            )
            note.setWordWrap(True)
            v.addWidget(note)

            close_btn = QtWidgets.QPushButton('Đóng')
            close_btn.setStyleSheet('QPushButton { background: #002060; color: white; border: none; '
                                     'border-radius: 4px; padding: 6px 20px; font-weight: bold; }')
            close_btn.clicked.connect(dlg.reject)
            br = QtWidgets.QHBoxLayout()
            br.addStretch(1); br.addWidget(close_btn)
            v.addLayout(br)
            dlg.exec_()

        btn_test.clicked.connect(_show_test_accounts)
        btn_test.show()

        # Caps Lock warning - hien duoi pw_field, an khi off
        # Detect: trong keyPressEvent neu typed letter co case khac voi shift state -> capslock on
        cap_warn = QtWidgets.QLabel('⚠ Caps Lock đang bật', pw_field.parent())
        cap_warn.setObjectName('lblCapsWarn')
        cap_warn.setGeometry(pw_geo.x(), pw_geo.y() + pw_geo.height() + 2, 250, 18)
        cap_warn.setStyleSheet('color: #c2410c; font-size: 11px; font-weight: bold; background: transparent;')
        cap_warn.hide()

        def _check_capslock(event):
            """Check Caps Lock state via Win32 API; fallback: detect tu typed text"""
            try:
                import ctypes  # Windows-only
                state = ctypes.WinDLL('user32').GetKeyState(0x14) & 1
                return bool(state)
            except Exception:
                # Fallback: check typed letter case vs shift modifier
                t = event.text() if event else ''
                if t and t.isalpha() and len(t) == 1:
                    shift_held = bool(event.modifiers() & Qt.ShiftModifier)
                    return t.isupper() != shift_held
                return None  # khong xac dinh

        class _CapsFilter(QtCore.QObject):
            def eventFilter(self, obj, ev):
                if ev.type() in (QtCore.QEvent.KeyPress, QtCore.QEvent.FocusIn):
                    state = _check_capslock(ev if ev.type() == QtCore.QEvent.KeyPress else None)
                    if state is True:
                        cap_warn.show()
                    elif state is False:
                        cap_warn.hide()
                elif ev.type() == QtCore.QEvent.FocusOut:
                    cap_warn.hide()
                return False
        # luu vao login_win de tranh garbage collect
        self.login_win._caps_filter = _CapsFilter()
        pw_field.installEventFilter(self.login_win._caps_filter)

        def on_login():
            # Username case-insensitive: FE luu lowercase ('hv2024001'), DB
            # WHERE username=%s la case-sensitive. Nếu user go 'HV2024001'
            # se khong khop -> login fail dù seed/registered username dung.
            # Lowercase de match dong nhat. Password giu nguyen case
            u = self.login_win.txtUsername.text().strip().lower()
            p = self.login_win.txtPassword.text().strip()

            if not DB_AVAILABLE:
                self.login_win.lblError.setText(
                    'Hệ thống chưa sẵn sàng. Hãy đảm bảo backend đang chạy '
                    '(uvicorn backend.api.main:app --port 8000).'
                )
                return

            try:
                user_obj = AuthService.login(u, p)
            except Exception as e:
                print(f'[AUTH] API loi: {e}')
                self.login_win.lblError.setText(
                    'Không kết nối được hệ thống. Vui lòng kiểm tra kết nối '
                    'rồi thử lại sau ít phút.'
                )
                return

            if not user_obj:
                self.login_win.lblError.setText('Sai tài khoản hoặc mật khẩu!')
                return

            # Login OK - set MOCK dict theo user that de sidebar/profile hien tai
            self._sync_mock_from_user(user_obj)
            save_last_username(u)
            self.login_win.close()
            window_cls = {
                'student': MainWindow, 'admin': AdminWindow,
                'teacher': TeacherWindow, 'employee': EmployeeWindow,
            }.get(user_obj.role)
            if window_cls:
                self.main_win = window_cls(self)
                self.main_win.current_user = user_obj
                # Append username + role vao title de phan biet khi multi-window
                cur_title = self.main_win.windowTitle()
                self.main_win.setWindowTitle(f'{cur_title}  •  {user_obj.full_name or user_obj.username} ({user_obj.role})')
                self.main_win.show()
                center_on_screen(self.main_win)

        self.login_win.btnLogin.clicked.connect(on_login)
        self.login_win.txtPassword.returnPressed.connect(on_login)
        self.login_win.txtUsername.returnPressed.connect(on_login)

        # Disable Login button khi 1 trong 2 field rong - chi cho phep submit khi du
        def _update_btn_state(_=None):
            has_user = bool(self.login_win.txtUsername.text().strip())
            has_pass = bool(self.login_win.txtPassword.text().strip())
            self.login_win.btnLogin.setEnabled(has_user and has_pass)
            # Clear error khi user bat dau go lai (UX: khong de error stale)
            if self.login_win.lblError.text():
                self.login_win.lblError.setText('')

        self.login_win.txtUsername.textChanged.connect(_update_btn_state)
        self.login_win.txtPassword.textChanged.connect(_update_btn_state)
        _update_btn_state()  # set initial state

        self.login_win.show()
        center_on_screen(self.login_win)

    def run(self):
        self.show_login()
        sys.exit(self.qapp.exec_())


if __name__ == '__main__':
    app = App()
    app.run()
