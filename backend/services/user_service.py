from backend.database.db import db
from backend.utils.hash_util import hash_password


def _create_user_base(username: str, password: str, role: str,
                      full_name: str, email: str = None, sdt: str = None):
    """Tao row trong users + tra ve user_id moi"""
    row = db.execute_returning(
        """INSERT INTO users (username, password, role, full_name, email, sdt)
                VALUES (%s, %s, %s, %s, %s, %s)
             RETURNING id""",
        (username, hash_password(password), role, full_name, email, sdt)
    )
    return row['id']


class StudentService:
    @staticmethod
    def get_all():
        sql = """
            SELECT u.id, u.full_name, u.sdt, u.email,
                   s.msv, s.ngaysinh, s.gioitinh, s.diachi,
                   COALESCE(
                     (SELECT string_agg(DISTINCT lop_id, ', ')
                        FROM registrations
                       WHERE hv_id = u.id
                         AND trang_thai IN ('pending_payment', 'paid', 'completed')),
                     '-'
                   ) AS cac_lop,
                   (SELECT COUNT(*) FROM registrations
                     WHERE hv_id = u.id
                       AND trang_thai IN ('pending_payment', 'paid', 'completed')) AS so_lop
              FROM users u
              JOIN students s ON s.user_id = u.id
             WHERE u.is_active = TRUE
             ORDER BY s.msv
        """
        return db.fetch_all(sql)

    @staticmethod
    def get_by_msv(msv: str):
        # Alias u.id AS user_id - dong nhat voi TeacherService.get_by_code,
        # EmployeeService.get_by_code (callers fallback row.get('user_id') or row.get('id')
        # -> alias rang buoc giup tranh case khi caller chi tim 'user_id')
        return db.fetch_one(
            """SELECT u.id AS user_id, u.id, u.full_name, u.email, u.sdt,
                      s.msv, s.ngaysinh, s.gioitinh, s.diachi
                 FROM users u JOIN students s ON s.user_id = u.id
                WHERE s.msv = %s""",
            (msv,)
        )

    @staticmethod
    def create(username: str, password: str, full_name: str, msv: str,
               email: str = None, sdt: str = None,
               ngaysinh=None, gioitinh: str = None, diachi: str = None):
        uid = _create_user_base(username, password, 'student', full_name, email, sdt)
        db.execute(
            """INSERT INTO students (user_id, msv, ngaysinh, gioitinh, diachi)
                    VALUES (%s, %s, %s, %s, %s)""",
            (uid, msv, ngaysinh, gioitinh, diachi)
        )
        return uid

    @staticmethod
    def update(user_id: int, email: str = None, sdt: str = None,
               diachi: str = None, full_name: str = None):
        """Return tong rowcount cua tat ca UPDATE - 0 = user khong ton tai."""
        total = 0
        pairs_u, vals_u = [], []
        if email is not None: pairs_u.append('email = %s'); vals_u.append(email)
        if sdt is not None: pairs_u.append('sdt = %s'); vals_u.append(sdt)
        if full_name is not None: pairs_u.append('full_name = %s'); vals_u.append(full_name)
        if pairs_u:
            vals_u.append(user_id)
            total += db.execute(f"UPDATE users SET {', '.join(pairs_u)} WHERE id = %s", tuple(vals_u)) or 0
        if diachi is not None:
            total += db.execute("UPDATE students SET diachi = %s WHERE user_id = %s", (diachi, user_id)) or 0
        # Neu khong co field nao, kiem tra user exist (return 1 neu co)
        if not pairs_u and diachi is None:
            row = db.fetch_one("SELECT 1 FROM users WHERE id = %s", (user_id,))
            return 1 if row else 0
        return total

    @staticmethod
    def delete(user_id: int):
        """Chi deactivate, khong xoa that (bao toan registrations)"""
        return db.execute("UPDATE users SET is_active = FALSE WHERE id = %s", (user_id,))


