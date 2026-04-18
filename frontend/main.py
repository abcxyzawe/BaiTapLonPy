import sys, os
from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QPixmap, QIcon, QColor, QFont
from PyQt5.QtCore import Qt, QDate
from theme_helper import (load_theme, setup_sidebar_icons, setup_stat_icons,
                          apply_eaut_overrides, COLORS, SIDEBAR_ACTIVE, SIDEBAR_NORMAL)

BASE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(BASE, 'ui')
RES = os.path.join(BASE, 'resources')
ICONS = os.path.join(RES, 'icons')

# mock data
MOCK_USER = {
    'username': 'user', 'password': 'passuser', 'role': 'Sinh viên',
    'name': 'Đào Viết Quang Huy', 'msv': '2024001', 'lop': 'CNTT-K20A',
    'khoa': 'Công nghệ thông tin', 'ngaysinh': '15/03/2004', 'gioitinh': 'Nam',
    'nienkhoa': '2024 - 2028', 'hedt': 'Chính quy',
    'email': 'quanghuy@sv.eaut.edu.vn', 'sdt': '0912345678',
    'diachi': 'Đà Nẵng', 'initials': 'QH',
}

MOCK_ADMIN = {
    'username': 'admin', 'password': 'passadmin',
    'name': 'Admin', 'role': 'Quản trị viên', 'initials': 'AD',
}

# admin pages
ADMIN_PAGES = [
    ('btnAdminDash', 'admin_dashboard.ui'),
    ('btnAdminCourse', 'admin_courses.ui'),
    ('btnAdminStudent', 'admin_students.ui'),
    ('btnAdminSemester', 'admin_semester.ui'),
    ('btnAdminCurriculum', 'admin_curriculum.ui'),
    ('btnAdminAudit', 'admin_audit.ui'),
    ('btnAdminStats', 'admin_stats.ui'),
]

ADMIN_MENU = [
    ('btnAdminDash', 'iconAdminDash', 'grid', 'Tổng quan'),
    ('btnAdminCourse', 'iconAdminCourse', 'database', 'Quản lý khóa học'),
    ('btnAdminStudent', 'iconAdminStudent', 'users', 'Quản lý sinh viên'),
    ('btnAdminSemester', 'iconAdminSemester', 'sliders', 'Quản lý học kỳ'),
    ('btnAdminCurriculum', 'iconAdminCurriculum', 'file-text', 'Khung chương trình'),
    ('btnAdminAudit', 'iconAdminAudit', 'shield', 'Nhật ký hệ thống'),
    ('btnAdminStats', 'iconAdminStats', 'pie-chart', 'Thống kê'),
]

# danh sach trang
PAGES = [
    ('btnHome', 'dashboard_student.ui'),
    ('btnRegister', 'register_course.ui'),
    ('btnCart', 'cart_preview.ui'),
    ('btnSchedule', 'schedule.ui'),
    ('btnExam', 'exam_schedule.ui'),
    ('btnGrades', 'grades.ui'),
    ('btnTuition', 'tuition.ui'),
    ('btnReview', 'teacher_review.ui'),
    ('btnNotice', 'notifications.ui'),
    ('btnProfile', 'profile.ui'),
]

