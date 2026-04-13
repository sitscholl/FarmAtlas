from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
from sqlalchemy.exc import IntegrityError

from .schemas import (
    FieldCreate,
    FieldOverview,
    FieldReplant,
    FieldRead,
    FieldUpdate,
    FieldWaterBalanceSummary,
    IrrigationCreate,
    IrrigationRead,
    IrrigationUpdate,
    VarietyCreate,
    VarietyRead,
    WaterBalanceSeriesPoint,
    WaterBalanceSummary,
    IrrigationCommandCreate,
    IrrigationTarget,
    IrrigationCommandResult
)
from .runtime import RuntimeContext
from .scheduler import WorkflowScheduler

logger = logging.getLogger(__name__)

runtime = RuntimeContext.from_config_file("config/config.yaml")
scheduler = WorkflowScheduler(runtime=runtime)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.runtime = runtime
    app.state.scheduler = scheduler
    scheduler.start()
    try:
        yield
    finally:
        scheduler.stop()


app = FastAPI(
    title="Farm Explorer Backend API",
    description="Api of the farm explorer backend",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
frontend_assets_dir = frontend_dist_dir / "assets"

if frontend_assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=frontend_assets_dir), name="assets")

def _validate_field_id(field_id: int):
    try:
        field = runtime.get_field(field_id)
        return field
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

def _serialize_field(field) -> FieldRead:
    return FieldRead.model_validate(field)


def _serialize_irrigation_event(event) -> IrrigationRead:
    return IrrigationRead.model_validate(event)


def _serialize_variety(variety) -> VarietyRead:
    return VarietyRead.model_validate(variety)


def _serialize_field_water_balance_summary(summary: dict[str, object] | None) -> FieldWaterBalanceSummary:
    if summary is None:
        return FieldWaterBalanceSummary(
            water_balance_as_of=None,
            current_water_deficit=None,
            current_soil_water_content=None,
            available_water_storage=None,
            readily_available_water=None,
            below_raw=None,
            safe_ratio=None,
        )

    return FieldWaterBalanceSummary(
        water_balance_as_of=summary.get("as_of"),
        current_water_deficit=summary.get("current_water_deficit"),
        current_soil_water_content=summary.get("current_soil_water_content"),
        available_water_storage=summary.get("available_water_storage"),
        readily_available_water=summary.get("readily_available_water"),
        below_raw=summary.get("below_raw"),
        safe_ratio=summary.get("safe_ratio"),
    )

def _get_irrigation_event(event_id: int):
    with runtime.db.session_scope() as session:
        event = runtime.db.irrigation.get_by_id(session, event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find any irrigation event with id {event_id}",
        )
    return event

def _build_field_overview(field_id: int) -> FieldOverview:
    field = _validate_field_id(field_id)
    with runtime.db.session_scope() as session:
        summary_by_field_id = {
            summary["field_id"]: summary
            for summary in runtime.db.water_balance.get_summary(session, field_ids=[field_id])
        }
    field_data = _serialize_field(field).model_dump()
    summary_data = _serialize_field_water_balance_summary(summary_by_field_id.get(field_id)).model_dump()
    return FieldOverview.model_validate(field_data | summary_data)

def _raise_write_http_error(exc: Exception, *, not_found_prefixes: tuple[str, ...] = ()) -> None:
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, IntegrityError):
        raise HTTPException(status_code=409, detail="Resource already exists or violates a uniqueness constraint.") from exc
    if isinstance(exc, ValueError):
        detail = str(exc)
        status_code = 404 if any(detail.startswith(prefix) for prefix in not_found_prefixes) else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    raise HTTPException(status_code=500, detail="Unexpected server error.") from exc

def _today_local() -> date:
    return datetime.now(runtime.timezone).date()

def _get_fields_by_name(field_name: str, *, active_only: bool = True):
    normalized = field_name.strip().casefold()
    matches = [
        field
        for field in runtime.fields
        if field.name.strip().casefold() == normalized and (field.active or not active_only)
    ]
    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find any {'active ' if active_only else ''}field with name '{field_name}'",
        )
    return matches


