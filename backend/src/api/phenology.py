import logging

from fastapi import APIRouter, HTTPException, status

from ..schemas import (
    PhenologyEventCreate,
    PhenologyEventRead,
    PhenologyEventUpdate,
)
from ..domain.phenology import (
    PhenologicalStageDefinition,
    get_phenological_stage as get_stage_definition,
    list_phenological_stages as list_stage_definitions,
)
from .utils import (
    raise_write_http_error,
    runtime,
    serialize_phenology_event,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["phenology"])


@router.get("/api/phenological-stages", response_model=list[PhenologicalStageDefinition])
async def list_phenological_stages():
    return list_stage_definitions()


@router.get("/api/phenological-stages/{stage_code}", response_model=PhenologicalStageDefinition)
async def get_phenological_stage(stage_code: str):
    stage = get_stage_definition(stage_code)
    if stage is None:
        raise HTTPException(status_code=404, detail=f"Could not find any phenological stage with code {stage_code}")
    return stage


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
            not_found_prefixes=("No section with id", "No phenological stage with code"),
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
                "No phenological stage with code",
            ),
        )


@router.delete("/api/phenology-events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phenology_event(event_id: int):
    deleted = runtime.db.phenology_event_service.delete(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any phenology event with id {event_id}")
