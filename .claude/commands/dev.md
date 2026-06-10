# /dev — 常用开发命令参考

当用户运行 `/dev` 时，列出以下常用开发命令。

---

## 后端

```powershell
cd D:\AI\vates
$env:PYTHONPATH = "D:\AI\vates;D:\AI\vates\backend"
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
```

## 前端

```bash
cd D:/AI/vates/frontend
npm run dev
# → localhost:5174，自动代理 /api → localhost:8001
```

## 数据库 (SQLite)

```bash
cd D:/AI/vates/db

# 查询持仓
py -c "
import sqlite3
conn = sqlite3.connect('vates.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM holdings WHERE is_deleted=0')
for r in cursor.fetchall():
    print(r)
conn.close()
"
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
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"茅台"}'
```

## 停止服务

```bash
# 后端
taskkill //f //pid $(netstat -ano | grep ':8001.*LISTENING' | awk '{print $NF}') 2>/dev/null

# 前端
taskkill //f //pid $(netstat -ano | grep ':5174.*LISTENING' | awk '{print $NF}') 2>/dev/null
```
