from datetime import datetime
from .entity import Entity


class Registration(Entity):
    """Dang ky cua 1 hoc vien vao 1 lop"""

    STATUS_PENDING = 'pending_payment'
    STATUS_PAID = 'paid'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'

    def __init__(self, id: int, hv_id: int, lop_id: str,
                 nv_xu_ly: int = None, ngay_dk: datetime = None,
                 trang_thai: str = 'pending_payment'):
        self._id = id
        self._hv_id = hv_id
        self._lop_id = lop_id
        self._nv_xu_ly = nv_xu_ly
        self._ngay_dk = ngay_dk
        self._trang_thai = trang_thai

    @property
    def id(self): return self._id

    @property
    def hv_id(self): return self._hv_id

    @property
    def lop_id(self): return self._lop_id

    @property
    def nv_xu_ly(self): return self._nv_xu_ly

    @property
    def ngay_dk(self): return self._ngay_dk

    @property
    def trang_thai(self): return self._trang_thai

    @property
    def is_paid(self) -> bool:
        return self._trang_thai == self.STATUS_PAID

    @property
    def is_pending(self) -> bool:
        return self._trang_thai == self.STATUS_PENDING

    @property
    def is_cancelled(self) -> bool:
        return self._trang_thai == self.STATUS_CANCELLED

    @classmethod
    def from_row(cls, row: dict) -> 'Registration':
        return cls(
            id=row['id'],
            hv_id=row['hv_id'],
            lop_id=row['lop_id'],
            nv_xu_ly=row.get('nv_xu_ly'),
            ngay_dk=row.get('ngay_dk'),
            trang_thai=row.get('trang_thai', 'pending_payment'),
        )

    def to_dict(self) -> dict:
        return {
            'id': self._id, 'hv_id': self._hv_id, 'lop_id': self._lop_id,
            'nv_xu_ly': self._nv_xu_ly, 'ngay_dk': self._ngay_dk,
            'trang_thai': self._trang_thai,
        }

    def _key(self):
        return f'#{self._id} HV{self._hv_id}→{self._lop_id} [{self._trang_thai}]'
