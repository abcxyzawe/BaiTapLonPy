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

# danh sach trang
PAGES = [
    ('btnHome', 'dashboard_student.ui'),
    ('btnRegister', 'register_course.ui'),
    ('btnSchedule', 'schedule.ui'),
    ('btnExam', 'exam_schedule.ui'),
    ('btnGrades', 'grades.ui'),
    ('btnTuition', 'tuition.ui'),
    ('btnNotice', 'notifications.ui'),
    ('btnProfile', 'profile.ui'),
]

MENU_ITEMS = [
    ('btnHome', 'iconHome', 'home', 'Trang chủ'),
    ('btnRegister', 'iconRegister', 'book-open', 'Đăng ký khóa học'),
    ('btnSchedule', 'iconSchedule', 'calendar', 'Lịch học'),
    ('btnExam', 'iconExam', 'clipboard', 'Lịch thi'),
    ('btnGrades', 'iconGrades', 'bar-chart', 'Xem điểm'),
    ('btnTuition', 'iconTuition', 'credit-card', 'Thanh toán học phí'),
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
            icon_lbl.setGeometry(24, y + 9, 18, 18)
            icon_lbl.setScaledContents(True)
            icon_lbl.setStyleSheet('background: transparent;')
            icon_path = os.path.join(ICONS, f'{icon_file}.png')
            if os.path.exists(icon_path):
                icon_lbl.setPixmap(QPixmap(icon_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
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
        self.lblStudentName.setGeometry(60, 626, 110, 17)
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
                self._fill_dashboard, self._fill_register, self._fill_schedule,
                self._fill_exam, self._fill_grades, self._fill_tuition,
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
            tbl.setColumnWidth(0, 70)
            tbl.setColumnWidth(1, 200)
            tbl.setColumnWidth(2, 55)
            tbl.setColumnWidth(3, 140)
            tbl.setColumnWidth(4, 130)
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

                btn = QtWidgets.QPushButton()
                btn.setMinimumHeight(32)
                if row[6] == 'full':
                    btn.setText('Hết chỗ')
                    btn.setEnabled(False)
                    btn.setStyleSheet(f'QPushButton {{ background: #edf2f7; color: #718096; border: none; border-radius: 6px; padding: 8px 24px; font-size: 13px; min-width: 100px; }}')
                else:
                    btn.setText('Đăng ký')
                    btn.setStyleSheet(f'QPushButton {{ background: {COLORS["navy"]}; color: white; border: none; border-radius: 6px; padding: 8px 24px; font-size: 13px; font-weight: bold; min-width: 100px; }} QPushButton:hover {{ background: {COLORS["navy_hover"]}; }}')
                    btn.setCursor(Qt.PointingHandCursor)
                tbl.setCellWidget(r, 6, btn)

            tbl.horizontalHeader().setStretchLastSection(False)
            for c, w in enumerate([60, 150, 30, 110, 110, 90, 140]):
                tbl.setColumnWidth(c, w)
            tbl.verticalHeader().setVisible(False)
            for r in range(len(data)):
                tbl.setRowHeight(r, 44)

    def _fill_schedule(self):
        page = self.page_widgets[2]

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
        page = self.page_widgets[3]
        tbl = page.findChild(QtWidgets.QTableWidget, 'tblExam')
        if not tbl:
            return
        data = [
            ['1', 'IT001', 'Lập trình ứng dụng với Python', '20/06/2026', 'Ca 1 (07:30-09:00)', 'P.A301', ''],
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
        tbl.verticalHeader().setVisible(False)

    def _fill_grades(self):
        page = self.page_widgets[4]
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
        for c, w in enumerate([70, 200, 40, 80, 80, 80]):
            tbl.setColumnWidth(c, w)
        tbl.verticalHeader().setVisible(False)
        for r in range(len(data)):
            tbl.setRowHeight(r, 40)

    def _fill_tuition(self):
        page = self.page_widgets[5]
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

    def _fill_notifications(self):
        page = self.page_widgets[6]
        # fix scroll - set minimum height cho scrollContent
        sc = page.findChild(QtWidgets.QWidget, 'scrollContent')
        if sc:
            sc.setMinimumHeight(760)

    def _fill_profile(self):
        page = self.page_widgets[7]
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
