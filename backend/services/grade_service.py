from backend.database.db import db


def _xep_loai_10(score: float) -> str:
    """chuyen diem tong ket (thang 10) sang xep loai A+/A/B+/B/C+/C/D/F"""
    if score >= 9:   return 'A+'
    if score >= 8.5: return 'A'
    if score >= 8:   return 'B+'
    if score >= 7:   return 'B'
    if score >= 6.5: return 'C+'
    if score >= 5.5: return 'C'
    if score >= 4:   return 'D'
    return 'F'


class GradeService:
    @staticmethod
    def get_grades_by_student(hv_id: int):
        """xem diem cua 1 HV qua cac lop"""
        sql = """
            SELECT g.lop_id, c.ma_mon, co.ten_mon,
                   g.diem_qt, g.diem_thi, g.tong_ket, g.xep_loai
              FROM grades g
              JOIN classes c ON c.ma_lop = g.lop_id
              JOIN courses co ON co.ma_mon = c.ma_mon
             WHERE g.hv_id = %s
             ORDER BY g.lop_id
        """
        return db.fetch_all(sql, (hv_id,))

    @staticmethod
    def get_grades_by_class(lop_id: str):
        """bang diem cua 1 lop (cho GV xem/nhap)"""
        sql = """
            SELECT u.id AS hv_id, s.msv, u.full_name,
                   g.diem_qt, g.diem_thi, g.tong_ket, g.xep_loai
              FROM students s
              JOIN users u ON u.id = s.user_id
              JOIN registrations r ON r.hv_id = u.id
         LEFT JOIN grades g ON g.hv_id = u.id AND g.lop_id = r.lop_id
             WHERE r.lop_id = %s
               AND r.trang_thai IN ('paid', 'completed')
             ORDER BY u.full_name
        """
        return db.fetch_all(sql, (lop_id,))

    @staticmethod
    def save_grade(hv_id: int, lop_id: str, diem_qt: float,
                   diem_thi: float, gv_id: int):
        """luu diem QT + Thi, auto tinh tong ket (30% QT + 70% Thi) + xep loai"""
        tong_ket = round(float(diem_qt) * 0.3 + float(diem_thi) * 0.7, 2)
        xl = _xep_loai_10(tong_ket)
        sql = """
            INSERT INTO grades (hv_id, lop_id, diem_qt, diem_thi, tong_ket, xep_loai, gv_nhap)
                 VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (hv_id, lop_id) DO UPDATE
                  SET diem_qt    = EXCLUDED.diem_qt,
                      diem_thi   = EXCLUDED.diem_thi,
                      tong_ket   = EXCLUDED.tong_ket,
                      xep_loai   = EXCLUDED.xep_loai,
                      gv_nhap    = EXCLUDED.gv_nhap,
                      updated_at = CURRENT_TIMESTAMP
        """
        db.execute(sql, (hv_id, lop_id, diem_qt, diem_thi, tong_ket, xl, gv_id))

    @staticmethod
    def get_gpa_stats(hv_id: int):
        """tinh diem TB tich luy + so lop hoan thanh"""
        row = db.fetch_one(
            """SELECT AVG(tong_ket) AS gpa,
                      COUNT(*) AS so_lop
                 FROM grades
                WHERE hv_id = %s""",
            (hv_id,)
        )
        if not row:
            return dict(gpa=0.0, so_lop=0)
        gpa = float(row['gpa']) if row['gpa'] is not None else 0.0
        return dict(gpa=round(gpa, 2), so_lop=row['so_lop'] or 0)

    @staticmethod
    def get_teacher_avg_rating(gv_id: int):
        """diem trung binh cua 1 GV (cho dashboard GV)"""
        row = db.fetch_one(
            "SELECT AVG(diem) AS avg_rating, COUNT(*) AS n FROM reviews WHERE gv_id = %s",
            (gv_id,)
        )
        if not row or row['avg_rating'] is None:
            return dict(avg_rating=0.0, count=0)
        return dict(avg_rating=round(float(row['avg_rating']), 1), count=row['n'])
