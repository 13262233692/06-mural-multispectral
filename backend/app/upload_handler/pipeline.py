from __future__ import annotations
"""后台配准流水线：配准 -> 融合 -> DZI 金字塔 -> 状态回写。"""

from bson import ObjectId

from app.config import settings
from app.database import get_db
from app.models import utcnow
from app.registration_engine import RegistrationError, false_color_fuse, register_bands, write_dzi
from app.registration_engine.image_io import load_image
from app.ws_hub import hub


async def run_registration(imageset_id: str) -> None:
    db = get_db()
    imageset = await db.imagesets.find_one({"_id": ObjectId(imageset_id)})
    if imageset is None:
        return

    async def report(status: str, **extra: object) -> None:
        await db.imagesets.update_one({"_id": ObjectId(imageset_id)}, {"$set": {"status": status, **extra}})
        imageset["status"] = status
        await hub.broadcast(imageset_id, {"type": "imageset_status", "status": status, **extra})

    try:
        await report("processing")
        bands_meta = imageset["bands"]
        visible = load_image(settings.uploads_dir / bands_meta["visible"]["filename"])

        target_images = {}
        for band in ("ir", "uv"):
            if band in bands_meta:
                target_images[band] = load_image(settings.uploads_dir / bands_meta[band]["filename"])

        aligned, match_stats = register_bands(visible, target_images)
        fused = false_color_fuse(
            visible,
            aligned.get("ir"),
            aligned.get("uv"),
        )

        dzi_root = settings.dzi_dir / imageset_id
        layers: dict[str, dict] = {}
        layers["visible"] = write_dzi(visible, dzi_root, "visible")
        for band, image in aligned.items():
            layers[band] = write_dzi(image, dzi_root, band)
        layers["fused"] = write_dzi(fused, dzi_root, "fused")

        height, width = visible.shape[:2]
        await report(
            "ready",
            layers=layers,
            width=width,
            height=height,
            match_stats=match_stats,
            processed_at=utcnow(),
        )
    except (RegistrationError, ValueError) as exc:
        await report("failed", error=str(exc))
    except Exception as exc:  # 防止后台任务静默崩溃
        await report("failed", error=f"处理失败: {exc}")
