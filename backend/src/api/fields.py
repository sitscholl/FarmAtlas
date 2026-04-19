import logging

from fastapi import APIRouter, HTTPException, status

from ..schemas import FieldCreate, FieldDetailRead, FieldRead, FieldUpdate
from .utils import raise_write_http_error, runtime, serialize_field, serialize_field_detail

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fields", tags=["fields"])


@router.get("", response_model=list[FieldRead])
async def list_fields():
    with runtime.db.session_scope() as session:
        fields = runtime.db.fields.list_all(session)
    return [serialize_field(field) for field in fields]


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
