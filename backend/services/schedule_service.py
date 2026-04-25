from datetime import date, timedelta
from backend.database.db import db


class ScheduleService:
    """Lich hoc theo tuan, cho ca HV va GV"""

    @staticmethod
    def get_by_week(week_start: date):
        """Lay tat ca buoi hoc trong tuan bat dau tu week_start (T2)"""
        week_end = week_start + timedelta(days=6)
        sql = """
            SELECT sc.*, c.ma_mon, co.ten_mon, u.full_name AS ten_gv, c.phong AS lop_phong
              FROM schedules sc
              JOIN classes c ON c.ma_lop = sc.lop_id
         LEFT JOIN courses co ON co.ma_mon = c.ma_mon
         LEFT JOIN teachers t ON t.user_id = c.gv_id
         LEFT JOIN users u ON u.id = t.user_id
             WHERE sc.ngay BETWEEN %s AND %s
             ORDER BY sc.ngay, sc.gio_bat_dau
        """
        return db.fetch_all(sql, (week_start, week_end))

    @staticmethod
    def get_for_student_week(hv_id: int, week_start: date):
        """Lich hoc cua 1 HV trong tuan (qua registrations)"""
        week_end = week_start + timedelta(days=6)
        sql = """
            SELECT sc.*, c.ma_mon, co.ten_mon, u.full_name AS ten_gv
              FROM schedules sc
              JOIN classes c ON c.ma_lop = sc.lop_id
              JOIN registrations r ON r.lop_id = c.ma_lop
         LEFT JOIN courses co ON co.ma_mon = c.ma_mon
         LEFT JOIN teachers t ON t.user_id = c.gv_id
         LEFT JOIN users u ON u.id = t.user_id
             WHERE r.hv_id = %s
               AND r.trang_thai IN ('paid', 'pending_payment', 'completed')
               AND sc.ngay BETWEEN %s AND %s
             ORDER BY sc.ngay, sc.gio_bat_dau
        """
        return db.fetch_all(sql, (hv_id, week_start, week_end))

    @staticmethod
    def get_for_teacher_week(gv_id: int, week_start: date):
        """Lich day cua GV trong tuan"""
        week_end = week_start + timedelta(days=6)
        sql = """
            SELECT sc.*, c.ma_mon, co.ten_mon, c.ma_lop, c.siso_hien_tai
              FROM schedules sc
              JOIN classes c ON c.ma_lop = sc.lop_id
         LEFT JOIN courses co ON co.ma_mon = c.ma_mon
             WHERE c.gv_id = %s
               AND sc.ngay BETWEEN %s AND %s
             ORDER BY sc.ngay, sc.gio_bat_dau
        """
        return db.fetch_all(sql, (gv_id, week_start, week_end))

    @staticmethod
    def get_today():
        return db.fetch_all("SELECT * FROM v_today_schedule")

    @staticmethod
    def get_for_class(lop_id: str):
        return db.fetch_all(
            "SELECT * FROM schedules WHERE lop_id = %s ORDER BY ngay",
            (lop_id,)
        )

    @staticmethod
    def create(lop_id: str, ngay: date, gio_bat_dau, gio_ket_thuc,
               phong: str = None, buoi_so: int = None, noi_dung: str = None,
               thu: int = None, trang_thai: str = 'scheduled'):
        db.execute(
            """INSERT INTO schedules
               (lop_id, ngay, thu, gio_bat_dau, gio_ket_thuc, phong, buoi_so, noi_dung, trang_thai)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (lop_id, ngay, thu, gio_bat_dau, gio_ket_thuc, phong, buoi_so, noi_dung, trang_thai)
        )
