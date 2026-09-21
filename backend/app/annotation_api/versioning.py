from __future__ import annotations
"""标注版本：每次提交保存全量快照，回滚即恢复快照并追加新版本。"""

from bson import ObjectId

from app.database import get_db
from app.models import utcnow


async def latest_version(db, imageset_id: str) -> int:
    doc = await db.annotation_versions.find_one(
        {"imageset_id": imageset_id}, sort=[("version", -1)]
    )
    return int(doc["version"]) if doc else 0


async def snapshot_version(imageset_id: str, username: str, comment: str = "") -> int:
    db = get_db()
    version = await latest_version(db, imageset_id) + 1
    cursor = db.annotations.find({"imageset_id": imageset_id})
    annotations = []
    async for annotation in cursor:
        annotation.pop("_id", None)
        annotations.append(annotation)
    await db.annotation_versions.insert_one({
        "_id": ObjectId(),
        "imageset_id": imageset_id,
        "version": version,
        "annotations": annotations,
        "annotation_count": len(annotations),
        "created_by": username,
        "comment": comment or "提交标注",
        "created_at": utcnow(),
    })
    return version


async def restore_version(imageset_id: str, target_version: int, username: str, comment: str) -> int:
    db = get_db()
    snapshot = await db.annotation_versions.find_one(
        {"imageset_id": imageset_id, "version": target_version}
    )
    if snapshot is None:
        raise ValueError(f"版本 {target_version} 不存在")

    await db.annotations.delete_many({"imageset_id": imageset_id})
    restored = []
    for annotation in snapshot.get("annotations", []):
        copy = dict(annotation)
        copy["_id"] = ObjectId()
        restored.append(copy)
    if restored:
        await db.annotations.insert_many(restored)

    new_version = await snapshot_version(
        imageset_id, username, f"{comment}（恢复自 v{target_version}）"
    )
    return new_version
