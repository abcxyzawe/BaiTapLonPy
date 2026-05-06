from backend.database.db import db


class RegistrationService:
    """quan ly dang ky + thanh toan"""

    @staticmethod
    def register_student(hv_id: int, lop_id: str, nv_id: int) -> int:
        """nhan vien dang ky cho HV, tra ve reg_id. trang thai = pending_payment.

        Validate: lop phai thuoc dot dang OPEN (trang_thai='open'),
        khong cho register vao lop dot da closed/upcoming.

        DB co UNIQUE (hv_id, lop_id) -> neu HV da co reg cu (cancelled), INSERT
        moi se vi pham unique. Detect va revive reg cancelled cu thay vi INSERT
        moi (UX: HV co the dang ky lai sau khi huy nham).
        """
        # Check sem status cua lop truoc khi register
        sem_row = db.fetch_one(
            """SELECT s.id, s.trang_thai FROM classes c
                 LEFT JOIN semesters s ON s.id = c.semester_id
                WHERE c.ma_lop = %s""",
            (lop_id,)
        )
        if not sem_row:
            raise ValueError(f'Lớp {lop_id} không tồn tại trong hệ thống')
        sem_status = sem_row.get('trang_thai')
        if sem_status != 'open':
            sem_id_disp = sem_row.get('id') or '(không có đợt)'
            status_vn = {'closed': 'đã đóng', 'upcoming': 'chưa mở',
                         None: 'không có đợt nào'}.get(sem_status, sem_status or 'không xác định')
            raise ValueError(
                f'Đợt "{sem_id_disp}" của lớp {lop_id} hiện {status_vn}. '
                'Không thể đăng ký mới vào lớp này.'
            )
        # Check reg cu (handle UNIQUE constraint) - neu cancelled thi revive,
        # con lai (pending/paid/completed) raise loi cho FE biet
        old = db.fetch_one(
            'SELECT id, trang_thai FROM registrations WHERE hv_id = %s AND lop_id = %s',
            (hv_id, lop_id)
        )
        if old:
            old_status = old.get('trang_thai')
            if old_status == 'cancelled':
                # Trigger trg_check_class_full chi BEFORE INSERT, khong fire khi
                # UPDATE -> can check capacity thu cong de tranh over-fill khi revive
                cap = db.fetch_one(
                    'SELECT siso_hien_tai, siso_max, trang_thai FROM classes WHERE ma_lop = %s',
                    (lop_id,)
                )
                if cap:
                    if cap.get('trang_thai') == 'closed':
                        raise ValueError(f'Lớp {lop_id} đã đóng, không thể đăng ký lại.')
                    if cap.get('siso_hien_tai', 0) >= cap.get('siso_max', 0):
                        raise ValueError(
                            f'Lớp {lop_id} đã đủ sĩ số '
                            f'({cap.get("siso_hien_tai")}/{cap.get("siso_max")}). '
                            'Không thể đăng ký lại.'
                        )
                # Revive: UPDATE trang_thai + nv_xu_ly + ngay_dk moi
                db.execute(
                    """UPDATE registrations
                          SET trang_thai = 'pending_payment',
                              nv_xu_ly = %s,
                              ngay_dk = CURRENT_TIMESTAMP
                        WHERE id = %s""",
                    (nv_id, old['id'])
                )
                return old['id']
            # Reg active (pending/paid/completed) - khong cho dang ky lai
            status_vn = {'pending_payment': 'chờ thanh toán',
                         'paid': 'đã thanh toán',
                         'completed': 'đã hoàn thành'}.get(old_status, old_status)
            raise ValueError(
                f'Học viên đã đăng ký lớp {lop_id} (trạng thái: {status_vn}). '
                'Mỗi học viên chỉ đăng ký 1 lần / lớp.'
            )
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
                   r.nv_xu_ly AS nv_id, r.hv_id,
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
        """ghi nhan thanh toan + update trang thai dang ky (transaction).

        Validate reg_id phai ton tai va dang o trang thai pending_payment.
        Truoc khong check -> co the goi vao reg cancelled lam reg do hoi sinh
        thanh paid, hoac ghi payment vao reg da paid (double-pay).
        """
        cur_row = db.fetch_one(
            "SELECT trang_thai FROM registrations WHERE id = %s",
            (reg_id,)
        )
        if not cur_row:
            raise ValueError(f'Đăng ký id={reg_id} không tồn tại')
        cur_status = cur_row.get('trang_thai')
        if cur_status != 'pending_payment':
            status_vn = {'paid': 'đã thanh toán', 'cancelled': 'đã huỷ',
                         'completed': 'đã hoàn tất'}.get(cur_status, cur_status or '?')
            raise ValueError(
                f'Đăng ký id={reg_id} hiện {status_vn}, không thể thu tiền.'
            )
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
        """Huy dang ky. Chi cho phep huy reg dang pending_payment hoac paid.
        Reg completed (da hoc xong) khong duoc huy de giu lich su.
        Reg cancelled san -> raise de UI bao 'da huy roi' thay vi silent no-op."""
        cur_row = db.fetch_one(
            "SELECT trang_thai FROM registrations WHERE id = %s",
            (reg_id,)
        )
        if not cur_row:
            return 0  # router tra 404
        cur_status = cur_row.get('trang_thai')
        if cur_status == 'completed':
            raise ValueError(
                f'Đăng ký id={reg_id} đã hoàn tất, không thể huỷ.'
            )
        if cur_status == 'cancelled':
            raise ValueError(
                f'Đăng ký id={reg_id} đã được huỷ trước đó.'
            )
        return db.execute(
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
