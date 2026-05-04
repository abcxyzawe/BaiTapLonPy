from backend.database.db import db


class CourseService:
    """CRUD mon hoc va lop"""

    # ===== Courses =====
    @staticmethod
    def get_all_courses():
        return db.fetch_all("SELECT * FROM courses ORDER BY ma_mon")

    @staticmethod
    def get_course(ma_mon: str):
        return db.fetch_one("SELECT * FROM courses WHERE ma_mon = %s", (ma_mon,))

    # ===== Classes =====
    @staticmethod
    def get_all_classes():
        return db.fetch_all("SELECT * FROM v_class_detail ORDER BY ma_lop")

    @staticmethod
    def get_class(ma_lop: str):
        return db.fetch_one("SELECT * FROM v_class_detail WHERE ma_lop = %s", (ma_lop,))

    @staticmethod
    def get_classes_by_teacher(gv_id: int):
        """danh sach lop ma 1 GV dang day"""
        return db.fetch_all(
            "SELECT * FROM v_class_detail WHERE gv_id = %s ORDER BY ma_lop",
            (gv_id,)
        )

    @staticmethod
    def get_classes_by_student(hv_id: int):
        """danh sach lop ma HV dang theo hoc (da dang ky, bao gom pending + paid)"""
        sql = """
            SELECT vc.*, r.id AS reg_id, r.trang_thai AS reg_status, r.ngay_dk
              FROM v_class_detail vc
              JOIN registrations r ON vc.ma_lop = r.lop_id
             WHERE r.hv_id = %s
               AND r.trang_thai IN ('pending_payment', 'paid', 'completed')
             ORDER BY r.ngay_dk DESC
        """
        return db.fetch_all(sql, (hv_id,))

    @staticmethod
    def get_students_in_class(ma_lop: str):
        """danh sach HV trong 1 lop"""
        sql = """
            SELECT s.user_id, u.full_name, s.msv, u.sdt, r.trang_thai AS reg_status
              FROM students s
              JOIN users u ON u.id = s.user_id
              JOIN registrations r ON r.hv_id = s.user_id
             WHERE r.lop_id = %s
               AND r.trang_thai IN ('pending_payment', 'paid', 'completed')
             ORDER BY u.full_name
        """
        return db.fetch_all(sql, (ma_lop,))

    @staticmethod
    def get_students_by_teacher(gv_id: int, lop_filter: str = None):
        """tat ca HV thuoc cac lop cua 1 GV"""
        sql = """
            SELECT s.user_id, u.full_name, s.msv, r.lop_id, u.sdt, r.trang_thai
              FROM students s
              JOIN users u ON u.id = s.user_id
              JOIN registrations r ON r.hv_id = s.user_id
              JOIN classes c ON c.ma_lop = r.lop_id
             WHERE c.gv_id = %s
               AND r.trang_thai IN ('pending_payment', 'paid', 'completed')
        """
        params = [gv_id]
        if lop_filter:
            sql += " AND r.lop_id = %s"
            params.append(lop_filter)
        sql += " ORDER BY r.lop_id, u.full_name"
        return db.fetch_all(sql, tuple(params))

    # ===== Courses CRUD (admin) =====
    @staticmethod
    def create_course(ma_mon: str, ten_mon: str, mo_ta: str = ''):
        db.execute(
            "INSERT INTO courses (ma_mon, ten_mon, mo_ta) VALUES (%s, %s, %s)",
            (ma_mon, ten_mon, mo_ta)
        )

    @staticmethod
    def update_course(ma_mon: str, ten_mon: str = None, mo_ta: str = None):
        """Return rowcount - 0 = course khong ton tai."""
        pairs, values = [], []
        if ten_mon is not None:
            pairs.append('ten_mon = %s'); values.append(ten_mon)
        if mo_ta is not None:
            pairs.append('mo_ta = %s'); values.append(mo_ta)
        if not pairs:
            row = db.fetch_one("SELECT 1 FROM courses WHERE ma_mon = %s", (ma_mon,))
            return 1 if row else 0
        values.append(ma_mon)
        return db.execute(f"UPDATE courses SET {', '.join(pairs)} WHERE ma_mon = %s", tuple(values))

    @staticmethod
    def delete_course(ma_mon: str):
        """Xoa course. Return rowcount de router check 404 neu khong ton tai."""
        return db.execute("DELETE FROM courses WHERE ma_mon = %s", (ma_mon,))

    # ===== Classes CRUD (admin) =====
    @staticmethod
    def create_class(ma_lop, ma_mon, gv_id=None, lich='', phong='',
                     siso_max=40, gia=0, semester_id=None,
                     siso_hien_tai=0, so_buoi=24):
        db.execute(
            """INSERT INTO classes
               (ma_lop, ma_mon, gv_id, semester_id, lich, phong,
                siso_max, siso_hien_tai, gia, so_buoi)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (ma_lop, ma_mon, gv_id, semester_id, lich, phong,
             siso_max, siso_hien_tai, gia, so_buoi)
        )

    @staticmethod
    def update_class(ma_lop: str, **fields):
        """Return rowcount - 0 = lop khong ton tai."""
        allowed = {'ma_mon', 'gv_id', 'semester_id', 'lich', 'phong',
                   'siso_max', 'siso_hien_tai', 'gia', 'trang_thai',
                   'ngay_bat_dau', 'ngay_ket_thuc', 'so_buoi'}
        pairs, values = [], []
        for k, v in fields.items():
            if k in allowed:
                pairs.append(f'{k} = %s'); values.append(v)
        if not pairs:
            row = db.fetch_one("SELECT 1 FROM classes WHERE ma_lop = %s", (ma_lop,))
            return 1 if row else 0
        values.append(ma_lop)
        return db.execute(f"UPDATE classes SET {', '.join(pairs)} WHERE ma_lop = %s", tuple(values))

    @staticmethod
    def delete_class(ma_lop: str):
        return db.execute("DELETE FROM classes WHERE ma_lop = %s", (ma_lop,))

    @staticmethod
    def update_class_price(ma_lop: str, gia: int):
        return db.execute("UPDATE classes SET gia = %s WHERE ma_lop = %s", (gia, ma_lop))

    @staticmethod
    def get_teachers_list():
        """Danh sach GV (id, ten, ma_gv) de populate combo admin"""
        return db.fetch_all(
            """SELECT u.id, u.full_name, t.ma_gv, t.hoc_vi, t.khoa
                 FROM users u
                 JOIN teachers t ON t.user_id = u.id
                WHERE u.is_active = TRUE
                ORDER BY u.full_name"""
        )
