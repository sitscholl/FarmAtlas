import asyncio
import logging

from fastapi import APIRouter, Body, HTTPException, status

from ..schemas import (
    TreatmentCsvImportResponse,
    TreatmentEventRead,
    TreatmentImportRead,
    TreatmentSectionAliasCreate,
    TreatmentSectionAliasRead,
    TreatmentSectionAliasUpdate,
    TreatmentSmartFarmerSyncResponse,
    TreatmentSmartFarmerSyncResult,
)
from .utils import raise_write_http_error, runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/treatments", tags=["treatments"])


@router.get("", response_model=list[TreatmentEventRead])
async def list_treatment_events(
    source: str | None = None,
    season_year: int | None = None,
    section_id: int | None = None,
    resolution_status: str | None = None,
    limit: int | None = None,
):
    if limit is not None and limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be greater than 0")
    with runtime.db.session_scope() as session:
        events = runtime.db.treatments.list_events(
            session,
            source=source,
            season_year=season_year,
            section_id=section_id,
            resolution_status=resolution_status,
            limit=limit,
        )
    return [TreatmentEventRead.model_validate(event) for event in events]


@router.get("/imports", response_model=list[TreatmentImportRead])
async def list_treatment_imports(source: str | None = None, season_year: int | None = None):
    with runtime.db.session_scope() as session:
        imports = runtime.db.treatments.list_imports(session, source=source, season_year=season_year)
    return [TreatmentImportRead.model_validate(item) for item in imports]


@router.post("/import-csv", response_model=TreatmentCsvImportResponse, status_code=status.HTTP_201_CREATED)
async def import_treatment_csv(
    season_year: int,
    source: str = "legal_export",
    csv_text: str = Body(..., media_type="text/csv"),
):
    try:
        import_summary = runtime.db.treatment_import_service.import_full_season_csv(
            csv_text=csv_text,
            season_year=season_year,
            source=source,
        )
        with runtime.db.session_scope() as session:
            unresolved_names = runtime.db.treatments.unresolved_external_section_names(
                session,
                source=source,
                season_year=season_year,
            )
        return TreatmentCsvImportResponse(
            import_summary=TreatmentImportRead.model_validate(import_summary),
            unresolved_external_section_names=unresolved_names,
        )
    except Exception as exc:
        logger.exception("Importing treatment CSV failed: %s", exc)
        raise_write_http_error(exc)


@router.post("/sync-smartfarmer", response_model=TreatmentSmartFarmerSyncResponse)
async def sync_smartfarmer_treatments():
    workflow_config = runtime.config.get("workflows", {}).get("fetch_treatment_data", {})
    run_kwargs = dict(workflow_config.get("run") or {})
    try:
        workflow_results = await asyncio.to_thread(
            runtime.run_workflow,
            "fetch_treatment_data",
            **run_kwargs,
        )
    except Exception as exc:
        logger.exception("Smart Farmer treatment sync failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc) or "Smart Farmer treatment sync failed.") from exc

    results = [
        TreatmentSmartFarmerSyncResult(
            workflow_name=result.workflow_name,
            source=result.source,
            season_year=result.season_year,
            status=result.status,
            row_count=result.row_count,
            unresolved_count=result.unresolved_count,
            error=result.error,
            metadata=result.metadata,
        )
        for result in workflow_results
    ]
    failed = [result for result in results if result.status == "failed"]
    warnings = [result for result in results if result.status == "warning"]

    if failed:
        message = "Smart Farmer sync failed: " + " | ".join(
            result.error or f"{result.source}/{result.season_year} failed"
            for result in failed
        )
        status_text = "failed"
    elif warnings:
        unresolved_count = sum(result.unresolved_count for result in warnings)
        message = f"Smart Farmer sync completed with {unresolved_count} unresolved section mapping(s)."
        status_text = "warning"
    else:
        row_count = sum(result.row_count for result in results)
        message = f"Smart Farmer sync completed. Imported {row_count} treatment row(s)."
        status_text = "success"

    return TreatmentSmartFarmerSyncResponse(
        status=status_text,
        message=message,
        results=results,
    )


@router.get("/products", response_model=list[str])
async def list_treatment_product_names(source: str | None = None):
    with runtime.db.session_scope() as session:
        return runtime.db.treatments.distinct_product_names(session, source=source)


@router.get("/unresolved-sections", response_model=list[str])
async def list_unresolved_treatment_sections(source: str | None = None, season_year: int | None = None):
    with runtime.db.session_scope() as session:
        return runtime.db.treatments.unresolved_external_section_names(
            session,
            source=source,
            season_year=season_year,
        )


@router.get("/section-aliases", response_model=list[TreatmentSectionAliasRead])
async def list_treatment_section_aliases(source: str | None = None):
    with runtime.db.session_scope() as session:
        aliases = runtime.db.treatments.list_aliases(session, source=source)
    return [TreatmentSectionAliasRead.model_validate(alias) for alias in aliases]


@router.post(
    "/section-aliases",
    response_model=TreatmentSectionAliasRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_treatment_section_alias(alias: TreatmentSectionAliasCreate):
    try:
        created = runtime.db.treatment_import_service.create_alias(**alias.model_dump())
        return TreatmentSectionAliasRead.model_validate(created)
    except Exception as exc:
        logger.exception("Creating treatment section alias failed: %s", exc)
        raise_write_http_error(exc, not_found_prefixes=("No section with id",))


@router.put("/section-aliases/{alias_id}", response_model=TreatmentSectionAliasRead)
async def update_treatment_section_alias(alias_id: int, alias: TreatmentSectionAliasUpdate):
    try:
        updated = runtime.db.treatment_import_service.update_alias(alias_id, **alias.model_dump())
        return TreatmentSectionAliasRead.model_validate(updated)
    except Exception as exc:
        logger.exception("Updating treatment section alias %s failed: %s", alias_id, exc)
        raise_write_http_error(
            exc,
            not_found_prefixes=("No section with id", "Could not find any treatment section alias with id"),
        )


@router.delete("/section-aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_treatment_section_alias(alias_id: int):
    try:
        deleted = runtime.db.treatment_import_service.delete_alias(alias_id)
    except Exception as exc:
        logger.exception("Deleting treatment section alias %s failed: %s", alias_id, exc)
        raise_write_http_error(exc)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any treatment section alias with id {alias_id}")
