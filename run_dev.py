"""开发模式启动入口 — 自动设置 PYTHONPATH（支持 reload）"""
import os
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"

# 通过环境变量传递，uvicorn reloader 子进程也能继承
os.environ.setdefault("PYTHONPATH", f"{ROOT}{os.pathsep}{BACKEND}")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8001, reload=True)
