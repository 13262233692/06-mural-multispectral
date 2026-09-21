"""多波段伪彩色融合。"""
from __future__ import annotations

import cv2
import numpy as np

from app.registration_engine.image_io import to_gray


def _stretch(channel: np.ndarray) -> np.ndarray:
    nonzero = channel[channel > 0]
    if nonzero.size == 0:
        return channel
    lo, hi = np.percentile(nonzero, (1, 99))
    if hi <= lo:
        return channel
    out = np.clip((channel.astype(np.float32) - lo) * 255.0 / (hi - lo), 0, 255)
    return out.astype(np.uint8)


def false_color_fuse(visible: np.ndarray, ir: np.ndarray | None, uv: np.ndarray | None) -> np.ndarray:
    """生成伪彩色合成 BGR 图：

    - B 通道: 紫外（凸显霉变/有机附着物）
    - G 通道: 可见光亮度（壁画本体）
    - R 通道: 红外（凸显起甲/底层线稿）
    """
    h, w = visible.shape[:2]
    vis_gray = _stretch(to_gray(visible))
    ir_gray = _stretch(to_gray(ir)) if ir is not None else np.zeros((h, w), np.uint8)
    uv_gray = _stretch(to_gray(uv)) if uv is not None else np.zeros((h, w), np.uint8)
    return cv2.merge([uv_gray, vis_gray, ir_gray])
