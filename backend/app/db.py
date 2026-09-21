from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from .config import settings

client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global client
    if client is None:
        client = AsyncIOMotorClient(settings.mongo_uri)
    return client


def get_db():
    return get_client()[settings.mongo_db]


def projects():
    return get_db()["projects"]


def image_sets():
    return get_db()["image_sets"]


def annotations():
    return get_db()["annotations"]


def annotation_versions():
    return get_db()["annotation_versions"]


async def ensure_indexes() -> None:
    await image_sets().create_index("project_id")
    await annotations().create_index("image_set_id")
    # 部分唯一索引：仅约束有效文档，兼容库中可能存在的遗留数据
    await annotation_versions().create_index(
        [("image_set_id", 1), ("version", -1)],
        unique=True,
        partialFilterExpression={"image_set_id": {"$type": "string"}},
    )
