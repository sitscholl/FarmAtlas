from datetime import datetime
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .api_models import (
    FieldOverviewResponse,
    FieldSummaryResponse,
    WaterBalanceSeriesPointResponse,
    WaterBalanceSummaryResponse,
)
from .runtime import RuntimeContext

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Farm Explorer Backend API",
    description="Api of the farm explorer backend",
    version="1.0.0",
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

runtime = RuntimeContext.from_config_file("config/config.yaml")


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
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.get("/api/fields", response_model=list[FieldSummaryResponse])
async def get_fields():
    return [
        FieldSummaryResponse(
            id=field.id,
            name=field.name,
            reference_provider=field.reference_provider,
            reference_station=field.reference_station,
            soil_type=field.soil_type,
            humus_pct=field.humus_pct,
            area_ha=field.area_ha,
            root_depth_cm=field.root_depth_cm,
            p_allowable=field.p_allowable,
        )
        for field in runtime.fields
    ]


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
            reference_provider=field.reference_provider,
            reference_station=field.reference_station,
            soil_type=field.soil_type,
            humus_pct=field.humus_pct,
            area_ha=field.area_ha,
            root_depth_cm=field.root_depth_cm,
            p_allowable=field.p_allowable,
            water_balance_as_of=summary_by_field_id.get(field.id, {}).get("as_of"),
            current_deficit=summary_by_field_id.get(field.id, {}).get("current_deficit"),
            current_soil_storage=summary_by_field_id.get(field.id, {}).get("current_soil_storage"),
            field_capacity=summary_by_field_id.get(field.id, {}).get("field_capacity"),
            readily_available_water=summary_by_field_id.get(field.id, {}).get("readily_available_water"),
            below_raw=summary_by_field_id.get(field.id, {}).get("below_raw"),
            safe_ratio=summary_by_field_id.get(field.id, {}).get("safe_ratio"),
        )
        for field in runtime.fields
    ]


@app.get("/api/fields/{field_id}/overview", response_model=FieldOverviewResponse)
async def get_field_overview(field_id: int):
    try:
        field = runtime.get_field(field_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    summary_by_field_id = {
        summary["field_id"]: summary
        for summary in runtime.db.get_water_balance_summary(field_ids=[field_id])
    }
    summary = summary_by_field_id.get(field_id, {})

    return FieldOverviewResponse(
        id=field.id,
        name=field.name,
        reference_provider=field.reference_provider,
        reference_station=field.reference_station,
        soil_type=field.soil_type,
        humus_pct=field.humus_pct,
        area_ha=field.area_ha,
        root_depth_cm=field.root_depth_cm,
        p_allowable=field.p_allowable,
        water_balance_as_of=summary.get("as_of"),
        current_deficit=summary.get("current_deficit"),
        current_soil_storage=summary.get("current_soil_storage"),
        field_capacity=summary.get("field_capacity"),
        readily_available_water=summary.get("readily_available_water"),
        below_raw=summary.get("below_raw"),
        safe_ratio=summary.get("safe_ratio"),
    )


@app.get("/api/fields/water-balance/summary", response_model=list[WaterBalanceSummaryResponse])
async def get_water_balance_summary():
    return [
        WaterBalanceSummaryResponse(**summary)
        for summary in runtime.db.get_water_balance_summary()
    ]


@app.get("/api/fields/{field_id}/water-balance/series", response_model=list[WaterBalanceSeriesPointResponse])
async def get_field_water_balance_series(field_id: int):
    try:
        runtime.get_field(field_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    records = runtime.db.query_water_balance_series(field_id=field_id)
    return [
        WaterBalanceSeriesPointResponse(
            date=record.date,
            precipitation=record.precipitation,
            irrigation=record.irrigation,
            evapotranspiration=record.evapotranspiration,
            incoming=record.incoming,
            net=record.net,
            soil_storage=record.soil_storage,
            field_capacity=record.field_capacity,
            deficit=record.deficit,
            readily_available_water=record.readily_available_water,
            safe_ratio=record.safe_ratio,
            below_raw=None if record.below_raw is None else bool(record.below_raw),
        )
        for record in records
    ]
