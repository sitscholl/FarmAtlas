import logging

from fastapi import APIRouter, HTTPException, status

from ..schemas import VarietyCreate, VarietyRead, VarietyUpdate
from .utils import raise_write_http_error, runtime, serialize_variety

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/varieties", tags=["varieties"])


@router.get("", response_model=list[VarietyRead])
async def list_varieties():
    with runtime.db.session_scope() as session:
        varieties = runtime.db.varieties.list_all(session)
    return [serialize_variety(variety) for variety in varieties]


@router.post("", response_model=VarietyRead, status_code=status.HTTP_201_CREATED)
async def create_variety(variety: VarietyCreate):
    try:
        with runtime.db.session_scope() as session:
            new_variety = runtime.db.varieties.create(session, **variety.model_dump())
        return serialize_variety(new_variety)
    except Exception as exc:
        logger.exception("Adding variety failed: %s", exc)
        raise_write_http_error(exc)


@router.put("/{variety_id}", response_model=VarietyRead)
async def update_variety(variety_id: int, variety: VarietyUpdate):
    try:
        with runtime.db.session_scope() as session:
            updated_variety = runtime.db.varieties.update(session, variety_id, **variety.model_dump())
        if updated_variety is None:
            raise HTTPException(status_code=404, detail=f"Could not find any variety with id {variety_id}")
        return serialize_variety(updated_variety)
    except Exception as exc:
        logger.exception("Updating variety %s failed: %s", variety_id, exc)
        raise_write_http_error(exc)


@router.delete("/{variety_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variety(variety_id: int):
    try:
        with runtime.db.session_scope() as session:
            deleted = runtime.db.varieties.delete(session, variety_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Could not find any variety with id {variety_id}")
    except Exception as exc:
        logger.exception("Deleting variety %s failed: %s", variety_id, exc)
        raise_write_http_error(exc)
