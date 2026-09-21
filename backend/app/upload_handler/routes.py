"""波段图像上传接口。"""
from __future__ import annotations

import asyncio

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.config import settings
from app.database import get_db
from app.models import utcnow
from app.security import CurrentUser
from app.serializers import serialize
from app.upload_handler.pipeline import run_registration

router = APIRouter(prefix="/api/projects/{project_id}/imagesets", tags=["upload"])

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
BAND_NAMES = {"visible", "ir", "uv"}


@router.post("")
async def create_imageset(
    project_id: str,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    visible: UploadFile = File(...),
    ir: UploadFile | None = File(None),
    uv: UploadFile | None = File(None),
    username: str = CurrentUser,
):
    db = get_db()
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    uploads: dict[str, UploadFile] = {"visible": visible, "ir": ir, "uv": uv}
    bands: dict[str, dict] = {}
    imageset_id = ObjectId()
    target_dir = settings.uploads_dir / str(imageset_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        for band, upload in uploads.items():
            if upload is None or not upload.filename:
                continue
            suffix = "." + upload.filename.rsplit(".", 1)[-1].lower()
            if suffix not in ALLOWED_SUFFIXES:
                raise HTTPException(status_code=400, detail=f"不支持的文件格式: {upload.filename}")
            stored_name = f"{band}{suffix}"
            with (target_dir / stored_name).open("wb") as handle:
                handle.write(await upload.read())
            bands[band] = {"filename": f"{imageset_id}/{stored_name}", "original_name": upload.filename}
    finally:
        await visible.close()
        for optional in (ir, uv):
            if optional is not None:
                await optional.close()

    if "visible" not in bands:
        raise HTTPException(status_code=400, detail="必须提供可见光基准图像")

    doc = {
        "_id": imageset_id,
        "project_id": project_id,
        "title": title,
        "status": "uploaded",
        "bands": bands,
        "layers": {},
        "width": None,
        "height": None,
        "match_stats": {},
        "error": None,
        "created_by": username,
        "created_at": utcnow(),
        "processed_at": None,
    }
    await db.imagesets.insert_one(doc)
    background_tasks.add_task(run_registration, str(imageset_id))
    return serialize(doc)


@router.get("/{imageset_id}")
async def get_imageset(project_id: str, imageset_id: str, username: str = CurrentUser):
    db = get_db()
    doc = await db.imagesets.find_one({"_id": ObjectId(imageset_id), "project_id": project_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="图像集不存在")
    return serialize(doc)


@router.post("/{imageset_id}/reprocess")
async def reprocess(
    project_id: str, imageset_id: str, background_tasks: BackgroundTasks, username: str = CurrentUser
):
    db = get_db()
    doc = await db.imagesets.find_one({"_id": ObjectId(imageset_id), "project_id": project_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="图像集不存在")
    background_tasks.add_task(run_registration, imageset_id)
    await asyncio.sleep(0)
    return {"status": "processing"}
