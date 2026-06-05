# 业务服务参考

> 所有服务位于 `backend/app/services/`

## LLM 与数据

| 文件 | 功能 | 关键接口 |
|------|------|----------|
| `services/data_engine/` | 数据引擎包 — 行情采集 + 预测数据组装 | 详见下方 |
| `services/news/` | 新闻采集 | `NewsCollector` |
| `services/llm.py` | LLM 调用封装 | `chat(messages)` → `{"content", "model", "usage"}` |

## 数据引擎 (`services/data_engine/`)

| 文件 | 功能 |
|------|------|
| `base.py` | 接口定义 — `QuoteData` 模型, `QuoteProvider` ABC |
| `tencent.py` | 腾讯行情适配器（主数据源，支持批量） |
| `eastmoney.py` | 东方财富行情适配器（次数据源） |
| `sina.py` | 新浪行情适配器（第三数据源） |
| `failover.py` | 故障转移管理器 — 按优先级获取，支持批量 |
| `manager.py` | 行情管理器单例 — TTL 缓存 + 故障转移 + DB 回退 |
| `scheduler.py` | APScheduler 调度 — `start_scheduler()` / `stop_scheduler()` |
| `assembler.py` | 预测数据组装 — `fetch_stock_data()` / `fetch_industry_data()` / `get_active_template()` |

## 定时任务 (`backend/app/tasks/`)

| 文件 | 功能 |
|------|------|
| `quote_jobs.py` | 定时行情采集（每1分钟） |
| `news_jobs.py` | 定时新闻采集（每5分钟） |
