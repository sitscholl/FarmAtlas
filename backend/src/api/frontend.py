from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .utils import frontend_dist_dir

router = APIRouter(include_in_schema=False)


@router.get("/")
async def serve_frontend_index():
    index_file = frontend_dist_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found.")
    return FileResponse(index_file)


@router.get("/{full_path:path}")
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