def _build_irrigation_targets() -> list[IrrigationTarget]:
    grouped: dict[str, list] = {}

    for field in runtime.fields:
        grouped.setdefault(field.name, []).append(field)

    targets: list[IrrigationTarget] = []
    for field_name, fields in grouped.items():
        active_fields = [field for field in fields if field.active]
        target_fields = active_fields if active_fields else fields

        sections = sorted(
            {
                field.section
                for field in target_fields
                if field.section is not None and field.section != ""
            }
        )
        varieties = sorted(
            {
                field.variety
                for field in target_fields
                if getattr(field, "variety", None) is not None
            }
        )

        targets.append(
            IrrigationTarget(
                field=field_name,
                active=any(field.active for field in fields),
                field_ids=[field.id for field in target_fields],
                field_count=len(target_fields),
                sections=sections,
                varieties=varieties,
            )
        )

    return sorted(targets, key=lambda target: target.field.casefold())

def _get_irrigation_events_for_fields_and_date(field_ids: list[int], target_date: date) -> dict[int, object]:
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

def _queue_water_balance_refresh(background_tasks: BackgroundTasks, field_ids: list[int]) -> None:
    for field_id in sorted(set(field_ids)):
        background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", field_id)

def _build_irrigation_command_result(
    *,
    success: bool,
    status_value: str,
    message: str,
    irrigation_command: IrrigationCommandCreate,
    target_date: date,
    matched_field_ids: list[int] | None = None,
    created_event_ids: list[int] | None = None,
    updated_event_ids: list[int] | None = None,
    unchanged_event_ids: list[int] | None = None,
    error: str | None = None,
) -> IrrigationCommandResult:
    created_event_ids = created_event_ids or []
    updated_event_ids = updated_event_ids or []
    unchanged_event_ids = unchanged_event_ids or []
    matched_field_ids = matched_field_ids or []

    return IrrigationCommandResult(
        success=success,
        status=status_value,
        message=message,
        field=irrigation_command.field,
        date=target_date,
        method=irrigation_command.method,
        duration=irrigation_command.duration,
        amount=irrigation_command.amount,
        matched_field_ids=matched_field_ids,
        error=error,
        created_event_ids=created_event_ids,
        updated_event_ids=updated_event_ids,
        unchanged_event_ids=unchanged_event_ids,
        created_count=len(created_event_ids),
        updated_count=len(updated_event_ids),
        unchanged_count=len(unchanged_event_ids),
    )

@app.get("/api/health")
async def health_check():
    try:
        fields = runtime.fields
        return {
            "status": "healthy",
            "field_count": len(fields),
            "timestamp": datetime.now(runtime.timezone),
        }
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.get("/api/varieties", response_model=list[VarietyRead])
async def list_varieties():
    with runtime.db.session_scope() as session:
        varieties = runtime.db.varieties.list_all(session)
    return [_serialize_variety(variety) for variety in varieties]


@app.post("/api/varieties", response_model=VarietyRead, status_code=status.HTTP_201_CREATED)
async def create_variety(variety: VarietyCreate):
    try:
        with runtime.db.session_scope() as session:
            new_variety = runtime.db.varieties.create(session, **variety.model_dump())
        return _serialize_variety(new_variety)
    except Exception as e:
        logger.exception(f"Adding variety failed: {e}")
        _raise_write_http_error(e)


@app.get("/api/fields", response_model=list[FieldRead])
async def list_fields():
    return [_serialize_field(field) for field in runtime.fields]

@app.post("/api/fields", response_model=FieldRead, status_code=status.HTTP_201_CREATED)
async def create_field(background_tasks: BackgroundTasks, field: FieldCreate):
    try: 
        with runtime.db.session_scope() as session:
            new_field = runtime.db.fields.create(session, **field.model_dump())
        background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", new_field.id)
        return _serialize_field(new_field)
    except Exception as e:
        logger.exception(f"Adding field failed: {e}")
        _raise_write_http_error(e)

@app.put("/api/fields/{field_id}", response_model=FieldRead)
async def update_field(background_tasks: BackgroundTasks, field_id: int, field: FieldUpdate):
    existing_field = _validate_field_id(field_id)
    try:
        updated_field = runtime.db.field_service.update(field_id=field_id, updates=field.model_dump())

        if any(
            getattr(existing_field, attr) != getattr(updated_field, attr)
            for attr in runtime.db.WATER_BALANCE_TRIGGER_FIELDS
        ):
            background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", field_id)
        return _serialize_field(updated_field)
    except Exception as e:
        logger.exception(f"Updating field {field_id} failed: {e}")
        _raise_write_http_error(e, not_found_prefixes=("Could not find any field with id",))

