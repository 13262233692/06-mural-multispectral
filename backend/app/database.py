from __future__ import annotations
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    global client, db
    client = AsyncIOMotorClient(settings.mongo_url)
    db = client[settings.mongo_db]
    await db.users.create_index("username", unique=True)
    await db.projects.create_index("name")
    await db.imagesets.create_index([("project_id", 1), ("created_at", -1)])
    await db.annotations.create_index([("imageset_id", 1), ("version", -1)])
    await db.annotation_versions.create_index([("imageset_id", 1), ("version", -1)], unique=True)


async def close_db() -> None:
    if client is not None:
        client.close()


def get_db() -> AsyncIOMotorDatabase:
    if db is None:
        raise RuntimeError("数据库尚未初始化")
    return db
