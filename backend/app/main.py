"""敦煌壁画多光谱图像处理平台 — 后端入口。

启动: uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import annotation_api, db, registration_engine, upload_handler
from .config import RESULT_DIR

app = FastAPI(title="Mural Multispectral Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_handler.router)
app.include_router(registration_engine.router)
app.include_router(annotation_api.router)

# 配准/融合结果静态访问，供 OpenSeadragon 加载
app.mount("/results", StaticFiles(directory=RESULT_DIR), name="results")


@app.on_event("startup")
async def startup() -> None:
    await db.ensure_indexes()


@app.get("/api/health")
async def health():
    return {"status": "ok"}
