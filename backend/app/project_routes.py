from __future__ import annotations
from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.models import MemberIn, ProjectIn, utcnow
from app.security import CurrentUser
from app.serializers import serialize
from bson import ObjectId

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
async def list_projects(username: str = CurrentUser):
    db = get_db()
    cursor = db.projects.find({"members": username}).sort("created_at", -1)
    return [serialize(doc) async for doc in cursor]


@router.post("", status_code=201)
async def create_project(payload: ProjectIn, username: str = CurrentUser):
    db = get_db()
    doc = {
        "_id": ObjectId(),
        "name": payload.name,
        "description": payload.description,
        "created_by": username,
        "members": [username],
        "created_at": utcnow(),
    }
    await db.projects.insert_one(doc)
    return serialize(doc)


async def _require_member(project_id: str, username: str) -> dict:
    db = get_db()
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    if username not in project["members"]:
        raise HTTPException(status_code=403, detail="不是项目成员")
    return project


@router.get("/{project_id}")
async def get_project(project_id: str, username: str = CurrentUser):
    return serialize(await _require_member(project_id, username))


@router.get("/{project_id}/imagesets")
async def list_imagesets(project_id: str, username: str = CurrentUser):
    await _require_member(project_id, username)
    db = get_db()
    cursor = db.imagesets.find({"project_id": project_id}).sort("created_at", -1)
    return [serialize(doc) async for doc in cursor]


@router.post("/{project_id}/members")
async def add_member(project_id: str, payload: MemberIn, username: str = CurrentUser):
    project = await _require_member(project_id, username)
    db = get_db()
    if not await db.users.find_one({"username": payload.username}):
        raise HTTPException(status_code=404, detail="用户不存在")
    if payload.username not in project["members"]:
        await db.projects.update_one(
            {"_id": ObjectId(project_id)}, {"$addToSet": {"members": payload.username}}
        )
    return {"members": sorted(set(project["members"]) | {payload.username})}
