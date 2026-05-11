import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # khong co dotenv cung chay duoc, fallback sang default


class Database:
    """singleton quan ly ket noi postgres.
    dung .cursor() context manager de auto commit/rollback.
    """
    _instance = None
    import threading
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._conn = None
            cls._instance._connected = False
            cls._instance.lock = cls._lock
        return cls._instance

    def connect(self):
        """tao hoac tra ve connection hien tai. raise Exception neu loi."""
        if self._conn is not None and not self._conn.closed:
            return self._conn

        self._conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', '5432')),
            dbname=os.getenv('POSTGRES_DB', 'eaut_db'),
            user=os.getenv('POSTGRES_USER', 'eaut_admin'),
            password=os.getenv('POSTGRES_PASSWORD', 'eaut_password'),
            connect_timeout=5,
        )
        self._connected = True
        return self._conn

    def is_connected(self) -> bool:
        """kiem tra xem co connect duoc khong (cho graceful fallback)"""
        try:
            conn = self.connect()
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
                cur.fetchone()
            return True
        except Exception as e:
            print(f"[DB ERROR] Loi ket noi that su la: {e}")
            self._connected = False
            return False

    @contextmanager
    def cursor(self, dict_cursor=True):
        """context manager voi auto-commit / rollback + auto-retry 1 lan..."""
        with self.lock:
            cur_factory = psycopg2.extras.RealDictCursor if dict_cursor else None

            # Step 1: get a usable cursor (retry 1 lan neu conn dead)
            try:
                conn = self.connect()
                cur = conn.cursor(cursor_factory=cur_factory)
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                # Conn da chet -> reset va connect lai 1 lan
                print(f'[DB] conn dead, retry 1x: {str(e)[:100]}')
                self._conn = None
                self._connected = False
                conn = self.connect()
                cur = conn.cursor(cursor_factory=cur_factory)

            # Step 2: chay user code, commit/rollback nhu cu
            try:
                yield cur
                conn.commit()
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                # Conn chet giua chung -> rollback se fail, chap nhan + reset conn
                try: conn.rollback()
                except Exception: pass
                self._conn = None
                self._connected = False
                print(f'[DB] conn lost mid-query, will reconnect next call: {str(e)[:100]}')
                raise
            except Exception:
                conn.rollback()
                raise
            finally:
                try: cur.close()
                except Exception: pass

    def fetch_all(self, sql: str, params=None):
        with self.cursor() as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def fetch_one(self, sql: str, params=None):
        with self.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def execute(self, sql: str, params=None):
        """dung cho INSERT/UPDATE/DELETE khong can return"""
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def execute_returning(self, sql: str, params=None):
        """dung cho INSERT ... RETURNING"""
        with self.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
        self._conn = None
        self._connected = False


# singleton global
db = Database()
