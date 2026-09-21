"""SIFT 特征配准与多光谱融合引擎。

以可见光图像为基准，对红外/紫外图像做 SIFT 特征匹配 +
RANSAC 单应性估计，warp 到基准坐标系后生成融合图。

POST /api/sets/{image_set_id}/register   执行配准与融合
GET  /api/sets/{image_set_id}            查询图像组状态
"""

import asyncio
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException

from . import db
from .config import RESULT_DIR
from .models import Band, utcnow

router = APIRouter(prefix="/api/sets", tags=["registration"])

MIN_MATCH_COUNT = 10
RATIO_TEST = 0.75


def _to_gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def _enhance(gray: np.ndarray) -> np.ndarray:
    """CLAHE 增强，提升红外/紫外低对比度图像的特征点数量。"""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def estimate_homography(ref_path: str, src_path: str) -> dict:
    """计算 src -> ref 的单应矩阵，返回矩阵与匹配统计。"""
    ref = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
    src = cv2.imread(src_path, cv2.IMREAD_GRAYSCALE)
    if ref is None or src is None:
        raise ValueError("图像读取失败")

    ref_eq, src_eq = _enhance(ref), _enhance(src)

    sift = cv2.SIFT_create()
    kp_ref, des_ref = sift.detectAndCompute(ref_eq, None)
    kp_src, des_src = sift.detectAndCompute(src_eq, None)
    if des_ref is None or des_src is None:
        raise ValueError("特征点不足，无法配准")

    matcher = cv2.BFMatcher(cv2.NORM_L2)
    knn = matcher.knnMatch(des_src, des_ref, k=2)
    good = [m for m, n in knn if m.distance < RATIO_TEST * n.distance]
    if len(good) < MIN_MATCH_COUNT:
        raise ValueError(f"有效匹配点过少: {len(good)} < {MIN_MATCH_COUNT}")

    src_pts = np.float32([kp_src[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    ref_pts = np.float32([kp_ref[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(src_pts, ref_pts, cv2.RANSAC, 5.0)
    if H is None:
        raise ValueError("单应矩阵估计失败")

    return {
        "homography": H,
        "inliers": int(mask.sum()),
        "matches": len(good),
        "ref_shape": ref.shape,
    }


def fuse_bands(visible_path: str, warped: dict[str, np.ndarray], out_path: Path) -> None:
    """融合：可见光亮度 + 红外/紫外伪彩色叠加，突出病害区域反差。"""
    vis = cv2.imread(visible_path, cv2.IMREAD_COLOR)
    vis_f = vis.astype(np.float32) / 255.0

    overlay = np.zeros_like(vis_f)
    if "infrared" in warped:
        ir = _to_gray(warped["infrared"]).astype(np.float32) / 255.0
        overlay[..., 2] = ir  # 红外 -> 红通道
    if "ultraviolet" in warped:
        uv = _to_gray(warped["ultraviolet"]).astype(np.float32) / 255.0
        overlay[..., 0] = uv  # 紫外 -> 蓝通道

    fused = np.clip(0.65 * vis_f + 0.35 * overlay, 0, 1)
    cv2.imwrite(str(out_path), (fused * 255).astype(np.uint8))


def run_registration(image_set: dict) -> dict:
    bands = image_set.get("bands", {})
    if Band.visible.value not in bands:
        raise ValueError("缺少可见光基准图像")

    visible_path = bands[Band.visible.value]["path"]
    warped: dict[str, np.ndarray] = {}
    stats: dict[str, dict] = {}

    ref_gray = cv2.imread(visible_path, cv2.IMREAD_GRAYSCALE)
    h, w = ref_gray.shape

    for band in (Band.infrared.value, Band.ultraviolet.value):
        if band not in bands:
            continue
        result = estimate_homography(visible_path, bands[band]["path"])
        src_img = cv2.imread(bands[band]["path"], cv2.IMREAD_UNCHANGED)
        warped[band] = cv2.warpPerspective(src_img, result["homography"], (w, h))
        stats[band] = {"inliers": result["inliers"], "matches": result["matches"]}

    out_dir = RESULT_DIR / image_set["image_set_id"]
    out_dir.mkdir(parents=True, exist_ok=True)

    fused_path = out_dir / "fused.jpg"
    fuse_bands(visible_path, warped, fused_path)

    aligned_paths = {}
    for band, img in warped.items():
        p = out_dir / f"aligned_{band}.jpg"
        cv2.imwrite(str(p), img)
        aligned_paths[band] = p.name

    return {
        "registered_at": utcnow(),
        "stats": stats,
        "fused_image": fused_path.name,
        "aligned": aligned_paths,
        "width": w,
        "height": h,
    }


@router.post("/{image_set_id}/register")
async def register(image_set_id: str):
    image_set = await db.image_sets().find_one({"image_set_id": image_set_id})
    if not image_set:
        raise HTTPException(404, "图像组不存在")
    try:
        # OpenCV 为 CPU 密集操作，放到线程池避免阻塞事件循环
        result = await asyncio.to_thread(run_registration, image_set)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    await db.image_sets().update_one(
        {"image_set_id": image_set_id},
        {"$set": {"registered": result, "fused_image": result["fused_image"]}},
    )
    return result


@router.get("/{image_set_id}")
async def get_image_set(image_set_id: str):
    doc = await db.image_sets().find_one({"image_set_id": image_set_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "图像组不存在")
    return doc
