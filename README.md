# 敦煌壁画多光谱图像处理平台

面向敦煌研究院的壁画病害协作标注平台：上传可见光 / 红外 / 紫外三波段图像，
后端用 OpenCV SIFT 特征配准并融合，前端用 OpenSeadragon 展示并圈选病害区域
（起甲 / 酥碱 / 霉变），标注数据存 MongoDB，支持多用户协作与版本回滚。

## 架构

```
backend/                        FastAPI + OpenCV + Motor(MongoDB)
  app/
    main.py                     应用入口、CORS、静态结果目录
    config.py                   环境配置（MONGO_URI / 存储目录等）
    db.py                       MongoDB 连接与集合
    models.py                   Pydantic 数据模型（病害标签枚举等）
    upload_handler.py           项目管理 + 三波段图像上传
    registration_engine.py      SIFT 配准（CLAHE 增强 + RANSAC 单应）+ 伪彩融合
    annotation_api.py           标注 CRUD、乐观锁并发、版本快照与回滚
frontend/                       Vue3 + OpenSeadragon (Vite)
  src/
    viewer/viewer_core.js       OSD 查看器封装、图像/视口坐标转换
    viewer/annotation_layer.js  SVG 标注层：多边形圈选、选中、删除
    project/project_manager.js  协作状态：保存/冲突重试/轮询同步/回滚
    api/client.js               REST 客户端
```

## 快速开始

前置：MongoDB 运行于 `mongodb://localhost:27017`（可用 `MURAL_MONGO_URI` 覆盖）。

```bash
# 后端
cd backend
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev        # http://localhost:5173 ，/api 与 /results 代理到 8000
```

## 使用流程

1. 输入用户名，创建项目（如"莫高窟第 220 窟"）。
2. 分别上传可见光、红外、紫外三个波段的图像。
3. 点击「SIFT 配准 + 融合」：以可见光为基准估计单应矩阵，
   将红外/紫外 warp 到统一坐标系并生成伪彩融合图。
4. 在融合图上用「圈选」模式按病害类型（起甲/酥碱/霉变）绘制多边形，
   双击闭合；「保存」生成一个新版本。
5. 侧栏「版本历史」可查看每次提交的作者与说明，并一键回滚
   （回滚本身生成新版本，历史不可变）。

## 协作与版本模型

- **乐观锁**：保存时携带 `base_version`，与服务端不一致返回 409，
  前端自动拉取最新标注后提示重试。
- **版本快照**：每次保存/回滚把当前全部标注快照进 `annotation_versions`，
  支持回滚到任意历史版本。
- **多用户同步**：前端每 5s 轮询 `/annotations/poll?since=N`，
  他人提交后自动刷新（本地有未保存修改时暂停同步，避免覆盖）。

## 主要 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/projects` | 创建项目 |
| POST | `/api/projects/{id}/images?band=visible\|infrared\|ultraviolet` | 上传波段图像 |
| POST | `/api/sets/{id}/register` | SIFT 配准 + 融合 |
| GET  | `/api/sets/{id}/annotations` | 当前标注 + 版本号 |
| POST | `/api/sets/{id}/annotations/save` | 批量保存（乐观锁） |
| GET  | `/api/sets/{id}/annotations/versions` | 版本历史 |
| POST | `/api/sets/{id}/annotations/rollback` | 回滚到指定版本 |
| GET  | `/api/sets/{id}/annotations/poll?since=N` | 协作轮询 |
