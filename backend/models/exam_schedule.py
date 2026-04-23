from datetime import date, time
from .entity import Entity


class ExamSchedule(Entity):
    """Lich thi cuoi ky cua 1 lop"""

    HINH_THUC_TRAC_NGHIEM = 'Trac nghiem'
    HINH_THUC_TU_LUAN = 'Tu luan'
    HINH_THUC_VAN_DAP = 'Van dap'
    HINH_THUC_THUC_HANH = 'Thuc hanh'

    def __init__(self, id: int, lop_id: str, ngay_thi: date,
                 semester_id: str = None, ca_thi: str = '',
                 gio_bat_dau: time = None, gio_ket_thuc: time = None,
                 phong: str = '', hinh_thuc: str = 'Tu luan',
                 so_cau: int = None, thoi_gian_phut: int = 90,
                 ghi_chu: str = None):
        self._id = id
        self._lop_id = lop_id
        self._ngay_thi = ngay_thi
        self._semester_id = semester_id
        self._ca_thi = ca_thi
        self._gio_bat_dau = gio_bat_dau
        self._gio_ket_thuc = gio_ket_thuc
        self._phong = phong
        self._hinh_thuc = hinh_thuc
        self._so_cau = so_cau
        self._thoi_gian_phut = thoi_gian_phut
        self._ghi_chu = ghi_chu

    @property
    def id(self): return self._id

    @property
    def lop_id(self): return self._lop_id

    @property
    def ngay_thi(self): return self._ngay_thi

    @property
    def semester_id(self): return self._semester_id

    @property
    def ca_thi(self): return self._ca_thi

    @property
    def gio_bat_dau(self): return self._gio_bat_dau

    @property
    def gio_ket_thuc(self): return self._gio_ket_thuc

    @property
    def phong(self): return self._phong

    @property
    def hinh_thuc(self): return self._hinh_thuc

    @property
    def so_cau(self): return self._so_cau

    @property
    def thoi_gian_phut(self): return self._thoi_gian_phut

    @property
    def is_past(self) -> bool:
        if not self._ngay_thi:
            return False
        return self._ngay_thi < date.today()

    @property
    def is_upcoming(self) -> bool:
        if not self._ngay_thi:
            return False
        return self._ngay_thi > date.today()

    @classmethod
    def from_row(cls, row: dict) -> 'ExamSchedule':
        return cls(
            id=row['id'],
            lop_id=row['lop_id'],
            ngay_thi=row['ngay_thi'],
            semester_id=row.get('semester_id'),
            ca_thi=row.get('ca_thi', '') or '',
            gio_bat_dau=row.get('gio_bat_dau'),
            gio_ket_thuc=row.get('gio_ket_thuc'),
            phong=row.get('phong', '') or '',
            hinh_thuc=row.get('hinh_thuc', 'Tu luan'),
            so_cau=row.get('so_cau'),
            thoi_gian_phut=int(row.get('thoi_gian_phut') or 90),
            ghi_chu=row.get('ghi_chu'),
        )

    def to_dict(self) -> dict:
        return {
            'id': self._id, 'lop_id': self._lop_id,
            'ngay_thi': self._ngay_thi, 'semester_id': self._semester_id,
            'ca_thi': self._ca_thi,
            'gio_bat_dau': self._gio_bat_dau, 'gio_ket_thuc': self._gio_ket_thuc,
            'phong': self._phong, 'hinh_thuc': self._hinh_thuc,
            'so_cau': self._so_cau, 'thoi_gian_phut': self._thoi_gian_phut,
            'ghi_chu': self._ghi_chu,
        }

    def _key(self):
        return f'#{self._id} {self._lop_id} @{self._ngay_thi} {self._ca_thi}'
