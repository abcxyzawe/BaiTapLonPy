from .entity import Entity


class Course(Entity):
    """Mon hoc trong trung tam"""

    def __init__(self, ma_mon: str, ten_mon: str, mo_ta: str = ''):
        self._ma_mon = ma_mon
        self._ten_mon = ten_mon
        self._mo_ta = mo_ta

    @property
    def ma_mon(self): return self._ma_mon

    @property
    def ten_mon(self): return self._ten_mon

    @property
    def mo_ta(self): return self._mo_ta

    @classmethod
    def from_row(cls, row: dict) -> 'Course':
        return cls(
            ma_mon=row['ma_mon'],
            ten_mon=row['ten_mon'],
            mo_ta=row.get('mo_ta', '') or '',
        )

    def to_dict(self) -> dict:
        return {'ma_mon': self._ma_mon, 'ten_mon': self._ten_mon, 'mo_ta': self._mo_ta}

    def _key(self):
        return f'{self._ma_mon} - {self._ten_mon}'