@app.post("/api/fields/{field_id}/replant", response_model=FieldRead, status_code=status.HTTP_201_CREATED)
async def replant_field(background_tasks: BackgroundTasks, field_id: int, field: FieldReplant):
    _validate_field_id(field_id)
    try:
        new_field = runtime.db.field_service.replant(
            field_id=field_id,
            valid_from=field.valid_from,
            updates=field.model_dump(exclude={"valid_from"}),
        )
        if new_field.active:
            background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", new_field.id)
        return _serialize_field(new_field)
    except Exception as e:
        logger.exception(f"Replanting field {field_id} failed: {e}")
        _raise_write_http_error(e, not_found_prefixes=("Could not find any field with id",))

@app.delete("/api/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(field_id: int):
    with runtime.db.session_scope() as session:
        deleted = runtime.db.fields.delete(session, field_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any field with id {field_id}")

@app.get("/api/fields/overview", response_model=list[FieldOverview])
async def get_fields_overview():
    with runtime.db.session_scope() as session:
        summary_by_field_id = {
            summary["field_id"]: summary
            for summary in runtime.db.water_balance.get_summary(session)
        }

    return [
        FieldOverview.model_validate(
            _serialize_field(field).model_dump()
            | _serialize_field_water_balance_summary(summary_by_field_id.get(field.id)).model_dump()
        )
        for field in runtime.fields
    ]

@app.get("/api/fields/{field_id}/overview", response_model=FieldOverview)
async def get_field_overview(field_id: int):
    return _build_field_overview(field_id)

@app.get("/api/fields/{field_id}/irrigation", response_model = list[IrrigationRead])
async def list_irrigation_events(field_id: int):
    _validate_field_id(field_id)
    
    with runtime.db.session_scope() as session:
        events = runtime.db.irrigation.list(session, field_id=field_id)
    return [_serialize_irrigation_event(event) for event in events]

@app.get("/api/irrigation", response_model=list[IrrigationRead])
async def list_all_irrigation_events():
    with runtime.db.session_scope() as session:
        events = runtime.db.irrigation.list(session)
    return [_serialize_irrigation_event(event) for event in events]

@app.post("/api/fields/{field_id}/irrigation", response_model=IrrigationRead, status_code=status.HTTP_201_CREATED)
async def create_irrigation_event(background_tasks: BackgroundTasks, field_id: int, irrigation_event: IrrigationCreate):
    _validate_field_id(field_id)
    try: 
        new_event = runtime.db.irrigation_service.create(
            field_id = field_id,
            date = irrigation_event.date,
            method= irrigation_event.method,
            duration = irrigation_event.duration,
            amount = irrigation_event.amount,
        )
        background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", field_id)
        return _serialize_irrigation_event(new_event)
    except Exception as e:
        logger.exception(f"Adding irrigation event for field with id {field_id} failed: {e}")
        _raise_write_http_error(e, not_found_prefixes=("No field with id", "Could not find any irrigation event with id"))

@app.put("/api/irrigation/{event_id}", response_model=IrrigationRead)
async def update_irrigation_event(
    background_tasks: BackgroundTasks,
    event_id: int,
    irrigation_event: IrrigationUpdate,
):
    existing_event = _get_irrigation_event(event_id)
    _validate_field_id(irrigation_event.field_id)
    try:
        updated_event = runtime.db.irrigation_service.update(event_id=event_id, updates=irrigation_event.model_dump())
        background_tasks.add_task(
            runtime.run_workflow_for_field,
            "water_balance",
            updated_event.field_id,
        )
        if existing_event.field_id != updated_event.field_id:
            background_tasks.add_task(
                runtime.run_workflow_for_field,
                "water_balance",
                existing_event.field_id,
            )
        return _serialize_irrigation_event(updated_event)
    except Exception as e:
        logger.exception(f"Updating irrigation event {event_id} failed: {e}")
        _raise_write_http_error(
            e,
            not_found_prefixes=("No field with id", "Could not find any irrigation event with id"),
        )

@app.delete("/api/irrigation/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_irrigation_event(background_tasks: BackgroundTasks, event_id: int):
    existing_event = _get_irrigation_event(event_id)
    deleted, _ = runtime.db.irrigation_service.delete(event_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find any irrigation event with id {event_id}",
        )
    background_tasks.add_task(
        runtime.run_workflow_for_field,
        "water_balance",
        existing_event.field_id,
    )

@app.delete("/api/fields/{field_id}/irrigation", response_model=FieldOverview)
async def clear_irrigation_events(field_id: int):
    _validate_field_id(field_id)
    try:
        runtime.db.irrigation_service.clear_for_field(field_id)
        return _build_field_overview(field_id)
    except Exception as e:
        logger.exception(f"Clearing irrigation events for field with id {field_id} failed: {e}")
        _raise_write_http_error(e, not_found_prefixes=("No field with id",))

@app.get("/api/irrigation/targets", response_model=list[IrrigationTarget])
async def list_irrigation_targets():
    return _build_irrigation_targets()

@app.post(
    "/api/commands/irrigation",
    response_model=IrrigationCommandResult,
    status_code=status.HTTP_200_OK,
)
async def create_irrigation_command(
    background_tasks: BackgroundTasks,
    irrigation_command: IrrigationCommandCreate,
):
    target_date = irrigation_command.date or _today_local()
    created_event_ids: list[int] = []
    updated_event_ids: list[int] = []
    unchanged_event_ids: list[int] = []
    matched_field_ids: list[int] = []
    changed_field_ids: list[int] = []

    try:
        matched_fields = _get_fields_by_name(irrigation_command.field, active_only=True)
        matched_field_ids = [field.id for field in matched_fields]
        existing_events_by_field_id = _get_irrigation_events_for_fields_and_date(matched_field_ids, target_date)

        for field in matched_fields:
            existing_event = existing_events_by_field_id.get(field.id)

            if existing_event is None:
                new_event = runtime.db.irrigation_service.create(
                    field_id=field.id,
                    date=target_date,
                    method=irrigation_command.method,
                    duration=irrigation_command.duration,
                    amount=irrigation_command.amount,
                )
                created_event_ids.append(new_event.id)
                changed_field_ids.append(field.id)
                continue

            resolved_amount = runtime.db.irrigation_service.resolve_amount(
                field=field,
                method=irrigation_command.method,
                duration=irrigation_command.duration,
                amount=irrigation_command.amount,
            )
            if (
                existing_event.method == irrigation_command.method
                and existing_event.duration == irrigation_command.duration
                and existing_event.amount == resolved_amount
            ):
                unchanged_event_ids.append(existing_event.id)
                continue

            updated_event = runtime.db.irrigation_service.update(
                event_id=existing_event.id,
                updates={
                    "field_id": field.id,
                    "date": target_date,
                    "method": irrigation_command.method,
                    "duration": irrigation_command.duration,
                    "amount": irrigation_command.amount,
                },
            )
            updated_event_ids.append(updated_event.id)
            changed_field_ids.append(field.id)

        _queue_water_balance_refresh(background_tasks, changed_field_ids)

        created_count = len(created_event_ids)
        updated_count = len(updated_event_ids)
        unchanged_count = len(unchanged_event_ids)

        if created_count > 0 and updated_count == 0 and unchanged_count == 0:
            status_value = "created"
        elif updated_count > 0 and created_count == 0 and unchanged_count == 0:
            status_value = "updated"
        elif unchanged_count > 0 and created_count == 0 and updated_count == 0:
            status_value = "unchanged"
        else:
            status_value = "ok"

        return _build_irrigation_command_result(
            success=True,
            status_value=status_value,
            message=(
                f"Irrigation command processed for field '{irrigation_command.field}' on "
                f"{target_date.isoformat()}: created={created_count}, "
                f"updated={updated_count}, unchanged={unchanged_count}."
            ),
            matched_field_ids=matched_field_ids,
            created_event_ids=created_event_ids,
            updated_event_ids=updated_event_ids,
            unchanged_event_ids=unchanged_event_ids,
            irrigation_command=irrigation_command,
            target_date=target_date,
        )
    except HTTPException as exc:
        logger.info(
            "Irrigation command for field '%s' failed with %s: %s",
            irrigation_command.field,
            exc.status_code,
            exc.detail,
        )
        return _build_irrigation_command_result(
            success=False,
            status_value="failed",
            message=str(exc.detail),
            irrigation_command=irrigation_command,
            target_date=target_date,
            matched_field_ids=matched_field_ids,
            created_event_ids=created_event_ids,
            updated_event_ids=updated_event_ids,
            unchanged_event_ids=unchanged_event_ids,
            error=str(exc.detail),
        )
    except ValueError as exc:
        logger.info(
            "Irrigation command for field '%s' failed validation: %s",
            irrigation_command.field,
            exc,
        )
        return _build_irrigation_command_result(
            success=False,
            status_value="failed",
            message=str(exc),
            irrigation_command=irrigation_command,
            target_date=target_date,
            matched_field_ids=matched_field_ids,
            created_event_ids=created_event_ids,
            updated_event_ids=updated_event_ids,
            unchanged_event_ids=unchanged_event_ids,
            error=str(exc),
        )
    except Exception as e:
        logger.exception(
            "Processing irrigation command for field name '%s' failed: %s",
            irrigation_command.field,
            e,
        )
        return _build_irrigation_command_result(
            success=False,
            status_value="failed",
            message="Unexpected server error.",
            irrigation_command=irrigation_command,
            target_date=target_date,
            matched_field_ids=matched_field_ids,
            created_event_ids=created_event_ids,
            updated_event_ids=updated_event_ids,
            unchanged_event_ids=unchanged_event_ids,
            error=str(e),
        )

@app.get("/api/fields/water-balance/summary", response_model=list[WaterBalanceSummary])
async def get_water_balance_summary():
    with runtime.db.session_scope() as session:
        summaries = runtime.db.water_balance.get_summary(session)
    return [WaterBalanceSummary(**summary) for summary in summaries]

@app.get("/api/fields/{field_id}/water-balance/series", response_model=list[WaterBalanceSeriesPoint])
async def get_field_water_balance_series(
    field_id: int,
    forecast_days: int = Query(default=0, ge=0, le=14),
):
    _validate_field_id(field_id)

    if forecast_days > 0:
        field_state = runtime.run_workflow_for_field(
            "water_balance",
            field_id,
            persist=True,
            forecast_days=forecast_days,
        )
        water_balance = None if field_state is None else field_state.water_balance
        if water_balance is None or water_balance.empty:
            return []

        series = water_balance.reset_index().rename(columns={"index": "date"})
        return [
            WaterBalanceSeriesPoint(
                date=pd.Timestamp(row["date"]).date(),
                precipitation=float(row["precipitation"]),
                irrigation=float(row["irrigation"]),
                evapotranspiration=float(row["evapotranspiration"]),
                incoming=float(row["incoming"]),
                net=float(row["net"]),
                soil_water_content=float(row["soil_water_content"]),
                available_water_storage=float(row["available_water_storage"]),
                water_deficit=float(row["water_deficit"]),
                readily_available_water=None if pd.isna(row.get("readily_available_water")) else float(row["readily_available_water"]),
                safe_ratio=None if pd.isna(row.get("safe_ratio")) else float(row["safe_ratio"]),
                below_raw=None if pd.isna(row.get("below_raw")) else bool(row["below_raw"]),
                value_type=None if pd.isna(row.get("value_type")) else str(row["value_type"]),
                model=None if pd.isna(row.get("model")) else str(row["model"]),
            )
            for _, row in series.iterrows()
        ]

    with runtime.db.session_scope() as session:
        records = runtime.db.water_balance.list_for_field(session, field_id=field_id)
    return [
        WaterBalanceSeriesPoint(
            date=record.date,
            precipitation=record.precipitation,
            irrigation=record.irrigation,
            evapotranspiration=record.evapotranspiration,
            incoming=record.incoming,
            net=record.net,
            soil_water_content=record.soil_water_content,
            available_water_storage=record.available_water_storage,
            water_deficit=record.water_deficit,
            readily_available_water=record.readily_available_water,
            safe_ratio=record.safe_ratio,
            below_raw=None if record.below_raw is None else bool(record.below_raw),
            value_type="observed",
            model="observation",
        )
        for record in records
    ]

@app.post("/api/fields/{field_id}/water-balance", response_model=FieldOverview)
async def trigger_water_balance_calculation(field_id: int):
    _validate_field_id(field_id)
    try:
        with runtime.db.session_scope() as session:
            runtime.db.water_balance.clear_for_field(session, field_id)
        runtime.run_workflow_for_field("water_balance", field_id)
        return _build_field_overview(field_id)
    except Exception as e:
        logger.exception(f"Refreshing water balance for field with id {field_id} failed: {e}")
        _raise_write_http_error(e, not_found_prefixes=("Unknown field id", "No field with id"))

@app.get("/", include_in_schema=False)
async def serve_frontend_index():
    index_file = frontend_dist_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found.")
    return FileResponse(index_file)


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend_app(full_path: str):
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="Not found")

    requested_path = frontend_dist_dir / full_path
    if requested_path.is_file():
        return FileResponse(requested_path)

    index_file = frontend_dist_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    raise HTTPException(status_code=404, detail="Frontend build not found.")
