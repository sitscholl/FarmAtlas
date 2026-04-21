import logging
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy.exc import IntegrityError

from ..schemas import (
    IrrigationBulkCreate,
    IrrigationBulkResponse,
    IrrigationBulkUpsertResponse,
    IrrigationCreate,
    IrrigationFieldNameUpsert,
    IrrigationRead,
    IrrigationUpdate,
)
from .utils import (
    get_irrigation_event,
    queue_water_balance_refresh,
    raise_write_http_error,
    runtime,
    serialize_irrigation_event,
    validate_field_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["irrigation"])


def get_irrigation_events_for_fields_and_date(field_ids: list[int], target_date: date) -> dict[int, object]:
    if not field_ids:
        return {}

    field_id_set = set(field_ids)
    with runtime.db.session_scope() as session:
        events = [
            event
            for event in runtime.db.irrigation.list(
                session,
                start=target_date,
                end=target_date + timedelta(days=1),
            )
            if event.field_id in field_id_set and event.date == target_date
        ]
    return {event.field_id: event for event in events}


def get_field_by_name(field_name: str):
    with runtime.db.session_scope() as session:
        field = runtime.db.fields.get_by_name(session, field_name)
    if field is None:
        raise HTTPException(status_code=404, detail=f"No field with name '{field_name}' found")
    return field


@router.get("/api/fields/{field_id}/irrigation", response_model=list[IrrigationRead])
async def list_irrigation_events(field_id: int):
    validate_field_id(field_id)
    with runtime.db.session_scope() as session:
        events = runtime.db.irrigation.list(session, field_id=field_id)
    return [serialize_irrigation_event(event) for event in events]


@router.get("/api/irrigation", response_model=list[IrrigationRead])
async def list_all_irrigation_events():
    with runtime.db.session_scope() as session:
        events = runtime.db.irrigation.list(session)
    return [serialize_irrigation_event(event) for event in events]


@router.post("/api/fields/{field_id}/irrigation", response_model=IrrigationRead, status_code=status.HTTP_201_CREATED)
async def create_irrigation_event(background_tasks: BackgroundTasks, field_id: int, irrigation_event: IrrigationCreate):
    validate_field_id(field_id)
    try:
        new_event = runtime.db.irrigation_service.create(
            field_id=field_id,
            date=irrigation_event.date,
            method=irrigation_event.method,
            duration=irrigation_event.duration,
            amount=irrigation_event.amount,
        )
        background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", field_id)
        return serialize_irrigation_event(new_event)
    except Exception as exc:
        logger.exception("Adding irrigation event for field with id %s failed: %s", field_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("No field with id", "Could not find any irrigation event with id"))


@router.post("/api/irrigation/bulk", response_model=IrrigationBulkResponse, status_code=status.HTTP_201_CREATED)
async def create_bulk_irrigation_events(
    background_tasks: BackgroundTasks,
    irrigation_event: IrrigationBulkCreate,
):
    unique_field_ids = sorted(set(irrigation_event.field_ids))
    created_event_ids: list[int] = []
    created_field_ids: list[int] = []
    skipped_field_ids: list[int] = []
    errors_by_field_id: dict[int, str] = {}

    for field_id in unique_field_ids:
        try:
            validate_field_id(field_id)
            new_event = runtime.db.irrigation_service.create(
                field_id=field_id,
                date=irrigation_event.date,
                method=irrigation_event.method,
                duration=irrigation_event.duration,
                amount=irrigation_event.amount,
            )
            created_event_ids.append(new_event.id)
            created_field_ids.append(field_id)
        except Exception as exc:
            logger.exception("Adding irrigation event for field with id %s failed: %s", field_id, exc)
            skipped_field_ids.append(field_id)
            if isinstance(exc, HTTPException):
                errors_by_field_id[field_id] = str(exc.detail)
            elif isinstance(exc, IntegrityError):
                errors_by_field_id[field_id] = "Resource already exists or violates a uniqueness constraint."
            else:
                errors_by_field_id[field_id] = str(exc)

    queue_water_balance_refresh(background_tasks, created_field_ids)

    return IrrigationBulkResponse(
        created_event_ids=created_event_ids,
        created_count=len(created_event_ids),
        skipped_field_ids=skipped_field_ids,
        errors_by_field_id=errors_by_field_id,
    )


