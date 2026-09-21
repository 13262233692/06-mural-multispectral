"""合成多光谱测试图，验证 SIFT 配准 + 伪彩色融合 + DZI 输出。

运行: python scripts/test_registration.py
"""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.registration_engine import false_color_fuse, register_bands, write_dzi


def make_mural(width: int = 1400, height: int = 1000) -> np.ndarray:
    rng = np.random.default_rng(42)
    image = np.full((height, width, 3), (176, 156, 130), np.uint8)
    # 模拟壁画纹理：圆斑（酥碱）、色块、大量可提取特征的边界
    for _ in range(60):
        center = (int(rng.integers(100, width - 100)), int(rng.integers(100, height - 100)))
        color = tuple(int(c) for c in rng.integers(60, 220, size=3))
        cv2.circle(image, center, int(rng.integers(12, 70)), color, -1)
    for _ in range(30):
        p1 = (int(rng.integers(0, width)), int(rng.integers(0, height)))
        p2 = (int(rng.integers(0, width)), int(rng.integers(0, height)))
        cv2.line(image, p1, p2, (60, 50, 40), int(rng.integers(2, 6)))
    cv2.rectangle(image, (200, 200), (1200, 800), (90, 70, 50), 8)
    return image


def warp_band(image: np.ndarray, shift: float = 1.0) -> np.ndarray:
    """施加已知透视变换 + 轻微模糊，模拟不同波段相机位置差异。"""
    matrix = np.array([[1.02, 0.03, -28], [-0.02, 0.98, 22], [0.00002, 0.00001, 1.0]])
    return cv2.warpPerspective(image, matrix, (image.shape[1], image.shape[0]))


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "data" / "test_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    visible = make_mural()
    ir = warp_band(visible)
    uv = warp_band(visible)
    # 让红外/紫外呈现不同的强度分布
    ir = cv2.convertScaleAbs(ir, alpha=0.7, beta=30)
    uv = cv2.convertScaleAbs(uv, alpha=1.3, beta=-40)

    aligned, stats = register_bands(visible, {"ir": ir, "uv": uv})
    for band, stat in stats.items():
        print(f"[{band}] 特征点 {stat['keypoints_target']} / 良好匹配 {stat['good_matches']} / RANSAC 内点 {stat['inliers']}")
        assert stat["inliers"] > 20, f"{band} 内点过少，配准可能失败"

    fused = false_color_fuse(visible, aligned["ir"], aligned["uv"])
    assert fused.shape == visible.shape

    dzi_meta = write_dzi(fused, out_dir, "fused")
    print(f"DZI 金字塔: {dzi_meta['width']}x{dzi_meta['height']}, maxLevel={dzi_meta['maxLevel']}")

    # 校验对齐误差（warp 后 IR 与可见光应高度重合）
    diff_before = np.mean(np.abs(visible.astype(int) - ir.astype(int)))
    diff_after = np.mean(np.abs(visible.astype(int) - aligned["ir"].astype(int)))
    print(f"配准前后平均像素差异: {diff_before:.1f} -> {diff_after:.1f}")
    assert diff_after < diff_before, "配准后差异未减小"

    top_tile = out_dir / "fused_files" / str(dzi_meta["maxLevel"]) / "0_0.jpg"
    assert top_tile.exists(), "最高层瓦片未生成"
    print(f"OK: 测试产物位于 {out_dir}")


if __name__ == "__main__":
    main()
