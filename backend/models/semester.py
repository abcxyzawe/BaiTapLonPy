from datetime import date
from .entity import Entity


class Semester(Entity):
    """Hoc ky dao tao"""

    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_UPCOMING = 'upcoming'

    def __init__(self, id: str, ten: str, nam_hoc: str,
                 bat_dau: date, ket_thuc: date,
                 trang_thai: str = 'closed'):
        self._id = id
        self._ten = ten
        self._nam_hoc = nam_hoc
        self._bat_dau = bat_dau
        self._ket_thuc = ket_thuc
        self._trang_thai = trang_thai

    @property
    def id(self): return self._id

    @property
    def ten(self): return self._ten

    @property
    def nam_hoc(self): return self._nam_hoc

    @property
    def bat_dau(self): return self._bat_dau

    @property
    def ket_thuc(self): return self._ket_thuc

    @property
    def trang_thai(self): return self._trang_thai

    @property
    def is_open(self) -> bool:
        return self._trang_thai == self.STATUS_OPEN

    @property
    def duration_days(self) -> int:
        if self._bat_dau and self._ket_thuc:
            return (self._ket_thuc - self._bat_dau).days
        return 0

    @classmethod
    def from_row(cls, row: dict) -> 'Semester':
        return cls(
            id=row['id'],
            ten=row['ten'],
            nam_hoc=row['nam_hoc'],
            bat_dau=row.get('bat_dau'),
            ket_thuc=row.get('ket_thuc'),
            trang_thai=row.get('trang_thai', 'closed'),
        )

    def to_dict(self) -> dict:
        return {
            'id': self._id, 'ten': self._ten, 'nam_hoc': self._nam_hoc,
            'bat_dau': self._bat_dau, 'ket_thuc': self._ket_thuc,
            'trang_thai': self._trang_thai,
        }

    def _key(self):
        return f'{self._id} ({self._trang_thai})'
