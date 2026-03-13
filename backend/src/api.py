from datetime import datetime
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .api_models import FieldSummaryResponse
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
