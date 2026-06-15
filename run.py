import os
from pathlib import Path

from dotenv import load_dotenv

# 自动加载项目根目录下的 .env 文件，无需每次手动设置环境变量
load_dotenv(Path(__file__).resolve().parent / ".env")

import uvicorn
from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    uvicorn.run(
        "app:create_app" if not debug else app,
        host="0.0.0.0",
        port=5000,
        reload=debug,
        factory=True if not debug else False,
    )
