from backend.database.db import db


class NotificationService:

    @staticmethod
    def get_all():
        sql = """
            SELECT n.id, n.tieu_de, n.noi_dung, n.loai, n.ngay_tao, n.den_lop,
                   u.full_name AS ten_nguoi_gui, u.role AS vai_tro_gui
              FROM notifications n
         LEFT JOIN users u ON u.id = n.tu_id
             ORDER BY n.ngay_tao DESC
        """
        return db.fetch_all(sql)

    @staticmethod
    def get_for_student(hv_id: int):
        """thong bao danh cho 1 HV: tat ca (den_lop null) + cac lop HV dang ky"""
        sql = """
            SELECT DISTINCT n.id, n.tieu_de, n.noi_dung, n.loai, n.ngay_tao, n.den_lop,
                   u.full_name AS ten_nguoi_gui, u.role AS vai_tro_gui
              FROM notifications n
         LEFT JOIN users u ON u.id = n.tu_id
             WHERE n.den_lop IS NULL
                OR n.den_lop IN (SELECT lop_id FROM registrations WHERE hv_id = %s)
             ORDER BY n.ngay_tao DESC
        """
        return db.fetch_all(sql, (hv_id,))

    @staticmethod
    def get_sent_by_teacher(gv_id: int, limit: int = 10):
        sql = """
            SELECT * FROM notifications
             WHERE tu_id = %s
             ORDER BY ngay_tao DESC
             LIMIT %s
        """
        return db.fetch_all(sql, (gv_id, limit))

    @staticmethod
    def send(tu_id: int, tieu_de: str, noi_dung: str,
             den_lop: str = None, loai: str = 'info'):
        db.execute(
            """INSERT INTO notifications (tu_id, den_lop, tieu_de, noi_dung, loai)
                    VALUES (%s, %s, %s, %s, %s)""",
            (tu_id, den_lop, tieu_de, noi_dung, loai)
        )
