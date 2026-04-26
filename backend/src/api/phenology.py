import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from ..schemas import (
    PhenologyBulkCreate,
    PhenologyBulkResponse,
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
    get_field_id_for_phenology_event_id,
    get_field_id_for_section_id,
    get_write_error_detail,
    queue_water_balance_refresh,
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
async def create_phenology_event(background_tasks: BackgroundTasks, event: PhenologyEventCreate):
    try:
        created = runtime.db.phenology_event_service.create(**event.model_dump())
        queue_water_balance_refresh(
            background_tasks,
            [field_id for field_id in [get_field_id_for_section_id(created.section_id)] if field_id is not None],
        )
        return serialize_phenology_event(created)
    except Exception as exc:
        logger.exception("Creating phenology event failed: %s", exc)
        raise_write_http_error(
            exc,
            not_found_prefixes=("No section with id", "No phenological stage with code"),
        )


@router.post("/api/phenology-events/bulk", response_model=PhenologyBulkResponse, status_code=status.HTTP_201_CREATED)
async def create_phenology_events_bulk(background_tasks: BackgroundTasks, payload: PhenologyBulkCreate):
    created_event_ids: list[int] = []
    skipped_section_ids: list[int] = []
    errors_by_section_id: dict[int, str] = {}
    successful_section_ids: list[int] = []

    for section_id in sorted(set(payload.section_ids)):
        try:
            created = runtime.db.phenology_event_service.create(
                section_id=section_id,
                stage_code=payload.stage_code,
                date=payload.date,
            )
            created_event_ids.append(created.id)
            successful_section_ids.append(section_id)
        except Exception as exc:
            logger.exception("Creating phenology event for section %s failed: %s", section_id, exc)
            skipped_section_ids.append(section_id)
            errors_by_section_id[section_id] = get_write_error_detail(exc)

    affected_field_ids = [
        field_id
        for field_id in [get_field_id_for_section_id(section_id) for section_id in successful_section_ids]
        if field_id is not None
    ]
    queue_water_balance_refresh(background_tasks, affected_field_ids)

    return PhenologyBulkResponse(
        created_event_ids=created_event_ids,
        created_count=len(created_event_ids),
        skipped_section_ids=skipped_section_ids,
        errors_by_section_id=errors_by_section_id,
    )


@router.get("/api/phenology-events/{event_id}", response_model=PhenologyEventRead)
async def get_phenology_event(event_id: int):
    with runtime.db.session_scope() as session:
        event = runtime.db.phenology_events.get_by_id(session, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Could not find any phenology event with id {event_id}")
    return serialize_phenology_event(event)


@router.put("/api/phenology-events/{event_id}", response_model=PhenologyEventRead)
async def update_phenology_event(background_tasks: BackgroundTasks, event_id: int, event: PhenologyEventUpdate):
    old_field_id = get_field_id_for_phenology_event_id(event_id)
    try:
        updated = runtime.db.phenology_event_service.update(event_id, event.model_dump())
        new_field_id = get_field_id_for_section_id(updated.section_id)
        queue_water_balance_refresh(
            background_tasks,
            [field_id for field_id in [old_field_id, new_field_id] if field_id is not None],
        )
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
async def delete_phenology_event(background_tasks: BackgroundTasks, event_id: int):
    field_id = get_field_id_for_phenology_event_id(event_id)
    deleted = runtime.db.phenology_event_service.delete(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any phenology event with id {event_id}")

    queue_water_balance_refresh(
        background_tasks,
        [field_id] if field_id is not None else [],
    )
