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
    def nearest_week_for_student(hv_id: int, ref_date: date):
        """Tim Monday cua tuan gan voi ref_date NHAT ma HV co lich. Tra None neu HV chua co lich nao.

        Logic: lay 1 buoi gan ref_date nhat (theo distance), tinh Monday cua tuan do.
        Dung khi UI mac dinh load tuan hien tai trong rong -> auto chuyen sang tuan co lich.
        """
        sql = """
            SELECT sc.ngay
              FROM schedules sc
              JOIN classes c ON c.ma_lop = sc.lop_id
              JOIN registrations r ON r.lop_id = c.ma_lop
             WHERE r.hv_id = %s
               AND r.trang_thai IN ('paid','pending_payment','completed')
          ORDER BY ABS(sc.ngay - %s)
             LIMIT 1
        """
        row = db.fetch_one(sql, (hv_id, ref_date))
        if not row or not row.get('ngay'):
            return None
        d = row['ngay']
        return d - timedelta(days=d.weekday())

    @staticmethod
    def nearest_week_for_teacher(gv_id: int, ref_date: date):
        """Tim Monday tuan gan ref_date nhat ma GV co lich day."""
        sql = """
            SELECT sc.ngay
              FROM schedules sc
              JOIN classes c ON c.ma_lop = sc.lop_id
             WHERE c.gv_id = %s
          ORDER BY ABS(sc.ngay - %s)
             LIMIT 1
        """
        row = db.fetch_one(sql, (gv_id, ref_date))
        if not row or not row.get('ngay'):
            return None
        d = row['ngay']
        return d - timedelta(days=d.weekday())

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
        # Auto compute thu (2-8) tu ngay neu khong truyen
        if thu is None and hasattr(ngay, 'weekday'):
            thu = ngay.weekday() + 2  # Mon=2..Sun=8
        # Auto fill phong tu classes neu khong truyen
        if not phong:
            row = db.fetch_one('SELECT phong FROM classes WHERE ma_lop = %s', (lop_id,))
            if row:
                phong = row.get('phong')
        row = db.execute_returning(
            """INSERT INTO schedules
               (lop_id, ngay, thu, gio_bat_dau, gio_ket_thuc, phong, buoi_so, noi_dung, trang_thai)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (lop_id, ngay, thu, gio_bat_dau, gio_ket_thuc, phong, buoi_so, noi_dung, trang_thai)
        )
        return row['id'] if row else None

    @staticmethod
    def delete(sched_id: int) -> bool:
        return db.execute('DELETE FROM schedules WHERE id = %s', (sched_id,)) > 0

    @staticmethod
    def update(sched_id: int, **fields) -> bool:
        """Update schedule. Cho phep update: ngay, gio_bat_dau, gio_ket_thuc,
        phong, buoi_so, noi_dung, thu, trang_thai. Tu re-compute thu tu ngay."""
        allowed = {'ngay', 'gio_bat_dau', 'gio_ket_thuc', 'phong',
                   'buoi_so', 'noi_dung', 'thu', 'trang_thai'}
        # Auto re-compute thu khi ngay change
        if 'ngay' in fields and fields['ngay'] and 'thu' not in fields:
            try:
                from datetime import date as _date
                ngay_val = fields['ngay']
                if isinstance(ngay_val, str):
                    ngay_val = _date.fromisoformat(ngay_val)
                fields['thu'] = ngay_val.weekday() + 2
            except Exception:
                pass
        sets = []
        vals = []
        for k, v in fields.items():
            if k in allowed and v is not None:
                sets.append(f'{k} = %s')
                vals.append(v)
        if not sets:
            return False
        vals.append(sched_id)
        return db.execute(
            f'UPDATE schedules SET {", ".join(sets)} WHERE id = %s', tuple(vals)
        ) > 0

    @staticmethod
    def create_batch(lop_id: str, days_of_week: list, start_date: date,
                     num_weeks: int, gio_bat_dau, gio_ket_thuc,
                     phong: str = None, start_buoi_so: int = 1,
                     noi_dung: str = None) -> list:
        """Bulk tao buoi hoc theo pattern: cac thu trong tuan, lap N tuan.

        Args:
            days_of_week: list of int 0-6 (Mon=0..Sun=6) hoac 2-8 (T2=2..CN=8)
            start_date: ngay bat dau (Monday cua tuan 1)
            num_weeks: so tuan (vd 12)
            start_buoi_so: buoi so bat dau dem tu (vd 1)

        Returns: list of created sched ids.
        """
        # Normalize days_of_week to weekday indices 0-6
        days_norm = []
        for d in days_of_week:
            if 2 <= d <= 8:
                days_norm.append((d - 2) % 7)  # T2=2 -> Mon=0, CN=8 -> Sun=6
            elif 0 <= d <= 6:
                days_norm.append(d)
        days_norm = sorted(set(days_norm))
        if not days_norm:
            return []
        # Auto fill phong tu classes neu khong truyen
        if not phong:
            row = db.fetch_one('SELECT phong FROM classes WHERE ma_lop = %s', (lop_id,))
            if row:
                phong = row.get('phong')
        # Find Monday of start_date week
        from datetime import timedelta as _td
        monday = start_date - _td(days=start_date.weekday())
        created_ids = []
        buoi_counter = start_buoi_so
        for week in range(num_weeks):
            for dow in days_norm:
                ngay = monday + _td(weeks=week, days=dow)
                thu = ngay.weekday() + 2
                row = db.execute_returning(
                    """INSERT INTO schedules
                       (lop_id, ngay, thu, gio_bat_dau, gio_ket_thuc, phong, buoi_so, noi_dung, trang_thai)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'scheduled')
                       RETURNING id""",
                    (lop_id, ngay, thu, gio_bat_dau, gio_ket_thuc, phong,
                     buoi_counter, noi_dung)
                )
                if row:
                    created_ids.append(row['id'])
                    buoi_counter += 1
        return created_ids

    @staticmethod
    def get_by_id(sched_id: int):
        return db.fetch_one(
            """SELECT sc.*, c.ma_mon, co.ten_mon
                 FROM schedules sc
                 JOIN classes c ON c.ma_lop = sc.lop_id
            LEFT JOIN courses co ON co.ma_mon = c.ma_mon
                WHERE sc.id = %s""",
            (sched_id,)
        )

    @staticmethod
    def get_all_for_student(hv_id: int, from_date: date = None, to_date: date = None):
        """Tat ca buoi hoc cua HV trong khoang ngay (default 1 nam tu hom nay)."""
        from datetime import date as _date, timedelta as _td
        if from_date is None:
            from_date = _date.today() - _td(days=180)
        if to_date is None:
            to_date = _date.today() + _td(days=180)
        sql = """
            SELECT DISTINCT sc.id, sc.lop_id, sc.ngay, sc.gio_bat_dau, sc.gio_ket_thuc,
                   sc.phong, sc.buoi_so, sc.noi_dung, sc.trang_thai,
                   c.ma_mon, co.ten_mon, u.full_name AS ten_gv
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
        return db.fetch_all(sql, (hv_id, from_date, to_date))

    @staticmethod
    def get_all_for_teacher(gv_id: int, from_date: date = None, to_date: date = None):
        """Tat ca buoi day cua GV trong khoang ngay."""
        from datetime import date as _date, timedelta as _td
        if from_date is None:
            from_date = _date.today() - _td(days=180)
        if to_date is None:
            to_date = _date.today() + _td(days=180)
        sql = """
            SELECT sc.id, sc.lop_id, sc.ngay, sc.gio_bat_dau, sc.gio_ket_thuc,
                   sc.phong, sc.buoi_so, sc.noi_dung, sc.trang_thai,
                   c.ma_mon, co.ten_mon, c.siso_hien_tai
              FROM schedules sc
              JOIN classes c ON c.ma_lop = sc.lop_id
         LEFT JOIN courses co ON co.ma_mon = c.ma_mon
             WHERE c.gv_id = %s
               AND sc.ngay BETWEEN %s AND %s
             ORDER BY sc.ngay, sc.gio_bat_dau
        """
        return db.fetch_all(sql, (gv_id, from_date, to_date))

    @staticmethod
    def check_conflicts(ngay: date, gio_bat_dau, gio_ket_thuc,
                         phong: str = None, lop_id: str = None,
                         gv_id: int = None, exclude_id: int = None):
        """Tim cac buoi hoc bi conflict (overlap thoi gian + cung phong/lop/GV).

        Conflict nghia la 2 buoi hoc xay ra cung ngay va overlap khoang gio:
            new.bd < other.kt AND new.kt > other.bd

        Args:
            phong: neu truyen, check trung phong
            lop_id: neu truyen, check trung lop (HV trung 2 lop cung gio)
            gv_id: neu truyen, check trung GV (GV day 2 lop cung gio)
            exclude_id: bo qua id nay (cho UPDATE - tranh self-conflict)

        Returns: list of conflicting schedules voi thong tin lop+mon+gv.
        """
        conditions = ['sc.ngay = %s', 'sc.gio_bat_dau < %s', 'sc.gio_ket_thuc > %s']
        params = [ngay, gio_ket_thuc, gio_bat_dau]
        # Filter by phong/lop/gv (OR logic - any of these matches)
        type_cond = []
        if phong:
            type_cond.append('sc.phong = %s')
            params.append(phong)
        if lop_id:
            type_cond.append('sc.lop_id = %s')
            params.append(lop_id)
        if gv_id:
            type_cond.append('c.gv_id = %s')
            params.append(gv_id)
        if not type_cond:
            return []  # Khong co tieu chi check
        conditions.append('(' + ' OR '.join(type_cond) + ')')
        if exclude_id:
            conditions.append('sc.id != %s')
            params.append(exclude_id)
        sql = f"""
            SELECT sc.id, sc.lop_id, sc.ngay, sc.gio_bat_dau, sc.gio_ket_thuc,
                   sc.phong, c.gv_id, co.ten_mon, u.full_name AS ten_gv
              FROM schedules sc
              JOIN classes c ON c.ma_lop = sc.lop_id
         LEFT JOIN courses co ON co.ma_mon = c.ma_mon
         LEFT JOIN users u ON u.id = c.gv_id
             WHERE {' AND '.join(conditions)}
             ORDER BY sc.gio_bat_dau
        """
        return db.fetch_all(sql, tuple(params))
