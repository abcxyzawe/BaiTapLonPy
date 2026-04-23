from .entity import Entity


class Curriculum(Entity):
    """Mon trong khung chuong trinh dao tao cua 1 nganh"""

    LOAI_BAT_BUOC = 'Bat buoc'
    LOAI_TU_CHON = 'Tu chon'
    LOAI_DAI_CUONG = 'Dai cuong'

    def __init__(self, id: int, ma_mon: str, tin_chi: int = 3,
                 loai: str = 'Bat buoc', hoc_ky_de_nghi: str = None,
                 mon_tien_quyet: str = None, nganh: str = 'CNTT',
                 ghi_chu: str = None):
        self._id = id
        self._ma_mon = ma_mon
        self._tin_chi = tin_chi
        self._loai = loai
        self._hoc_ky_de_nghi = hoc_ky_de_nghi
        self._mon_tien_quyet = mon_tien_quyet
        self._nganh = nganh
        self._ghi_chu = ghi_chu

    @property
    def id(self): return self._id

    @property
    def ma_mon(self): return self._ma_mon

    @property
    def tin_chi(self): return self._tin_chi

    @property
    def loai(self): return self._loai

    @property
    def hoc_ky_de_nghi(self): return self._hoc_ky_de_nghi

    @property
    def mon_tien_quyet(self): return self._mon_tien_quyet

    @property
    def nganh(self): return self._nganh

    @property
    def ghi_chu(self): return self._ghi_chu

    @property
    def has_prerequisite(self) -> bool:
        """Co mon tien quyet khong"""
        return bool(self._mon_tien_quyet and self._mon_tien_quyet.strip())

    def get_prerequisites(self) -> list:
        """Parse chuoi mon tien quyet thanh list ma mon"""
        if not self.has_prerequisite:
            return []
        return [m.strip() for m in self._mon_tien_quyet.split(',') if m.strip()]

    @classmethod
    def from_row(cls, row: dict) -> 'Curriculum':
        return cls(
            id=row['id'],
            ma_mon=row['ma_mon'],
            tin_chi=int(row.get('tin_chi') or 3),
            loai=row.get('loai', 'Bat buoc'),
            hoc_ky_de_nghi=row.get('hoc_ky_de_nghi'),
            mon_tien_quyet=row.get('mon_tien_quyet'),
            nganh=row.get('nganh', 'CNTT'),
            ghi_chu=row.get('ghi_chu'),
        )

    def to_dict(self) -> dict:
        return {
            'id': self._id, 'ma_mon': self._ma_mon,
            'tin_chi': self._tin_chi, 'loai': self._loai,
            'hoc_ky_de_nghi': self._hoc_ky_de_nghi,
            'mon_tien_quyet': self._mon_tien_quyet,
            'nganh': self._nganh, 'ghi_chu': self._ghi_chu,
        }

    def _key(self):
        return f'{self._ma_mon}/{self._nganh} ({self._loai})'
