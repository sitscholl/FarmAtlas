import logging
from typing import Any

from sqlalchemy.orm import Session, selectinload

from .. import models
from .varieties import VarietyRepository

logger = logging.getLogger(__name__)


class NutrientRequirementRepository:
    UPDATE_ALLOWLIST = {"variety", "nutrient_code", "requirement_per_kg_yield"}

    def __init__(self, variety_repository: VarietyRepository) -> None:
        self._varieties = variety_repository

    def _query(self, session: Session):
        return session.query(models.NutrientRequirement).options(
            selectinload(models.NutrientRequirement.variety),
        )

    def _normalize_optional_variety_name(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        text = str(value).strip()
        return text or None

    def _normalize_nutrient_code(self, value: Any) -> str:
        code = str(value).strip().upper()
        if code == "":
            raise ValueError("Expected a non-empty value for 'nutrient_code'")
        return code

    def _normalize_requirement(self, value: Any) -> float:
        requirement = float(value)
        if requirement <= 0:
            raise ValueError("requirement_per_kg_yield must be greater than 0")
        return requirement

    def _resolve_variety_id(self, session: Session, variety_name: Any) -> int | None:
        normalized_name = self._normalize_optional_variety_name(variety_name)
        if normalized_name is None:
            return None

        variety = self._varieties.get_by_name(session, normalized_name)
        if variety is None:
            raise ValueError(
                f"Unknown variety '{normalized_name}'. Create the variety master data before adding nutrient requirements."
            )
        return variety.id

    def get_by_id(self, session: Session, nutrient_id: int) -> models.NutrientRequirement | None:
        return self._query(session).filter(models.NutrientRequirement.id == nutrient_id).one_or_none()

    def list_all(self, session: Session) -> list[models.NutrientRequirement]:
        return (
            self._query(session)
            .outerjoin(models.NutrientRequirement.variety)
            .order_by(models.NutrientRequirement.nutrient_code, models.Variety.name, models.NutrientRequirement.id)
            .all()
        )

    def create(
        self,
        session: Session,
        *,
        variety: str | None = None,
        nutrient_code: str,
        requirement_per_kg_yield: float,
    ) -> models.NutrientRequirement:
        nutrient_requirement = models.NutrientRequirement(
            variety_id=self._resolve_variety_id(session, variety),
            nutrient_code=self._normalize_nutrient_code(nutrient_code),
            requirement_per_kg_yield=self._normalize_requirement(requirement_per_kg_yield),
        )
        session.add(nutrient_requirement)
        session.flush()
        logger.debug("Added new nutrient requirement %s", nutrient_requirement)
        return self.get_by_id(session, nutrient_requirement.id) or nutrient_requirement

    def update(
        self,
        session: Session,
        nutrient_id: int,
        updates: dict[str, Any],
    ) -> tuple[models.NutrientRequirement, set[str]]:
        nutrient_requirement = self.get_by_id(session, nutrient_id)
        if nutrient_requirement is None:
            raise ValueError(f"Could not find any nutrient requirement with id {nutrient_id}")

        changed_keys: set[str] = set()
        for field_key, raw_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(
                    f"Invalid key {field_key} in update_nutrient_requirement. Choose one of {self.UPDATE_ALLOWLIST}"
                )

            if field_key == "variety":
                new_value = self._resolve_variety_id(session, raw_value)
                attr_name = "variety_id"
            elif field_key == "nutrient_code":
                new_value = self._normalize_nutrient_code(raw_value)
                attr_name = field_key
            elif field_key == "requirement_per_kg_yield":
                new_value = self._normalize_requirement(raw_value)
                attr_name = field_key
            else:
                raise ValueError(
                    f"Invalid key {field_key} in update_nutrient_requirement. Choose one of {self.UPDATE_ALLOWLIST}"
                )

            if getattr(nutrient_requirement, attr_name) != new_value:
                setattr(nutrient_requirement, attr_name, new_value)
                changed_keys.add(field_key)

        if not changed_keys:
            return nutrient_requirement, changed_keys

        session.flush()
        return self.get_by_id(session, nutrient_id) or nutrient_requirement, changed_keys

    def delete(self, session: Session, nutrient_id: int) -> bool:
        nutrient_requirement = self.get_by_id(session, nutrient_id)
        if nutrient_requirement is None:
            return False
        session.delete(nutrient_requirement)
        session.flush()
        return True
