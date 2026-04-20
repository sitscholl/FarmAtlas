import logging

from fastapi import APIRouter, HTTPException, status

from ..schemas import NutrientRequirementCreate, NutrientRequirementRead, NutrientRequirementUpdate
from .utils import raise_write_http_error, runtime, serialize_nutrient_requirement

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nutrients", tags=["nutrients"])


@router.get("", response_model=list[NutrientRequirementRead])
async def list_nutrient_requirements():
    with runtime.db.session_scope() as session:
        nutrient_requirements = runtime.db.nutrients.list_all(session)
    return [serialize_nutrient_requirement(item) for item in nutrient_requirements]


@router.post("", response_model=NutrientRequirementRead, status_code=status.HTTP_201_CREATED)
async def create_nutrient_requirement(nutrient_requirement: NutrientRequirementCreate):
    try:
        created = runtime.db.nutrient_service.create(**nutrient_requirement.model_dump())
        return serialize_nutrient_requirement(created)
    except Exception as exc:
        logger.exception("Creating nutrient requirement failed: %s", exc)
        raise_write_http_error(exc)


@router.get("/{nutrient_id}", response_model=NutrientRequirementRead)
async def get_nutrient_requirement(nutrient_id: int):
    with runtime.db.session_scope() as session:
        nutrient_requirement = runtime.db.nutrients.get_by_id(session, nutrient_id)
    if nutrient_requirement is None:
        raise HTTPException(status_code=404, detail=f"Could not find any nutrient requirement with id {nutrient_id}")
    return serialize_nutrient_requirement(nutrient_requirement)


@router.put("/{nutrient_id}", response_model=NutrientRequirementRead)
async def update_nutrient_requirement(nutrient_id: int, nutrient_requirement: NutrientRequirementUpdate):
    try:
        updated = runtime.db.nutrient_service.update(nutrient_id, nutrient_requirement.model_dump())
        return serialize_nutrient_requirement(updated)
    except Exception as exc:
        logger.exception("Updating nutrient requirement %s failed: %s", nutrient_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("Could not find any nutrient requirement with id",))


@router.delete("/{nutrient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nutrient_requirement(nutrient_id: int):
    deleted = runtime.db.nutrient_service.delete(nutrient_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any nutrient requirement with id {nutrient_id}")
