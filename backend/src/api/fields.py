import logging

from fastapi import APIRouter, HTTPException, status

from ..schemas import FieldCreate, FieldDetailRead, FieldRead, FieldSummaryRead, WaterBalanceSummary, FieldUpdate
from .utils import (
    get_water_balance_summary_for_field,
    raise_write_http_error,
    runtime,
    serialize_field,
    serialize_field_detail,
    serialize_field_summary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fields", tags=["fields"])


@router.get("", response_model=list[FieldRead])
async def list_fields():
    with runtime.db.session_scope() as session:
        fields = runtime.db.fields.list_all(session)
    return [serialize_field(field) for field in fields]


@router.get("/summary", response_model=list[FieldSummaryRead])
async def list_field_summaries():
    with runtime.db.session_scope() as session:
        fields = runtime.db.fields.list_all(session)
        latest_irrigation_dates = runtime.db.irrigation.get_latest_dates(session, field_ids=[field.id for field in fields])
        water_balance_summaries = {
            summary.field_id: summary
            for summary in [WaterBalanceSummary(**item) for item in runtime.db.water_balance.get_summary(session)]
        }

    return [
        serialize_field_summary(
            field,
            water_balance_summary=water_balance_summaries.get(field.id)
            or WaterBalanceSummary(
                field_id=field.id,
                as_of=None,
                current_water_deficit=None,
                current_soil_water_content=None,
                available_water_storage=None,
                readily_available_water=None,
                below_raw=None,
                safe_ratio=None,
            ),
            last_irrigation_date=latest_irrigation_dates.get(field.id),
        )
        for field in fields
    ]


@router.post("", response_model=FieldRead, status_code=status.HTTP_201_CREATED)
async def create_field(field: FieldCreate):
    try:
        new_field = runtime.db.field_service.create(**field.model_dump())
        return serialize_field(new_field)
    except Exception as exc:
        logger.exception("Adding field failed: %s", exc)
        raise_write_http_error(exc)


@router.get("/{field_id}", response_model=FieldDetailRead)
async def get_field_detail(field_id: int):
    with runtime.db.session_scope() as session:
        field = runtime.db.fields.get_by_id(session, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail=f"Could not find any field with id {field_id}")
    return serialize_field_detail(field)


@router.put("/{field_id}", response_model=FieldRead)
async def update_field(field_id: int, field: FieldUpdate):
    try:
        updated_field = runtime.db.field_service.update(field_id=field_id, updates=field.model_dump())
        return serialize_field(updated_field)
    except Exception as exc:
        logger.exception("Updating field %s failed: %s", field_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("Could not find any field with id",))


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(field_id: int):
    deleted = runtime.db.field_service.delete(field_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any field with id {field_id}")
