from backend.database.db import db


class StatsService:
    """thong ke cho admin + employee dashboard"""

    @staticmethod
    def admin_overview():
        """4 stat card chinh cho admin dashboard"""
        total_students = db.fetch_one("SELECT COUNT(*) AS c FROM students")['c']
        total_classes = db.fetch_one(
            "SELECT COUNT(*) AS c FROM classes WHERE trang_thai IN ('open', 'full')"
        )['c']
        total_regs = db.fetch_one("SELECT COUNT(*) AS c FROM registrations")['c']
        cur_sem_row = db.fetch_one(
            "SELECT id, ten FROM semesters WHERE trang_thai = 'open' LIMIT 1"
        )
        current_sem = cur_sem_row['id'] if cur_sem_row else 'HK2'
        return dict(
            total_students=total_students,
            total_classes=total_classes,
            total_registrations=total_regs,
            current_semester=current_sem,
        )

    @staticmethod
    def stats_by_semester(semester_id: str):
        """Thong ke chi tiet cho 1 hoc ky (chart/dept/class data)"""
        # chart data: lop cua HK do + siso
        chart = db.fetch_all(
            """SELECT co.ten_mon, vc.siso_hien_tai AS cur, vc.siso_max AS mx
                 FROM v_class_detail vc
                 JOIN courses co ON co.ma_mon = vc.ma_mon
                WHERE vc.semester_id = %s
                ORDER BY vc.siso_hien_tai DESC""",
            (semester_id,)
        )
        # dept stats: nhom theo khoa GV (CNTT/Toan/Ngoai ngu)
        dept = db.fetch_all(
            """SELECT COALESCE(t.khoa, 'Khac') AS khoa,
                      COUNT(DISTINCT r.hv_id) AS so_hv,
                      COUNT(DISTINCT c.ma_lop) AS so_lop
                 FROM classes c
            LEFT JOIN teachers t ON t.user_id = c.gv_id
            LEFT JOIN registrations r ON r.lop_id = c.ma_lop
                WHERE c.semester_id = %s
                GROUP BY COALESCE(t.khoa, 'Khac')
                ORDER BY so_hv DESC""",
            (semester_id,)
        )
        # class stats voi avg GPA
        cls = db.fetch_all(
            """SELECT vc.ma_lop, vc.siso_hien_tai,
                      COALESCE(ROUND(AVG(g.tong_ket)::numeric, 1), 0) AS gpa,
                      (vc.siso_hien_tai * vc.gia) AS doanh_thu
                 FROM v_class_detail vc
            LEFT JOIN grades g ON g.lop_id = vc.ma_lop
                WHERE vc.semester_id = %s
                GROUP BY vc.ma_lop, vc.siso_hien_tai, vc.gia
                ORDER BY gpa DESC""",
            (semester_id,)
        )
        return dict(chart=chart, dept=dept, class_stats=cls)

    @staticmethod
    def top_classes(limit: int = 5):
        """top lop dong HV nhat (tinh ty le % siso/siso_max)"""
        sql = """
            SELECT vc.ma_lop, co.ten_mon,
                   vc.siso_hien_tai, vc.siso_max,
                   ROUND((vc.siso_hien_tai::numeric / NULLIF(vc.siso_max, 0)) * 100) AS ty_le
              FROM v_class_detail vc
              JOIN courses co ON co.ma_mon = vc.ma_mon
             ORDER BY ty_le DESC NULLS LAST
             LIMIT %s
        """
        return db.fetch_all(sql, (limit,))

    @staticmethod
    def recent_activity(limit: int = 5):
        """hoat dong gan day: ket hop dang ky + thanh toan"""
        sql = """
            SELECT 'reg' AS loai, r.ngay_dk AS thoi_gian,
                   u.full_name || ' đăng ký ' || r.lop_id AS noi_dung
              FROM registrations r
              JOIN students s ON s.user_id = r.hv_id
              JOIN users u ON u.id = s.user_id
             UNION ALL
            SELECT 'pay' AS loai, p.ngay_thu AS thoi_gian,
                   u.full_name || ' thanh toán ' || p.so_tien::text || ' đ' AS noi_dung
              FROM payments p
              JOIN registrations r ON r.id = p.reg_id
              JOIN students s ON s.user_id = r.hv_id
              JOIN users u ON u.id = s.user_id
             ORDER BY thoi_gian DESC
             LIMIT %s
        """
        return db.fetch_all(sql, (limit,))

    @staticmethod
    def by_course():
        """thong ke dang ky theo mon hoc"""
        sql = """
            SELECT co.ma_mon, co.ten_mon,
                   COUNT(DISTINCT c.ma_lop) AS so_lop,
                   COUNT(r.id) AS so_dang_ky,
                   COALESCE(SUM(c.siso_hien_tai), 0) AS tong_hv
              FROM courses co
         LEFT JOIN classes c ON c.ma_mon = co.ma_mon
         LEFT JOIN registrations r ON r.lop_id = c.ma_lop
                                  AND r.trang_thai IN ('paid', 'completed')
             GROUP BY co.ma_mon, co.ten_mon
             ORDER BY co.ma_mon
        """
        return db.fetch_all(sql)

    @staticmethod
    def class_enrollment():
        """si so theo lop, co %"""
        sql = """
            SELECT vc.ma_lop, co.ten_mon,
                   vc.siso_hien_tai AS da_dk,
                   vc.siso_max AS toi_da,
                   CASE WHEN vc.siso_max > 0
                        THEN ROUND((vc.siso_hien_tai::numeric / vc.siso_max) * 100)
                        ELSE 0 END AS ty_le
              FROM v_class_detail vc
              JOIN courses co ON co.ma_mon = vc.ma_mon
             ORDER BY ty_le DESC
        """
        return db.fetch_all(sql)

    # ===== Employee dashboard =====
    @staticmethod
    def employee_today(emp_id: int):
        """stat card cho NV: dang ky hom nay / da TT / cho TT / doanh thu"""
        today_reg = db.fetch_one(
            """SELECT COUNT(*) AS c
                 FROM registrations
                WHERE DATE(ngay_dk) = CURRENT_DATE
                  AND nv_xu_ly = %s""",
            (emp_id,)
        )
        today_pay = db.fetch_one(
            """SELECT COUNT(*) AS c, COALESCE(SUM(so_tien), 0) AS tong
                 FROM payments
                WHERE DATE(ngay_thu) = CURRENT_DATE
                  AND nv_thu = %s""",
            (emp_id,)
        )
        pending = db.fetch_one(
            "SELECT COUNT(*) AS c FROM registrations WHERE trang_thai = 'pending_payment'"
        )
        return dict(
            today_reg=today_reg['c'] if today_reg else 0,
            today_paid=today_pay['c'] if today_pay else 0,
            today_revenue=int(today_pay['tong']) if today_pay and today_pay['tong'] else 0,
            pending=pending['c'] if pending else 0,
        )

    @staticmethod
    def recent_pending_registrations(limit: int = 5):
        """cho dashboard NV - cac DK dang cho xu ly"""
        sql = """
            SELECT u.full_name AS ten_hv, r.lop_id, r.trang_thai
              FROM registrations r
              JOIN students s ON s.user_id = r.hv_id
              JOIN users u ON u.id = s.user_id
             WHERE r.trang_thai = 'pending_payment'
             ORDER BY r.ngay_dk DESC
             LIMIT %s
        """
        return db.fetch_all(sql, (limit,))

    # ===== Teacher dashboard =====
    @staticmethod
    def teacher_overview(gv_id: int):
        so_lop = db.fetch_one(
            "SELECT COUNT(*) AS c FROM classes WHERE gv_id = %s", (gv_id,)
        )['c']
        tong_hv = db.fetch_one(
            """SELECT COALESCE(SUM(siso_hien_tai), 0) AS t
                 FROM classes
                WHERE gv_id = %s""",
            (gv_id,)
        )['t']
        diem_tb = db.fetch_one(
            "SELECT COALESCE(AVG(diem), 0) AS d FROM reviews WHERE gv_id = %s",
            (gv_id,)
        )['d']
        return dict(
            so_lop=so_lop,
            tong_hv=int(tong_hv),
            buoi_tuan=12,  # fake so tuong doi, chua co bang schedule thuc
            diem_danh_gia=round(float(diem_tb), 1),
        )
