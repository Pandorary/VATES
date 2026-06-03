# 常用命令

## 后端启动

```bash
# 从仓库根目录启动（需 PYTHONPATH）
cd D:\AI\vates
PYTHONPATH="backend;." python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## 前端启动

```bash
cd D:\AI\vates\frontend
npx vite --host
```

前端运行在 `http://localhost:5174`，自动代理 `/api` → `http://localhost:8001`。

## 数据库操作

```bash
# SQLite 数据库位置
cd D:\AI\vates\backend

# 连接并查询
python -c "
import sqlite3
conn = sqlite3.connect('vates.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM holdings WHERE is_deleted=0')
for r in cursor.fetchall():
    print(r)
conn.close()
"
```

## 手动触发 GitHub 同步

```bash
cd D:\AI\vates
PYTHONPATH="backend;." python -c "
from app.services.github_sync import sync_github_topics
import asyncio
asyncio.run(sync_github_topics(limit=3))
"
```

## 停止服务

```bash
# 停止后端
taskkill //f //pid $(netstat -ano | grep ':8001.*LISTENING' | awk '{print $NF}') 2>/dev/null

# 停止前端
taskkill //f //pid $(netstat -ano | grep ':5174.*LISTENING' | awk '{print $NF}') 2>/dev/null
```

## API 调试

```bash
# 健康检查
curl http://localhost:8001/api/health

# 定时任务状态
curl http://localhost:8001/api/admin/jobs

# 持仓列表
curl http://localhost:8001/api/v1/holdings

# 预测跟踪列表
curl http://localhost:8001/api/v1/tracking

# 搜索分类
curl -X POST http://localhost:8001/api/v1/search -H "Content-Type: application/json" -d "{\"query\":\"茅台\"}"
```
