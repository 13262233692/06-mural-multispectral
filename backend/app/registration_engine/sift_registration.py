"""基于 SIFT 特征 + FLANN 匹配 + RANSAC 单应性矩阵的波段配准。"""

import cv2
import numpy as np

from app.registration_engine.image_io import to_gray

MIN_MATCHES = 8


class RegistrationError(RuntimeError):
    pass


def _enhance_for_matching(gray: np.ndarray) -> np.ndarray:
    """CLAHE 局部对比度增强，改善红外/紫外低对比图像的特征提取。"""
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _match_homography(reference_gray: np.ndarray, target_gray: np.ndarray) -> tuple[np.ndarray, dict]:
    detector = cv2.SIFT_create(nfeatures=4000)
    kp_ref, desc_ref = detector.detectAndCompute(_enhance_for_matching(reference_gray), None)
    kp_tgt, desc_tgt = detector.detectAndCompute(_enhance_for_matching(target_gray), None)
    if desc_ref is None or desc_tgt is None or len(kp_ref) < MIN_MATCHES or len(kp_tgt) < MIN_MATCHES:
        raise RegistrationError("有效 SIFT 特征点不足，无法配准")

    index_params = {"algorithm": 1, "trees": 5}  # FLANN_INDEX_KDTREE
    search_params = {"checks": 50}
    matcher = cv2.FlannBasedMatcher(index_params, search_params)
    knn = matcher.knnMatch(desc_tgt, desc_ref, k=2)

    good = [m for m, n in knn if m.distance < 0.75 * n.distance]
    if len(good) < MIN_MATCHES:
        raise RegistrationError(f"可靠匹配点不足（{len(good)}/{MIN_MATCHES}）")

    src = np.float32([kp_tgt[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_ref[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    homography, inlier_mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    if homography is None:
        raise RegistrationError("RANSAC 单应性矩阵求解失败")

    inliers = int(inlier_mask.sum()) if inlier_mask is not None else len(good)
    return homography, {"keypoints_ref": len(kp_ref), "keypoints_target": len(kp_tgt),
                        "good_matches": len(good), "inliers": inliers}


def register_bands(reference: np.ndarray, targets: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], dict]:
    """以参考图像（可见光）坐标系为基准，将红外/紫外 warp 对齐。

    返回: (对齐后的各波段图像, 匹配统计数据)
    """
    ref_gray = to_gray(reference)
    aligned: dict[str, np.ndarray] = {}
    stats: dict[str, dict] = {}
    for band, image in targets.items():
        homography, band_stats = _match_homography(ref_gray, to_gray(image))
        warped = cv2.warpPerspective(
            image, homography, (reference.shape[1], reference.shape[0]),
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0),
        )
        aligned[band] = warped
        stats[band] = band_stats
    return aligned, stats
