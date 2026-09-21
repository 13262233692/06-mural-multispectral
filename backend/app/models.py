from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Band = Literal["visible", "ir", "uv"]
DiseaseType = Literal["flaking", "efflorescence", "mold"]

DISEASE_LABELS: dict[str, str] = {
    "flaking": "起甲",
    "efflorescence": "酥碱",
    "mold": "霉变",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------- 用户 ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=4, max_length=128)
    display_name: str = ""


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    username: str
    display_name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- 项目 ----------
class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = ""


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    created_by: str
    members: list[str]
    created_at: datetime


class MemberIn(BaseModel):
    username: str


# ---------- 图像集 ----------
class ImageSetOut(BaseModel):
    id: str
    project_id: str
    title: str
    status: str
    bands: dict[str, Any]
    layers: dict[str, Any]
    width:Optional[int] = None
    height:Optional[int] = None
    match_stats: dict[str, Any] = {}
    error:Optional[str] = None
    created_by: str
    created_at: datetime
    processed_at:Optional[datetime] = None


# ---------- 标注 ----------
class AnnotationIn(BaseModel):
    disease_type: DiseaseType
    geometry: dict[str, Any]
    confidence: float = 1.0
    note: str = ""


class AnnotationPatch(BaseModel):
    disease_type:Optional[DiseaseType] = None
    geometry:Optional[dict[str, Any]] = None
    confidence:Optional[float] = None
    note:Optional[str] = None


class AnnotationOut(BaseModel):
    id: str
    imageset_id: str
    disease_type: DiseaseType
    geometry: dict[str, Any]
    confidence: float
    note: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class VersionOut(BaseModel):
    version: int
    imageset_id: str
    annotation_count: int
    created_by: str
    comment: str
    created_at: datetime


class RollbackIn(BaseModel):
    version: int
    comment: str = "回滚"
