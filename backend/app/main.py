from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.annotation_api.routes import router as annotation_router
from app.auth_routes import router as auth_router
from app.config import settings
from app.database import close_db, connect_db
from app.project_routes import router as project_router
from app.upload_handler.routes import router as upload_router
from app.ws_routes import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(title="敦煌壁画多光谱图像处理平台", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(upload_router)
app.include_router(annotation_router)
app.include_router(ws_router)

# OpenSeadragon 金字塔瓦片
# check_dir=False：瓦片由上传后的后台流水线动态生成，启动时尚不存在，
# 关闭启动期目录快照校验，避免新写入瓦片被误判 404。
app.mount("/tiles", StaticFiles(directory=str(settings.dzi_dir), check_dir=False), name="tiles")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "mural-multispectral-platform"}