@router.post("/api/irrigation/bulk/upsert", response_model=IrrigationBulkUpsertResponse, status_code=status.HTTP_200_OK)
async def upsert_bulk_irrigation_events(
    background_tasks: BackgroundTasks,
    irrigation_event: IrrigationBulkCreate,
):
    unique_field_ids = sorted(set(irrigation_event.field_ids))
    existing_events_by_field_id = get_irrigation_events_for_fields_and_date(unique_field_ids, irrigation_event.date)

    created_event_ids: list[int] = []
    updated_event_ids: list[int] = []
    unchanged_event_ids: list[int] = []
    changed_field_ids: list[int] = []
    skipped_field_ids: list[int] = []
    errors_by_field_id: dict[int, str] = {}

    for field_id in unique_field_ids:
        try:
            field = validate_field_id(field_id)
            existing_event = existing_events_by_field_id.get(field_id)

            if existing_event is None:
                new_event = runtime.db.irrigation_service.create(
                    field_id=field_id,
                    date=irrigation_event.date,
                    method=irrigation_event.method,
                    duration=irrigation_event.duration,
                    amount=irrigation_event.amount,
                )
                created_event_ids.append(new_event.id)
                changed_field_ids.append(field_id)
                continue

            resolved_amount = runtime.db.irrigation_service.resolve_amount(
                field=field,
                method=irrigation_event.method,
                duration=irrigation_event.duration,
                amount=irrigation_event.amount,
            )
            if (
                existing_event.method == irrigation_event.method
                and existing_event.duration == irrigation_event.duration
                and existing_event.amount == resolved_amount
            ):
                unchanged_event_ids.append(existing_event.id)
                continue

            updated_event = runtime.db.irrigation_service.update(
                event_id=existing_event.id,
                updates={
                    "field_id": field_id,
                    "date": irrigation_event.date,
                    "method": irrigation_event.method,
                    "duration": irrigation_event.duration,
                    "amount": irrigation_event.amount,
                },
            )
            updated_event_ids.append(updated_event.id)
            changed_field_ids.append(field_id)
        except Exception as exc:
            logger.exception("Upserting irrigation event for field with id %s failed: %s", field_id, exc)
            skipped_field_ids.append(field_id)
            if isinstance(exc, HTTPException):
                errors_by_field_id[field_id] = str(exc.detail)
            elif isinstance(exc, IntegrityError):
                errors_by_field_id[field_id] = "Resource already exists or violates a uniqueness constraint."
            else:
                errors_by_field_id[field_id] = str(exc)

    queue_water_balance_refresh(background_tasks, changed_field_ids)

    return IrrigationBulkUpsertResponse(
        created_event_ids=created_event_ids,
        updated_event_ids=updated_event_ids,
        unchanged_event_ids=unchanged_event_ids,
        created_count=len(created_event_ids),
        updated_count=len(updated_event_ids),
        unchanged_count=len(unchanged_event_ids),
        skipped_field_ids=skipped_field_ids,
        errors_by_field_id=errors_by_field_id,
    )


@router.post("/api/irrigation/upsert", response_model=IrrigationRead, status_code=status.HTTP_200_OK)
async def upsert_irrigation_event_by_field_name(
    background_tasks: BackgroundTasks,
    irrigation_event: IrrigationFieldNameUpsert,
):
    try:
        field = get_field_by_name(irrigation_event.field)
        existing_event = get_irrigation_events_for_fields_and_date([field.id], irrigation_event.date).get(field.id)

        if existing_event is None:
            event = runtime.db.irrigation_service.create(
                field_id=field.id,
                date=irrigation_event.date,
                method=irrigation_event.method,
                duration=irrigation_event.duration,
                amount=irrigation_event.amount,
            )
        else:
            event = runtime.db.irrigation_service.update(
                event_id=existing_event.id,
                updates={
                    "field_id": field.id,
                    "date": irrigation_event.date,
                    "method": irrigation_event.method,
                    "duration": irrigation_event.duration,
                    "amount": irrigation_event.amount,
                },
            )

        background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", field.id)
        return serialize_irrigation_event(event)
    except Exception as exc:
        logger.exception("Upserting irrigation event for field with name %s failed: %s", irrigation_event.field, exc)
        raise_write_http_error(exc, not_found_prefixes=("No field with name", "Could not find any irrigation event with id"))


@router.put("/api/irrigation/{event_id}", response_model=IrrigationRead)
async def update_irrigation_event(
    background_tasks: BackgroundTasks,
    event_id: int,
    irrigation_event: IrrigationUpdate,
):
    existing_event = get_irrigation_event(event_id)
    validate_field_id(irrigation_event.field_id)
    try:
        updated_event = runtime.db.irrigation_service.update(event_id=event_id, updates=irrigation_event.model_dump())
        background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", updated_event.field_id)
        if existing_event.field_id != updated_event.field_id:
            background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", existing_event.field_id)
        return serialize_irrigation_event(updated_event)
    except Exception as exc:
        logger.exception("Updating irrigation event %s failed: %s", event_id, exc)
        raise_write_http_error(
            exc,
            not_found_prefixes=("No field with id", "Could not find any irrigation event with id"),
        )


@router.delete("/api/irrigation/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_irrigation_event(background_tasks: BackgroundTasks, event_id: int):
    existing_event = get_irrigation_event(event_id)
    deleted, _ = runtime.db.irrigation_service.delete(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any irrigation event with id {event_id}")
    background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", existing_event.field_id)


@router.delete("/api/fields/{field_id}/irrigation", status_code=status.HTTP_204_NO_CONTENT)
async def clear_irrigation_events(field_id: int):
    validate_field_id(field_id)
    try:
        runtime.db.irrigation_service.clear_for_field(field_id)
    except Exception as exc:
        logger.exception("Clearing irrigation events for field with id %s failed: %s", field_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("No field with id",))
