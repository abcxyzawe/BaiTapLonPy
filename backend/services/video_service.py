"""Class videos service - GV upload link video bai giang (YouTube/Drive/Vimeo),
HV xem lai khi vang hoc hoac on tap. Khong store video file - chi link."""
from backend.database.db import db


class ClassVideoService:
    """CRUD cho class_videos table."""

    @staticmethod
    def create(lop_id: str, gv_id: int, tieu_de: str, video_url: str,
               mo_ta: str = None, buoi_so: int = None) -> int:
        """GV them link video moi cho lop. Tra ve video_id."""
        row = db.execute_returning(
            """INSERT INTO class_videos (lop_id, gv_id, tieu_de, video_url, mo_ta, buoi_so)
                    VALUES (%s, %s, %s, %s, %s, %s)
                 RETURNING id""",
            (lop_id, gv_id, tieu_de, video_url, mo_ta, buoi_so)
        )
        return row['id']

    @staticmethod
    def update(video_id: int, **fields):
        """GV sua thong tin video (tieu_de, video_url, mo_ta, buoi_so).
        Tra ve rowcount - 0 = video khong ton tai."""
        allowed = {'tieu_de', 'video_url', 'mo_ta', 'buoi_so'}
        sets, vals = [], []
        for k, v in fields.items():
            if k in allowed and v is not None:
                sets.append(f'{k} = %s')
                vals.append(v)
        if not sets:
            row = db.fetch_one('SELECT 1 FROM class_videos WHERE id = %s', (video_id,))
            return 1 if row else 0
        vals.append(video_id)
        return db.execute(
            f'UPDATE class_videos SET {", ".join(sets)} WHERE id = %s', tuple(vals)
        ) or 0

    @staticmethod
    def delete(video_id: int) -> bool:
        return db.execute('DELETE FROM class_videos WHERE id = %s', (video_id,)) > 0

    @staticmethod
    def get_by_id(video_id: int):
        return db.fetch_one(
            """SELECT cv.*, u.full_name AS ten_gv, co.ten_mon
                 FROM class_videos cv
                 JOIN classes c ON c.ma_lop = cv.lop_id
                 JOIN courses co ON co.ma_mon = c.ma_mon
                 JOIN users u ON u.id = cv.gv_id
                WHERE cv.id = %s""",
            (video_id,)
        )

    @staticmethod
    def get_by_class(lop_id: str):
        """List tat ca video cua 1 lop - HV xem khi vao trang lop hoc."""
        sql = """
            SELECT cv.id, cv.tieu_de, cv.video_url, cv.mo_ta, cv.buoi_so,
                   cv.created_at, u.full_name AS ten_gv
              FROM class_videos cv
              JOIN users u ON u.id = cv.gv_id
             WHERE cv.lop_id = %s
             ORDER BY cv.buoi_so NULLS LAST, cv.created_at DESC
        """
        return db.fetch_all(sql, (lop_id,))

    @staticmethod
    def get_by_teacher(gv_id: int):
        """Tat ca video GV da upload (tat ca lop) - cho trang quan ly GV."""
        sql = """
            SELECT cv.id, cv.lop_id, cv.tieu_de, cv.video_url, cv.mo_ta,
                   cv.buoi_so, cv.created_at, co.ten_mon
              FROM class_videos cv
              JOIN classes c ON c.ma_lop = cv.lop_id
              JOIN courses co ON co.ma_mon = c.ma_mon
             WHERE cv.gv_id = %s
             ORDER BY cv.created_at DESC
        """
        return db.fetch_all(sql, (gv_id,))

    @staticmethod
    def get_for_student(hv_id: int, lop_id: str = None):
        """HV xem video cua cac lop minh dang ky (paid/completed).
        Neu pass lop_id thi filter chi 1 lop. Khong thi tra all lop HV dang ky."""
        if lop_id:
            sql = """
                SELECT cv.id, cv.lop_id, cv.tieu_de, cv.video_url, cv.mo_ta,
                       cv.buoi_so, cv.created_at, u.full_name AS ten_gv, co.ten_mon
                  FROM class_videos cv
                  JOIN classes c ON c.ma_lop = cv.lop_id
                  JOIN courses co ON co.ma_mon = c.ma_mon
                  JOIN users u ON u.id = cv.gv_id
                  JOIN registrations r ON r.lop_id = cv.lop_id
                                      AND r.hv_id = %s
                                      AND r.trang_thai IN ('paid', 'completed')
                 WHERE cv.lop_id = %s
                 ORDER BY cv.buoi_so NULLS LAST, cv.created_at DESC
            """
            return db.fetch_all(sql, (hv_id, lop_id))
        sql = """
            SELECT cv.id, cv.lop_id, cv.tieu_de, cv.video_url, cv.mo_ta,
                   cv.buoi_so, cv.created_at, u.full_name AS ten_gv, co.ten_mon
              FROM class_videos cv
              JOIN classes c ON c.ma_lop = cv.lop_id
              JOIN courses co ON co.ma_mon = c.ma_mon
              JOIN users u ON u.id = cv.gv_id
              JOIN registrations r ON r.lop_id = cv.lop_id
                                  AND r.hv_id = %s
                                  AND r.trang_thai IN ('paid', 'completed')
             ORDER BY cv.lop_id, cv.buoi_so NULLS LAST, cv.created_at DESC
        """
        return db.fetch_all(sql, (hv_id,))
