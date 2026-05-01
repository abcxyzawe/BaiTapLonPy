"""run.py - EAUT app launcher
1 click bat docker (postgres) + spawn API server + launch PyQt5 frontend.

Kien truc client-server:
    PyQt5 (frontend) --HTTP--> FastAPI server (uvicorn :8000)
                                    |
                                    v psycopg2
                              PostgreSQL (container eaut_postgres)

Khi chay duoi dang script: `python run.py`
Khi build .exe: PyInstaller bundle file nay + toan bo project,
double-click 1 file -> Docker compose up -> spawn API -> launch UI.
"""
import os
import shutil
import subprocess
import sys
import tempfile
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
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'eaut_run.lock')

NO_WIN = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def _is_pid_alive(pid):
    """Check process voi PID co dang chay khong (Windows + Unix)."""
    if pid <= 0:
        return False
    try:
        if os.name == 'nt':
            # Windows: dung tasklist
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                capture_output=True, text=True, timeout=5,
                creationflags=NO_WIN
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def acquire_singleton_lock():
    """Bao dam chi 1 instance chay tai 1 thoi diem.
    Dung file lock voi PID + check live de xu ly stale lock."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                old_pid = int(f.read().strip() or '0')
            if _is_pid_alive(old_pid):
                return False  # instance khac dang chay
        except Exception:
            pass  # lock loi -> coi nhu stale
    # Khong co instance khac -> ghi lock
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
    return True


def release_singleton_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


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


# API server duoc chay trong THREAD (cung process voi PyQt5).
# Ly do: trong PyInstaller --onefile, sys.executable la run.exe (bootloader),
# nen subprocess([sys.executable, '-m', 'uvicorn', ...]) se spawn LAI run.exe
# -> infinite loop spam process. Threading tranh van de nay.
_api_thread = None
_api_server = None
API_LOG_FILE = os.path.join(tempfile.gettempdir(), 'eaut_api_error.log')


def _log_api_error(msg):
    """Ghi loi vao file de user share khi report bug (vi console=False)."""
    try:
        with open(API_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write('[' + time.strftime('%H:%M:%S') + '] ' + msg + '\n')
    except Exception:
        pass


def _run_api_inline():
    """Chay uvicorn server trong thread. Catch BAT KY exception nao + log."""
    import traceback
    try:
        import asyncio
        sys.path.insert(0, BASE)
        # Test import truoc khi config uvicorn de log loi cu the
        try:
            import uvicorn
        except Exception as e:
            _log_api_error('Import uvicorn fail: ' + repr(e) + '\n' + traceback.format_exc())
            return
        try:
            from backend.api.main import app
        except Exception as e:
            _log_api_error('Import backend.api.main fail: ' + repr(e) + '\n' + traceback.format_exc())
            return

        global _api_server
        try:
            # lifespan='off' tranh @asynccontextmanager startup hook block khi DB cham
            config = uvicorn.Config(app, host='127.0.0.1', port=8000,
                                     log_level='warning', access_log=False,
                                     lifespan='off')
            _api_server = uvicorn.Server(config)
        except Exception as e:
            _log_api_error('Create uvicorn config fail: ' + repr(e) + '\n' + traceback.format_exc())
            return

        # Tao asyncio loop moi cho thread (main thread co loop khac)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_api_server.serve())
        except Exception as e:
            _log_api_error('uvicorn.serve fail: ' + repr(e) + '\n' + traceback.format_exc())
        finally:
            try: loop.close()
            except Exception: pass
    except BaseException as e:
        # KeyboardInterrupt / SystemExit - bat tat ca
        _log_api_error('Outer exception: ' + repr(e) + '\n' + traceback.format_exc())


def start_api_server():
    """Spawn API server trong daemon thread."""
    global _api_thread
    import threading
    # Reset log file moi run
    try:
        if os.path.exists(API_LOG_FILE):
            os.remove(API_LOG_FILE)
    except Exception: pass
    try:
        _api_thread = threading.Thread(target=_run_api_inline, daemon=True,
                                        name='eaut-api-server')
        _api_thread.start()
    except Exception as e:
        show_error('Khong start duoc API server', str(e))
        return False
    return True


def wait_for_api(timeout=30):
    """Poll http://127.0.0.1:8000/health cho den khi API san sang."""
    import urllib.request
    import urllib.error
    import json
    for _ in range(timeout):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2) as r:
                data = json.loads(r.read())
                if data.get('api') == 'ok' and data.get('db') == 'connected':
                    return True
        except (urllib.error.URLError, ConnectionError, OSError, ValueError):
            pass
        # Kiem tra thread crash
        if _api_thread and not _api_thread.is_alive():
            err_log = ''
            try:
                if os.path.exists(API_LOG_FILE):
                    with open(API_LOG_FILE, encoding='utf-8') as f:
                        err_log = f.read()[:1500]
            except Exception: pass
            show_error(
                'API server bi crash',
                'Thread uvicorn da tat.\n\n'
                'Log file: ' + API_LOG_FILE + '\n\n'
                'Noi dung loi:\n' + (err_log if err_log else '(khong ghi duoc log)')
            )
            return False
        time.sleep(1)
    return False


