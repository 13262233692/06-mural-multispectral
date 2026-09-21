"""端到端冒烟测试（需后端运行在 BASE_URL）。

流程：注册两个用户 -> 建项目/加成员 -> 上传三波段 -> 轮询配准 ->
     增改删标注 -> 提交版本 -> 回滚 -> 校验数据一致性。
"""

import io
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import requests

BASE_URL = "http://localhost:8011"


def jpeg_bytes(image: np.ndarray) -> io.BytesIO:
    buf = io.BytesIO()
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    buf.write(encoded.tobytes())
    buf.seek(0)
    return buf


def make_bands() -> dict[str, np.ndarray]:
    rng = np.random.default_rng(7)
    base = np.full((900, 1200, 3), (170, 150, 120), np.uint8)
    for _ in range(50):
        cv2.circle(
            base,
            (int(rng.integers(80, 1120)), int(rng.integers(80, 820))),
            int(rng.integers(15, 60)),
            tuple(int(c) for c in rng.integers(50, 220, 3)),
            -1,
        )
    matrix = np.array([[1.02, 0.02, -20], [-0.01, 0.99, 15], [0.0, 0.0, 1.0]])
    ir = cv2.warpPerspective(base, matrix, (1200, 900))
    uv = cv2.warpPerspective(base, matrix, (1200, 900))
    return {"visible": base, "ir": ir, "uv": uv}


def main() -> None:
    suffix = str(int(time.time()))
    user_a, user_b = f"restorer_a{suffix}", f"restorer_b{suffix}"

    # 1. 注册
    resp = requests.post(f"{BASE_URL}/api/auth/register", json={
        "username": user_a, "password": "pass1234", "display_name": "修复师甲",
    }, timeout=10)
    assert resp.status_code == 200, resp.text
    token_a = resp.json()["access_token"]
    resp = requests.post(f"{BASE_URL}/api/auth/register", json={
        "username": user_b, "password": "pass1234", "display_name": "修复师乙",
    }, timeout=10)
    assert resp.status_code == 200, resp.text
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print("✓ 两个用户注册成功")

    # 2. 建项目并加成员
    project = requests.post(f"{BASE_URL}/api/projects", headers=headers_a, json={
        "name": f"第 {suffix} 窟", "description": "冒烟测试窟区",
    }, timeout=10).json()
    project_id = project["id"]
    members = requests.post(f"{BASE_URL}/api/projects/{project_id}/members",
                            headers=headers_a, json={"username": user_b}, timeout=10).json()
    assert user_b in members["members"]
    print("✓ 项目创建，协作成员加入")

    # 3. 上传三波段
    bands = make_bands()
    with jpeg_bytes(bands["visible"]) as vis, jpeg_bytes(bands["ir"]) as ir, jpeg_bytes(bands["uv"]) as uv:
        resp = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/imagesets",
            headers=headers_a,
            files={"visible": ("visible.jpg", vis, "image/jpeg"),
                   "ir": ("ir.jpg", ir, "image/jpeg"),
                   "uv": ("uv.jpg", uv, "image/jpeg")},
            data={"title": "南壁局部"},
            timeout=60,
        )
    assert resp.status_code == 200, resp.text
    imageset = resp.json()
    imageset_id = imageset["id"]
    print(f"✓ 三波段上传完成，图像集 {imageset_id}")

    # 4. 轮询配准结果
    for _ in range(30):
        info = requests.get(f"{BASE_URL}/api/projects/{project_id}/imagesets/{imageset_id}",
                            headers=headers_a, timeout=10).json()
        if info["status"] in {"ready", "failed"}:
            break
        time.sleep(1)
    assert info["status"] == "ready", f"配准未就绪: {info.get('error')}"
    assert {"visible", "ir", "uv", "fused"} <= set(info["layers"])
    assert info["match_stats"]["ir"]["inliers"] > 20
    print(f"✓ SIFT 配准完成（IR 内点 {info['match_stats']['ir']['inliers']}），DZI 四层就绪")

    # 5. 标注增改
    annotation = requests.post(
        f"{BASE_URL}/api/imagesets/{imageset_id}/annotations",
        headers=headers_a,
        json={"disease_type": "flaking",
              "geometry": {"type": "polygon",
                           "coordinates": [[100, 100], [300, 100], [300, 260], [100, 260]]},
              "note": "甲标注"},
        timeout=10,
    ).json()
    annotation_id = annotation["id"]
    requests.patch(f"{BASE_URL}/api/imagesets/{imageset_id}/annotations/{annotation_id}",
                   headers=headers_a,
                   json={"disease_type": "mold", "note": "乙复核改为霉变"}, timeout=10)
    # 用户乙也能看到标注（协作）
    token_b = requests.post(f"{BASE_URL}/api/auth/login",
                            json={"username": user_b, "password": "pass1234"}, timeout=10).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    seen = requests.get(f"{BASE_URL}/api/imagesets/{imageset_id}/annotations",
                        headers=headers_b, timeout=10).json()
    assert len(seen) == 1 and seen[0]["disease_type"] == "mold"
    print("✓ 标注创建/修改成功，协作成员可实时读取")

    # 6. 提交 v1，再加一条标注，提交 v2
    v1 = requests.post(f"{BASE_URL}/api/imagesets/{imageset_id}/versions",
                       headers=headers_a, params={"comment": "初次标注"}, timeout=10).json()["version"]
    assert v1 == 1
    requests.post(f"{BASE_URL}/api/imagesets/{imageset_id}/annotations", headers=headers_b,
                  json={"disease_type": "efflorescence",
                        "geometry": {"type": "rectangle",
                                     "coordinates": [[400, 400], [600, 400], [600, 550], [400, 550]]}},
                  timeout=10)
    v2 = requests.post(f"{BASE_URL}/api/imagesets/{imageset_id}/versions",
                       headers=headers_b, params={"comment": "新增酥碱"}, timeout=10).json()["version"]
    assert v2 == 2
    print("✓ 版本 v1/v2 快照提交成功")

    # 7. 回滚到 v1：应只剩 1 条标注，并生成 v3
    result = requests.post(f"{BASE_URL}/api/imagesets/{imageset_id}/rollback",
                           headers=headers_a, json={"version": 1, "comment": "回滚验证"}, timeout=10).json()
    assert result["new_version"] == 3
    assert len(result["annotations"]) == 1
    assert result["annotations"][0]["disease_type"] == "mold"
    versions = requests.get(f"{BASE_URL}/api/imagesets/{imageset_id}/versions",
                            headers=headers_a, timeout=10).json()
    assert [v["version"] for v in versions] == [3, 2, 1]
    print("✓ 回滚到 v1 成功：标注恢复为 1 条，历史版本完整保留（v3/v2/v1）")

    # 8. 乐观锁冲突：携带过期版本号应 409
    conflict = requests.post(
        f"{BASE_URL}/api/imagesets/{imageset_id}/annotations",
        headers={**headers_a, "X-Base-Version": "1"},
        json={"disease_type": "flaking",
              "geometry": {"type": "point", "coordinates": [[50, 50]]}},
        timeout=10,
    )
    assert conflict.status_code == 409
    print("✓ 乐观锁版本冲突正确返回 409")

    print("\n全部端到端冒烟测试通过 🎉")


if __name__ == "__main__":
    sys.exit(main())
