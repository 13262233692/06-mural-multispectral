"""病害标注 API：多用户协作 + 版本快照 + 回滚。

并发模型：乐观锁。客户端保存时携带 base_version，
若与服务端当前版本不一致则返回 409，由前端合并后重试。

GET  /api/sets/{id}/annotations                  当前标注 + 版本号
POST /api/sets/{id}/annotations/save             保存一批变更（产生新版本）
GET  /api/sets/{id}/annotations/versions         版本历史
POST /api/sets/{id}/annotations/rollback         回滚到指定版本（产生新版本）
GET  /api/sets/{id}/annotations/poll?since=N     轻量轮询，用于协作同步
"""

import uuid

from fastapi import APIRouter, HTTPException

from . import db
from .models import RollbackRequest, SaveRequest, utcnow

router = APIRouter(prefix="/api/sets", tags=["annotations"])

PROJECTION = {"_id": 0}


async def _current_version(image_set_id: str) -> int:
    doc = await db.annotation_versions().find_one(
        {"image_set_id": image_set_id},
        sort=[("version", -1)],
        projection={"version": 1},
    )
    return doc["version"] if doc else 0


async def _live_annotations(image_set_id: str) -> list[dict]:
    cursor = db.annotations().find(
        {"image_set_id": image_set_id, "deleted": False}, PROJECTION
    )
    return await cursor.to_list(length=5000)


async def _commit_version(
    image_set_id: str, author: str, message: str, kind: str
) -> dict:
    """把当前 live 标注整体快照为一个新版本。"""
    version = await _current_version(image_set_id) + 1
    snapshot = await _live_annotations(image_set_id)
    doc = {
        "image_set_id": image_set_id,
        "version": version,
        "author": author,
        "message": message,
        "kind": kind,
        "snapshot": snapshot,
        "created_at": utcnow(),
    }
    await db.annotation_versions().insert_one(doc)
    doc.pop("_id", None)
    return {"version": version, "annotation_count": len(snapshot)}


@router.get("/{image_set_id}/annotations")
async def get_annotations(image_set_id: str):
    return {
        "version": await _current_version(image_set_id),
        "annotations": await _live_annotations(image_set_id),
    }


@router.get("/{image_set_id}/annotations/poll")
async def poll_annotations(image_set_id: str, since: int = 0):
    """协作轮询：版本未变时只返回版本号，减少传输量。"""
    version = await _current_version(image_set_id)
    if version == since:
        return {"version": version, "changed": False}
    return {
        "version": version,
        "changed": True,
        "annotations": await _live_annotations(image_set_id),
    }


@router.post("/{image_set_id}/annotations/save")
async def save_annotations(image_set_id: str, req: SaveRequest):
    current = await _current_version(image_set_id)
    if req.base_version != current:
        raise HTTPException(
            409,
            detail={
                "error": "version_conflict",
                "current_version": current,
                "message": "其他用户已提交新版本的标注，请刷新合并后重试",
            },
        )

    now = utcnow()
    for item in req.upserts:
        doc = item.model_dump()
        doc.update(
            annotation_id=uuid.uuid4().hex,
            image_set_id=image_set_id,
            author=req.author,
            created_at=now,
            updated_at=now,
            deleted=False,
        )
        await db.annotations().insert_one(doc)

    for annotation_id, item in req.update_ids.items():
        await db.annotations().update_one(
            {"annotation_id": annotation_id, "image_set_id": image_set_id},
            {"$set": {**item.model_dump(), "updated_at": now}},
        )

    if req.delete_ids:
        await db.annotations().update_many(
            {"annotation_id": {"$in": req.delete_ids}, "image_set_id": image_set_id},
            {"$set": {"deleted": True, "updated_at": now}},
        )

    return await _commit_version(image_set_id, req.author, req.message, kind="edit")


@router.get("/{image_set_id}/annotations/versions")
async def list_versions(image_set_id: str):
    cursor = db.annotation_versions().find(
        {"image_set_id": image_set_id},
        {"_id": 0, "snapshot": 0},
        sort=[("version", -1)],
    )
    return await cursor.to_list(length=500)


@router.post("/{image_set_id}/annotations/rollback")
async def rollback(image_set_id: str, req: RollbackRequest):
    """回滚：把目标版本快照恢复为 live 标注，并生成一个新版本（历史不可变）。"""
    target = await db.annotation_versions().find_one(
        {"image_set_id": image_set_id, "version": req.target_version}, PROJECTION
    )
    if not target:
        raise HTTPException(404, f"版本 {req.target_version} 不存在")

    await db.annotations().delete_many({"image_set_id": image_set_id})
    restored = []
    for ann in target["snapshot"]:
        ann = {k: v for k, v in ann.items() if k != "_id"}
        ann["deleted"] = False
        ann["updated_at"] = utcnow()
        restored.append(ann)
    if restored:
        await db.annotations().insert_many(restored)

    message = req.message or f"回滚到版本 {req.target_version}"
    return await _commit_version(image_set_id, req.author, message, kind="rollback")
