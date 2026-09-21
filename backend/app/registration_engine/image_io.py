from __future__ import annotations
from pathlib import Path

import cv2
import numpy as np


def load_image(path: str | Path) -> np.ndarray:
    """读取任意位深/通道图像，统一返回 uint8 BGR（三通道）。"""
    raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise ValueError(f"无法读取图像: {path}")
    return to_uint8_bgr(raw)


def to_uint8_bgr(image: np.ndarray) -> np.ndarray:
    """16 位/高动态范围图像按 1%-99% 分位归一化，并统一为三通道 BGR。"""
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    if image.dtype == np.uint8:
        return image

    work = image.astype(np.float32)
    if work.max() > 1.0:
        lo, hi = np.percentile(work[work > 0] if np.any(work > 0) else work, (1, 99))
        if hi <= lo:
            lo, hi = float(work.min()), float(work.max())
        work = np.clip((work - lo) * 255.0 / (hi - lo + 1e-6), 0, 255)
    else:
        work = np.clip(work * 255.0, 0, 255)
    return work.astype(np.uint8)


def to_gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
