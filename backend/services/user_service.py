from backend.database.db import db


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
