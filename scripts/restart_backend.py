"""重启后端服务 — 可靠地杀掉端口占用并启动"""
import subprocess
import sys
import time
from pathlib import Path

# 项目根目录（脚本位于 scripts/ 子目录）
ROOT = Path(__file__).resolve().parent.parent
PORT = 8001


def kill_port(port: int) -> bool:
    """杀掉占用指定端口的进程（Windows）"""
    try:
        import subprocess
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, shell=True,
        )
        pids = set()
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                if pid.isdigit():
                    pids.add(pid)

        if not pids:
            print(f"[OK] 端口 {port} 未被占用")
            return True

        print(f"[INFO] 端口 {port} 被以下 PID 占用: {', '.join(pids)}")
        for pid in pids:
            r = subprocess.run(
                ["taskkill", "/f", "/pid", pid],
                capture_output=True, text=True, shell=True,
            )
            if r.returncode != 0:
                print(f"[WARN] 杀掉 PID {pid} 失败: {r.stderr.strip()}")
            else:
                print(f"[OK] 已杀掉 PID {pid}")

        time.sleep(1)
        return True
    except Exception as e:
        print(f"[ERROR] kill_port: {e}")
        return False


def start_backend():
    """启动后端"""
    os.environ.setdefault("PYTHONPATH", f"{ROOT}{os.pathsep}{ROOT / 'backend'}")
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "backend"))

    import uvicorn
    print(f"[INFO] 启动后端 on port {PORT}...")
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
    )


if __name__ == "__main__":
    import os
    os.chdir(ROOT)
    kill_port(PORT)
    start_backend()
