from datetime import datetime
from .entity import Entity


class AuditLog(Entity):
    """Ban ghi nhat ky he thong - ghi lai moi thao tac quan trong"""

    def __init__(self, id: int, user_id: int = None,
                 username: str = None, role: str = None,
                 action: str = '', target_type: str = None,
                 target_id: str = None, description: str = None,
                 ip_address: str = None, created_at: datetime = None):
        self._id = id
        self._user_id = user_id
        self._username = username
        self._role = role
        self._action = action
        self._target_type = target_type
        self._target_id = target_id
        self._description = description
        self._ip_address = ip_address
        self._created_at = created_at

    @property
    def id(self): return self._id

    @property
    def user_id(self): return self._user_id

    @property
    def username(self): return self._username

    @property
    def role(self): return self._role

    @property
    def action(self): return self._action

    @property
    def target_type(self): return self._target_type

    @property
    def target_id(self): return self._target_id

    @property
    def description(self): return self._description

    @property
    def ip_address(self): return self._ip_address

    @property
    def created_at(self): return self._created_at

    @classmethod
    def from_row(cls, row: dict) -> 'AuditLog':
        return cls(
            id=row['id'],
            user_id=row.get('user_id'),
            username=row.get('username'),
            role=row.get('role'),
            action=row.get('action', '') or '',
            target_type=row.get('target_type'),
            target_id=row.get('target_id'),
            description=row.get('description'),
            ip_address=row.get('ip_address'),
            created_at=row.get('created_at'),
        )

    def to_dict(self) -> dict:
        return {
            'id': self._id, 'user_id': self._user_id,
            'username': self._username, 'role': self._role,
            'action': self._action, 'target_type': self._target_type,
            'target_id': self._target_id, 'description': self._description,
            'ip_address': self._ip_address, 'created_at': self._created_at,
        }

    def _key(self):
        return f'#{self._id} [{self._username}] {self._action}'
