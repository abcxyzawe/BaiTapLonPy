from datetime import date, time, datetime
from .entity import Entity


class Schedule(Entity):
    """Lich hoc 1 buoi cu the cua 1 lop"""

    STATUS_SCHEDULED = 'scheduled'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_POSTPONED = 'postponed'

    def __init__(self, id: int, lop_id: str, ngay: date,
                 thu: int = None, gio_bat_dau: time = None,
                 gio_ket_thuc: time = None, phong: str = '',
                 buoi_so: int = None, noi_dung: str = '',
                 trang_thai: str = 'scheduled', ghi_chu: str = None):
        self._id = id
        self._lop_id = lop_id
        self._ngay = ngay
        self._thu = thu
        self._gio_bat_dau = gio_bat_dau
        self._gio_ket_thuc = gio_ket_thuc
        self._phong = phong
        self._buoi_so = buoi_so
        self._noi_dung = noi_dung
        self._trang_thai = trang_thai
        self._ghi_chu = ghi_chu

    @property
    def id(self): return self._id

    @property
    def lop_id(self): return self._lop_id

    @property
    def ngay(self): return self._ngay

    @property
    def thu(self): return self._thu

    @property
    def gio_bat_dau(self): return self._gio_bat_dau

    @property
    def gio_ket_thuc(self): return self._gio_ket_thuc

    @property
    def phong(self): return self._phong

    @property
    def buoi_so(self): return self._buoi_so

    @property
    def noi_dung(self): return self._noi_dung

    @property
    def trang_thai(self): return self._trang_thai

    @property
    def is_past(self) -> bool:
        if not self._ngay:
            return False
        return self._ngay < date.today()

    @property
    def is_today(self) -> bool:
        if not self._ngay:
            return False
        return self._ngay == date.today()

    @property
    def duration_minutes(self) -> int:
        if not self._gio_bat_dau or not self._gio_ket_thuc:
            return 0
        bd = datetime.combine(date.today(), self._gio_bat_dau)
        kt = datetime.combine(date.today(), self._gio_ket_thuc)
        return int((kt - bd).total_seconds() / 60)

    @classmethod
    def from_row(cls, row: dict) -> 'Schedule':
        return cls(
            id=row['id'],
            lop_id=row['lop_id'],
            ngay=row['ngay'],
            thu=row.get('thu'),
            gio_bat_dau=row.get('gio_bat_dau'),
            gio_ket_thuc=row.get('gio_ket_thuc'),
            phong=row.get('phong', '') or '',
            buoi_so=row.get('buoi_so'),
            noi_dung=row.get('noi_dung', '') or '',
            trang_thai=row.get('trang_thai', 'scheduled'),
            ghi_chu=row.get('ghi_chu'),
        )

    def to_dict(self) -> dict:
        return {
            'id': self._id, 'lop_id': self._lop_id, 'ngay': self._ngay,
            'thu': self._thu, 'gio_bat_dau': self._gio_bat_dau,
            'gio_ket_thuc': self._gio_ket_thuc, 'phong': self._phong,
            'buoi_so': self._buoi_so, 'noi_dung': self._noi_dung,
            'trang_thai': self._trang_thai, 'ghi_chu': self._ghi_chu,
        }

    def _key(self):
        return f'#{self._id} {self._lop_id} {self._ngay} buoi {self._buoi_so}'
