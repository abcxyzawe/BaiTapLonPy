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

    # ===== mutation (admin) =====
    @staticmethod
    def create_class(ma_lop, ma_mon, gv_id, lich, phong, siso_max, gia):
        db.execute(
            """INSERT INTO classes (ma_lop, ma_mon, gv_id, lich, phong, siso_max, gia)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (ma_lop, ma_mon, gv_id, lich, phong, siso_max, gia)
        )

    @staticmethod
    def delete_class(ma_lop: str):
        db.execute("DELETE FROM classes WHERE ma_lop = %s", (ma_lop,))

    @staticmethod
    def update_class_price(ma_lop: str, gia: int):
        db.execute("UPDATE classes SET gia = %s WHERE ma_lop = %s", (gia, ma_lop))
