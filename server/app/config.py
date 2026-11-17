import os
from pathlib import Path

# server/ 根目录
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.getenv("TVFLASH_DATA", str(BASE_DIR / "data")))
DB_PATH = DATA_DIR / "tvflash.db"

# 生产环境务必通过环境变量覆盖
SECRET_KEY = os.getenv("TVFLASH_SECRET", "dev-secret-change-me-please-1234567890")
ADMIN_USERNAME = os.getenv("TVFLASH_ADMIN", "admin")
ADMIN_PASSWORD = os.getenv("TVFLASH_PASSWORD", "admin123")

# 前端构建产物目录（Vue 打包后的 dist）
WEB_DIST = Path(os.getenv("TVFLASH_WEB", str(BASE_DIR / "web_dist")))
