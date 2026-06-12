from typing import Any

from ..core import DatabaseCore
from ..repositories import FieldRepository

class FieldService:
    def __init__(
        self,
        core: DatabaseCore,
        fields: FieldRepository,
    ) -> None:
        self._core = core
        self._fields = fields

    def create(self, **kwargs):
        with self._core.session_scope() as session:
            return self._fields.create(session, **kwargs)

    def update(self, field_id: int, updates: dict[str, Any]):
        with self._core.session_scope() as session:
            updated_field, _ = self._fields.update(session, field_id, updates)
            return updated_field

    def delete(self, field_id: int) -> bool:
        with self._core.session_scope() as session:
            return self._fields.delete(session, field_id)
