"""三波段（可见光/红外/紫外）图像上传处理。

POST /api/projects                       创建项目
GET  /api/projects                       项目列表
POST /api/projects/{project_id}/images   上传一个波段的图像
GET  /api/projects/{project_id}/sets     列出项目下的图像组
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from . import db
from .config import UPLOAD_DIR
from .models import Band, ProjectCreate, utcnow

router = APIRouter(prefix="/api", tags=["upload"])

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


@router.post("/projects")
async def create_project(payload: ProjectCreate):
    doc = {
        "project_id": uuid.uuid4().hex,
        "name": payload.name,
        "description": payload.description,
        "owner": payload.owner,
        "members": [payload.owner],
        "created_at": utcnow(),
    }
    await db.projects().insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/projects")
async def list_projects():
    cursor = db.projects().find({}, {"_id": 0})
    return await cursor.to_list(length=200)


async def _get_or_create_set(project_id: str) -> dict:
    """每个项目当前只维护一个图像组（三波段各一张），可按需扩展。"""
    existing = await db.image_sets().find_one({"project_id": project_id}, {"_id": 0})
    if existing:
        return existing
    doc = {
        "image_set_id": uuid.uuid4().hex,
        "project_id": project_id,
        "bands": {},
        "registered": None,
        "fused_image": None,
        "created_at": utcnow(),
    }
    await db.image_sets().insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.post("/projects/{project_id}/images")
async def upload_band_image(project_id: str, band: Band, file: UploadFile = File(...)):
    project = await db.projects().find_one({"project_id": project_id})
    if not project:
        raise HTTPException(404, "项目不存在")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"不支持的文件类型: {suffix}")

    image_set = await _get_or_create_set(project_id)
    dest_dir = UPLOAD_DIR / image_set["image_set_id"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{band.value}{suffix}"

    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            out.write(chunk)

    band_info = {
        "path": str(dest),
        "filename": file.filename,
        "size": size,
        "uploaded_at": utcnow(),
    }
    await db.image_sets().update_one(
        {"image_set_id": image_set["image_set_id"]},
        {
            "$set": {f"bands.{band.value}": band_info},
            # 新图像上传后旧的配准结果失效
            "$unset": {"registered": "", "fused_image": ""},
        },
    )
    return {"image_set_id": image_set["image_set_id"], "band": band.value, "size": size}


@router.get("/projects/{project_id}/sets")
async def list_image_sets(project_id: str):
    cursor = db.image_sets().find({"project_id": project_id}, {"_id": 0})
    return await cursor.to_list(length=100)
