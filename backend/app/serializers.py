from __future__ import annotations
"""Mongo 文档 -> API 输出的转换工具。"""

from typing import Any


def serialize(doc: dict[str, Any]) -> dict[str, Any]:
    if doc is None:
        return doc
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    return out
