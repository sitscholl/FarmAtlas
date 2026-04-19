from typing import Any

from .. import models
from ..core import DatabaseCore
from ..repositories import SectionRepository


class SectionService:
    def __init__(
        self,
        core: DatabaseCore,
        sections: SectionRepository,
    ) -> None:
        self._core = core
        self._sections = sections

    def create(self, **kwargs) -> models.Section:
        with self._core.session_scope() as session:
            return self._sections.create(session, **kwargs)

    def update(self, section_id: int, updates: dict[str, Any]) -> models.Section:
        with self._core.session_scope() as session:
            updated_section, _ = self._sections.update(session, section_id, updates)
            return updated_section

    def delete(self, section_id: int) -> bool:
        with self._core.session_scope() as session:
            return self._sections.delete(session, section_id)
