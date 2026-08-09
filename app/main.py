from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .cme import scan_cme
from .config import get_settings
from .converter import scan_conversion_files
from .paths import PathAccessError, PathResolver
from .schemas import JobCreate, validate_task
from .store import JobStore, TERMINAL_STATES


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
settings = get_settings()
resolver = PathResolver(settings.roots)
store = JobStore(settings.database_path)

app = FastAPI(title=settings.app_title, version=__version__)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ScanRequest(BaseModel):
    root: str
    path: str = ""
    mode: str = "cme"
    recursive: bool = True


def _path_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    worker = store.worker_state()
    worker_age = None
    worker_alive = False
    if worker:
        updated = datetime.fromisoformat(worker["updated_at"])
        worker_age = (datetime.now(timezone.utc) - updated).total_seconds()
        worker_alive = worker_age < 45
    return {
        "status": "ok",
        "version": __version__,
        "worker_alive": worker_alive,
        "worker_age_seconds": worker_age,
    }


@app.get("/api/config")
def config():
    return {
        "title": settings.app_title,
        "version": __version__,
        "roots": [
            {
                "key": root.key,
                "label": root.label,
                "available": root.path.exists() and root.path.is_dir(),
            }
            for root in settings.roots.values()
        ],
        "capabilities": {
            "ffmpeg": bool(shutil.which(settings.ffmpeg)),
            "ffprobe": bool(shutil.which(settings.ffprobe)),
            "intel_gpu": Path("/dev/dri/renderD128").exists(),
        },
    }


@app.get("/api/browse")
def browse(root: str, path: str = ""):
    try:
        return resolver.list_directory(root, path)
    except (PathAccessError, OSError) as exc:
        raise _path_error(exc) from exc


@app.post("/api/scan")
def scan(request: ScanRequest):
    try:
        path = resolver.resolve(request.root, request.path)
        if request.mode == "cme":
            if not path.is_dir():
                raise PathAccessError("切分、合并和抽取必须选择输入目录")
            return scan_cme(path)
        files = scan_conversion_files(path, request.mode, request.recursive)
        return {
            "count": len(files),
            "items": [resolver.relative(request.root, item) for item in files[:500]],
            "truncated": len(files) > 500,
        }
    except (PathAccessError, OSError, ValueError) as exc:
        raise _path_error(exc) from exc


@app.post("/api/jobs", status_code=201)
def create_job(request: JobCreate):
    try:
        payload = validate_task(request.kind, request.payload)
        input_kind = None if request.kind == "convert" else "dir"
        resolver.resolve(payload["input_root"], payload["input_path"], kind=input_kind)
        output = resolver.resolve(
            payload["output_root"], payload["output_path"], must_exist=False
        )
        if output.exists() and not output.is_dir():
            raise PathAccessError("输出路径必须是目录")
    except (PathAccessError, ValueError) as exc:
        raise _path_error(exc) from exc
    return store.create(request.kind, payload)


@app.get("/api/jobs")
def list_jobs(limit: int = Query(default=50, ge=1, le=200)):
    jobs = store.list(limit)
    for job in jobs:
        job.pop("logs", None)
    return jobs


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    job = store.request_cancel(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job["status"] not in TERMINAL_STATES:
        raise HTTPException(status_code=409, detail="只能删除已经结束的任务记录")
    store.delete(job_id)
    return {"deleted": True}


@app.get("/api/jobs/{job_id}/result/{index}")
def download_result(job_id: str, index: int, download: bool = False):
    job = store.get(job_id)
    if not job or not job.get("result"):
        raise HTTPException(status_code=404, detail="任务结果不存在")
    files = job["result"].get("files", [])
    if index < 0 or index >= len(files):
        raise HTTPException(status_code=404, detail="结果文件不存在")
    item = files[index]
    try:
        path = resolver.resolve(item["root"], item["path"], kind="file")
    except PathAccessError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    disposition = "attachment" if download else "inline"
    return FileResponse(path, filename=path.name if download else None, content_disposition_type=disposition)
