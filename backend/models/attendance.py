from datetime import time, datetime
from .entity import Entity


class Attendance(Entity):
    """Ban ghi diem danh 1 HV o 1 buoi hoc"""

    STATUS_PRESENT = 'present'
    STATUS_ABSENT = 'absent'
    STATUS_LATE = 'late'
    STATUS_EXCUSED = 'excused'

    def __init__(self, id: int, schedule_id: int, hv_id: int,
                 trang_thai: str = 'present', gio_vao: time = None,
                 ghi_chu: str = None, recorded_at: datetime = None,
                 recorded_by: int = None):
        self._id = id
        self._schedule_id = schedule_id
        self._hv_id = hv_id
        self._trang_thai = trang_thai
        self._gio_vao = gio_vao
        self._ghi_chu = ghi_chu
        self._recorded_at = recorded_at
        self._recorded_by = recorded_by

    @property
    def id(self): return self._id

    @property
    def schedule_id(self): return self._schedule_id

    @property
    def hv_id(self): return self._hv_id

    @property
    def trang_thai(self): return self._trang_thai

    @property
    def gio_vao(self): return self._gio_vao

    @property
    def ghi_chu(self): return self._ghi_chu

    @property
    def recorded_at(self): return self._recorded_at

    @property
    def recorded_by(self): return self._recorded_by

    @property
    def is_present(self) -> bool:
        return self._trang_thai in (self.STATUS_PRESENT, self.STATUS_LATE)

    @property
    def is_late(self) -> bool:
        return self._trang_thai == self.STATUS_LATE

    @property
    def is_absent(self) -> bool:
        return self._trang_thai == self.STATUS_ABSENT

    @classmethod
    def from_row(cls, row: dict) -> 'Attendance':
        return cls(
            id=row['id'],
            schedule_id=row['schedule_id'],
            hv_id=row['hv_id'],
            trang_thai=row.get('trang_thai', 'present'),
            gio_vao=row.get('gio_vao'),
            ghi_chu=row.get('ghi_chu'),
            recorded_at=row.get('recorded_at'),
            recorded_by=row.get('recorded_by'),
        )

    def to_dict(self) -> dict:
        return {
            'id': self._id, 'schedule_id': self._schedule_id,
            'hv_id': self._hv_id, 'trang_thai': self._trang_thai,
            'gio_vao': self._gio_vao, 'ghi_chu': self._ghi_chu,
            'recorded_at': self._recorded_at, 'recorded_by': self._recorded_by,
        }

    def _key(self):
        return f'HV{self._hv_id}@sch{self._schedule_id}={self._trang_thai}'
