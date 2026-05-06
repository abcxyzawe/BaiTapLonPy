"""Assignment service - GV giao bai tap, HV nop bai, GV cham + gop y."""
from backend.database.db import db


class AssignmentService:
    """Quan ly bai tap (assignments) + bai nop (submissions)."""

    # ============ ASSIGNMENTS (GV side) ============

    @staticmethod
    def create(lop_id: str, gv_id: int, tieu_de: str, mo_ta: str = '',
               han_nop=None, diem_toi_da: float = 10) -> int:
        """GV tao bai tap moi cho lop. Tra ve assignment_id."""
        row = db.execute_returning(
            """INSERT INTO assignments (lop_id, gv_id, tieu_de, mo_ta, han_nop, diem_toi_da)
                    VALUES (%s, %s, %s, %s, %s, %s)
                 RETURNING id""",
            (lop_id, gv_id, tieu_de, mo_ta, han_nop, diem_toi_da)
        )
        return row['id']

    @staticmethod
    def update(assignment_id: int, **fields):
        """GV sua bai tap. Chi update fields da truyen vao."""
        allowed = {'tieu_de', 'mo_ta', 'han_nop', 'diem_toi_da'}
        sets = []
        vals = []
        for k, v in fields.items():
            if k in allowed and v is not None:
                sets.append(f'{k} = %s')
                vals.append(v)
        if not sets:
            return False
        vals.append(assignment_id)
        db.execute(f'UPDATE assignments SET {", ".join(sets)} WHERE id = %s', tuple(vals))
        return True

    @staticmethod
    def delete(assignment_id: int) -> bool:
        """GV xoa bai tap (cascade xoa luon submissions cua bai do)."""
        return db.execute(
            'DELETE FROM assignments WHERE id = %s', (assignment_id,)
        ) > 0

    @staticmethod
    def get_by_id(assignment_id: int):
        """Chi tiet 1 bai tap."""
        return db.fetch_one(
            """SELECT a.*, c.ma_mon, co.ten_mon, u.full_name AS ten_gv
                 FROM assignments a
                 JOIN classes c ON c.ma_lop = a.lop_id
                 JOIN courses co ON co.ma_mon = c.ma_mon
                 JOIN users u ON u.id = a.gv_id
                WHERE a.id = %s""",
            (assignment_id,)
        )

    @staticmethod
    def get_by_teacher(gv_id: int):
        """Tat ca bai tap GV da giao (tat ca lop), kem so HV nop."""
        sql = """
            SELECT a.id, a.lop_id, a.tieu_de, a.han_nop,
                   a.diem_toi_da, a.created_at,
                   co.ten_mon,
                   (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id = a.id) AS so_nop,
                   (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id = a.id AND s.diem IS NOT NULL) AS so_cham
              FROM assignments a
              JOIN classes c ON c.ma_lop = a.lop_id
              JOIN courses co ON co.ma_mon = c.ma_mon
             WHERE a.gv_id = %s
             ORDER BY a.created_at DESC
        """
        return db.fetch_all(sql, (gv_id,))

    @staticmethod
    def get_by_class(lop_id: str):
        """Tat ca bai tap cua 1 lop (cho HV xem)."""
        sql = """
            SELECT a.id, a.tieu_de, a.mo_ta, a.han_nop,
                   a.diem_toi_da, a.created_at,
                   u.full_name AS ten_gv
              FROM assignments a
              JOIN users u ON u.id = a.gv_id
             WHERE a.lop_id = %s
             ORDER BY COALESCE(a.han_nop, a.created_at) DESC
        """
        return db.fetch_all(sql, (lop_id,))

    # ============ SUBMISSIONS (HV side) ============

    @staticmethod
    def submit(assignment_id: int, hv_id: int, noi_dung: str,
               file_url: str = None) -> int:
        """HV nop bai. ON CONFLICT (assignment_id, hv_id) -> update content (re-nop).
        Tra ve submission_id."""
        row = db.execute_returning(
            """INSERT INTO submissions (assignment_id, hv_id, noi_dung, file_url, nop_luc)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
               ON CONFLICT (assignment_id, hv_id) DO UPDATE
                     SET noi_dung = EXCLUDED.noi_dung,
                         file_url = EXCLUDED.file_url,
                         nop_luc = CURRENT_TIMESTAMP,
                         diem = NULL,        -- reset diem khi HV nop lai
                         nhan_xet = NULL,
                         cham_luc = NULL
                 RETURNING id""",
            (assignment_id, hv_id, noi_dung, file_url)
        )
        return row['id']

    @staticmethod
    def grade(submission_id: int, diem: float, nhan_xet: str = ''):
        """GV cham diem + gop y cho 1 bai nop."""
        db.execute(
            """UPDATE submissions
                  SET diem = %s, nhan_xet = %s, cham_luc = CURRENT_TIMESTAMP
                WHERE id = %s""",
            (diem, nhan_xet, submission_id)
        )

    @staticmethod
    def get_submissions_by_assignment(assignment_id: int):
        """GV xem tat ca bai HV da nop cho 1 assignment.
        Bao gom HV CHUA nop (LEFT JOIN students -> registrations)."""
        sql = """
            SELECT s.user_id AS hv_id, s.msv, u.full_name,
                   sub.id AS submission_id, sub.noi_dung, sub.file_url,
                   sub.nop_luc, sub.diem, sub.nhan_xet, sub.cham_luc
              FROM students s
              JOIN users u ON u.id = s.user_id
              JOIN registrations r ON r.hv_id = s.user_id
                                  AND r.lop_id = (SELECT lop_id FROM assignments WHERE id = %s)
                                  AND r.trang_thai IN ('paid', 'completed')
         LEFT JOIN submissions sub ON sub.assignment_id = %s AND sub.hv_id = s.user_id
             ORDER BY u.full_name
        """
        return db.fetch_all(sql, (assignment_id, assignment_id))

    @staticmethod
    def get_submission(assignment_id: int, hv_id: int):
        """Lay bai nop cua 1 HV cho 1 assignment (None neu chua nop)."""
        return db.fetch_one(
            """SELECT * FROM submissions
                WHERE assignment_id = %s AND hv_id = %s""",
            (assignment_id, hv_id)
        )

    @staticmethod
    def get_submissions_by_student(hv_id: int):
        """HV xem lich su nop bai cua minh - kem feedback cua GV."""
        sql = """
            SELECT sub.id, sub.assignment_id, sub.noi_dung, sub.nop_luc,
                   sub.diem, sub.nhan_xet, sub.cham_luc,
                   a.tieu_de, a.lop_id, a.han_nop, a.diem_toi_da,
                   co.ten_mon
              FROM submissions sub
              JOIN assignments a ON a.id = sub.assignment_id
              JOIN classes c ON c.ma_lop = a.lop_id
              JOIN courses co ON co.ma_mon = c.ma_mon
             WHERE sub.hv_id = %s
             ORDER BY sub.nop_luc DESC
        """
        return db.fetch_all(sql, (hv_id,))

    @staticmethod
    def get_pending_for_student(hv_id: int):
        """Bai tap HV CAN nop (chua nop hoac da qua han) - cho dashboard / banner."""
        sql = """
            SELECT a.id, a.tieu_de, a.lop_id, a.han_nop, a.diem_toi_da,
                   co.ten_mon,
                   sub.id AS submission_id, sub.diem
              FROM assignments a
              JOIN classes c ON c.ma_lop = a.lop_id
              JOIN courses co ON co.ma_mon = c.ma_mon
              JOIN registrations r ON r.lop_id = a.lop_id
                                  AND r.hv_id = %s
                                  AND r.trang_thai IN ('paid', 'completed')
         LEFT JOIN submissions sub ON sub.assignment_id = a.id AND sub.hv_id = %s
             ORDER BY a.han_nop NULLS LAST, a.created_at DESC
        """
        return db.fetch_all(sql, (hv_id, hv_id))
