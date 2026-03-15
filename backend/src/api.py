from datetime import datetime
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .api_models import (
    FieldOverviewResponse,
    FieldSummaryResponse,
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
        )
        for field in runtime.fields
    ]


@app.get("/api/fields/water-balance/summary", response_model=list[WaterBalanceSummaryResponse])
async def get_water_balance_summary():
    return [
        WaterBalanceSummaryResponse(**summary)
        for summary in runtime.db.get_water_balance_summary()
    ]
