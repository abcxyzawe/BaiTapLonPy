from backend.database.db import db


class CurriculumService:
    """CRUD khung chuong trinh dao tao"""

    @staticmethod
    def get_all(nganh: str = None):
        sql = """
            SELECT cu.id, cu.ma_mon, co.ten_mon, cu.tin_chi, cu.loai,
                   cu.hoc_ky_de_nghi, cu.mon_tien_quyet, cu.nganh, cu.ghi_chu
              FROM curriculum cu
         LEFT JOIN courses co ON co.ma_mon = cu.ma_mon
        """
        params = None
        if nganh:
            sql += " WHERE cu.nganh = %s"
            params = (nganh,)
        sql += " ORDER BY cu.hoc_ky_de_nghi, cu.ma_mon"
        return db.fetch_all(sql, params)

    @staticmethod
    def get(cur_id: int):
        return db.fetch_one(
            """SELECT cu.*, co.ten_mon FROM curriculum cu
              LEFT JOIN courses co ON co.ma_mon = cu.ma_mon
              WHERE cu.id = %s""",
            (cur_id,)
        )

    @staticmethod
    def create(ma_mon: str, tin_chi: int, loai: str,
               hoc_ky_de_nghi: str = None, mon_tien_quyet: str = None,
               nganh: str = 'CNTT', ghi_chu: str = None):
        row = db.execute_returning(
            """INSERT INTO curriculum
               (ma_mon, tin_chi, loai, hoc_ky_de_nghi, mon_tien_quyet, nganh, ghi_chu)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (ma_mon, tin_chi, loai, hoc_ky_de_nghi, mon_tien_quyet, nganh, ghi_chu)
        )
        return row['id'] if row else None

    @staticmethod
    def update(cur_id: int, **fields):
        """Cap nhat partial - chi cac field truyen vao"""
        allowed = {'ma_mon', 'tin_chi', 'loai', 'hoc_ky_de_nghi',
                   'mon_tien_quyet', 'nganh', 'ghi_chu'}
        pairs = []
        values = []
        for k, v in fields.items():
            if k in allowed:
                pairs.append(f'{k} = %s')
                values.append(v)
        if not pairs:
            return
        values.append(cur_id)
        db.execute(f"UPDATE curriculum SET {', '.join(pairs)} WHERE id = %s", tuple(values))

    @staticmethod
    def delete(cur_id: int):
        db.execute("DELETE FROM curriculum WHERE id = %s", (cur_id,))
