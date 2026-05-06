from backend.database.db import db


class AuditService:
    """Nhat ky he thong - tu ghi + truy xuat"""

    @staticmethod
    def get_all(limit: int = 100, user_id: int = None, action: str = None,
                from_date=None, to_date=None):
        sql = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        if user_id is not None:
            sql += " AND user_id = %s"
            params.append(user_id)
        if action:
            sql += " AND action LIKE %s"
            params.append(f'%{action}%')
        if from_date:
            sql += " AND created_at >= %s"
            params.append(from_date)
        if to_date:
            sql += " AND created_at <= %s"
            params.append(to_date)
        sql += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def log(action: str, user_id: int = None, username: str = None,
            role: str = None, target_type: str = None, target_id: str = None,
            description: str = None, ip_address: str = None):
        """Tao manual 1 audit log (ngoai trigger tu dong)"""
        db.execute(
            """INSERT INTO audit_logs
               (user_id, username, role, action, target_type, target_id, description, ip_address)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, username, role, action, target_type, target_id, description, ip_address)
        )

    @staticmethod
    def log_login(user_id: int, username: str, role: str,
                  success: bool = True, ip: str = None):
        action = 'login' if success else 'login_failed'
        desc = 'Dang nhap thanh cong' if success else 'Dang nhap that bai'
        AuditService.log(action, user_id, username, role,
                         description=desc, ip_address=ip)

    @staticmethod
    def purge_old(days: int = 90):
        """Xoa log cu hon X ngay (housekeeping).

        Cast int -> string trong placeholder '%s days' co the gay rui ro
        SQL injection neu days bi bypass type hint (Python runtime khong enforce).
        Dung make_interval(days) - param thuan int, an toan hon.
        """
        days_int = int(days)  # ep kieu de chac chan
        if days_int < 0:
            return
        db.execute(
            "DELETE FROM audit_logs WHERE created_at < CURRENT_DATE - make_interval(days => %s)",
            (days_int,)
        )
