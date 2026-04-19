import logging

from fastapi import APIRouter, HTTPException, status

from ..schemas import SectionCreate, SectionRead, SectionUpdate
from .utils import raise_write_http_error, runtime, serialize_section

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sections"])


@router.get("/api/plantings/{planting_id}/sections", response_model=list[SectionRead])
async def list_planting_sections(planting_id: int):
    try:
        with runtime.db.session_scope() as session:
            sections = runtime.db.sections.list_for_planting(session, planting_id)
        return [serialize_section(section) for section in sections]
    except Exception as exc:
        raise_write_http_error(exc, not_found_prefixes=("No planting with id",))


@router.post("/api/sections", response_model=SectionRead, status_code=status.HTTP_201_CREATED)
async def create_section(section: SectionCreate):
    try:
        created = runtime.db.section_service.create(**section.model_dump())
        return serialize_section(created)
    except Exception as exc:
        logger.exception("Creating section failed: %s", exc)
        raise_write_http_error(exc)


@router.get("/api/sections/{section_id}", response_model=SectionRead)
async def get_section(section_id: int):
    with runtime.db.session_scope() as session:
        section = runtime.db.sections.get_by_id(session, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Could not find any section with id {section_id}")
    return serialize_section(section)


@router.put("/api/sections/{section_id}", response_model=SectionRead)
async def update_section(section_id: int, section: SectionUpdate):
    try:
        updated = runtime.db.section_service.update(section_id, section.model_dump())
        return serialize_section(updated)
    except Exception as exc:
        logger.exception("Updating section %s failed: %s", section_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("Could not find any section with id",))


@router.delete("/api/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(section_id: int):
    deleted = runtime.db.section_service.delete(section_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any section with id {section_id}")