def stop_api_server():
    """Yeu cau uvicorn server tat. Daemon thread se tu chet khi process exit."""
    global _api_server
    if _api_server is not None:
        try:
            _api_server.should_exit = True
        except Exception:
            pass


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
    """Add path + exec frontend/main.py.
    Verify cac asset can thiet bundle day du - bail som voi msg ro neu thieu."""
    sys.path.insert(0, BASE)
    sys.path.insert(0, os.path.join(BASE, 'frontend'))
    os.chdir(os.path.join(BASE, 'frontend'))

    main_path = os.path.join(BASE, 'frontend', 'main.py')
    login_ui_path = os.path.join(BASE, 'frontend', 'ui', 'login.ui')

    # Pre-flight check - file thieu nghia la build .exe loi
    missing = [p for p in (main_path, login_ui_path) if not os.path.exists(p)]
    if missing:
        if splash:
            splash.close()
        show_error(
            'Build run.exe loi - thieu file',
            'Cac file sau khong co trong bundle:\n\n' +
            '\n'.join(missing) +
            '\n\nGiai phap: chay lai `build_exe.bat` de rebuild run.exe '
            'voi day du file (ban dist/run.exe hien tai la cu hoac build sai).'
        )
        return

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
    import atexit

    # 1. Singleton check - tranh user double-click nhieu lan -> spawn nhieu instance
    if not acquire_singleton_lock():
        # Co instance khac dang chay -> show msg roi exit (KHONG sys.exit(1) tranh OS auto-restart)
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.information(
                None, 'EAUT da chay',
                'EAUT app dang chay roi.\nKiem tra taskbar hoac thu lai sau vai giay.'
            )
        except Exception:
            sys.stderr.write('[EAUT] Co instance khac dang chay\n')
        return  # khong sys.exit(1)

    atexit.register(release_singleton_lock)
    atexit.register(stop_api_server)

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
                       'PostgreSQL khong san sang sau 60 giay.')
            return
        update_splash(splash, qapp, 'Khoi dong REST API server...')
        if not start_api_server():
            return
        if not wait_for_api():
            show_error('API server khong phan hoi',
                       'FastAPI server khong san sang sau 30 giay.')
            return
        update_splash(splash, qapp, 'Mo giao dien dang nhap...')
        time.sleep(0.3)
        launch_frontend(qapp, splash)
    except KeyboardInterrupt:
        stop_api_server()
        release_singleton_lock()
        sys.exit(0)
    except Exception as e:
        stop_api_server()
        release_singleton_lock()
        show_error('Loi khoi dong', type(e).__name__ + ': ' + str(e))


if __name__ == '__main__':
    main()
