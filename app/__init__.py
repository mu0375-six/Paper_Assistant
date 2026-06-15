"""ScholarFlow FastAPI 应用工厂。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .deepseek_client import DeepSeekClient
from .main import BASE_DIR, DATA_DIR, create_router
from .scholar_service import ScholarService
from .storage import JsonStore


def create_app() -> FastAPI:
    app = FastAPI(
        title="ScholarFlow API",
        description="AI 辅助学术论文阅读与写作平台",
        version="1.0.0",
    )

    # CORS：允许前端本地开发访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 静态文件
    web_dir = BASE_DIR / "web"
    if web_dir.exists():
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

    # 初始化服务
    store = JsonStore(DATA_DIR)
    llm_client = DeepSeekClient()
    scholar = ScholarService(store, llm_client)

    # 注册路由
    router = create_router(store, llm_client, scholar)
    app.include_router(router)

    return app
