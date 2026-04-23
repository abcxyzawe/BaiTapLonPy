from backend.database.db import db


class RegistrationService:
    """quan ly dang ky + thanh toan"""

    @staticmethod
    def register_student(hv_id: int, lop_id: str, nv_id: int) -> int:
        """nhan vien dang ky cho HV, tra ve reg_id. trang thai = pending_payment"""
        row = db.execute_returning(
            """INSERT INTO registrations (hv_id, lop_id, nv_xu_ly, trang_thai)
                    VALUES (%s, %s, %s, 'pending_payment')
                 RETURNING id""",
            (hv_id, lop_id, nv_id)
        )
        return row['id']

    @staticmethod
    def get_all_registrations(limit: int = 100):
        sql = """
            SELECT r.id, r.ngay_dk, r.trang_thai,
                   u.full_name AS ten_hv, s.msv,
                   r.lop_id, c.gia,
                   co.ten_mon
              FROM registrations r
              JOIN students s ON s.user_id = r.hv_id
              JOIN users u ON u.id = s.user_id
              JOIN classes c ON c.ma_lop = r.lop_id
              JOIN courses co ON co.ma_mon = c.ma_mon
             ORDER BY r.ngay_dk DESC
             LIMIT %s
        """
        return db.fetch_all(sql, (limit,))

    @staticmethod
    def get_pending_payments():
        """dang ky dang cho thanh toan"""
        sql = """
            SELECT r.id, u.full_name AS ten_hv, s.msv,
                   r.lop_id, c.gia
              FROM registrations r
              JOIN students s ON s.user_id = r.hv_id
              JOIN users u ON u.id = s.user_id
              JOIN classes c ON c.ma_lop = r.lop_id
             WHERE r.trang_thai = 'pending_payment'
             ORDER BY r.ngay_dk DESC
        """
        return db.fetch_all(sql)

    @staticmethod
    def confirm_payment(reg_id: int, so_tien: int, hinh_thuc: str,
                        nv_id: int, ghi_chu: str = None):
        """ghi nhan thanh toan + update trang thai dang ky (transaction)"""
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO payments (reg_id, so_tien, hinh_thuc, nv_thu, ghi_chu)
                        VALUES (%s, %s, %s, %s, %s)""",
                (reg_id, so_tien, hinh_thuc, nv_id, ghi_chu)
            )
            cur.execute(
                "UPDATE registrations SET trang_thai = 'paid' WHERE id = %s",
                (reg_id,)
            )

    @staticmethod
    def cancel_registration(reg_id: int):
        db.execute(
            "UPDATE registrations SET trang_thai = 'cancelled' WHERE id = %s",
            (reg_id,)
        )

    @staticmethod
    def get_registration(reg_id: int):
        sql = """
            SELECT r.*, u.full_name AS ten_hv, s.msv, c.gia
              FROM registrations r
              JOIN students s ON s.user_id = r.hv_id
              JOIN users u ON u.id = s.user_id
              JOIN classes c ON c.ma_lop = r.lop_id
             WHERE r.id = %s
        """
        return db.fetch_one(sql, (reg_id,))

    @staticmethod
    def get_total_revenue_today():
        row = db.fetch_one(
            """SELECT COALESCE(SUM(so_tien), 0) AS tong
                 FROM payments
                WHERE DATE(ngay_thu) = CURRENT_DATE"""
        )
        return int(row['tong']) if row else 0
