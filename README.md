# 敦煌壁画多光谱图像处理平台

面向壁画保护修复的多光谱采集与协同标注平台。上传同一区域的**可见光 / 红外 / 紫外**三波段图像，
后端以可见光为基准完成 **SIFT 特征配准**，生成**伪彩色融合图**与 OpenSeadragon 深度缩放金字塔；
前端在配准后的影像上标注 **起甲 / 酥碱 / 霉变** 三类病害，支持**多用户实时协作**与**标注版本快照回滚**。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python · FastAPI · OpenCV(headless) · NumPy · Motor(异步 MongoDB 驱动) · WebSocket |
| 前端 | Vue 3 · Vite · Pinia · Vue Router · OpenSeadragon · 原生 SVG 标注层 |
| 存储 | MongoDB（用户 / 项目 / 图像集元数据 / 标注 / 版本快照），本地文件系统存原图与瓦片 |

## 核心处理流程

1. **分波段上传**：可见光为必传基准，红外/紫外可选；文件落盘后创建图像集（`status=uploaded`）。
2. **后台流水线**（FastAPI `BackgroundTasks`，非阻塞）：
   - `registration_engine.image_io`：兼容 8/16 位、灰度/多通道，按 1%–99% 分位归一化为 uint8 BGR；
   - `registration_engine.sift_registration`：CLAHE 增强 → SIFT 特征（4000 点）→ FLANN KNN 匹配
     （Lowe 0.75 比率筛选）→ RANSAC 单应性矩阵 → `warpPerspective` 将红外/紫外对齐到可见光坐标系；
   - `registration_engine.fusion`：伪彩色合成 **B=紫外 / G=可见光亮度 / R=红外**，
     便于在一张图上同时分辨霉变（蓝）、壁画本体（绿）、起甲与底层线稿（红）；
   - `registration_engine.dzi`：纯 OpenCV 为四个图层（可见光/红外/紫外/融合）生成 256px JPEG 瓦片金字塔。
3. 处理状态经 WebSocket 实时推送给前端（`processing → ready/failed`），失败可一键重新配准。

## 协同与版本机制

- **实时协作**：每个图像集一条 WebSocket 房间；他人增改删标注、提交版本、回滚、在线光标均即时广播。
- **乐观并发**：客户端保存进入图像集时的基准版本号，写请求带 `X-Base-Version`；他人已提交新版本时返回
  `409`，避免多人覆盖。
- **版本回滚**：每次“提交版本”保存当时**全部标注的全量快照**（实现简单、恢复确定、天然审计留痕）；
  回滚到历史版本 = 用该快照重建标注集，并**追加一个新版本**，因此历史永不丢失。

## 模块划分（按需求分离）

**后端**

```
backend/app/
├── upload_handler/          # 上传与配准触发
│   ├── routes.py            #   多波段 multipart 上传 / 查询 / 重新配准
│   └── pipeline.py          #   后台配准-融合-DZI 流水线 + 状态广播
├── registration_engine/     # 图像处理核心（不依赖 Web/DB，可独立测试）
│   ├── image_io.py          #   多格式读取、位深归一化
│   ├── sift_registration.py #   SIFT + FLANN + RANSAC 配准
│   ├── fusion.py            #   多波段伪彩色融合
│   └── dzi.py               #   OpenSeadragon DZI 瓦片金字塔
├── annotation_api/          # 标注与版本
│   ├── routes.py            #   标注 CRUD、乐观锁、版本列表/提交、回滚
│   └── versioning.py        #   全量快照与回滚恢复
├── ws_hub.py / ws_routes.py # 协作 WebSocket 房间与光标转发
├── project_routes.py        # 项目、成员、图像集列表
├── auth_routes.py / security.py  # 注册登录、JWT、密码哈希
├── models.py / database.py / config.py / main.py
```

**前端**

```
frontend/src/
├── modules/
│   ├── viewer_core/         # OpenSeadragon 封装：多波段图层切换、视口/图像坐标换算
│   │   └── viewer_core.js
│   ├── annotation_layer/    # SVG 标注覆盖层：多边形/矩形绘制、命中选中、远程光标
│   │   └── annotation_layer.js
│   └── project_manager/     # 领域中枢：项目/图像集/标注状态 + 协作事件桥接
│       └── project_manager.js
├── api/                     # axios 接口封装 + WebSocket 客户端
├── stores/auth.js           # Pinia 登录态
├── components/              # MuralViewer / Toolbar / UploadPanel / AnnotationPanel / VersionPanel
└── views/                   # LoginView / ProjectListView / WorkbenchView
```

