from datetime import datetime
from .entity import Entity


class Review(Entity):
    """HV danh gia GV theo lop"""

    def __init__(self, id: int, hv_id: int, gv_id: int,
                 lop_id: str = None, diem: int = 5,
                 nhan_xet: str = None, ngay: datetime = None):
        self._id = id
        self._hv_id = hv_id
        self._gv_id = gv_id
        self._lop_id = lop_id
        if not (1 <= int(diem) <= 5):
            raise ValueError(f'Diem danh gia phai tu 1-5, nhan duoc {diem}')
        self._diem = int(diem)
        self._nhan_xet = nhan_xet
        self._ngay = ngay

    @property
    def id(self): return self._id

    @property
    def hv_id(self): return self._hv_id

    @property
    def gv_id(self): return self._gv_id

    @property
    def lop_id(self): return self._lop_id

    @property
    def diem(self): return self._diem

    @property
    def nhan_xet(self): return self._nhan_xet

    @property
    def ngay(self): return self._ngay

    @property
    def stars(self) -> str:
        """Hien thi kieu ⭐⭐⭐⭐⭐"""
        return '⭐' * self._diem + '☆' * (5 - self._diem)

    @classmethod
    def from_row(cls, row: dict) -> 'Review':
        return cls(
            id=row['id'],
            hv_id=row['hv_id'],
            gv_id=row['gv_id'],
            lop_id=row.get('lop_id'),
            diem=int(row['diem']),
            nhan_xet=row.get('nhan_xet'),
            ngay=row.get('ngay'),
        )

    def to_dict(self) -> dict:
        return {
            'id': self._id, 'hv_id': self._hv_id, 'gv_id': self._gv_id,
            'lop_id': self._lop_id, 'diem': self._diem,
            'nhan_xet': self._nhan_xet, 'ngay': self._ngay,
        }

    def _key(self):
        return f'#{self._id} HV{self._hv_id}→GV{self._gv_id} {self._diem}/5'
