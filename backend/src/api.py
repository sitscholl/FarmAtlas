from contextlib import asynccontextmanager
from datetime import datetime
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
from sqlalchemy.exc import IntegrityError

from .api_models import (
    FieldOverviewResponse,
    FieldPost,
    FieldPut,
    FieldSummaryResponse,
    IrrigationResponse,
    IrrigationPost,
    IrrigationPut,
    WaterBalanceSeriesPointResponse,
    WaterBalanceSummaryResponse,
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

def _serialize_field(field) -> FieldSummaryResponse:
    return FieldSummaryResponse(
        id=field.id,
        name=field.name,
        section=field.section,
        variety=field.variety,
        planting_year=field.planting_year,
        tree_count=field.tree_count,
        tree_height=field.tree_height,
        row_distance=field.row_distance,
        tree_distance=field.tree_distance,
        running_metre=field.running_metre,
        herbicide_free=field.herbicide_free,
        active=field.active,
        reference_provider=field.reference_provider,
        reference_station=field.reference_station,
        soil_type=field.soil_type,
        soil_weight=field.soil_weight,
        humus_pct=field.humus_pct,
        area_ha=field.area_ha,
        effective_root_depth_cm=field.effective_root_depth_cm,
        p_allowable=field.p_allowable,
    )

def _serialize_irrigation_event(event) -> IrrigationResponse:
    return IrrigationResponse(
        id=event.id,
        field_id=event.field_id,
        date=event.date,
        method=event.method,
        amount=event.amount,
    )

def _get_irrigation_event(event_id: int):
    event = next(
        (event for event in runtime.db.list_irrigation_events() if event.id == event_id),
        None,
    )
    if event is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find any irrigation event with id {event_id}",
        )
    return event

def _build_field_overview(field_id: int) -> FieldOverviewResponse:
    field = _validate_field_id(field_id)
    summary_by_field_id = {
        summary["field_id"]: summary
        for summary in runtime.db.get_water_balance_summary(field_ids=[field_id])
    }
    summary = summary_by_field_id.get(field_id, {})

    return FieldOverviewResponse(
        id=field.id,
        name=field.name,
        section=field.section,
        variety=field.variety,
        planting_year=field.planting_year,
        tree_count=field.tree_count,
        tree_height=field.tree_height,
        row_distance=field.row_distance,
        tree_distance=field.tree_distance,
        running_metre=field.running_metre,
        herbicide_free=field.herbicide_free,
        active=field.active,
        reference_provider=field.reference_provider,
        reference_station=field.reference_station,
        soil_type=field.soil_type,
        soil_weight=field.soil_weight,
        humus_pct=field.humus_pct,
        area_ha=field.area_ha,
        effective_root_depth_cm=field.effective_root_depth_cm,
        p_allowable=field.p_allowable,
        water_balance_as_of=summary.get("as_of"),
        current_water_deficit=summary.get("current_water_deficit"),
        current_soil_water_content=summary.get("current_soil_water_content"),
        available_water_storage=summary.get("available_water_storage"),
        readily_available_water=summary.get("readily_available_water"),
        below_raw=summary.get("below_raw"),
        safe_ratio=summary.get("safe_ratio"),
    )

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


@app.get("/api/fields", response_model=list[FieldSummaryResponse])
async def list_fields():
    return [_serialize_field(field) for field in runtime.fields]