class TeacherService:
    @staticmethod
    def get_all():
        sql = """
            SELECT u.id, u.full_name, u.email, u.sdt,
                   t.ma_gv, t.hoc_vi, t.khoa, t.chuyen_nganh, t.tham_nien,
                   (SELECT COUNT(*) FROM classes WHERE gv_id = u.id) AS so_lop,
                   COALESCE((SELECT AVG(diem) FROM reviews WHERE gv_id = u.id), 0) AS diem_tb,
                   (SELECT COUNT(*) FROM reviews WHERE gv_id = u.id) AS so_danh_gia
              FROM users u
              JOIN teachers t ON t.user_id = u.id
             WHERE u.is_active = TRUE
             ORDER BY t.ma_gv
        """
        return db.fetch_all(sql)

    @staticmethod
    def get_for_review():
        """danh sach GV de HV danh gia (cho trang review)"""
        sql = """
            SELECT u.id AS gv_id, u.full_name, t.hoc_vi,
                   COALESCE((SELECT AVG(diem) FROM reviews WHERE gv_id = u.id), 0) AS diem_tb,
                   (SELECT COUNT(*) FROM reviews WHERE gv_id = u.id) AS so_danh_gia
              FROM users u
              JOIN teachers t ON t.user_id = u.id
             WHERE u.is_active = TRUE
             ORDER BY u.full_name
        """
        return db.fetch_all(sql)

    @staticmethod
    def create(username: str, password: str, full_name: str, ma_gv: str,
               email: str = None, sdt: str = None,
               hoc_vi: str = None, khoa: str = None,
               chuyen_nganh: str = None, tham_nien: int = 0):
        uid = _create_user_base(username, password, 'teacher', full_name, email, sdt)
        db.execute(
            """INSERT INTO teachers (user_id, ma_gv, hoc_vi, khoa, chuyen_nganh, tham_nien)
                    VALUES (%s, %s, %s, %s, %s, %s)""",
            (uid, ma_gv, hoc_vi, khoa, chuyen_nganh, tham_nien)
        )
        return uid

    @staticmethod
    def update(user_id: int, **fields):
        """Return tong rowcount - 0 = user khong ton tai."""
        total = 0
        u_fields = {k: fields[k] for k in ('full_name', 'email', 'sdt') if k in fields}
        t_fields = {k: fields[k] for k in ('hoc_vi', 'khoa', 'chuyen_nganh', 'tham_nien') if k in fields}
        if u_fields:
            pairs = [f'{k} = %s' for k in u_fields]
            vals = list(u_fields.values()) + [user_id]
            total += db.execute(f"UPDATE users SET {', '.join(pairs)} WHERE id = %s", tuple(vals)) or 0
        if t_fields:
            pairs = [f'{k} = %s' for k in t_fields]
            vals = list(t_fields.values()) + [user_id]
            total += db.execute(f"UPDATE teachers SET {', '.join(pairs)} WHERE user_id = %s", tuple(vals)) or 0
        if not u_fields and not t_fields:
            row = db.fetch_one("SELECT 1 FROM teachers WHERE user_id = %s", (user_id,))
            return 1 if row else 0
        return total

    @staticmethod
    def delete(user_id: int):
        return db.execute("UPDATE users SET is_active = FALSE WHERE id = %s", (user_id,))

    @staticmethod
    def get_by_code(ma_gv: str):
        """Lookup teacher user_id + info from ma_gv code."""
        sql = """
            SELECT u.id AS user_id, u.full_name, u.email, t.ma_gv, t.hoc_vi, t.khoa
              FROM users u
              JOIN teachers t ON t.user_id = u.id
             WHERE t.ma_gv = %s AND u.is_active = TRUE
        """
        return db.fetch_one(sql, (ma_gv,))


class EmployeeService:
    @staticmethod
    def get_all():
        sql = """
            SELECT u.id, u.full_name, u.email, u.sdt, u.is_active,
                   e.ma_nv, e.chuc_vu, e.phong_ban, e.ngay_vao_lam
              FROM users u
              JOIN employees e ON e.user_id = u.id
             ORDER BY e.ma_nv
        """
        return db.fetch_all(sql)

    @staticmethod
    def create(username: str, password: str, full_name: str, ma_nv: str,
               email: str = None, sdt: str = None,
               chuc_vu: str = None, phong_ban: str = None, ngay_vao_lam=None):
        uid = _create_user_base(username, password, 'employee', full_name, email, sdt)
        db.execute(
            """INSERT INTO employees (user_id, ma_nv, chuc_vu, phong_ban, ngay_vao_lam)
                    VALUES (%s, %s, %s, %s, %s)""",
            (uid, ma_nv, chuc_vu, phong_ban, ngay_vao_lam)
        )
        return uid

    @staticmethod
    def update(user_id: int, **fields):
        """Return tong rowcount - 0 = user khong ton tai."""
        total = 0
        u_fields = {k: fields[k] for k in ('full_name', 'email', 'sdt') if k in fields}
        e_fields = {k: fields[k] for k in ('chuc_vu', 'phong_ban', 'ngay_vao_lam') if k in fields}
        if u_fields:
            pairs = [f'{k} = %s' for k in u_fields]
            vals = list(u_fields.values()) + [user_id]
            total += db.execute(f"UPDATE users SET {', '.join(pairs)} WHERE id = %s", tuple(vals)) or 0
        if e_fields:
            pairs = [f'{k} = %s' for k in e_fields]
            vals = list(e_fields.values()) + [user_id]
            total += db.execute(f"UPDATE employees SET {', '.join(pairs)} WHERE user_id = %s", tuple(vals)) or 0
        if not u_fields and not e_fields:
            row = db.fetch_one("SELECT 1 FROM employees WHERE user_id = %s", (user_id,))
            return 1 if row else 0
        return total

    @staticmethod
    def delete(user_id: int):
        return db.execute("UPDATE users SET is_active = FALSE WHERE id = %s", (user_id,))

    @staticmethod
    def get_by_code(ma_nv: str):
        """Lookup employee user_id + info from ma_nv code."""
        sql = """
            SELECT u.id AS user_id, u.full_name, u.email, e.ma_nv, e.chuc_vu, e.phong_ban
              FROM users u
              JOIN employees e ON e.user_id = u.id
             WHERE e.ma_nv = %s AND u.is_active = TRUE
        """
        return db.fetch_one(sql, (ma_nv,))


class ReviewService:
    @staticmethod
    def submit_review(hv_id: int, gv_id: int, lop_id: str,
                      diem: int, nhan_xet: str = None):
        """HV danh gia GV (UPSERT)"""
        sql = """
            INSERT INTO reviews (hv_id, gv_id, lop_id, diem, nhan_xet)
                 VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (hv_id, gv_id, lop_id) DO UPDATE
                  SET diem = EXCLUDED.diem,
                      nhan_xet = EXCLUDED.nhan_xet,
                      ngay = CURRENT_TIMESTAMP
        """
        db.execute(sql, (hv_id, gv_id, lop_id, diem, nhan_xet))
