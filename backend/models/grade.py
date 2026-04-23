from datetime import datetime
from .entity import Entity


class Grade(Entity):
    """Diem cua 1 hoc vien o 1 lop"""

    # diem tong ket <= diem rot
    PASS_THRESHOLD = 5.0

    def __init__(self, hv_id: int, lop_id: str,
                 diem_qt: float = None, diem_thi: float = None,
                 tong_ket: float = None, xep_loai: str = None,
                 gv_nhap: int = None, updated_at: datetime = None):
        self._hv_id = hv_id
        self._lop_id = lop_id
        self._diem_qt = diem_qt
        self._diem_thi = diem_thi
        self._tong_ket = tong_ket
        self._xep_loai = xep_loai
        self._gv_nhap = gv_nhap
        self._updated_at = updated_at

    @property
    def hv_id(self): return self._hv_id

    @property
    def lop_id(self): return self._lop_id

    @property
    def diem_qt(self): return self._diem_qt

    @property
    def diem_thi(self): return self._diem_thi

    @property
    def tong_ket(self): return self._tong_ket

    @property
    def xep_loai(self): return self._xep_loai

    @property
    def gv_nhap(self): return self._gv_nhap

    @property
    def is_passing(self) -> bool:
        if self._tong_ket is None:
            return False
        return float(self._tong_ket) >= self.PASS_THRESHOLD

    # ---- business: tinh diem tong ket + xep loai ----
    @staticmethod
    def compute_total(diem_qt: float, diem_thi: float) -> float:
        """Cong thuc: 30% qua trinh + 70% thi"""
        return round(float(diem_qt) * 0.3 + float(diem_thi) * 0.7, 2)

    @staticmethod
    def compute_letter(tong_ket: float) -> str:
        """Chuyen diem 10 sang A+/A/B+/.../F"""
        s = float(tong_ket)
        if s >= 9:   return 'A+'
        if s >= 8.5: return 'A'
        if s >= 8:   return 'B+'
        if s >= 7:   return 'B'
        if s >= 6.5: return 'C+'
        if s >= 5.5: return 'C'
        if s >= 4:   return 'D'
        return 'F'

    def recompute(self):
        """Tinh lai tong_ket + xep_loai khi co diem_qt va diem_thi"""
        if self._diem_qt is not None and self._diem_thi is not None:
            self._tong_ket = Grade.compute_total(self._diem_qt, self._diem_thi)
            self._xep_loai = Grade.compute_letter(self._tong_ket)

    @classmethod
    def from_row(cls, row: dict) -> 'Grade':
        return cls(
            hv_id=row['hv_id'],
            lop_id=row['lop_id'],
            diem_qt=float(row['diem_qt']) if row.get('diem_qt') is not None else None,
            diem_thi=float(row['diem_thi']) if row.get('diem_thi') is not None else None,
            tong_ket=float(row['tong_ket']) if row.get('tong_ket') is not None else None,
            xep_loai=row.get('xep_loai'),
            gv_nhap=row.get('gv_nhap'),
            updated_at=row.get('updated_at'),
        )

    def to_dict(self) -> dict:
        return {
            'hv_id': self._hv_id, 'lop_id': self._lop_id,
            'diem_qt': self._diem_qt, 'diem_thi': self._diem_thi,
            'tong_ket': self._tong_ket, 'xep_loai': self._xep_loai,
            'gv_nhap': self._gv_nhap, 'updated_at': self._updated_at,
        }

    def _key(self):
        return f'HV{self._hv_id}@{self._lop_id} = {self._tong_ket} ({self._xep_loai})'
