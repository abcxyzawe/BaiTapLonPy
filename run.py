"""run.py - EAUT app launcher
1 click bat docker (postgres) + launch PyQt5 frontend.

Khi chay duoi dang script: cd vao folder roi `python run.py`
Khi build .exe: PyInstaller bundle file nay + toan bo project, doi gianh
file mot click duy nhat -> Docker compose up -> wait DB -> launch UI.
"""
import os
import shutil
import subprocess
import sys
import time


def get_base_dir():
    """PyInstaller bundle: sys._MEIPASS la temp dir extract.
    Script binh thuong: dirname cua file nay."""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


BASE = get_base_dir()
COMPOSE_FILE = os.path.join(BASE, 'docker-compose.yml')
CONTAINER_NAME = 'eaut_postgres'
DB_USER = 'eaut_admin'
DB_NAME = 'eaut_db'

NO_WIN = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def show_error(title, msg):
    """Try Qt popup, fallback console + sys.exit(1)."""
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, title, msg)
    except Exception:
        sys.stderr.write('[ERROR] ' + title + '\n' + msg + '\n')
    sys.exit(1)


def show_splash(text='Dang khoi dong he thong EAUT...'):
    """Splash screen toi gian de user biet app dang load."""
    try:
        from PyQt5.QtWidgets import QApplication, QSplashScreen
        from PyQt5.QtGui import QPixmap, QFont, QColor
        from PyQt5.QtCore import Qt

        qapp = QApplication.instance() or QApplication(sys.argv)
        pix = QPixmap(420, 180)
        pix.fill(QColor('#002060'))
        splash = QSplashScreen(pix, Qt.WindowStaysOnTopHint)
        splash.setFont(QFont('Segoe UI', 11, QFont.Bold))
        splash.showMessage(
            'EAUT - He thong Dang ky khoa hoc\n\n' + text,
            Qt.AlignCenter, QColor('white')
        )
        splash.show()
        qapp.processEvents()
        return qapp, splash
    except Exception:
        return None, None


def update_splash(splash, qapp, text):
    if not splash:
        sys.stdout.write('[RUN] ' + text + '\n')
        sys.stdout.flush()
        return
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor
    splash.showMessage(
        'EAUT - He thong Dang ky khoa hoc\n\n' + text,
        Qt.AlignCenter, QColor('white')
    )
    if qapp:
        qapp.processEvents()


def check_docker():
    """Kiem tra docker CLI + daemon."""
    if not shutil.which('docker'):
        show_error(
            'Thieu Docker',
            'Docker chua duoc cai dat tren may.\n\n'
            'Vui long cai Docker Desktop:\n'
            'https://www.docker.com/products/docker-desktop\n\n'
            'Sau khi cai xong, mo Docker Desktop va doi no san sang roi chay lai.'
        )
        return False
    try:
        result = subprocess.run(
            ['docker', 'info'], capture_output=True, text=True, timeout=10,
            creationflags=NO_WIN
        )
        if result.returncode != 0:
            show_error(
                'Docker chua chay',
                'Docker daemon chua hoat dong.\n\n'
                'Vui long mo Docker Desktop va doi vai chuc giay cho no khoi dong xong, '
                'roi chay lai run.exe.'
            )
            return False
    except subprocess.TimeoutExpired:
        show_error('Docker khong phan hoi', 'Lenh `docker info` qua thoi gian (10s).')
        return False
    return True


def container_already_running():
    """Tra ve True neu container eaut_postgres da chay."""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=' + CONTAINER_NAME, '--filter', 'status=running',
             '--format', '{{.Names}}'],
            capture_output=True, text=True, timeout=5,
            creationflags=NO_WIN
        )
        return CONTAINER_NAME in result.stdout
    except Exception:
        return False


def start_postgres():
    """docker compose up -d postgres."""
    if not os.path.exists(COMPOSE_FILE):
        show_error('Thieu docker-compose.yml',
                   'Khong tim thay file:\n' + COMPOSE_FILE +
                   '\n\nFile nay phai di kem run.exe.')
        return False
    try:
        result = subprocess.run(
            ['docker', 'compose', '-f', COMPOSE_FILE, 'up', '-d', 'postgres'],
            capture_output=True, text=True, cwd=BASE, timeout=120,
            creationflags=NO_WIN
        )
        if result.returncode != 0:
            show_error('Docker compose loi',
                       'Khong start duoc container postgres:\n\n' +
                       (result.stderr or result.stdout))
            return False
    except subprocess.TimeoutExpired:
        show_error('Docker compose treo', 'Lenh `docker compose up` qua 2 phut.')
        return False
    return True


def wait_for_db(timeout=60):
    """Poll pg_isready trong container."""
    for i in range(timeout):
        try:
            result = subprocess.run(
                ['docker', 'exec', CONTAINER_NAME, 'pg_isready', '-U', DB_USER, '-d', DB_NAME],
                capture_output=True, timeout=5, creationflags=NO_WIN
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def launch_frontend(qapp, splash):
    """Add path + exec frontend/main.py."""
    sys.path.insert(0, BASE)
    sys.path.insert(0, os.path.join(BASE, 'frontend'))
    os.chdir(os.path.join(BASE, 'frontend'))

    main_path = os.path.join(BASE, 'frontend', 'main.py')
    with open(main_path, encoding='utf-8') as f:
        code = f.read()

    namespace = {
        '__name__': '__main__',
        '__file__': main_path,
    }
    if splash:
        splash.close()
    exec(compile(code, main_path, 'exec'), namespace)


def main():
    qapp, splash = show_splash('Kiem tra Docker...')
    try:
        if not check_docker():
            return
        update_splash(splash, qapp, 'Khoi dong PostgreSQL container...')
        if not container_already_running():
            if not start_postgres():
                return
        update_splash(splash, qapp, 'Doi database san sang...')
        if not wait_for_db():
            show_error('Database khong phan hoi',
                       'PostgreSQL khong san sang sau 60 giay.\n'
                       'Hay kiem tra Docker Desktop.')
            return
        update_splash(splash, qapp, 'Mo giao dien dang nhap...')
        time.sleep(0.3)
        launch_frontend(qapp, splash)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        show_error('Loi khoi dong', type(e).__name__ + ': ' + str(e))


if __name__ == '__main__':
    main()
