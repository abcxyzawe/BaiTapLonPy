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
        """thong bao danh cho 1 HV:
        - Broadcast all (den_lop=NULL AND den_hv_id=NULL)
        - Lop HV dang ky (den_lop in HV's ACTIVE classes)
        - Direct message gui rieng (den_hv_id = hv_id)

        Loc trang_thai != 'cancelled' o subquery: HV da huy DK lop khong
        nhan thong bao cua lop do nua. Truoc khong loc -> HV cancel xong van
        nhan thong bao cua lop cu, gay confusing UX.
        """
        sql = """
            SELECT DISTINCT n.id, n.tieu_de, n.noi_dung, n.loai, n.ngay_tao,
                   n.den_lop, n.den_hv_id,
                   u.full_name AS ten_nguoi_gui, u.role AS vai_tro_gui,
                   CASE WHEN n.den_hv_id = %s THEN 'rieng'
                        WHEN n.den_lop IS NOT NULL THEN 'lop'
                        ELSE 'all' END AS muc_tieu
              FROM notifications n
         LEFT JOIN users u ON u.id = n.tu_id
             WHERE (n.den_lop IS NULL AND n.den_hv_id IS NULL)
                OR n.den_lop IN (
                    SELECT lop_id FROM registrations
                     WHERE hv_id = %s
                       AND trang_thai IN ('paid', 'pending_payment', 'completed')
                )
                OR n.den_hv_id = %s
             ORDER BY n.ngay_tao DESC
        """
        return db.fetch_all(sql, (hv_id, hv_id, hv_id))

    @staticmethod
    def get_sent_by_teacher(gv_id: int, limit: int = 10):
        # JOIN users de lay ten HV neu notif gui rieng (den_hv_id != NULL).
        # Truoc chi SELECT * -> FE chi co den_lop / den_hv_id thieu ten HV
        # -> display fallback 'Tat ca' bi sai khi notif gui rieng 1 HV
        sql = """
            SELECT n.*, u.full_name AS ten_hv_dich
              FROM notifications n
         LEFT JOIN users u ON u.id = n.den_hv_id
             WHERE n.tu_id = %s
             ORDER BY n.ngay_tao DESC
             LIMIT %s
        """
        return db.fetch_all(sql, (gv_id, limit))

    @staticmethod
    def send(tu_id: int, tieu_de: str, noi_dung: str,
             den_lop: str = None, den_hv_id: int = None, loai: str = 'info'):
        """Gui notification:
        - den_lop=None + den_hv_id=None -> broadcast tat ca HV
        - den_lop=X -> tat ca HV cua lop X
        - den_hv_id=N -> 1 HV cu the (uu tien hon den_lop)
        """
        db.execute(
            """INSERT INTO notifications (tu_id, den_lop, den_hv_id, tieu_de, noi_dung, loai)
                    VALUES (%s, %s, %s, %s, %s, %s)""",
            (tu_id, den_lop, den_hv_id, tieu_de, noi_dung, loai)
        )

    @staticmethod
    def get_recent(limit: int = 10):
        """Lay thong bao gan day nhat (cho admin dashboard)"""
        sql = """
            SELECT n.*, u.full_name AS ten_nguoi_gui
              FROM notifications n
         LEFT JOIN users u ON u.id = n.tu_id
             ORDER BY n.ngay_tao DESC
             LIMIT %s
        """
        return db.fetch_all(sql, (limit,))

    @staticmethod
    def delete(notif_id: int):
        return db.execute("DELETE FROM notifications WHERE id = %s", (notif_id,))
