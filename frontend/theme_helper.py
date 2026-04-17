import os
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RES_DIR = os.path.join(BASE_DIR, 'resources')
ICON_DIR = os.path.join(RES_DIR, 'icons')
STYLE_DIR = os.path.join(BASE_DIR, 'styles')

# mau EAUT
COLORS = {
    'navy': '#002060',
    'navy_hover': '#1a3a6c',
    'gold': '#b8860b',
    'green': '#276749',
    'orange': '#c05621',
    'red': '#c53030',
    'text_dark': '#1a1a2e',
    'text_mid': '#4a5568',
    'text_light': '#718096',
    'border': '#d2d6dc',
    'bg': '#edf2f7',
    'bg_card': '#ffffff',
    'bg_alt': '#f7fafc',
    'active_bg': 'rgba(0,32,96,0.08)',
}

# sidebar active style
SIDEBAR_ACTIVE = (
    'QPushButton { background: rgba(0,32,96,0.08); color: #002060; '
    'border: none; border-radius: 8px; text-align: left; '
    'padding-left: 38px; font-size: 12px; font-weight: bold; }'
)

SIDEBAR_NORMAL = (
    'QPushButton { background: transparent; color: #4a5568; '
    'border: none; border-radius: 8px; text-align: left; '
    'padding-left: 38px; font-size: 12px; } '
    'QPushButton:hover { background: #edf2f7; }'
)


def load_theme(app):
    """doc file qss va apply"""
    qss_path = os.path.join(STYLE_DIR, 'eaut_theme.qss')
    if os.path.exists(qss_path):
        with open(qss_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())


def setup_sidebar_icons(win):
    """gan icon feather cho sidebar"""
    icon_map = {
        'iconHome': 'home',
        'iconRegister': 'book-open',
        'iconSchedule': 'calendar',
        'iconExam': 'clipboard',
        'iconGrades': 'bar-chart',
        'iconTuition': 'credit-card',
        'iconNotice': 'bell',
        'iconProfile': 'user',
        'iconLogout': 'log-out',
    }
    for attr, icon_name in icon_map.items():
        widget = getattr(win, attr, None)
        if widget:
            path = os.path.join(ICON_DIR, f'{icon_name}.png')
            if os.path.exists(path):
                widget.setPixmap(
                    QPixmap(path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )

    # logo
    logo_widget = getattr(win, 'lblSidebarLogo', None)
    if logo_widget:
        logo_path = os.path.join(RES_DIR, 'logo.png')
        if os.path.exists(logo_path):
            logo_widget.setPixmap(
                QPixmap(logo_path).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    # window icon
    logo_path = os.path.join(RES_DIR, 'logo.png')
    if os.path.exists(logo_path):
        win.setWindowIcon(QIcon(logo_path))


def setup_stat_icons(win):
    """gan icon cho stat cards (dashboard)"""
    stat_map = {
        'iconStat1Img': 'layers',
        'iconStat2Img': 'check-circle',
        'iconStat3Img': 'clock',
    }
    for attr, icon_name in stat_map.items():
        widget = getattr(win, attr, None)
        if widget:
            path = os.path.join(ICON_DIR, f'{icon_name}.png')
            if os.path.exists(path):
                widget.setPixmap(
                    QPixmap(path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )


def apply_eaut_overrides(win, active_btn_name=None):
    """override mau cho cac widget cu the"""
    # sidebar label colors
    for attr, style in [
        ('lblSidebarSchool', f'color: {COLORS["navy"]}; font-size: 13px; font-weight: bold; background: transparent;'),
        ('lblSidebarSub', f'color: {COLORS["text_mid"]}; font-size: 11px; background: transparent;'),
        ('lblStudentName', f'color: {COLORS["text_dark"]}; font-size: 12px; font-weight: bold; background: transparent;'),
        ('lblStudentId', f'color: {COLORS["text_mid"]}; font-size: 10px; background: transparent;'),
        ('lblAvatar', f'background: {COLORS["active_bg"]}; border-radius: 19px; color: {COLORS["navy"]}; font-size: 13px; font-weight: bold;'),
        ('lblPageTitle', f'color: {COLORS["text_dark"]}; font-size: 17px; font-weight: bold; background: transparent;'),
    ]:
        widget = getattr(win, attr, None)
        if widget:
            widget.setStyleSheet(style)

    # sidebar buttons
    btn_names = ['btnHome', 'btnRegister', 'btnSchedule', 'btnExam',
                 'btnGrades', 'btnTuition', 'btnNotice', 'btnProfile']
    for name in btn_names:
        btn = getattr(win, name, None)
        if btn:
            if name == active_btn_name:
                btn.setStyleSheet(SIDEBAR_ACTIVE)
            else:
                btn.setStyleSheet(SIDEBAR_NORMAL)

    # raise icon cua active button
    if active_btn_name:
        icon_name = active_btn_name.replace('btn', 'icon')
        icon_widget = getattr(win, icon_name, None)
        if icon_widget:
            icon_widget.raise_()

    # stat card icon backgrounds
    for attr, color in [('iconStat1', COLORS['navy']), ('iconStat2', COLORS['green']), ('iconStat3', COLORS['gold'])]:
        widget = getattr(win, attr, None)
        if widget:
            widget.setStyleSheet(f'background: rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.08); border-radius: 10px;')

    # stat number colors
    for attr, color in [('lblStatCourses', COLORS['navy']), ('lblStatCredits', COLORS['green']), ('lblStatRemaining', COLORS['gold'])]:
        widget = getattr(win, attr, None)
        if widget:
            widget.setStyleSheet(f'color: {color}; font-size: 24px; font-weight: bold; background: transparent;')

    for attr in ['lblStatCoursesLabel', 'lblStatCreditsLabel', 'lblStatRemainingLabel']:
        widget = getattr(win, attr, None)
        if widget:
            widget.setStyleSheet(f'color: {COLORS["text_mid"]}; font-size: 12px; background: transparent;')
