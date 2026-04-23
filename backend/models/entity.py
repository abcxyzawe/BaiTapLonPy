from abc import ABC, abstractmethod


class Entity(ABC):
    """Lop co so abstract cho moi domain entity.
    Moi entity phai biet tu build tu 1 dict (row tu DB) va serialize ra dict.
    """

    @classmethod
    @abstractmethod
    def from_row(cls, row: dict) -> 'Entity':
        """Factory method: build entity tu 1 row SELECT cua DB"""
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict:
        """Serialize nguoc lai de ghi DB hoac truyen qua API"""
        raise NotImplementedError

    def __repr__(self):
        return f'<{self.__class__.__name__} {self._key()}>'

    def _key(self) -> str:
        """PK de hien thi khi repr - lop con co the override"""
        return ''
