from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Band(str, Enum):
    visible = "visible"
    infrared = "infrared"
    ultraviolet = "ultraviolet"


class DiseaseLabel(str, Enum):
    flaking = "flaking"      # 起甲
    powdering = "powdering"  # 酥碱
    mold = "mold"            # 霉变


LABEL_ZH = {
    DiseaseLabel.flaking: "起甲",
    DiseaseLabel.powdering: "酥碱",
    DiseaseLabel.mold: "霉变",
}


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    owner: str


class Point(BaseModel):
    x: float
    y: float


class Geometry(BaseModel):
    type: Literal["polygon", "rect"] = "polygon"
    points: list[Point] = Field(min_length=3)


class AnnotationIn(BaseModel):
    label: DiseaseLabel
    geometry: Geometry
    note: str = ""


class Annotation(AnnotationIn):
    annotation_id: str
    image_set_id: str
    author: str
    created_at: datetime
    updated_at: datetime
    deleted: bool = False


class SaveRequest(BaseModel):
    """一次协作保存：携带客户端基于的版本号做乐观并发控制。"""

    author: str
    message: str = ""
    base_version: int = 0
    upserts: list[AnnotationIn] = []
    update_ids: dict[str, AnnotationIn] = {}
    delete_ids: list[str] = []


class RollbackRequest(BaseModel):
    author: str
    target_version: int
    message: str = ""
