from datetime import datetime
from .entity import Entity


class Notification(Entity):
    """Thong bao gui tu admin/GV"""

    LOAI_INFO = 'info'
    LOAI_WARNING = 'warning'
    LOAI_URGENT = 'urgent'

    def __init__(self, id: int, tu_id: int = None, den_lop: str = None,
                 tieu_de: str = '', noi_dung: str = '',
                 loai: str = 'info', ngay_tao: datetime = None):
        self._id = id
        self._tu_id = tu_id
        self._den_lop = den_lop
        self._tieu_de = tieu_de
        self._noi_dung = noi_dung
        self._loai = loai
        self._ngay_tao = ngay_tao

    @property
    def id(self): return self._id

    @property
    def tu_id(self): return self._tu_id

    @property
    def den_lop(self): return self._den_lop

    @property
    def tieu_de(self): return self._tieu_de

    @property
    def noi_dung(self): return self._noi_dung

    @property
    def loai(self): return self._loai

    @property
    def ngay_tao(self): return self._ngay_tao

    @property
    def is_urgent(self) -> bool:
        return self._loai == self.LOAI_URGENT

    @property
    def is_broadcast(self) -> bool:
        """Gui cho tat ca (khong chi dinh lop)"""
        return self._den_lop is None

    @classmethod
    def from_row(cls, row: dict) -> 'Notification':
        return cls(
            id=row['id'],
            tu_id=row.get('tu_id'),
            den_lop=row.get('den_lop'),
            tieu_de=row.get('tieu_de', '') or '',
            noi_dung=row.get('noi_dung', '') or '',
            loai=row.get('loai', 'info'),
            ngay_tao=row.get('ngay_tao'),
        )

    def to_dict(self) -> dict:
        return {
            'id': self._id, 'tu_id': self._tu_id, 'den_lop': self._den_lop,
            'tieu_de': self._tieu_de, 'noi_dung': self._noi_dung,
            'loai': self._loai, 'ngay_tao': self._ngay_tao,
        }

    def _key(self):
        target = self._den_lop or 'all'
        return f'#{self._id} [{self._loai}] → {target}'
