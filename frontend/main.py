import sys, os
from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QPixmap, QIcon, QColor, QFont
from PyQt5.QtCore import Qt, QDate
from theme_helper import (load_theme, setup_sidebar_icons, setup_stat_icons,
                          apply_eaut_overrides, COLORS, SIDEBAR_ACTIVE, SIDEBAR_NORMAL)


# ===== helpers popup =====
def msg_info(parent, title, text):
    QtWidgets.QMessageBox.information(parent, title, text)


def msg_warn(parent, title, text):
    QtWidgets.QMessageBox.warning(parent, title, text)


def msg_confirm(parent, title, text):
    ans = QtWidgets.QMessageBox.question(
        parent, title, text,
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.No,
    )
    return ans == QtWidgets.QMessageBox.Yes


def msg_input(parent, title, label, default=''):
    text, ok = QtWidgets.QInputDialog.getText(parent, title, label, text=default)
    return text.strip() if ok else None


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

BASE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(BASE, 'ui')
RES = os.path.join(BASE, 'resources')
ICONS = os.path.join(RES, 'icons')

# mock data - 4 role
MOCK_USER = {
    'username': 'user', 'password': 'passuser', 'role': 'Học viên',
    'name': 'Đào Viết Quang Huy', 'msv': 'HV2024001', 'lop': 'IT001-A',
    'khoa': 'Công nghệ thông tin', 'ngaysinh': '15/03/2004', 'gioitinh': 'Nam',
    'nienkhoa': '2024 - 2028', 'hedt': 'Chính quy',
    'email': 'quanghuy@sv.eaut.edu.vn', 'sdt': '0912345678',
    'diachi': 'Đà Nẵng', 'initials': 'QH',
}

MOCK_ADMIN = {
    'username': 'admin', 'password': 'passadmin',
    'name': 'Admin', 'role': 'Quản trị viên', 'initials': 'AD',
}

MOCK_TEACHER = {
    'username': 'teacher', 'password': 'passtea', 'role': 'Giảng viên',
    'id': 'GV001', 'name': 'Nguyễn Đức Thiện', 'initials': 'NT',
    'khoa': 'Công nghệ thông tin', 'hocvi': 'Tiến sĩ',
    'email': 'thien@eaut.edu.vn', 'sdt': '0901234567',
}

MOCK_EMPLOYEE = {
    'username': 'employee', 'password': 'passemp', 'role': 'Nhân viên',
    'id': 'NV001', 'name': 'Trần Thu Hương', 'initials': 'TH',
    'chucvu': 'Nhân viên đăng ký',
    'email': 'huongtt@eaut.edu.vn', 'sdt': '0987654321',
}

# mock classes - mỗi môn có nhiều lớp với giá khác nhau
MOCK_COURSES = [
    ('IT001', 'Lập trình Python'),
    ('IT002', 'Cơ sở dữ liệu'),
    ('IT003', 'Mạng máy tính'),
    ('IT004', 'Trí tuệ nhân tạo'),
    ('MA001', 'Toán rời rạc'),
]

MOCK_CLASSES = [
    # (ma_lop, ma_mon, ten_mon, gv, lich, phong, sisoMax, siso, gia)
    ('IT001-A', 'IT001', 'Lập trình Python', 'Nguyễn Đức Thiện', 'T3, T5 (7:00-9:30)', 'P.A301', 40, 35, 2500000),
    ('IT001-B', 'IT001', 'Lập trình Python', 'Lê Trung Thực', 'T4, T6 (13:00-15:30)', 'P.B205', 40, 28, 1800000),
    ('IT001-C', 'IT001', 'Lập trình Python', 'Ngô Thảo Anh', 'T2, T7 (15:40-18:10)', 'P.C102', 35, 35, 2000000),
    ('IT002-A', 'IT002', 'Cơ sở dữ liệu', 'Lê Thị C', 'T5 (7:00-9:30)', 'P.A202', 40, 35, 2200000),
    ('IT002-B', 'IT002', 'Cơ sở dữ liệu', 'Phạm Văn K', 'T3 (13:00-15:30)', 'P.B108', 40, 22, 1800000),
    ('IT003-A', 'IT003', 'Mạng máy tính', 'Phạm Văn D', 'T6 (7:00-9:30)', 'P.A105', 30, 18, 2000000),
    ('IT004-A', 'IT004', 'Trí tuệ nhân tạo', 'Nguyễn Đức Thiện', 'T3 (7:00-9:30)', 'P.A301', 40, 28, 2800000),
    ('IT004-B', 'IT004', 'Trí tuệ nhân tạo', 'Hoàng Minh Tuấn', 'T5 (13:00-15:30)', 'P.B301', 35, 20, 2200000),
    ('MA001-A', 'MA001', 'Toán rời rạc', 'Nguyễn Thị E', 'T2 (9:30-12:00)', 'P.A203', 40, 30, 1500000),
    ('MA001-B', 'MA001', 'Toán rời rạc', 'Lê Văn M', 'T4 (9:30-12:00)', 'P.B204', 40, 25, 1200000),
]


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
    ('btnTeaNotice', 'teacher_notice.ui'),
    ('btnTeaGrades', 'teacher_grades.ui'),
    ('btnTeaProfile', 'profile.ui'),
]