@app.post("/api/fields", response_model=FieldSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_field(background_tasks: BackgroundTasks, field: FieldPost):
    try: 
        new_field = runtime.db.create_field(
            name = field.name,
            section = field.section,
            variety = field.variety,
            planting_year = field.planting_year,
            reference_provider = field.reference_provider,
            reference_station = field.reference_station,
            soil_type = field.soil_type,
            soil_weight = field.soil_weight,
            humus_pct = field.humus_pct,
            area_ha = field.area_ha,
            effective_root_depth_cm = field.effective_root_depth_cm,
            p_allowable = field.p_allowable,
            tree_count = field.tree_count,
            tree_height = field.tree_height,
            row_distance = field.row_distance,
            tree_distance = field.tree_distance,
            running_metre = field.running_metre,
            herbicide_free = field.herbicide_free,
            active = field.active,
        )
        background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", new_field.id)
        return _serialize_field(new_field)
    except Exception as e:
        logger.exception(f"Adding field failed: {e}")
        _raise_write_http_error(e)

@app.put("/api/fields/{field_id}", response_model=FieldSummaryResponse)
async def update_field(background_tasks: BackgroundTasks, field_id: int, field: FieldPut):
    existing_field = _validate_field_id(field_id)
    try:
        updated_field = runtime.db.update_field(
            id=field_id,
            updates={
                "name": field.name,
                "section": field.section,
                "variety": field.variety,
                "planting_year": field.planting_year,
                "reference_provider": field.reference_provider,
                "reference_station": field.reference_station,
                "soil_type": field.soil_type,
                "soil_weight": field.soil_weight,
                "humus_pct": field.humus_pct,
                "area_ha": field.area_ha,
                "effective_root_depth_cm": field.effective_root_depth_cm,
                "p_allowable": field.p_allowable,
                "tree_count": field.tree_count,
                "tree_height": field.tree_height,
                "row_distance": field.row_distance,
                "tree_distance": field.tree_distance,
                "running_metre": field.running_metre,
                "herbicide_free": field.herbicide_free,
                "active": field.active,
            },
        )

        if any(
            getattr(existing_field, attr) != getattr(updated_field, attr)
            for attr in runtime.db.WATER_BALANCE_TRIGGER_FIELDS
        ):
            background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", field_id)
        return _serialize_field(updated_field)
    except Exception as e:
        logger.exception(f"Updating field {field_id} failed: {e}")
        _raise_write_http_error(e, not_found_prefixes=("Could not find any field with id",))

@app.delete("/api/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(field_id: int):
    deleted = runtime.db.delete_field(field_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any field with id {field_id}")

@app.get("/api/fields/overview", response_model=list[FieldOverviewResponse])
async def get_fields_overview():
    summary_by_field_id = {
        summary["field_id"]: summary
        for summary in runtime.db.get_water_balance_summary()
    }

    return [
        FieldOverviewResponse(
            id=field.id,
            name=field.name,
            section=field.section,
            variety=field.variety,
            planting_year=field.planting_year,
            tree_count=field.tree_count,
            tree_height=field.tree_height,
            row_distance=field.row_distance,
            tree_distance=field.tree_distance,
            running_metre=field.running_metre,
            herbicide_free=field.herbicide_free,
            active=field.active,
            reference_provider=field.reference_provider,
            reference_station=field.reference_station,
            soil_type=field.soil_type,
            soil_weight=field.soil_weight,
            humus_pct=field.humus_pct,
            area_ha=field.area_ha,
            effective_root_depth_cm=field.effective_root_depth_cm,
            p_allowable=field.p_allowable,
            water_balance_as_of=summary_by_field_id.get(field.id, {}).get("as_of"),
            current_water_deficit=summary_by_field_id.get(field.id, {}).get("current_water_deficit"),
            current_soil_water_content=summary_by_field_id.get(field.id, {}).get("current_soil_water_content"),
            available_water_storage=summary_by_field_id.get(field.id, {}).get("available_water_storage"),
            readily_available_water=summary_by_field_id.get(field.id, {}).get("readily_available_water"),
            below_raw=summary_by_field_id.get(field.id, {}).get("below_raw"),
            safe_ratio=summary_by_field_id.get(field.id, {}).get("safe_ratio"),
        )
        for field in runtime.fields
    ]

@app.get("/api/fields/{field_id}/overview", response_model=FieldOverviewResponse)
async def get_field_overview(field_id: int):
    return _build_field_overview(field_id)

@app.get("/api/fields/{field_id}/irrigation", response_model = list[IrrigationResponse])
async def list_irrigation_events(field_id: int):
    _validate_field_id(field_id)
    
    events = runtime.db.list_irrigation_events(field_id = field_id)
    return [_serialize_irrigation_event(event) for event in events]

@app.get("/api/irrigation", response_model=list[IrrigationResponse])
async def list_all_irrigation_events():
    events = runtime.db.list_irrigation_events()
    return [_serialize_irrigation_event(event) for event in events]

@app.post("/api/fields/{field_id}/irrigation", response_model=IrrigationResponse, status_code=status.HTTP_201_CREATED)
async def create_irrigation_event(background_tasks: BackgroundTasks, field_id: int, irrigation_event: IrrigationPost):
    _validate_field_id(field_id)
    try: 
        new_event = runtime.db.create_irrigation_event(
            field_id = field_id,
            date = irrigation_event.date,
            method= irrigation_event.method,
            amount = irrigation_event.amount,
        )
        background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", field_id)
        return _serialize_irrigation_event(new_event)
    except Exception as e:
        logger.exception(f"Adding irrigation event for field with id {field_id} failed: {e}")
        _raise_write_http_error(e, not_found_prefixes=("No field with id", "Could not find any irrigation event with id"))

@app.put("/api/irrigation/{event_id}", response_model=IrrigationResponse)
async def update_irrigation_event(
    background_tasks: BackgroundTasks,
    event_id: int,
    irrigation_event: IrrigationPut,
):
    existing_event = _get_irrigation_event(event_id)
    _validate_field_id(irrigation_event.field_id)
    try:
        updated_event = runtime.db.update_irrigation_event(
            event_id=event_id,
            updates={
                "field_id": irrigation_event.field_id,
                "date": irrigation_event.date,
                "method": irrigation_event.method,
                "amount": irrigation_event.amount,
            },
        )
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
    deleted = runtime.db.delete_irrigation_event(event_id)
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

@app.delete("/api/fields/{field_id}/irrigation", response_model=FieldOverviewResponse)
async def clear_irrigation_events(field_id: int):
    _validate_field_id(field_id)
    try:
        runtime.db.clear_irrigation_events(field_id)
        return _build_field_overview(field_id)
    except Exception as e:
        logger.exception(f"Clearing irrigation events for field with id {field_id} failed: {e}")
        _raise_write_http_error(e, not_found_prefixes=("No field with id",))

@app.get("/api/fields/water-balance/summary", response_model=list[WaterBalanceSummaryResponse])
async def get_water_balance_summary():
    return [
        WaterBalanceSummaryResponse(**summary)
        for summary in runtime.db.get_water_balance_summary()
    ]

@app.get("/api/fields/{field_id}/water-balance/series", response_model=list[WaterBalanceSeriesPointResponse])
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
            WaterBalanceSeriesPointResponse(
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

    records = runtime.db.get_water_balance(field_id=field_id)
    return [
        WaterBalanceSeriesPointResponse(
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

@app.post("/api/fields/{field_id}/water-balance", response_model=FieldOverviewResponse)
async def trigger_water_balance_calculation(field_id: int):
    _validate_field_id(field_id)
    try:
        runtime.db.clear_water_balance(field_id)
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