MENU_ITEMS = [
    ('btnHome', 'iconHome', 'home', 'Trang chủ'),
    ('btnRegister', 'iconRegister', 'book-open', 'Đăng ký khóa học'),
    ('btnCart', 'iconCart', 'shopping-cart', 'Giỏ hàng đăng ký'),
    ('btnSchedule', 'iconSchedule', 'calendar', 'Lịch học'),
    ('btnExam', 'iconExam', 'clipboard', 'Lịch thi'),
    ('btnGrades', 'iconGrades', 'bar-chart', 'Xem điểm'),
    ('btnTuition', 'iconTuition', 'credit-card', 'Thanh toán học phí'),
    ('btnReview', 'iconReview', 'star', 'Đánh giá giảng viên'),
    ('btnNotice', 'iconNotice', 'bell', 'Thông báo'),
    ('btnProfile', 'iconProfile', 'user', 'Thông tin cá nhân'),
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
                self._fill_dashboard, self._fill_register, self._fill_cart,
                self._fill_schedule, self._fill_exam, self._fill_grades,
                self._fill_tuition, self._fill_review,
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

    def _fill_register(self):
        page = self.page_widgets[1]

        # search icon
        si = page.findChild(QtWidgets.QLabel, 'iconSearch')
        if si:
            si.setPixmap(QPixmap(os.path.join(ICONS, 'search.png')).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        data = [
            ['IT004', 'Trí tuệ nhân tạo', '3', 'Nguyễn Văn G', 'T3 (7:00-9:30)', '12/40', 'ok'],
            ['IT005', 'Phát triển web', '3', 'Trần Thị H', 'T5 (13:00-15:30)', '8/35', 'ok'],
            ['IT006', 'An toàn thông tin', '3', 'Lê Văn K', 'T2 (7:00-9:30)', '40/40', 'full'],
            ['MA002', 'Xác suất thống kê', '3', 'Phạm Thị L', 'T4 (9:30-12:00)', '20/40', 'ok'],
            ['IT007', 'Kiểm thử phần mềm', '2', 'Hoàng Văn M', 'T6 (7:00-9:00)', '5/30', 'ok'],
            ['EN002', 'TA chuyên ngành', '2', 'Vũ Thị N', 'T3 (13:00-15:00)', '15/35', 'ok'],
            ['IT008', 'Lập trình di động', '3', 'Đỗ Văn P', 'T4 (13:00-15:30)', '32/40', 'ok'],
            ['MA003', 'Giải tích 2', '3', 'Trần Thị Q', 'T2 (9:30-12:00)', '18/40', 'ok'],
        ]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCourses')
        if tbl:
            tbl.setRowCount(len(data))
            for r, row in enumerate(data):
                for c in range(6):
                    item = QtWidgets.QTableWidgetItem(row[c])
                    if c == 5:
                        item.setForeground(QColor(COLORS['red'] if row[6] == 'full' else COLORS['green']))
                    tbl.setItem(r, c, item)

                if row[6] == 'full':
                    btn_act = QtWidgets.QPushButton('Đăng ký chờ')
                    btn_act.setCursor(Qt.PointingHandCursor)
                    btn_act.setFixedSize(118, 31)
                    btn_act.setStyleSheet(f'QPushButton {{ background: white; color: {COLORS["orange"]}; border: 1px solid {COLORS["orange"]}; border-radius: 6px; font-size: 12px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["orange"]}; color: white; }}')
                else:
                    btn_act = QtWidgets.QPushButton('Đăng ký')
                    btn_act.setCursor(Qt.PointingHandCursor)
                    btn_act.setFixedSize(100, 31)
                    btn_act.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 6px; font-size: 12px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
                w = QtWidgets.QWidget()
                hl = QtWidgets.QHBoxLayout(w)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setAlignment(Qt.AlignCenter)
                hl.addWidget(btn_act)
                tbl.setCellWidget(r, 6, w)

            tbl.horizontalHeader().setStretchLastSection(False)
            for c, cw in enumerate([65, 140, 28, 105, 105, 80, 157]):
                tbl.setColumnWidth(c, cw)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 48)

    def _fill_cart(self):
        page = self.page_widgets[2]
        cart_data = [
            ['IT004', 'Trí tuệ nhân tạo', '3', 'Nguyễn Văn G', 'T3 (7:00-9:30)', '1,800,000'],
            ['IT005', 'Phát triển web', '3', 'Trần Thị H', 'T5 (13:00-15:30)', '1,800,000'],
            ['MA002', 'Xác suất thống kê', '3', 'Phạm Thị L', 'T4 (9:30-12:00)', '1,800,000'],
            ['IT007', 'Kiểm thử phần mềm', '2', 'Hoàng Văn M', 'T6 (7:00-9:00)', '1,200,000'],
        ]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblCart')
        if tbl:
            tbl.setRowCount(len(cart_data))
            for r, row in enumerate(cart_data):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    if c == 5:
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    tbl.setItem(r, c, item)
                btn_del = QtWidgets.QPushButton('Xóa')
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setFixedSize(62, 24)
                btn_del.setStyleSheet(f'QPushButton {{ background: white; color: {COLORS["red"]}; border: 1px solid {COLORS["red"]}; border-radius: 5px; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ background: {COLORS["red"]}; color: white; }}')
                w_act = QtWidgets.QWidget()
                hl_act = QtWidgets.QHBoxLayout(w_act)
                hl_act.setContentsMargins(0, 0, 0, 0)
                hl_act.setAlignment(Qt.AlignCenter)
                hl_act.addWidget(btn_del)
                tbl.setCellWidget(r, 6, w_act)
            for c, cw in enumerate([65, 150, 28, 115, 110, 95, 100]):
                tbl.setColumnWidth(c, cw)
            tbl.horizontalHeader().setStretchLastSection(False)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(cart_data)):
                tbl.setRowHeight(r, 50)

        # summary
        total_tc = sum(int(r[2]) for r in cart_data)
        total_fee = sum(int(r[5].replace(',', '')) for r in cart_data)
        for attr, val in [('lblCartCount', str(len(cart_data))),
                          ('lblCartCredits', str(total_tc)),
                          ('lblCartFee', f'{total_fee:,} đ'.replace(',', '.'))]:
            w = page.findChild(QtWidgets.QLabel, attr)
            if w:
                w.setText(val)

        # preview schedule
        tbl2 = page.findChild(QtWidgets.QTableWidget, 'tblPreview')
        if tbl2:
            hours = ['7:00-9:30', '9:30-12:00', '13:00-15:30', '15:40-18:10', '18:30-20:00', '20:00-21:30']
            tbl2.setRowCount(len(hours))
            tbl2.setColumnWidth(0, 90)
            for i in range(1, 7):
                tbl2.setColumnWidth(i, 112)
            for r, h in enumerate(hours):
                item = QtWidgets.QTableWidgetItem(h)
                item.setForeground(QColor('#718096'))
                item.setFont(QFont('Segoe UI', 9))
                tbl2.setItem(r, 0, item)
                tbl2.setRowHeight(r, 28)
            # dat mon vao lich
            preview = [
                (0, 3, 'Trí tuệ NH', COLORS['gold']),
                (1, 4, 'Xác suất TK', COLORS['green']),
                (2, 5, 'Phát triển web', COLORS['navy']),
                (0, 6, 'Kiểm thử PM', COLORS['orange']),
            ]
            for row, col, name, color in preview:
                item = QtWidgets.QTableWidgetItem(name)
                item.setForeground(QColor(color))
                item.setFont(QFont('Segoe UI', 9, QFont.Bold))
                item.setTextAlignment(Qt.AlignCenter)
                tbl2.setItem(row, col, item)
            tbl2.verticalHeader().setVisible(False)

    def _fill_schedule(self):
        page = self.page_widgets[3]

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
        page = self.page_widgets[4]
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

    def _fill_grades(self):
        page = self.page_widgets[5]
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

    def _fill_tuition(self):
        page = self.page_widgets[6]
        detail = [
            ['Học phí tín chỉ (15 TC x 600,000)', '9,000,000', '9,000,000', '0'],
            ['Bảo hiểm y tế', '563,000', '563,000', '0'],
            ['Phí ký túc xá', '3,600,000', '3,600,000', '0'],
            ['Phí hoạt động ngoại khóa', '337,000', '337,000', '0'],
            ['Học phí bổ sung (3 TC)', '1,800,000', '0', '1,800,000'],
            ['Lệ phí thi lại', '2,700,000', '0', '2,700,000'],
        ]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblDetail')
        if tbl:
            tbl.setRowCount(len(detail))
            for r, row in enumerate(detail):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter if c > 0 else Qt.AlignLeft | Qt.AlignVCenter)
                    if c == 3 and val != '0':
                        item.setForeground(QColor(COLORS['red']))
                    elif c == 2 and val != '0':
                        item.setForeground(QColor(COLORS['green']))
                    tbl.setItem(r, c, item)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setColumnWidth(0, 320)
            tbl.setColumnWidth(1, 140)
            tbl.setColumnWidth(2, 140)
            tbl.verticalHeader().setVisible(False)

        # QR payment - them vao payFrame (giu nguyen kich thuoc goc)
        pf = page.findChild(QtWidgets.QFrame, 'payFrame')
        if pf:
            btn_qr = QtWidgets.QPushButton('Quét mã QR', pf)
            btn_qr.setGeometry(15, 56, 180, 24)
            btn_qr.setCursor(Qt.PointingHandCursor)
            btn_qr.setStyleSheet(f'QPushButton {{ background: transparent; color: {COLORS["navy"]}; border: 1px solid {COLORS["navy"]}; border-radius: 4px; font-size: 11px; }} QPushButton:hover {{ background: {COLORS["navy"]}; color: white; }}')

        history = [
            ['15/01/2026', 'Đợt 1 - HK2 2025-2026', '9,000,000', 'Chuyển khoản NH'],
            ['15/01/2026', 'BHYT + Ngoại khóa', '900,000', 'Chuyển khoản NH'],
            ['20/08/2025', 'Đợt 1 - HK1 2025-2026', '9,000,000', 'Chuyển khoản NH'],
            ['01/09/2025', 'Ký túc xá HK1', '3,600,000', 'Tiền mặt'],
        ]
        tbl2 = page.findChild(QtWidgets.QTableWidget, 'tblHistory')
        if tbl2:
            tbl2.setRowCount(len(history))
            for r, row in enumerate(history):
                for c, val in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter if c != 1 else Qt.AlignLeft | Qt.AlignVCenter)
                    tbl2.setItem(r, c, item)
            tbl2.horizontalHeader().setStretchLastSection(True)
            tbl2.setColumnWidth(0, 120)
            tbl2.setColumnWidth(1, 300)
            tbl2.setColumnWidth(2, 140)
            tbl2.verticalHeader().setVisible(False)

    def _fill_review(self):
        page = self.page_widgets[7]
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

    def _fill_notifications(self):
        page = self.page_widgets[8]
        # fix scroll - set minimum height cho scrollContent
        sc = page.findChild(QtWidgets.QWidget, 'scrollContent')
        if sc:
            sc.setMinimumHeight(760)

    def _fill_profile(self):
        page = self.page_widgets[9]
        u = MOCK_USER
        for attr, val in [('lblProfileName', u['name']), ('lblProfileRole', f"Sinh viên - Khoa {u['khoa']}"),
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
                    self._fill_admin_students, self._fill_admin_semester,
                    self._fill_admin_curriculum, self._fill_admin_audit,
                    self._fill_admin_stats]
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
                item_ss.setFont(QFont('Segoe UI', 11, QFont.Bold))
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
            tbl.horizontalHeader().setStretchLastSection(False)
            for c, cw in enumerate([70, 180, 30, 140, 130, 110, 150]):
                tbl.setColumnWidth(c, cw)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)

    def _fill_admin_students(self):
        page = self.page_widgets[2]
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
            tbl.horizontalHeader().setStretchLastSection(False)
            for c, cw in enumerate([75, 140, 100, 95, 90, 100, 150]):
                tbl.setColumnWidth(c, cw)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)

    def _fill_admin_semester(self):
        page = self.page_widgets[3]
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
                item_st.setFont(QFont('Segoe UI', 11, QFont.Bold))
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
            tbl.horizontalHeader().setStretchLastSection(False)
            for c, cw in enumerate([95, 90, 95, 105, 105, 95, 130]):
                tbl.setColumnWidth(c, cw)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)

    def _fill_admin_curriculum(self):
        page = self.page_widgets[4]
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
                        item.setFont(QFont('Segoe UI', 10, QFont.Bold))
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
            tbl.horizontalHeader().setStretchLastSection(False)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)

    def _fill_admin_audit(self):
        page = self.page_widgets[5]
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
                        item.setFont(QFont('Segoe UI', 10, QFont.Bold))
                    elif c == 5:
                        item.setForeground(QColor(COLORS['text_light']))
                    tbl.setItem(r, c, item)
            for c, cw in enumerate([135, 90, 50, 95, 260, 120]):
                tbl.setColumnWidth(c, cw)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 36)

    def _fill_admin_stats(self):
        page = self.page_widgets[6]
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
