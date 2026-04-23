import logging

from fastapi import APIRouter, HTTPException, status

from ..schemas import (
    PhenologicalStageCreate,
    PhenologicalStageRead,
    PhenologicalStageUpdate,
    PhenologyEventCreate,
    PhenologyEventRead,
    PhenologyEventUpdate,
)
from .utils import (
    raise_write_http_error,
    runtime,
    serialize_phenological_stage,
    serialize_phenology_event,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["phenology"])


@router.get("/api/phenological-stages", response_model=list[PhenologicalStageRead])
async def list_phenological_stages():
    with runtime.db.session_scope() as session:
        stages = runtime.db.phenological_stages.list_all(session)
    return [serialize_phenological_stage(stage) for stage in stages]


@router.post("/api/phenological-stages", response_model=PhenologicalStageRead, status_code=status.HTTP_201_CREATED)
async def create_phenological_stage(stage: PhenologicalStageCreate):
    try:
        created = runtime.db.phenological_stage_service.create(**stage.model_dump())
        return serialize_phenological_stage(created)
    except Exception as exc:
        logger.exception("Creating phenological stage failed: %s", exc)
        raise_write_http_error(exc)


@router.get("/api/phenological-stages/{stage_id}", response_model=PhenologicalStageRead)
async def get_phenological_stage(stage_id: int):
    with runtime.db.session_scope() as session:
        stage = runtime.db.phenological_stages.get_by_id(session, stage_id)
    if stage is None:
        raise HTTPException(status_code=404, detail=f"Could not find any phenological stage with id {stage_id}")
    return serialize_phenological_stage(stage)


@router.put("/api/phenological-stages/{stage_id}", response_model=PhenologicalStageRead)
async def update_phenological_stage(stage_id: int, stage: PhenologicalStageUpdate):
    try:
        updated = runtime.db.phenological_stage_service.update(stage_id, stage.model_dump())
        return serialize_phenological_stage(updated)
    except Exception as exc:
        logger.exception("Updating phenological stage %s failed: %s", stage_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("Could not find any phenological stage with id",))


@router.delete("/api/phenological-stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phenological_stage(stage_id: int):
    deleted = runtime.db.phenological_stage_service.delete(stage_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any phenological stage with id {stage_id}")


@router.get("/api/sections/{section_id}/phenology-events", response_model=list[PhenologyEventRead])
async def list_section_phenology_events(section_id: int):
    try:
        with runtime.db.session_scope() as session:
            events = runtime.db.phenology_events.list_for_section(session, section_id)
        return [serialize_phenology_event(event) for event in events]
    except Exception as exc:
        raise_write_http_error(exc, not_found_prefixes=("No section with id",))


@router.post("/api/phenology-events", response_model=PhenologyEventRead, status_code=status.HTTP_201_CREATED)
async def create_phenology_event(event: PhenologyEventCreate):
    try:
        created = runtime.db.phenology_event_service.create(**event.model_dump())
        return serialize_phenology_event(created)
    except Exception as exc:
        logger.exception("Creating phenology event failed: %s", exc)
        raise_write_http_error(
            exc,
            not_found_prefixes=("No section with id", "No phenological stage with id"),
        )


@router.get("/api/phenology-events/{event_id}", response_model=PhenologyEventRead)
async def get_phenology_event(event_id: int):
    with runtime.db.session_scope() as session:
        event = runtime.db.phenology_events.get_by_id(session, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Could not find any phenology event with id {event_id}")
    return serialize_phenology_event(event)


@router.put("/api/phenology-events/{event_id}", response_model=PhenologyEventRead)
async def update_phenology_event(event_id: int, event: PhenologyEventUpdate):
    try:
        updated = runtime.db.phenology_event_service.update(event_id, event.model_dump())
        return serialize_phenology_event(updated)
    except Exception as exc:
        logger.exception("Updating phenology event %s failed: %s", event_id, exc)
        raise_write_http_error(
            exc,
            not_found_prefixes=(
                "Could not find any phenology event with id",
                "No section with id",
                "No phenological stage with id",
            ),
        )


@router.delete("/api/phenology-events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phenology_event(event_id: int):
    deleted = runtime.db.phenology_event_service.delete(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any phenology event with id {event_id}")
