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
        """Cap nhat partial - return rowcount, 0 = khong ton tai."""
        allowed = {'ma_mon', 'tin_chi', 'loai', 'hoc_ky_de_nghi',
                   'mon_tien_quyet', 'nganh', 'ghi_chu'}
        pairs = []
        values = []
        for k, v in fields.items():
            if k in allowed:
                pairs.append(f'{k} = %s')
                values.append(v)
        if not pairs:
            row = db.fetch_one("SELECT 1 FROM curriculum WHERE id = %s", (cur_id,))
            return 1 if row else 0
        values.append(cur_id)
        return db.execute(f"UPDATE curriculum SET {', '.join(pairs)} WHERE id = %s", tuple(values))

    @staticmethod
    def delete(cur_id: int):
        return db.execute("DELETE FROM curriculum WHERE id = %s", (cur_id,))

    # ===== Cac method nghiep vu - lien ket khung CT voi grades + classes =====
    @staticmethod
    def get_prerequisites(ma_mon: str, nganh: str = 'CNTT') -> list:
        """Lay danh sach mon tien quyet cua 1 mon trong khung CT.
        Tra ve list ma_mon (vd ['IT001', 'MA001']) hoac []"""
        row = db.fetch_one(
            "SELECT mon_tien_quyet FROM curriculum WHERE ma_mon = %s AND nganh = %s",
            (ma_mon, nganh)
        )
        if not row or not row.get('mon_tien_quyet'):
            return []
        return [m.strip() for m in row['mon_tien_quyet'].split(',') if m.strip()]

    @staticmethod
    def check_prerequisites_for_student(hv_id: int, ma_mon: str,
                                         nganh: str = 'CNTT') -> dict:
        """Kiem tra HV co du dieu kien tien quyet de hoc 1 mon khong.
        Tra ve {ok: bool, missing: [ma_mon], passed: [ma_mon]}"""
        required = CurriculumService.get_prerequisites(ma_mon, nganh)
        if not required:
            return {'ok': True, 'missing': [], 'passed': []}

        # Lay cac mon HV da PASS (tong_ket >= 5)
        rows = db.fetch_all(
            """SELECT DISTINCT c.ma_mon
                 FROM grades g
                 JOIN classes c ON c.ma_lop = g.lop_id
                WHERE g.hv_id = %s AND g.tong_ket >= 5""",
            (hv_id,)
        )
        passed_set = {r['ma_mon'] for r in rows}
        missing = [m for m in required if m not in passed_set]
        passed_required = [m for m in required if m in passed_set]
        return {
            'ok': len(missing) == 0,
            'missing': missing,
            'passed': passed_required,
            'required': required,
        }

    @staticmethod
    def get_progress_for_student(hv_id: int, nganh: str = 'CNTT') -> dict:
        """Tinh tien do hoc khung CT cua 1 HV.
        Tra ve {tong_mon, da_pass, da_fail, dang_hoc, chua_hoc, ty_le, chi_tiet}"""
        # Tat ca mon trong khung CT cua nganh
        curr_rows = db.fetch_all(
            """SELECT cu.ma_mon, co.ten_mon, cu.tin_chi, cu.loai, cu.hoc_ky_de_nghi
                 FROM curriculum cu
            LEFT JOIN courses co ON co.ma_mon = cu.ma_mon
                WHERE cu.nganh = %s
                ORDER BY cu.hoc_ky_de_nghi, cu.ma_mon""",
            (nganh,)
        )
        if not curr_rows:
            return {'tong_mon': 0, 'da_pass': 0, 'ty_le': 0, 'chi_tiet': []}

        # Diem cao nhat cua HV cho moi mon (qua cac lop khac nhau)
        grade_rows = db.fetch_all(
            """SELECT c.ma_mon, MAX(g.tong_ket) AS best_score
                 FROM grades g
                 JOIN classes c ON c.ma_lop = g.lop_id
                WHERE g.hv_id = %s
                GROUP BY c.ma_mon""",
            (hv_id,)
        )
        best_by_mon = {r['ma_mon']: float(r['best_score']) if r.get('best_score') else 0
                       for r in grade_rows}

        # Cac mon dang hoc (paid, chua co diem)
        learning_rows = db.fetch_all(
            """SELECT DISTINCT c.ma_mon
                 FROM registrations r
                 JOIN classes c ON c.ma_lop = r.lop_id
            LEFT JOIN grades g ON g.hv_id = r.hv_id AND g.lop_id = r.lop_id
                WHERE r.hv_id = %s AND r.trang_thai = 'paid' AND g.tong_ket IS NULL""",
            (hv_id,)
        )
        learning_set = {r['ma_mon'] for r in learning_rows}

        chi_tiet = []
        da_pass = da_fail = dang_hoc = chua_hoc = 0
        for cur in curr_rows:
            ma = cur['ma_mon']
            score = best_by_mon.get(ma)
            if score is not None and score >= 5:
                trang_thai = 'pass'
                da_pass += 1
            elif score is not None:
                trang_thai = 'fail'
                da_fail += 1
            elif ma in learning_set:
                trang_thai = 'learning'
                dang_hoc += 1
            else:
                trang_thai = 'not_started'
                chua_hoc += 1
            chi_tiet.append({
                'ma_mon': ma,
                'ten_mon': cur.get('ten_mon', ''),
                'tin_chi': cur.get('tin_chi', 3),
                'loai': cur.get('loai', ''),
                'hoc_ky': cur.get('hoc_ky_de_nghi', ''),
                'diem': score,
                'trang_thai': trang_thai,
            })

        tong = len(curr_rows)
        return {
            'tong_mon': tong,
            'da_pass': da_pass,
            'da_fail': da_fail,
            'dang_hoc': dang_hoc,
            'chua_hoc': chua_hoc,
            'ty_le': round(da_pass / tong * 100, 1) if tong else 0,
            'chi_tiet': chi_tiet,
        }
