from backend.database.db import db


class AttendanceService:
    """Diem danh buoi hoc"""

    @staticmethod
    def get_for_schedule(schedule_id: int):
        """Diem danh cua 1 buoi hoc"""
        sql = """
            SELECT a.*, u.full_name, s.msv
              FROM attendance a
              JOIN students s ON s.user_id = a.hv_id
              JOIN users u ON u.id = s.user_id
             WHERE a.schedule_id = %s
             ORDER BY u.full_name
        """
        return db.fetch_all(sql, (schedule_id,))

    @staticmethod
    def get_for_student(hv_id: int, lop_id: str = None):
        """Lich su diem danh cua 1 HV"""
        sql = """
            SELECT a.*, sc.ngay, sc.buoi_so, sc.lop_id
              FROM attendance a
              JOIN schedules sc ON sc.id = a.schedule_id
             WHERE a.hv_id = %s
        """
        params = [hv_id]
        if lop_id:
            sql += " AND sc.lop_id = %s"
            params.append(lop_id)
        sql += " ORDER BY sc.ngay DESC"
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def mark(schedule_id: int, hv_id: int, trang_thai: str,
             gio_vao=None, recorded_by: int = None, ghi_chu: str = None):
        """Ghi diem danh (UPSERT)"""
        db.execute(
            """INSERT INTO attendance (schedule_id, hv_id, trang_thai, gio_vao, recorded_by, ghi_chu)
                    VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (schedule_id, hv_id) DO UPDATE
                  SET trang_thai = EXCLUDED.trang_thai,
                      gio_vao = EXCLUDED.gio_vao,
                      recorded_by = EXCLUDED.recorded_by,
                      ghi_chu = EXCLUDED.ghi_chu,
                      recorded_at = CURRENT_TIMESTAMP""",
            (schedule_id, hv_id, trang_thai, gio_vao, recorded_by, ghi_chu)
        )

    @staticmethod
    def class_summary(lop_id: str):
        """Summary diem danh tat ca HV trong 1 lop. Tra ve list dict {msv, present_cnt, total, rate}.
        Dung de tinh diem chuyen can hang loat - tranh N+1 query."""
        sql = """
            SELECT s.msv,
                   COUNT(*) FILTER (WHERE a.trang_thai IN ('present','late')) AS present_cnt,
                   COUNT(*) AS total
              FROM students s
              JOIN attendance a ON a.hv_id = s.user_id
              JOIN schedules sc ON sc.id = a.schedule_id
             WHERE sc.lop_id = %s
          GROUP BY s.msv
        """
        rows = db.fetch_all(sql, (lop_id,))
        out = []
        for r in rows:
            total = r.get('total') or 0
            present = r.get('present_cnt') or 0
            out.append({
                'msv': r['msv'],
                'present_cnt': present,
                'total': total,
                'rate': round(present / total * 100, 1) if total else 0.0,
            })
        return out

    @staticmethod
    def attendance_rate(hv_id: int, lop_id: str) -> float:
        """Ty le diem danh cua HV trong 1 lop (present + late / tong)"""
        row = db.fetch_one(
            """SELECT COUNT(*) FILTER (WHERE a.trang_thai IN ('present', 'late')) AS present_cnt,
                      COUNT(*) AS total
                 FROM attendance a
                 JOIN schedules sc ON sc.id = a.schedule_id
                WHERE a.hv_id = %s AND sc.lop_id = %s""",
            (hv_id, lop_id)
        )
        if not row or not row['total']:
            return 0.0
        return round(row['present_cnt'] / row['total'] * 100, 1)
