"""
FastAPI integration example for the MeteoDB timeseries database.
This demonstrates how to expose the database via REST API for fast access to cached meteo data.
"""

from fastapi import FastAPI, HTTPException

from datetime import datetime
import pytz
import logging

from .api_models import FieldContextResponse
from .runtime import RuntimeContext
# from .utils import split_url_parameters

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Farm Explorer Backend API",
    description="Api of the farm explorer backend",
    version="1.0.0"
)

## Initialize runtime context
runtime = RuntimeContext.from_config_file("config/config.yaml")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        fields = runtime.fields
        return {
            "status": "healthy",
            "field_count": len(fields),
            "timestamp": datetime.now(runtime.timezone)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")

@app.get("/api/fields", response_model=list[FieldContextResponse])
async def get_fields():
    return [
        FieldContextResponse(
            id=field.id,
            name=field.name,
            reference_station=field.reference_station,
            soil_type=field.soil_type,
            humus_pct=field.humus_pct,
            area_ha=field.area_ha,
            root_depth_cm=field.root_depth_cm,
            p_allowable=field.p_allowable
        )
        for field in runtime.fields
    ]