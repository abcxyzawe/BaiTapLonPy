from datetime import datetime
from .entity import Entity


class Payment(Entity):
    """Thanh toan hoc phi cho 1 dang ky (do nhan vien thu tai quay)"""

    HINH_THUC_TIEN_MAT = 'Tien mat'
    HINH_THUC_CHUYEN_KHOAN = 'Chuyen khoan'
    HINH_THUC_VNPAY = 'VNPay'
    HINH_THUC_MOMO = 'Momo'

    def __init__(self, id: int, reg_id: int, so_tien: int,
                 hinh_thuc: str, ngay_thu: datetime = None,
                 nv_thu: int = None, ghi_chu: str = None,
                 so_bien_lai: str = None):
        self._id = id
        self._reg_id = reg_id
        self._so_tien = so_tien
        self._hinh_thuc = hinh_thuc
        self._ngay_thu = ngay_thu
        self._nv_thu = nv_thu
        self._ghi_chu = ghi_chu
        self._so_bien_lai = so_bien_lai

    @property
    def id(self): return self._id

    @property
    def reg_id(self): return self._reg_id

    @property
    def so_tien(self): return self._so_tien

    @property
    def hinh_thuc(self): return self._hinh_thuc

    @property
    def ngay_thu(self): return self._ngay_thu

    @property
    def nv_thu(self): return self._nv_thu

    @property
    def ghi_chu(self): return self._ghi_chu

    @property
    def so_bien_lai(self): return self._so_bien_lai

    def format_amount(self) -> str:
        return f'{int(self._so_tien):,}'.replace(',', '.') + ' đ'

    @classmethod
    def from_row(cls, row: dict) -> 'Payment':
        return cls(
            id=row['id'],
            reg_id=row['reg_id'],
            so_tien=int(row['so_tien']),
            hinh_thuc=row['hinh_thuc'],
            ngay_thu=row.get('ngay_thu'),
            nv_thu=row.get('nv_thu'),
            ghi_chu=row.get('ghi_chu'),
            so_bien_lai=row.get('so_bien_lai'),
        )

    def to_dict(self) -> dict:
        return {
            'id': self._id, 'reg_id': self._reg_id,
            'so_tien': self._so_tien, 'hinh_thuc': self._hinh_thuc,
            'ngay_thu': self._ngay_thu, 'nv_thu': self._nv_thu,
            'ghi_chu': self._ghi_chu, 'so_bien_lai': self._so_bien_lai,
        }

    def _key(self):
        return f'#{self._id} {self.format_amount()} via {self._hinh_thuc}'