TEACHER_MENU = [
    ('btnTeaDash', 'iconTeaDash', 'home', 'Tổng quan'),
    ('btnTeaSchedule', 'iconTeaSchedule', 'calendar', 'Lịch dạy'),
    ('btnTeaClasses', 'iconTeaClasses', 'layers', 'Lớp của tôi'),
    ('btnTeaStudents', 'iconTeaStudents', 'users', 'Học viên'),
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
        self.setFixedSize(1100, 700)
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
        self.lblSidebarSub.setGeometry(68, 40, 150, 16)
        self.lblSidebarSub.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 11px; background: transparent;')

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
        for r in range(len(hours)):
            tbl.setRowHeight(r, 45)
            item = QtWidgets.QTableWidgetItem(hours[r])
            item.setTextAlignment(Qt.AlignRight | Qt.AlignTop)
            item.setForeground(QColor('#718096'))
            item.setFont(QFont('Segoe UI', 8))
            tbl.setItem(r, 0, item)

        for r in range(len(hours)):
            for c in range(1, 7):
                if not tbl.item(r, c) and not tbl.cellWidget(r, c):
                    tbl.setItem(r, c, QtWidgets.QTableWidgetItem(''))

        def mk_card(ten, ts, toa, phong, gv, color):
            f = QtWidgets.QFrame()
            f.setStyleSheet(f'QFrame {{ background: white; border: 1px solid #d2d6dc; border-radius: 4px; border-top: 3px solid {color}; margin: 1px; }}')
            vb = QtWidgets.QVBoxLayout(f)
            vb.setContentsMargins(4, 3, 4, 3)
            vb.setSpacing(1)
            for txt, st in [(ten, f'color: {color}; font-size: 9px; font-weight: bold; border: none;'),
                            (ts, 'color: #4a5568; font-size: 8px; border: none;'),
                            (f'Tòa {toa} - {phong}', 'color: #718096; font-size: 8px; border: none;'),
                            (gv, 'color: #4a5568; font-size: 8px; border: none;')]:
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
            cbo.currentIndexChanged.connect(lambda idx: msg_info(self, 'Lịch thi', f'Hiển thị lịch thi của kỳ: {cbo.currentText()}'))

    def _fill_grades(self):
        page = self.page_widgets[3]
        data = [
            ['IT001', 'Nhập môn lập trình', '3', '8.5', '7.0', '7.5', 'B+'],
            ['IT002', 'Cấu trúc dữ liệu', '3', '9.0', '8.5', '8.7', 'A'],
            ['MA001', 'Giải tích 1', '3', '7.0', '6.5', '6.7', 'C+'],
            ['MA002', 'Đại số tuyến tính', '3', '8.0', '7.5', '7.7', 'B'],
            ['EN001', 'Tiếng Anh 1', '3', '9.0', '9.0', '9.0', 'A+'],
            ['IT003', 'Kỹ thuật lập trình', '3', '8.0', '8.0', '8.0', 'B+'],
            ['PH001', 'Vật lý đại cương', '2', '7.5', '6.0', '6.6', 'C+'],
            ['IT004', 'Hệ điều hành', '3', '8.5', '8.0', '8.2', 'B+'],
            ['MA003', 'Xác suất thống kê', '3', '7.0', '7.5', '7.3', 'B'],
            ['IT005', 'Mạng máy tính', '3', '9.0', '8.0', '8.4', 'A'],
        ]
        grade_colors = {'A+': COLORS['green'], 'A': COLORS['green'], 'B+': COLORS['navy'], 'B': COLORS['navy'], 'C+': COLORS['orange']}
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblGrades')
        if not tbl:
            return
        tbl.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, val in enumerate(row):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c >= 2 else Qt.AlignLeft | Qt.AlignVCenter)
                if c == 6:
                    item.setForeground(QColor(grade_colors.get(val, '#4a5568')))
                    item.setFont(QFont('Segoe UI', 11, QFont.Bold))
                elif c == 5:
                    s = float(val)
                    item.setForeground(QColor(COLORS['green'] if s >= 8 else COLORS['navy'] if s >= 6.5 else COLORS['orange']))
                tbl.setItem(r, c, item)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, w in enumerate([60, 180, 35, 75, 75, 80]):
            tbl.setColumnWidth(c, w)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 40)

        # GPA cards
        for attr, val, color in [('lblGpa', '3.24', COLORS['navy']),
                                 ('lblGpaSem', '3.40', COLORS['green']),
                                 ('lblTotalCredits', '45', COLORS['gold'])]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setText(val)
                w.setStyleSheet(f'color: {color}; font-size: 22px; font-weight: bold; background: transparent;')

        # export button
        header = page.findChild(QtWidgets.QFrame, 'headerBar')
        if header:
            btn_export = QtWidgets.QPushButton('Xuất PDF', header)
            btn_export.setGeometry(720, 14, 90, 28)
            btn_export.setCursor(Qt.PointingHandCursor)
            btn_export.setStyleSheet(f'QPushButton {{ background: white; color: {COLORS["navy"]}; border: 1px solid {COLORS["navy"]}; border-radius: 4px; padding: 4px 12px; font-size: 11px; }} QPushButton:hover {{ background: {COLORS["navy"]}; color: white; }}')
            btn_export.show()
            btn_export.clicked.connect(lambda: msg_info(self, 'Xuất PDF', 'Đã xuất bảng điểm ra file PDF (tinh.nang.demo)'))

        # loc theo hoc ky
        cbo = page.findChild(QtWidgets.QComboBox, 'cboSemester')
        if cbo:
            cbo.currentIndexChanged.connect(lambda idx: self._filter_grades_sem(idx))

    def _filter_grades_sem(self, idx):
        page = self.page_widgets[3]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblGrades')
        if not tbl:
            return
        # idx 0 = tat ca, 1 = HK2 (odd rows), 2 = HK1 (even rows)
        for r in range(tbl.rowCount()):
            if idx == 0:
                tbl.setRowHidden(r, False)
            elif idx == 1:
                tbl.setRowHidden(r, r % 2 == 1)
            else:
                tbl.setRowHidden(r, r % 2 == 0)

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
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
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

    def _change_pass(self):
        dlg = QtWidgets.QDialog(self)
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
        msg_info(self, 'Thành công', 'Đổi mật khẩu thành công')


