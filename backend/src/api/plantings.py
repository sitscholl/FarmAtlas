import logging

from fastapi import APIRouter, HTTPException, status

from ..schemas import PlantingCreate, PlantingRead, PlantingUpdate
from .utils import raise_write_http_error, runtime, serialize_planting

logger = logging.getLogger(__name__)

router = APIRouter(tags=["plantings"])


@router.get("/api/fields/{field_id}/plantings", response_model=list[PlantingRead])
async def list_field_plantings(field_id: int):
    try:
        with runtime.db.session_scope() as session:
            plantings = runtime.db.plantings.list_for_field(session, field_id)
        return [serialize_planting(planting) for planting in plantings]
    except Exception as exc:
        raise_write_http_error(exc, not_found_prefixes=("No field with id",))


@router.post("/api/plantings", response_model=PlantingRead, status_code=status.HTTP_201_CREATED)
async def create_planting(planting: PlantingCreate):
    try:
        created = runtime.db.planting_service.create(**planting.model_dump())
        return serialize_planting(created)
    except Exception as exc:
        logger.exception("Creating planting failed: %s", exc)
        raise_write_http_error(exc)


@router.get("/api/plantings/{planting_id}", response_model=PlantingRead)
async def get_planting(planting_id: int):
    with runtime.db.session_scope() as session:
        planting = runtime.db.plantings.get_by_id(session, planting_id)
    if planting is None:
        raise HTTPException(status_code=404, detail=f"Could not find any planting with id {planting_id}")
    return serialize_planting(planting)


@router.put("/api/plantings/{planting_id}", response_model=PlantingRead)
async def update_planting(planting_id: int, planting: PlantingUpdate):
    try:
        updated = runtime.db.planting_service.update(planting_id, planting.model_dump())
        return serialize_planting(updated)
    except Exception as exc:
        logger.exception("Updating planting %s failed: %s", planting_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("Could not find any planting with id",))


@router.delete("/api/plantings/{planting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_planting(planting_id: int):
    deleted = runtime.db.planting_service.delete(planting_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any planting with id {planting_id}")
