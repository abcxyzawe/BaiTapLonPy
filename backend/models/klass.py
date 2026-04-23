from datetime import date
from .entity import Entity


class Klass(Entity):
    """Lop hoc cu the cua 1 mon trong 1 hoc ky.
    Dat ten la Klass vi 'class' la keyword cua Python.
    """

    STATUS_OPEN = 'open'
    STATUS_FULL = 'full'
    STATUS_CLOSED = 'closed'

    def __init__(self, ma_lop: str, ma_mon: str, gv_id: int = None,
                 semester_id: str = None, lich: str = '', phong: str = '',
                 siso_max: int = 40, siso_hien_tai: int = 0,
                 gia: int = 0, trang_thai: str = 'open',
                 ngay_bat_dau: date = None, ngay_ket_thuc: date = None,
                 so_buoi: int = 24):
        self._ma_lop = ma_lop
        self._ma_mon = ma_mon
        self._gv_id = gv_id
        self._semester_id = semester_id
        self._lich = lich
        self._phong = phong
        self._siso_max = siso_max
        self._siso_hien_tai = siso_hien_tai
        self._gia = gia
        self._trang_thai = trang_thai
        self._ngay_bat_dau = ngay_bat_dau
        self._ngay_ket_thuc = ngay_ket_thuc
        self._so_buoi = so_buoi

    @property
    def ma_lop(self): return self._ma_lop

    @property
    def ma_mon(self): return self._ma_mon

    @property
    def gv_id(self): return self._gv_id

    @property
    def semester_id(self): return self._semester_id

    @property
    def lich(self): return self._lich

    @property
    def phong(self): return self._phong

    @property
    def siso_max(self): return self._siso_max

    @property
    def siso_hien_tai(self): return self._siso_hien_tai

    @property
    def gia(self): return self._gia

    @property
    def trang_thai(self): return self._trang_thai

    @property
    def ngay_bat_dau(self): return self._ngay_bat_dau

    @property
    def ngay_ket_thuc(self): return self._ngay_ket_thuc

    @property
    def so_buoi(self): return self._so_buoi

    # ---- business methods ----
    @property
    def is_full(self) -> bool:
        return self._siso_hien_tai >= self._siso_max

    @property
    def available_slots(self) -> int:
        return max(0, self._siso_max - self._siso_hien_tai)

    @property
    def fill_percent(self) -> int:
        if not self._siso_max:
            return 0
        return int(self._siso_hien_tai / self._siso_max * 100)

    def format_price(self) -> str:
        """Dinh dang gia hien thi (VND, co dau cham)"""
        return f'{int(self._gia):,}'.replace(',', '.') + ' đ'

    @classmethod
    def from_row(cls, row: dict) -> 'Klass':
        return cls(
            ma_lop=row['ma_lop'],
            ma_mon=row['ma_mon'],
            gv_id=row.get('gv_id'),
            semester_id=row.get('semester_id'),
            lich=row.get('lich', '') or '',
            phong=row.get('phong', '') or '',
            siso_max=int(row.get('siso_max') or 40),
            siso_hien_tai=int(row.get('siso_hien_tai') or 0),
            gia=int(row.get('gia') or 0),
            trang_thai=row.get('trang_thai', 'open'),
            ngay_bat_dau=row.get('ngay_bat_dau'),
            ngay_ket_thuc=row.get('ngay_ket_thuc'),
            so_buoi=int(row.get('so_buoi') or 24),
        )

    def to_dict(self) -> dict:
        return {
            'ma_lop': self._ma_lop, 'ma_mon': self._ma_mon,
            'gv_id': self._gv_id, 'semester_id': self._semester_id,
            'lich': self._lich, 'phong': self._phong,
            'siso_max': self._siso_max, 'siso_hien_tai': self._siso_hien_tai,
            'gia': self._gia, 'trang_thai': self._trang_thai,
            'ngay_bat_dau': self._ngay_bat_dau, 'ngay_ket_thuc': self._ngay_ket_thuc,
            'so_buoi': self._so_buoi,
        }

    def _key(self):
        return f'{self._ma_lop} ({self._siso_hien_tai}/{self._siso_max})'
