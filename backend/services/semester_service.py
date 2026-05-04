from backend.database.db import db


class SemesterService:
    """CRUD hoc ky"""

    @staticmethod
    def get_all():
        return db.fetch_all(
            "SELECT * FROM semesters ORDER BY bat_dau DESC"
        )

    @staticmethod
    def get_current():
        """Tra ve HK dang mo (status = 'open')"""
        return db.fetch_one(
            "SELECT * FROM semesters WHERE trang_thai = 'open' ORDER BY bat_dau DESC LIMIT 1"
        )

    @staticmethod
    def get(sem_id: str):
        return db.fetch_one("SELECT * FROM semesters WHERE id = %s", (sem_id,))

    @staticmethod
    def create(sem_id: str, ten: str, nam_hoc: str,
               bat_dau, ket_thuc, trang_thai: str = 'closed'):
        db.execute(
            """INSERT INTO semesters (id, ten, nam_hoc, bat_dau, ket_thuc, trang_thai)
                    VALUES (%s, %s, %s, %s, %s, %s)""",
            (sem_id, ten, nam_hoc, bat_dau, ket_thuc, trang_thai)
        )

    @staticmethod
    def set_status(sem_id: str, trang_thai: str):
        """Mo / dong dang ky mot HK. Return rowcount - 0 = sem khong ton tai."""
        return db.execute(
            "UPDATE semesters SET trang_thai = %s WHERE id = %s",
            (trang_thai, sem_id)
        )

    @staticmethod
    def delete(sem_id: str):
        return db.execute("DELETE FROM semesters WHERE id = %s", (sem_id,))