class AdminWindow(QtWidgets.QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.setObjectName('MainWindow')
        self.setWindowTitle('EAUT - Quản trị hệ thống')
        self.setFixedSize(1250, 720)
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
        lbl_sub.setGeometry(68, 40, 150, 16)
        lbl_sub.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 11px; background: transparent;')

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
        # top courses voi progress bar
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblTopCourses')
        if tbl:
            data = [('Lập trình Python', 40, 40), ('Cơ sở dữ liệu', 35, 40),
                    ('Trí tuệ nhân tạo', 28, 40), ('Phát triển web', 22, 35),
                    ('Mạng máy tính', 18, 30)]
            tbl.setRowCount(len(data))
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
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setColumnWidth(0, 150)
            tbl.setColumnWidth(1, 55)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 34)

        # recent voi badge loai
        tbl2 = page.findChild(QtWidgets.QTableWidget, 'tblRecent')
        if tbl2:
            data = [('2 phút trước', 'Trần Văn B đăng ký IT003', COLORS['green']),
                    ('15 phút trước', 'Lê Thị C hủy MA002', COLORS['red']),
                    ('1 giờ trước', 'Phạm Văn D đăng ký IT005', COLORS['green']),
                    ('3 giờ trước', 'Nguyễn Thị E đăng ký EN001', COLORS['green']),
                    ('5 giờ trước', 'Hoàng Văn F đổi mật khẩu', COLORS['text_mid'])]
            tbl2.setRowCount(len(data))
            for r, (time_str, content, color) in enumerate(data):
                item_time = QtWidgets.QTableWidgetItem(time_str)
                item_time.setForeground(QColor(COLORS['text_light']))
                item_time.setFont(QFont('Segoe UI', 9))
                tbl2.setItem(r, 0, item_time)
                item_content = QtWidgets.QTableWidgetItem(content)
                tbl2.setItem(r, 1, item_content)
            tbl2.horizontalHeader().setStretchLastSection(True)
            tbl2.setColumnWidth(0, 100)
            tbl2.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl2.setRowHeight(r, 34)

        # by dept
        tbl3 = page.findChild(QtWidgets.QTableWidget, 'tblByDept')
        if tbl3:
            data = [['CNTT', '98', '12', '186', '4.8'], ['Toán', '30', '6', '78', '4.2'],
                    ['Ngoại ngữ', '18', '4', '42', '3.8'], ['Vật lý', '10', '2', '16', '3.2']]
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

    def _fill_admin_courses(self):
        page = self.page_widgets[1]
        si = page.findChild(QtWidgets.QLabel, 'iconSearchCourse')
        if si:
            si.setPixmap(QPixmap(os.path.join(ICONS, 'search.png')).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        data = [
            ['IT001', 'Lập trình Python', '3', 'Nguyễn Đức Thiện', 'T3 (7:00-9:30)', 40, 40],
            ['IT002', 'Cơ sở dữ liệu', '3', 'Lê Thị C', 'T5 (7:00-9:30)', 35, 40],
            ['IT003', 'Mạng máy tính', '3', 'Phạm Văn D', 'T6 (7:00-9:30)', 18, 30],
            ['MA001', 'Toán rời rạc', '3', 'Nguyễn Thị E', 'T2 (9:30-12:00)', 30, 40],
            ['EN001', 'Tiếng Anh 3', '3', 'Hoàng Văn F', 'T4 (13:00-15:30)', 15, 35],
            ['IT004', 'Trí tuệ nhân tạo', '3', 'Nguyễn Văn G', 'T3 (7:00-9:30)', 28, 40],
        ]
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

        # wire search / filter / add
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchCourse')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[0, 1, 3]))
        btn_s = page.findChild(QtWidgets.QPushButton, 'btnSearchCourse')
        if btn_s and txt:
            btn_s.clicked.connect(lambda: table_filter(tbl, txt.text(), cols=[0, 1, 3]))
        cbo = page.findChild(QtWidgets.QComboBox, 'cboFilterDept')
        if cbo:
            cbo.currentIndexChanged.connect(lambda idx: msg_info(self, 'Lọc khoa', f'Đã lọc theo: {cbo.currentText()}'))
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddCourse')
        if btn_add:
            btn_add.clicked.connect(self._admin_add_course)

    def _admin_add_course(self):
        dlg = QtWidgets.QDialog(self)
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
            vals = [txt_code.text().upper(), txt_name.text(), txt_tc.text() or '3', txt_gv.text() or '—', '—']
            for c, v in enumerate(vals):
                tbl.setItem(r, c, QtWidgets.QTableWidgetItem(v))
            item_ss = QtWidgets.QTableWidgetItem('0/40')
            item_ss.setTextAlignment(Qt.AlignCenter)
            item_ss.setForeground(QColor(COLORS['green']))
            tbl.setItem(r, 5, item_ss)
            tbl.setRowHeight(r, 44)
        # them vao MOCK_COURSES
        MOCK_COURSES.append((txt_code.text().upper(), txt_name.text()))
        msg_info(self, 'Thành công', f'Đã thêm môn {txt_code.text()} - {txt_name.text()}')

    def _admin_edit_course(self, ma, nm):
        new_name = msg_input(self, 'Sửa môn học', f'Tên mới cho {ma}:', nm)
        if new_name:
            tbl = self.page_widgets[1].findChild(QtWidgets.QTableWidget, 'tblAdminCourses')
            if tbl:
                for r in range(tbl.rowCount()):
                    it = tbl.item(r, 0)
                    if it and it.text() == ma:
                        tbl.setItem(r, 1, QtWidgets.QTableWidgetItem(new_name))
                        break
            msg_info(self, 'Đã sửa', f'Đã cập nhật {ma} thành: {new_name}')

    def _admin_del_row(self, tbl, ma, nm, loai):
        if not msg_confirm(self, 'Xác nhận xóa', f'Xóa {loai} {ma} - {nm}?'):
            return
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

        data = [
            ['2024001', 'Đào Viết Quang Huy', 'CNTT-K20A', 'CNTT', '0912345678', '5'],
            ['2024002', 'Trần Thị B', 'CNTT-K20A', 'CNTT', '0923456789', '4'],
            ['2024003', 'Lê Văn C', 'CNTT-K20B', 'CNTT', '0934567890', '6'],
            ['2024010', 'Phạm Thị D', 'TOAN-K20', 'Toán', '0945678901', '5'],
            ['2024015', 'Hoàng Văn E', 'NN-K20', 'Ngoại ngữ', '0956789012', '3'],
            ['2024020', 'Vũ Thị F', 'CNTT-K20B', 'CNTT', '0967890123', '5'],
        ]
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
                        btns[0].clicked.connect(lambda ch, rd=row: msg_info(
                            self, 'Chi tiết học viên',
                            f"MSV: {rd[0]}\nHọ tên: {rd[1]}\nLớp: {rd[2]}\nKhoa: {rd[3]}\nSDT: {rd[4]}\nSố môn đăng ký: {rd[5]}"))
                        btns[1].clicked.connect(lambda ch, ma=row[0], nm=row[1], t=tbl: self._admin_del_row(t, ma, nm, 'học viên'))

        # search / filter / add
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchStudent')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[0, 1]))
        btn_s = page.findChild(QtWidgets.QPushButton, 'btnSearchStudent')
        if btn_s and txt:
            btn_s.clicked.connect(lambda: table_filter(tbl, txt.text(), cols=[0, 1]))
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboFilterClass')
        cbo_d = page.findChild(QtWidgets.QComboBox, 'cboFilterDeptSt')
        if cbo_c:
            cbo_c.currentIndexChanged.connect(lambda: self._admin_filter_students())
        if cbo_d:
            cbo_d.currentIndexChanged.connect(lambda: self._admin_filter_students())
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddStudent')
        if btn_add:
            btn_add.clicked.connect(self._admin_add_student)

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
        msg_info(self, 'Thành công', f'Đã thêm học viên {widgets["msv"].text()}')

    def _fill_admin_semester(self):
        page = self.page_widgets[6]
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
        btn.setText('Mở ĐK' if is_open else 'Đóng ĐK')
        msg_info(self, 'Thành công', f'Đã {new_state} đăng ký cho {ma}')

    def _admin_add_semester(self):
        dlg = QtWidgets.QDialog(self)
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
        msg_info(self, 'Thành công', f'Đã thêm học kỳ {ma.text()}')

    def _fill_admin_curriculum(self):
        page = self.page_widgets[7]
        si = page.findChild(QtWidgets.QLabel, 'iconSearchCurr')
        if si:
            si.setPixmap(QPixmap(os.path.join(ICONS, 'search.png')).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

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
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCurriculum')
        if tbl:
            tbl.setRowCount(len(data))
            type_colors = {'Bắt buộc': COLORS['navy'], 'Tự chọn': COLORS['green'], 'Đại cương': COLORS['gold']}
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter if c in (0, 3, 4, 5) else Qt.AlignLeft | Qt.AlignVCenter)
                    if c == 4:
                        item.setForeground(QColor(type_colors.get(val, COLORS['text_mid'])))
                    tbl.setItem(r, c, item)
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
                tbl.setCellWidget(r, 7, w)
            for c, cw in enumerate([32, 65, 160, 28, 95, 50, 100, 155]):
                tbl.setColumnWidth(c, cw)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)
            # wire action
            for r, row in enumerate(data):
                w = tbl.cellWidget(r, 7)
                if w:
                    btns = w.findChildren(QtWidgets.QPushButton)
                    if len(btns) >= 2:
                        btns[0].clicked.connect(lambda ch, rd=row: msg_info(self, 'Sửa môn',
                            f"Mã môn: {rd[1]}\nTên: {rd[2]}\nTín chỉ: {rd[3]}\nLoại: {rd[4]}\nHK: {rd[5]}"))
                        btns[1].clicked.connect(lambda ch, ma=row[1], nm=row[2], t=tbl: self._admin_del_row(t, ma, nm, 'môn trong CT'))

        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchCurr')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[1, 2]))
        for nm in ('cboNganh', 'cboLoai', 'cboHocKy'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda idx, n=nm, c=cbo:
                    msg_info(self, 'Bộ lọc', f'Đã áp dụng: {c.currentText()}') if idx > 0 else None)
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddCurr')
        if btn_add:
            btn_add.clicked.connect(lambda: msg_info(self, 'Thêm môn', 'Đã mở hộp thoại thêm môn vào khung CT (demo)'))
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportCurr')
        if btn_exp:
            btn_exp.clicked.connect(lambda: msg_info(self, 'Xuất CTĐT', 'Đã xuất khung chương trình ra PDF'))

    def _fill_admin_audit(self):
        page = self.page_widgets[8]
        si = page.findChild(QtWidgets.QLabel, 'iconSearchAudit')
        if si:
            si.setPixmap(QPixmap(os.path.join(ICONS, 'search.png')).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

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

        # search + filter
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchAudit')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[1, 3, 4]))
        for nm in ('cboAuditUser', 'cboAuditAction', 'cboAuditDate'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda idx, c=cbo:
                    msg_info(self, 'Lọc log', f'Đã lọc: {c.currentText()}') if idx > 0 else None)
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportAudit')
        if btn_exp:
            btn_exp.clicked.connect(lambda: msg_info(self, 'Xuất log', 'Đã xuất nhật ký hệ thống ra CSV'))

    def _fill_admin_stats(self):
        page = self.page_widgets[9]
        # chart data voi progress bar
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblChartData')
        if tbl:
            data = [('Lập trình Python', 40, 40), ('CSDL', 35, 40),
                    ('Mạng MT', 18, 30), ('Toán rời rạc', 30, 40),
                    ('Tiếng Anh 3', 15, 35), ('Trí tuệ nhân tạo', 28, 40)]
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

        # dept stats
        tbl2 = page.findChild(QtWidgets.QTableWidget, 'tblDeptStats')
        if tbl2:
            data = [['CNTT', '98', '63%'], ['Toán', '30', '19%'], ['Ngoại ngữ', '18', '12%'], ['Khác', '10', '6%']]
            tbl2.setRowCount(len(data))
            for r, row in enumerate(data):
                for c, val in enumerate(row):
                    tbl2.setItem(r, c, QtWidgets.QTableWidgetItem(val))
            tbl2.horizontalHeader().setStretchLastSection(True)
            tbl2.setColumnWidth(0, 100)
            tbl2.setColumnWidth(1, 60)
            tbl2.verticalHeader().setVisible(False)

        # class stats
        tbl3 = page.findChild(QtWidgets.QTableWidget, 'tblClassStats')
        if tbl3:
            data = [['CNTT-K20A', '35', '4.8', '504'], ['CNTT-K20B', '33', '4.5', '445'],
                    ['TOAN-K20', '30', '4.2', '378'], ['NN-K20', '28', '3.8', '319']]
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

        cbo = page.findChild(QtWidgets.QComboBox, 'cboStatSemester')
        if cbo:
            cbo.currentIndexChanged.connect(lambda idx:
                msg_info(self, 'Thống kê', f'Hiển thị thống kê kỳ: {cbo.currentText()}'))

    def _fill_admin_classes(self):
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmClasses')
        if not tbl:
            return
        type_colors = {'Còn chỗ': COLORS['green'], 'Đầy': COLORS['red']}
        tbl.setRowCount(len(MOCK_CLASSES))
        for r, cls in enumerate(MOCK_CLASSES):
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
            btn_edit.clicked.connect(lambda ch, cls_ma=ma, cls_mon=tmon, cls_gv=gv: msg_info(
                self, 'Sửa lớp', f'Mở form sửa lớp {cls_ma} - {cls_mon} (GV: {cls_gv})'))
            btn_del.clicked.connect(lambda ch, cls_ma=ma, cls_mon=tmon, t=tbl: self._admin_del_row(t, cls_ma, cls_mon, 'lớp'))
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([85, 155, 140, 150, 75, 75, 115, 130]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(MOCK_CLASSES)):
            tbl.setRowHeight(r, 44)

        # search / filter / add
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchCls')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[0, 1, 2]))
        for nm in ('cboAdmClsCourse', 'cboAdmClsTeacher', 'cboAdmClsStatus'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda idx, c=cbo:
                    msg_info(self, 'Lọc lớp', f'Lọc: {c.currentText()}') if idx > 0 else None)
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddClass')
        if btn_add:
            btn_add.clicked.connect(self._admin_add_class)

    def _admin_add_class(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle('Thêm lớp')
        dlg.setFixedSize(400, 320)
        form = QtWidgets.QFormLayout(dlg)
        ma = QtWidgets.QLineEdit()
        mon = QtWidgets.QLineEdit()
        gv = QtWidgets.QLineEdit()
        lich = QtWidgets.QLineEdit('T2 (7:00-9:30)')
        phong = QtWidgets.QLineEdit('P.?')
        smax = QtWidgets.QLineEdit('40')
        gia = QtWidgets.QLineEdit('2000000')
        form.addRow('Mã lớp:', ma)
        form.addRow('Môn:', mon)
        form.addRow('GV:', gv)
        form.addRow('Lịch:', lich)
        form.addRow('Phòng:', phong)
        form.addRow('Sĩ số max:', smax)
        form.addRow('Học phí:', gia)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if not ma.text().strip() or not mon.text().strip():
            msg_warn(self, 'Thiếu', 'Mã lớp và môn không được trống')
            return
        try:
            smax_n = int(smax.text())
            gia_n = int(gia.text())
        except ValueError:
            msg_warn(self, 'Sai dữ liệu', 'Sĩ số và học phí phải là số')
            return
        MOCK_CLASSES.append((ma.text().upper(), '???', mon.text(), gv.text() or '—',
                             lich.text(), phong.text(), smax_n, 0, gia_n))
        # re-fill
        self.pages_filled[2] = False
        self._fill_admin_classes()
        self.pages_filled[2] = True
        msg_info(self, 'Thành công', f'Đã thêm lớp {ma.text()}')

    def _fill_admin_teachers(self):
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmTeachers')
        if not tbl:
            return
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
            btn_edit.clicked.connect(lambda ch, rd=row: msg_info(
                self, 'Chi tiết GV',
                f"Mã: {rd[0]}\nHọ tên: {rd[1]}\nKhoa: {rd[2]}\nHọc vị: {rd[3]}\nSDT: {rd[4]}\nSố lớp: {rd[5]}\nĐiểm đánh giá: {rd[6]:.1f}/5"))
            btn_del.clicked.connect(lambda ch, ma=row[0], nm=row[1], t=tbl: self._admin_del_row(t, ma, nm, 'giảng viên'))
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([75, 170, 140, 110, 115, 70, 90, 140]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 44)

        # search / filter / add
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchTea')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[0, 1]))
        for nm in ('cboTeaKhoa', 'cboTeaHocVi'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda idx, c=cbo:
                    msg_info(self, 'Lọc GV', f'Lọc: {c.currentText()}') if idx > 0 else None)
        btn_add = page.findChild(QtWidgets.QPushButton, 'btnAddTeacher')
        if btn_add:
            btn_add.clicked.connect(lambda: self._admin_add_user('giảng viên', 4, 'tblAdmTeachers',
                                                                  ['Mã GV', 'Họ tên', 'Khoa', 'Học vị', 'SDT']))

    def _admin_add_user(self, role_name, page_idx, tbl_name, fields):
        dlg = QtWidgets.QDialog(self)
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
        msg_info(self, 'Thành công', f'Đã thêm {role_name}: {widgets[1].text()}')

    def _fill_admin_employees(self):
        page = self.page_widgets[5]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblAdmEmployees')
        if not tbl:
            return
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
            btn_edit.clicked.connect(lambda ch, rd=row: msg_info(
                self, 'Chi tiết NV',
                f"Mã: {rd[0]}\nHọ tên: {rd[1]}\nChức vụ: {rd[2]}\nSDT: {rd[3]}\nEmail: {rd[4]}\nTrạng thái: {rd[5]}"))
            btn_del.clicked.connect(lambda ch, ma=row[0], nm=row[1], t=tbl: self._admin_del_row(t, ma, nm, 'nhân viên'))
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([75, 170, 170, 115, 195, 90, 140]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 44)

        # search / filter / add
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchEmp')
        if txt:
            txt.textChanged.connect(lambda s: table_filter(tbl, s, cols=[0, 1]))
        for nm in ('cboEmpRole', 'cboEmpStatus'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda idx, c=cbo:
                    msg_info(self, 'Lọc NV', f'Lọc: {c.currentText()}') if idx > 0 else None)
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
        self.setFixedSize(1100, 700)
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
        lbl_sub.setGeometry(68, 40, 150, 16)
        lbl_sub.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 11px; background: transparent;')

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
                    self._fill_tea_notice, self._fill_tea_grades,
                    self._fill_tea_profile]
            fill[index]()
            self.pages_filled[index] = True

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
        for r in range(len(hours)):
            tbl.setRowHeight(r, 45)
            item = QtWidgets.QTableWidgetItem(hours[r])
            item.setTextAlignment(Qt.AlignRight | Qt.AlignTop)
            item.setForeground(QColor('#718096'))
            item.setFont(QFont('Segoe UI', 8))
            tbl.setItem(r, 0, item)
        for r in range(len(hours)):
            for c in range(1, 7):
                if not tbl.item(r, c) and not tbl.cellWidget(r, c):
                    tbl.setItem(r, c, QtWidgets.QTableWidgetItem(''))

        def mk(ten, ts, toa, phong, ss, color):
            f = QtWidgets.QFrame()
            f.setStyleSheet(f'QFrame {{ background: white; border: 1px solid #d2d6dc; border-radius: 4px; border-top: 3px solid {color}; margin: 1px; }}')
            vb = QtWidgets.QVBoxLayout(f)
            vb.setContentsMargins(4, 3, 4, 3)
            vb.setSpacing(1)
            for txt, st in [(ten, f'color: {color}; font-size: 9px; font-weight: bold; border: none;'),
                            (ts, 'color: #4a5568; font-size: 8px; border: none;'),
                            (f'Tòa {toa} - {phong}', 'color: #718096; font-size: 8px; border: none;'),
                            (ss, 'color: #4a5568; font-size: 8px; border: none;')]:
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

    def _fill_tea_classes(self):
        page = self.page_widgets[2]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblTeacherClasses')
        if not tbl:
            return
        # lớp của GV Nguyễn Đức Thiện (GV001)
        my_classes = [c for c in MOCK_CLASSES if c[3] == 'Nguyễn Đức Thiện']
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
            tbl.setItem(r, 3, QtWidgets.QTableWidgetItem(lich))
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
            btn.setFixedSize(76, 26)
            btn.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
            btn.clicked.connect(lambda ch, m=ma, n=tmon, s=siso, mx=smax, p=phong, l=lich:
                msg_info(self, 'Chi tiết lớp',
                         f'Mã lớp: {m}\nMôn: {n}\nLịch: {l}\nPhòng: {p}\nSĩ số: {s}/{mx}'))
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(btn)
            tbl.setCellWidget(r, 6, w)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([100, 180, 80, 160, 80, 120, 96]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(my_classes)):
            tbl.setRowHeight(r, 44)

    def _fill_tea_students(self):
        page = self.page_widgets[3]
        # populate class filter
        cbo = page.findChild(QtWidgets.QComboBox, 'cboClass')
        if cbo:
            cbo.clear()
            cbo.addItem('Tất cả lớp')
            for cls in MOCK_CLASSES:
                if cls[3] == 'Nguyễn Đức Thiện':
                    cbo.addItem(cls[0])

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblStudents')
        if not tbl:
            return
        data = [
            ['1', 'HV2024001', 'Đào Viết Quang Huy', 'IT001-A', '0912345678', 'Đang học'],
            ['2', 'HV2024002', 'Trần Thị Bích', 'IT001-A', '0923456789', 'Đang học'],
            ['3', 'HV2024003', 'Lê Văn Cường', 'IT001-A', '0934567890', 'Đang học'],
            ['4', 'HV2024010', 'Phạm Thị Dung', 'IT001-A', '0945678901', 'Tạm nghỉ'],
            ['5', 'HV2024015', 'Hoàng Văn Em', 'IT001-A', '0956789012', 'Đang học'],
            ['6', 'HV2024020', 'Vũ Thị Phương', 'IT004-A', '0967890123', 'Đang học'],
            ['7', 'HV2024025', 'Nguyễn Thanh Giang', 'IT004-A', '0978901234', 'Đang học'],
            ['8', 'HV2024030', 'Bùi Thị Hồng', 'IT001-C', '0989012345', 'Đang học'],
        ]
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

        # filter + search
        txt_s = page.findChild(QtWidgets.QLineEdit, 'txtSearchStudent')
        if txt_s:
            txt_s.textChanged.connect(lambda t: table_filter(tbl, t, cols=[1, 2]))
        if cbo:
            cbo.currentIndexChanged.connect(lambda: self._filter_tea_students())
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportStudents')
        if btn_exp:
            btn_exp.clicked.connect(lambda: msg_info(self, 'Xuất danh sách', 'Đã xuất danh sách học viên ra Excel'))

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
        page = self.page_widgets[4]
        cbo = page.findChild(QtWidgets.QComboBox, 'cboTargetClass')
        if cbo:
            cbo.clear()
            cbo.addItem('Tất cả lớp đang dạy')
            for cls in MOCK_CLASSES:
                if cls[3] == 'Nguyễn Đức Thiện':
                    cbo.addItem(cls[0])

        # populate sent list
        sc = page.findChild(QtWidgets.QWidget, 'sentContent')
        if sc:
            sc.setMinimumHeight(500)
            vlay = QtWidgets.QVBoxLayout(sc)
            vlay.setContentsMargins(4, 4, 4, 4)
            vlay.setSpacing(8)
            sent = [
                ('IT001-A', 'Nghỉ học ngày 20/04', '2 ngày trước'),
                ('IT004-A', 'Bài tập tuần 8', '3 ngày trước'),
                ('Tất cả', 'Thông báo kiểm tra giữa kỳ', '1 tuần trước'),
                ('IT001-C', 'Đổi phòng học', '1 tuần trước'),
            ]
            for to, subj, t in sent:
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
                l3 = QtWidgets.QLabel(t)
                l3.setStyleSheet(f'color: {COLORS["text_light"]}; font-size: 10px; background: transparent; border: none;')
                vb.addWidget(l1)
                vb.addWidget(l2)
                vb.addWidget(l3)
                vlay.addWidget(card)
            vlay.addStretch()

        # nut gui / clear
        btn_send = page.findChild(QtWidgets.QPushButton, 'btnSendNotice')
        if btn_send:
            btn_send.clicked.connect(self._tea_send_notice)
        btn_clear = page.findChild(QtWidgets.QPushButton, 'btnClearNotice')
        if btn_clear:
            btn_clear.clicked.connect(self._tea_clear_notice)

    def _tea_send_notice(self):
        page = self.page_widgets[4]
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
        msg_info(self, 'Gửi thông báo', f'Đã gửi thông báo đến: {target}\nTiêu đề: {subj.text()}')
        subj.clear(); content.clear()

    def _tea_clear_notice(self):
        page = self.page_widgets[4]
        for name in ('txtSubject',):
            w = page.findChild(QtWidgets.QLineEdit, name)
            if w: w.clear()
        w = page.findChild(QtWidgets.QTextEdit, 'txtContent')
        if w: w.clear()

    def _fill_tea_grades(self):
        page = self.page_widgets[5]
        cbo = page.findChild(QtWidgets.QComboBox, 'cboGradeClass')
        if cbo:
            cbo.clear()
            cbo.addItem('-- Chọn lớp để nhập điểm --')
            for cls in MOCK_CLASSES:
                if cls[3] == 'Nguyễn Đức Thiện':
                    cbo.addItem(cls[0])

        tbl = page.findChild(QtWidgets.QTableWidget, 'tblTeacherGrades')
        if not tbl:
            return
        data = [
            ['1', 'HV2024001', 'Đào Viết Quang Huy', '8.5', '7.5', '7.8', 'B+'],
            ['2', 'HV2024002', 'Trần Thị Bích', '9.0', '8.5', '8.7', 'A'],
            ['3', 'HV2024003', 'Lê Văn Cường', '7.0', '6.5', '6.7', 'C+'],
            ['4', 'HV2024010', 'Phạm Thị Dung', '8.0', '7.5', '7.7', 'B'],
            ['5', 'HV2024015', 'Hoàng Văn Em', '9.5', '9.0', '9.2', 'A+'],
            ['6', 'HV2024018', 'Đinh Văn Khánh', '7.5', '7.0', '7.2', 'B'],
            ['7', 'HV2024022', 'Lâm Thị Nga', '8.5', '8.0', '8.2', 'B+'],
            ['8', 'HV2024028', 'Trịnh Minh Quân', '6.0', '6.5', '6.4', 'C'],
        ]
        grade_colors = {'A+': COLORS['green'], 'A': COLORS['green'], 'B+': COLORS['navy'], 'B': COLORS['navy'], 'C+': COLORS['orange'], 'C': COLORS['orange']}
        tbl.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, val in enumerate(row):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c != 2 else Qt.AlignLeft | Qt.AlignVCenter)
                if c == 6:
                    item.setForeground(QColor(grade_colors.get(val, COLORS['text_mid'])))
                # chi cho edit cot 3 (diem qt), 4 (diem thi)
                if c not in (3, 4):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                tbl.setItem(r, c, item)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([45, 110, 210, 90, 90, 95, 100]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 42)

        # setEditTriggers de cho nhap dc
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)
        tbl.itemChanged.connect(self._recalc_grade_row)
        self._grades_recalc_lock = False

        # save button
        btn = page.findChild(QtWidgets.QPushButton, 'btnSaveGrades')
        if btn:
            btn.clicked.connect(self._save_tea_grades)
        if cbo:
            cbo.currentIndexChanged.connect(lambda idx:
                msg_info(self, 'Chọn lớp', f'Đang nhập điểm cho lớp: {cbo.currentText()}') if idx > 0 else None)

    def _recalc_grade_row(self, item):
        if getattr(self, '_grades_recalc_lock', False):
            return
        c = item.column()
        if c not in (3, 4):
            return
        page = self.page_widgets[5]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblTeacherGrades')
        if not tbl:
            return
        r = item.row()
        try:
            qt = float(tbl.item(r, 3).text().replace(',', '.')) if tbl.item(r, 3) else 0
            thi = float(tbl.item(r, 4).text().replace(',', '.')) if tbl.item(r, 4) else 0
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
        tbl.setItem(r, 5, it_tot)
        grade_colors = {'A+': COLORS['green'], 'A': COLORS['green'], 'B+': COLORS['navy'], 'B': COLORS['navy'],
                        'C+': COLORS['orange'], 'C': COLORS['orange'], 'D': COLORS['red'], 'F': COLORS['red']}
        it_let = QtWidgets.QTableWidgetItem(letter)
        it_let.setTextAlignment(Qt.AlignCenter)
        it_let.setForeground(QColor(grade_colors.get(letter, COLORS['text_mid'])))
        it_let.setFlags(it_let.flags() & ~Qt.ItemIsEditable)
        tbl.setItem(r, 6, it_let)
        self._grades_recalc_lock = False

    def _save_tea_grades(self):
        if msg_confirm(self, 'Lưu điểm', 'Xác nhận lưu điểm cho tất cả học viên trong bảng?'):
            msg_info(self, 'Thành công', 'Đã lưu điểm thành công!')

    def _fill_tea_profile(self):
        page = self.page_widgets[6]
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
        self.setFixedSize(1100, 700)
        self.setWindowIcon(QIcon(os.path.join(RES, 'logo.png')))

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
        lbl_sub.setGeometry(68, 40, 150, 16)
        lbl_sub.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 11px; background: transparent;')

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
        # mock data
        db = {
            'HV2024001': ('Đào Viết Quang Huy', 'quanghuy@sv.eaut.edu.vn', '0912345678'),
            'HV2024002': ('Trần Thị Bích', 'bich@sv.eaut.edu.vn', '0923456789'),
            'HV2024003': ('Lê Văn Cường', 'cuong@sv.eaut.edu.vn', '0934567890'),
        }
        msv = txt_msv.text().strip().upper()
        if msv not in db:
            msg_warn(self, 'Không tìm thấy', f'Không tìm thấy học viên với MSV: {msv}')
            return
        ten, email, sdt = db[msv]
        for attr, val in [('txtHoTen', ten), ('txtEmail', email), ('txtSDT', sdt)]:
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
        if not msg_confirm(self, 'Xác nhận', f'Đăng ký {hoten.text()} vào lớp {cbo_cls.currentText()}?'):
            return
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
            # trang thai
            st = row[5]
            item_st = QtWidgets.QTableWidgetItem(st)
            item_st.setTextAlignment(Qt.AlignCenter)
            color = COLORS['green'] if st == 'Đã thanh toán' else COLORS['orange'] if st == 'Chờ thanh toán' else COLORS['red']
            item_st.setForeground(QColor(color))
            tbl.setItem(r, 5, item_st)
            # action
            btn = QtWidgets.QPushButton('Chi tiết')
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(76, 26)
            btn.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }}')
            btn.clicked.connect(lambda ch, rdata=row: msg_info(
                self, 'Chi tiết đăng ký',
                f'Mã: {rdata[0]}\nNgày: {rdata[1]}\nHọc viên: {rdata[2]}\nLớp: {rdata[3]}\nHọc phí: {rdata[4]} đ\nTrạng thái: {rdata[5]}'))
            w = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(btn)
            tbl.setCellWidget(r, 6, w)
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([70, 95, 195, 90, 110, 125, 96]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 40)

        # search + filter + export
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchReg')
        if txt:
            txt.textChanged.connect(lambda t: table_filter(tbl, t, cols=[0, 2, 3]))
        for nm in ('cboRegStatus', 'cboRegDate'):
            cbo = page.findChild(QtWidgets.QComboBox, nm)
            if cbo:
                cbo.currentIndexChanged.connect(lambda idx, n=nm: self._emp_filter_reg(n))
        btn_exp = page.findChild(QtWidgets.QPushButton, 'btnExportReg')
        if btn_exp:
            btn_exp.clicked.connect(lambda: msg_info(self, 'Xuất báo cáo', 'Đã xuất danh sách đăng ký ra Excel'))

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
        gia = tbl.item(r, 3).text() if tbl.item(r, 3) else '?'
        if not msg_confirm(self, 'Xác nhận thu tiền', f'Thu {gia} đ từ {ten} ({ma}) - {method}?'):
            return
        tbl.removeRow(r)
        if note: note.clear()
        msg_info(self, 'Thành công', f'Đã xác nhận thanh toán {gia} đ cho {ten}')

    def _emp_print_receipt(self, tbl):
        rows = tbl.selectionModel().selectedRows() if tbl else []
        if not rows:
            msg_warn(self, 'Chưa chọn', 'Hãy chọn 1 dòng để in biên lai')
            return
        r = rows[0].row()
        ma = tbl.item(r, 0).text() if tbl.item(r, 0) else '?'
        msg_info(self, 'In biên lai', f'Đã in biên lai cho {ma}')

    def _fill_emp_classes(self):
        page = self.page_widgets[4]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblEmpClasses')
        if not tbl:
            return
        tbl.setRowCount(len(MOCK_CLASSES))
        for r, cls in enumerate(MOCK_CLASSES):
            ma, mmon, tmon, gv, lich, phong, smax, siso, gia = cls
            for c, val in enumerate([ma, tmon, gv, lich]):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c == 0 else Qt.AlignLeft | Qt.AlignVCenter)
                tbl.setItem(r, c, item)
            siso_item = QtWidgets.QTableWidgetItem(f'{siso}/{smax}')
            siso_item.setTextAlignment(Qt.AlignCenter)
            pct = int(siso / smax * 100)
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
        tbl.horizontalHeader().setStretchLastSection(True)
        for c, cw in enumerate([85, 155, 135, 145, 70, 110, 96]):
            tbl.setColumnWidth(c, cw)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(MOCK_CLASSES)):
            tbl.setRowHeight(r, 40)

        # search + filter
        txt = page.findChild(QtWidgets.QLineEdit, 'txtSearchEmpCls')
        if txt:
            txt.textChanged.connect(lambda t: table_filter(tbl, t, cols=[0, 1, 2]))
        cbo_c = page.findChild(QtWidgets.QComboBox, 'cboEmpClsCourse')
        if cbo_c:
            cbo_c.currentIndexChanged.connect(lambda: self._emp_filter_cls())
        cbo_s = page.findChild(QtWidgets.QComboBox, 'cboEmpClsStatus')
        if cbo_s:
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
        self.main_win = None
        self.login_win = None

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
