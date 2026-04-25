from backend.database.db import db


class ExamService:
    """Lich thi cuoi ky"""

    @staticmethod
    def get_all(semester_id: str = None):
        sql = """
            SELECT es.*, c.ma_mon, co.ten_mon
              FROM exam_schedules es
              JOIN classes c ON c.ma_lop = es.lop_id
         LEFT JOIN courses co ON co.ma_mon = c.ma_mon
        """
        params = None
        if semester_id:
            sql += " WHERE es.semester_id = %s"
            params = (semester_id,)
        sql += " ORDER BY es.ngay_thi, es.ca_thi"
        return db.fetch_all(sql, params)

    @staticmethod
    def get_for_student(hv_id: int, semester_id: str = None):
        """Lich thi cua HV (qua cac lop da dang ky)"""
        sql = """
            SELECT DISTINCT es.*, c.ma_mon, co.ten_mon
              FROM exam_schedules es
              JOIN classes c ON c.ma_lop = es.lop_id
              JOIN registrations r ON r.lop_id = c.ma_lop
         LEFT JOIN courses co ON co.ma_mon = c.ma_mon
             WHERE r.hv_id = %s
               AND r.trang_thai IN ('paid', 'completed')
        """
        params = [hv_id]
        if semester_id:
            sql += " AND es.semester_id = %s"
            params.append(semester_id)
        sql += " ORDER BY es.ngay_thi"
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def get_for_class(lop_id: str):
        return db.fetch_all(
            "SELECT * FROM exam_schedules WHERE lop_id = %s ORDER BY ngay_thi",
            (lop_id,)
        )

    @staticmethod
    def create(lop_id: str, ngay_thi, ca_thi: str, phong: str = None,
               hinh_thuc: str = 'Tu luan', semester_id: str = None,
               gio_bat_dau=None, gio_ket_thuc=None,
               so_cau: int = None, thoi_gian_phut: int = 90):
        db.execute(
            """INSERT INTO exam_schedules
               (lop_id, semester_id, ngay_thi, ca_thi, gio_bat_dau, gio_ket_thuc,
                phong, hinh_thuc, so_cau, thoi_gian_phut)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (lop_id, semester_id, ngay_thi, ca_thi, gio_bat_dau, gio_ket_thuc,
             phong, hinh_thuc, so_cau, thoi_gian_phut)
        )
