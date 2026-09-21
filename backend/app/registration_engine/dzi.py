"""纯 OpenCV 实现的 Deep Zoom Image (DZI) 金字塔生成。

输出 OpenSeadragon 兼容的 {name}.dzi 描述文件与 {name}_files/{level}/{x}_{y}.jpg 瓦片。
"""

from pathlib import Path

import cv2
import numpy as np

TILE_SIZE = 256
TILE_OVERLAP = 0


def _level_dimensions(width: int, height: int) -> list[tuple[int, int, float]]:
    levels = int(np.ceil(np.log2(max(width, height)))) + 1
    dims: list[tuple[int, int, float]] = []
    for level in range(levels):
        scale = 0.5 ** (levels - 1 - level)
        dims.append((max(1, int(round(width * scale))), max(1, int(round(height * scale))), scale))
    return dims


def write_dzi(image: np.ndarray, output_dir: Path, name: str, jpeg_quality: int = 85) -> dict:
    output_dir = Path(output_dir)
    files_dir = output_dir / f"{name}_files"
    files_dir.mkdir(parents=True, exist_ok=True)

    height, width = image.shape[:2]
    dims = _level_dimensions(width, height)
    max_level = len(dims) - 1

    for level, (level_w, level_h, scale) in enumerate(dims):
        level_dir = files_dir / str(level)
        level_dir.mkdir(exist_ok=True)
        if level == max_level:
            pyramid = image
        else:
            pyramid = cv2.resize(image, (level_w, level_h), interpolation=cv2.INTER_AREA)

        cols = int(np.ceil(level_w / TILE_SIZE))
        rows = int(np.ceil(level_h / TILE_SIZE))
        for col in range(cols):
            for row in range(rows):
                x0 = col * TILE_SIZE
                y0 = row * TILE_SIZE
                tile = pyramid[y0:y0 + TILE_SIZE, x0:x0 + TILE_SIZE]
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
                cv2.imwrite(str(level_dir / f"{col}_{row}.jpg"), tile, encode_params)

    dzi_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" TileSize="256" Overlap="0" Format="jpg">\n'
        f'  <Size Width="{width}" Height="{height}"/>\n'
        '</Image>\n'
    )
    (output_dir / f"{name}.dzi").write_text(dzi_xml, encoding="utf-8")

    return {
        "type": "image/jpeg",
        "tilesUrl": f"/tiles/{name}_files/",
        "tileSize": TILE_SIZE,
        "overlap": TILE_OVERLAP,
        "width": width,
        "height": height,
        "minLevel": 0,
        "maxLevel": max_level,
    }
