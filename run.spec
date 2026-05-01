# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec - bundle EAUT app vao 1 file run.exe.

Build: pyinstaller --clean --noconfirm run.spec
Output: dist/run.exe (~50-80 MB voi PyQt5)

Required packages tren may build:
    pip install pyinstaller PyQt5 psycopg2-binary python-dotenv

User chay run.exe yeu cau:
    - Docker Desktop installed + running
"""
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Bundle toan bo cay project (truoc UI/icons/SQL)
DATAS = [
    # frontend - .py source files de exec (main.py + theme_helper.py)
    ('frontend/main.py', 'frontend'),
    ('frontend/theme_helper.py', 'frontend'),
    # frontend - tat ca .ui, qss, images, icons
    ('frontend/ui', 'frontend/ui'),
    ('frontend/styles', 'frontend/styles'),
    ('frontend/resources', 'frontend/resources'),
    # backend - source code (de exec sau khi extract) + database SQL
    ('backend', 'backend'),
    # docker compose
    ('docker-compose.yml', '.'),
]

# Hidden imports - PyInstaller doi khi bo sot
HIDDEN = [
    'psycopg2',
    'psycopg2.extras',
    'psycopg2.extensions',
    'python-dotenv',
    'dotenv',
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.uic',
]
# Backend services - PyInstaller co the bo sot do dynamic import
HIDDEN += [
    'backend.database.db',
    'backend.services.auth_service',
    'backend.services.course_service',
    'backend.services.registration_service',
    'backend.services.grade_service',
    'backend.services.notification_service',
    'backend.services.user_service',
    'backend.services.stats_service',
    'backend.services.semester_service',
    'backend.services.curriculum_service',
    'backend.services.schedule_service',
    'backend.services.exam_service',
    'backend.services.attendance_service',
    'backend.services.audit_service',
]
# Frontend module
HIDDEN += ['theme_helper']


a = Analysis(
    ['run.py'],
    pathex=['.', 'frontend'],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy'],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='run',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # False = khong hien CMD window khi click
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='frontend/resources/icons/home.png' if os.path.exists('frontend/resources/icons/home.png') else None,
)
