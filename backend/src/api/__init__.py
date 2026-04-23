from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .fields import router as fields_router
from .frontend import router as frontend_router
from .irrigation import router as irrigation_router
from .nutrients import router as nutrients_router
from .phenology import router as phenology_router
from .plantings import router as plantings_router
from .sections import router as sections_router
from .utils import frontend_assets_dir, lifespan, runtime
from .varieties import router as varieties_router
from .water_balance import router as water_balance_router

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

if frontend_assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=frontend_assets_dir), name="assets")


@app.get("/api/health")
async def health_check():
    try:
        fields = runtime.fields
        return {
            "status": "healthy",
            "field_count": len(fields),
            "timestamp": datetime.now(runtime.timezone),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


app.include_router(varieties_router)
app.include_router(nutrients_router)
app.include_router(phenology_router)
app.include_router(fields_router)
app.include_router(plantings_router)
app.include_router(sections_router)
app.include_router(irrigation_router)
app.include_router(water_balance_router)
app.include_router(frontend_router)
