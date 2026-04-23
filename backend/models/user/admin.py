from .base import User


class Admin(User):
    """Quan tri vien - co ma admin rieng"""

    def __init__(self, id, username, full_name, ma_admin='AD001',
                 email=None, sdt=None, is_active=True):
        super().__init__(id, username, 'admin', full_name,
                         email, sdt, is_active)
        self._ma_admin = ma_admin

    @property
    def ma_admin(self): return self._ma_admin

    def get_display_role(self):
        return 'Quản trị viên'
