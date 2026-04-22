from backend.database.db import db
from backend.models.user import Student, Teacher, Employee, Admin
from backend.utils.hash_util import verify_password


class AuthService:
    """service xac thuc, tra ve User object sau khi login"""

    @staticmethod
    def login(username: str, password: str):
        """tra ve User object neu login OK, None neu sai"""
        user_row = db.fetch_one(
            "SELECT * FROM users WHERE username = %s AND is_active = TRUE",
            (username,)
        )
        if not user_row:
            return None

        if not verify_password(password, user_row['password']):
            return None

        return AuthService._build_user(user_row)

    @staticmethod
    def _build_user(user_row):
        """dua theo role ma tao instance con phu hop (factory)"""
        role = user_row['role']
        uid = user_row['id']
        common = dict(
            id=uid,
            username=user_row['username'],
            full_name=user_row['full_name'],
            email=user_row.get('email'),
            sdt=user_row.get('sdt'),
            is_active=user_row.get('is_active', True),
        )

        if role == 'student':
            d = db.fetch_one("SELECT * FROM students WHERE user_id = %s", (uid,))
            if not d:
                return None
            return Student(
                msv=d['msv'],
                ngaysinh=d.get('ngaysinh'),
                gioitinh=d.get('gioitinh'),
                diachi=d.get('diachi'),
                **common,
            )

        if role == 'teacher':
            d = db.fetch_one("SELECT * FROM teachers WHERE user_id = %s", (uid,))
            if not d:
                return None
            return Teacher(
                ma_gv=d['ma_gv'],
                hoc_vi=d.get('hoc_vi'),
                khoa=d.get('khoa'),
                chuyen_nganh=d.get('chuyen_nganh'),
                tham_nien=d.get('tham_nien', 0),
                **common,
            )

        if role == 'employee':
            d = db.fetch_one("SELECT * FROM employees WHERE user_id = %s", (uid,))
            if not d:
                return None
            return Employee(
                ma_nv=d['ma_nv'],
                chuc_vu=d.get('chuc_vu'),
                phong_ban=d.get('phong_ban'),
                ngay_vao_lam=d.get('ngay_vao_lam'),
                **common,
            )

        if role == 'admin':
            d = db.fetch_one("SELECT * FROM admins WHERE user_id = %s", (uid,))
            return Admin(
                ma_admin=d['ma_admin'] if d else 'AD001',
                **common,
            )

        return None

    @staticmethod
    def change_password(user_id: int, new_password: str):
        """doi mk (hash bang sha256)"""
        from backend.utils.hash_util import hash_password
        db.execute(
            "UPDATE users SET password = %s WHERE id = %s",
            (hash_password(new_password), user_id)
        )
