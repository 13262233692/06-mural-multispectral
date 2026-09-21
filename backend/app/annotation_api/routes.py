"""标注 CRUD、乐观锁校验、版本历史与回滚接口。"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from app.annotation_api.versioning import latest_version, restore_version, snapshot_version
from app.database import get_db
from app.models import AnnotationIn, AnnotationPatch, RollbackIn, utcnow
from app.security import CurrentUser
from app.serializers import serialize
from app.ws_hub import hub
from bson import ObjectId

router = APIRouter(prefix="/api/imagesets", tags=["annotations"])


def _validate_geometry(geometry: dict) -> None:
    if geometry.get("type") not in {"polygon", "rectangle", "point"}:
        raise HTTPException(status_code=422, detail="geometry.type 必须为 polygon/rectangle/point")
    coords = geometry.get("coordinates")
    if not isinstance(coords, list) or not coords:
        raise HTTPException(status_code=422, detail="geometry.coordinates 必须为非空坐标数组")


async def _check_imageset(imageset_id: str) -> None:
    db = get_db()
    if not ObjectId.is_valid(imageset_id):
        raise HTTPException(status_code=400, detail="图像集 ID 非法")
    if await db.imagesets.find_one({"_id": ObjectId(imageset_id)}) is None:
        raise HTTPException(status_code=404, detail="图像集不存在")


async def _check_version(imageset_id: str, expected: int | None) -> None:
    if expected is None:
        return
    actual = await latest_version(get_db(), imageset_id)
    if actual != expected:
        raise HTTPException(status_code=409, detail=f"版本冲突：当前为 v{actual}，请刷新后重试")


@router.get("/{imageset_id}/annotations")
async def list_annotations(imageset_id: str, username: str = CurrentUser):
    await _check_imageset(imageset_id)
    db = get_db()
    cursor = db.annotations.find({"imageset_id": imageset_id}).sort("created_at", 1)
    return [serialize(doc) async for doc in cursor]


@router.post("/{imageset_id}/annotations", status_code=201)
async def create_annotation(
    imageset_id: str,
    payload: AnnotationIn,
    username: str = CurrentUser,
    x_base_version: int | None = Header(default=None, alias="X-Base-Version"),
):
    await _check_imageset(imageset_id)
    await _check_version(imageset_id, x_base_version)
    _validate_geometry(payload.geometry)
    db = get_db()
    now = utcnow()
    doc = {
        "_id": ObjectId(),
        "imageset_id": imageset_id,
        "disease_type": payload.disease_type,
        "geometry": payload.geometry,
        "confidence": payload.confidence,
        "note": payload.note,
        "created_by": username,
        "updated_by": username,
        "created_at": now,
        "updated_at": now,
    }
    await db.annotations.insert_one(doc)
    out = serialize(doc)
    await hub.broadcast(imageset_id, {"type": "annotation_created", "annotation": out})
    return out


@router.patch("/{imageset_id}/annotations/{annotation_id}")
async def update_annotation(
    imageset_id: str,
    annotation_id: str,
    payload: AnnotationPatch,
    username: str = CurrentUser,
    x_base_version: int | None = Header(default=None, alias="X-Base-Version"),
):
    await _check_imageset(imageset_id)
    await _check_version(imageset_id, x_base_version)
    if payload.geometry is not None:
        _validate_geometry(payload.geometry)
    db = get_db()
    changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    changes.update({"updated_by": username, "updated_at": utcnow()})
    result = await db.annotations.update_one(
        {"_id": ObjectId(annotation_id), "imageset_id": imageset_id}, {"$set": changes}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="标注不存在")
    doc = await db.annotations.find_one({"_id": ObjectId(annotation_id)})
    out = serialize(doc)
    await hub.broadcast(imageset_id, {"type": "annotation_updated", "annotation": out})
    return out


@router.delete("/{imageset_id}/annotations/{annotation_id}")
async def delete_annotation(
    imageset_id: str,
    annotation_id: str,
    username: str = CurrentUser,
    x_base_version: int | None = Header(default=None, alias="X-Base-Version"),
):
    await _check_imageset(imageset_id)
    await _check_version(imageset_id, x_base_version)
    db = get_db()
    result = await db.annotations.delete_one(
        {"_id": ObjectId(annotation_id), "imageset_id": imageset_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="标注不存在")
    await hub.broadcast(imageset_id, {"type": "annotation_deleted", "annotation_id": annotation_id})
    return {"deleted": annotation_id}


@router.post("/{imageset_id}/versions")
async def commit_version(imageset_id: str, comment: str = Query(default=""), username: str = CurrentUser):
    await _check_imageset(imageset_id)
    version = await snapshot_version(imageset_id, username, comment)
    await hub.broadcast(imageset_id, {"type": "version_committed", "version": version})
    return {"version": version}


@router.get("/{imageset_id}/versions")
async def list_versions(imageset_id: str, username: str = CurrentUser):
    await _check_imageset(imageset_id)
    db = get_db()
    cursor = db.annotation_versions.find({"imageset_id": imageset_id}).sort("version", -1)
    results = []
    async for doc in cursor:
        doc.pop("annotations", None)
        results.append(serialize(doc))
    return results


@router.post("/{imageset_id}/rollback")
async def rollback(imageset_id: str, payload: RollbackIn, username: str = CurrentUser):
    await _check_imageset(imageset_id)
    db = get_db()
    try:
        new_version = await restore_version(imageset_id, payload.version, username, payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    cursor = db.annotations.find({"imageset_id": imageset_id})
    current = [serialize(doc) async for doc in cursor]
    await hub.broadcast(imageset_id, {
        "type": "rolled_back",
        "from_version": payload.version,
        "new_version": new_version,
        "annotations": current,
    })
    return {"new_version": new_version, "annotations": current}
