from backend.database.db import db


class StatsService:
    """thong ke cho admin + employee dashboard"""

    @staticmethod
    def admin_overview():
        """4 stat card chinh cho admin dashboard.

        Optimize: 1 query voi sub-select thay 4 round-trip db. Latency 4x->1x.
        """
        row = db.fetch_one("""
            SELECT
              (SELECT COUNT(*) FROM students) AS total_students,
              (SELECT COUNT(*) FROM classes WHERE trang_thai IN ('open', 'full')) AS total_classes,
              (SELECT COUNT(*) FROM registrations) AS total_registrations,
              (SELECT id FROM semesters WHERE trang_thai = 'open' LIMIT 1) AS current_semester
        """) or {}
        return dict(
            total_students=row.get('total_students', 0) or 0,
            total_classes=row.get('total_classes', 0) or 0,
            total_registrations=row.get('total_registrations', 0) or 0,
            current_semester=row.get('current_semester'),  # None neu khong co dot open
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
        """hoat dong gan day: ket hop dang ky + thanh toan.

        Format so tien VN voi dau cham ngan nghin qua TO_CHAR + REPLACE
        (PostgreSQL khong co built-in '.' separator nhu ',' nen replace).
        """
        sql = """
            SELECT 'reg' AS loai, r.ngay_dk AS thoi_gian,
                   u.full_name || ' đăng ký ' || r.lop_id AS noi_dung
              FROM registrations r
              JOIN students s ON s.user_id = r.hv_id
              JOIN users u ON u.id = s.user_id
             UNION ALL
            SELECT 'pay' AS loai, p.ngay_thu AS thoi_gian,
                   u.full_name || ' thanh toán '
                     || REPLACE(TO_CHAR(p.so_tien, 'FM999,999,999'), ',', '.')
                     || ' đ' AS noi_dung
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
        """stat card cho NV: dang ky hom nay / da TT / cho TT / doanh thu

        Optimize: 3 query -> 1 sub-select query (giam 3x round-trip DB).
        """
        row = db.fetch_one("""
            SELECT
              (SELECT COUNT(*) FROM registrations
                WHERE DATE(ngay_dk) = CURRENT_DATE AND nv_xu_ly = %s) AS today_reg,
              (SELECT COUNT(*) FROM payments
                WHERE DATE(ngay_thu) = CURRENT_DATE AND nv_thu = %s) AS today_paid,
              (SELECT COALESCE(SUM(so_tien), 0) FROM payments
                WHERE DATE(ngay_thu) = CURRENT_DATE AND nv_thu = %s) AS today_revenue,
              (SELECT COUNT(*) FROM registrations
                WHERE trang_thai = 'pending_payment') AS pending
        """, (emp_id, emp_id, emp_id)) or {}
        return dict(
            today_reg=row.get('today_reg', 0) or 0,
            today_paid=row.get('today_paid', 0) or 0,
            today_revenue=int(row.get('today_revenue', 0) or 0),
            pending=row.get('pending', 0) or 0,
        )

    @staticmethod
    def employee_revenue_report(emp_id: int, from_date, to_date):
        """Bao cao doanh thu chi tiet cua NV trong khoang ngay [from_date, to_date].
        Tra ve dict: total, count, payments=[{ngay, ten_hv, lop, so_tien, hinh_thuc, ghi_chu}]
        """
        # Aggregated total
        agg = db.fetch_one("""
            SELECT COUNT(*) AS so_lan,
                   COALESCE(SUM(so_tien), 0) AS tong_tien
              FROM payments
             WHERE nv_thu = %s
               AND DATE(ngay_thu) BETWEEN %s AND %s
        """, (emp_id, from_date, to_date)) or {}
        # Detail list
        details = db.fetch_all("""
            SELECT p.id, p.ngay_thu, p.so_tien, p.hinh_thuc, p.ghi_chu,
                   r.lop_id, u.full_name AS ten_hv, s.msv,
                   co.ten_mon
              FROM payments p
              JOIN registrations r ON r.id = p.reg_id
              JOIN students s ON s.user_id = r.hv_id
              JOIN users u ON u.id = s.user_id
              JOIN classes c ON c.ma_lop = r.lop_id
              JOIN courses co ON co.ma_mon = c.ma_mon
             WHERE p.nv_thu = %s
               AND DATE(p.ngay_thu) BETWEEN %s AND %s
             ORDER BY p.ngay_thu DESC
        """, (emp_id, from_date, to_date)) or []
        # Group by hinh_thuc for breakdown
        bd = db.fetch_all("""
            SELECT hinh_thuc, COUNT(*) AS so_lan, SUM(so_tien) AS tong
              FROM payments
             WHERE nv_thu = %s
               AND DATE(ngay_thu) BETWEEN %s AND %s
             GROUP BY hinh_thuc
             ORDER BY tong DESC
        """, (emp_id, from_date, to_date)) or []
        return {
            'so_lan': int(agg.get('so_lan', 0) or 0),
            'tong_tien': int(agg.get('tong_tien', 0) or 0),
            'payments': details,
            'breakdown_by_method': bd,
        }

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
        """Optimize: 3 query -> 1 sub-select query (giam 3x round-trip DB)."""
        row = db.fetch_one("""
            SELECT
              (SELECT COUNT(*) FROM classes WHERE gv_id = %s) AS so_lop,
              (SELECT COALESCE(SUM(siso_hien_tai), 0) FROM classes WHERE gv_id = %s) AS tong_hv,
              (SELECT COALESCE(AVG(diem), 0) FROM reviews WHERE gv_id = %s) AS diem_tb
        """, (gv_id, gv_id, gv_id)) or {}
        return dict(
            so_lop=row.get('so_lop', 0) or 0,
            tong_hv=int(row.get('tong_hv', 0) or 0),
            buoi_tuan=12,  # fake so tuong doi, chua co bang schedule thuc
            diem_danh_gia=round(float(row.get('diem_tb', 0) or 0), 1),
        )
