from abc import ABC, abstractmethod


class User(ABC):
    """Lop co so truu tuong cho moi nguoi dung.
    Ap dung OOP: encapsulation (private attr + property), abstract class,
    va polymorphism (lop con phai override get_display_role).
    """

    def __init__(self, id, username, role, full_name,
                 email=None, sdt=None, is_active=True):
        self._id = id
        self._username = username
        self._role = role
        self._full_name = full_name
        self._email = email
        self._sdt = sdt
        self._is_active = is_active

    # ---- encapsulation: expose qua property ----
    @property
    def id(self): return self._id

    @property
    def username(self): return self._username

    @property
    def role(self): return self._role

    @property
    def full_name(self): return self._full_name

    @property
    def email(self): return self._email

    @property
    def sdt(self): return self._sdt

    @property
    def is_active(self): return self._is_active

    @property
    def initials(self) -> str:
        """lay 2 chu cai dau tu ho ten de hien avatar.
        vd: 'Dao Viet Quang Huy' -> 'QH'"""
        parts = self._full_name.strip().split()
        if len(parts) >= 2:
            return (parts[-2][0] + parts[-1][0]).upper()
        if parts:
            return parts[0][:2].upper()
        return 'NA'

    # ---- polymorphism: moi lop con tu override ----
    @abstractmethod
    def get_display_role(self) -> str:
        """Tra ve ten role de hien thi cho user cuoi"""
        raise NotImplementedError

    def __repr__(self):
        return f'<{self.__class__.__name__} {self._username} ({self._full_name})>'