## 数据模型（MongoDB 集合）

- `users`：用户名（唯一）、密码哈希（pbkdf2_sha256）、显示名。
- `projects`：名称、描述、创建者、`members[]`、创建时间。
- `imagesets`：所属项目、标题、`status`、三波段文件信息、`layers`(DZI 描述)、
  图像宽高、`match_stats`(SIFT 匹配点数/内点数)、错误信息、时间戳。
- `annotations`：所属图像集、`disease_type`(flaking/efflorescence/mold)、
  `geometry`(`{type: polygon|rectangle|point, coordinates: [[x,y],...]}`，坐标为**原图像素**)、
  置信度、备注、创建/更新者与时间。
- `annotation_versions`：图像集、版本号、全量标注快照、标注数、提交者、备注、时间（版本号唯一索引）。

## 本地启动

需要 Docker（用于 MongoDB）、Python 3.9+、Node 18+。

**1) 启动 MongoDB**

```bash
docker run -d --name mural-mongo -p 27017:27017 mongo:7
# 或： docker compose up -d mongo
```

**2) 启动后端（端口 8011）**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 按需修改 JWT_SECRET
python run.py                 # 或 uvicorn app.main:app --port 8011
```

**3) 启动前端（端口 5173）**

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173 ，注册两个账号即可体验协作（一个项目“添加成员”后两人同时打开同一图像集）。

**一键 Docker 部署**（MongoDB + 后端；前端可 `npm run build` 后用任意静态服务器托管 `dist/`）：

```bash
docker compose up -d --build
```

## 主要 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register` · `/api/auth/login` | 注册 / 登录，返回 JWT |
| GET/POST | `/api/projects` | 项目列表 / 创建 |
| POST | `/api/projects/{id}/members` | 添加协作成员 |
| POST | `/api/projects/{id}/imagesets` | multipart 上传 visible/ir/uv，触发配准 |
| GET | `/api/projects/{id}/imagesets/{sid}` | 查询配准状态与图层 DZI 信息 |
| GET/POST | `/api/imagesets/{sid}/annotations` | 标注列表 / 新建 |
| PATCH/DELETE | `/api/imagesets/{sid}/annotations/{aid}` | 修改 / 删除 |
| GET/POST | `/api/imagesets/{sid}/versions` | 版本列表 / 提交快照 |
| POST | `/api/imagesets/{sid}/rollback` | 回滚到指定版本（生成新版本） |
| WS | `/ws/imagesets/{sid}?token=<JWT>` | 协作事件与在线光标 |

写类标注接口支持可选请求头 `X-Base-Version: <int>` 做乐观锁校验。交互式文档见 `/docs`。

## 测试

```bash
cd backend && source .venv/bin/activate
python scripts/test_registration.py   # 合成图验证 SIFT 配准/融合/DZI（无需数据库）
python scripts/smoke_e2e.py           # 端到端：注册→上传→配准→标注→版本→回滚→409（需后端与 Mongo 运行）
```

## 病害类型与配色

| 编码 | 名称 | 标注颜色 | 多光谱线索（融合图） |
| --- | --- | --- | --- |
| `flaking` | 起甲 | 红 `#e8504a` | 红外通道反射强，显翘起边缘与下层线稿 |
| `efflorescence` | 酥碱 | 黄 `#f2b134` | 可见光层可见泛白、粉化区域 |
| `mold` | 霉变 | 绿 `#3aa55a` | 紫外激发荧光，蓝通道异常 |

## 说明与后续可扩展点

- 当前认证为平台自带 JWT，便于内网独立部署；可对接院所统一身份认证（LDAP/OAuth）。
- 版本采用全量快照，标注规模极大时可改为事件溯源 + 定期快照压缩。
- 配准现使用单应性矩阵（平面壁画近似）；对曲面洞窟壁可升级为 TPS/薄板样条非刚性配准。
- 可增加病害面积自动量算、配准特征点可视化、标注导出 GeoJSON/Shapefile 等。
