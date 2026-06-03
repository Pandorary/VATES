# 业务服务参考

> 所有服务位于 `backend/app/services/`

## LLM 与数据

| 文件 | 功能 | 关键接口 |
|------|------|----------|
| `services/llm.py` | LLM 调用封装 | `chat(messages)` → `{"content", "model", "usage"}` |
| `services/data_engine.py` | 数据引擎（采集+组装） | 为预测提供结构化数据 |

## 行情采集子系统 (`services/quotes/`)

| 文件 | 功能 |
|------|------|
| `base.py` | 接口定义 — `QuoteData` dataclass, `QuoteProvider` ABC |
| `tencent.py` | 腾讯行情源（实时行情） |
| `eastmoney.py` | 东方财富行情源（实时行情） |
| `sina.py` | 新浪行情源（实时行情） |
| `failover.py` | 故障转移管理 — 按优先级获取，支持批量 |
| `cross_validate.py` | 多源交叉验证 |
| `manager.py` | 行情管理器单例 — TTL 缓存 + 故障转移 + DB 回退 |
| `scheduler.py` | APScheduler 调度 — `start_scheduler()` / `stop_scheduler()` |

## 定时任务 (`backend/app/tasks/`)

| 文件 | 功能 |
|------|------|
| `quote_jobs.py` | 定时行情采集（APScheduler 触发） |
