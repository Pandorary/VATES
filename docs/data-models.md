# 数据模型参考

> 所有 ORM 模型位于 `backend/app/models/`，使用 SQLAlchemy 2.0 DeclarativeBase

## 核心业务表

| 文件 | 主要表 | 关键字段 |
|------|--------|----------|
| `stock.py` | `stocks` | code, name, industry |
| | `daily_quotes` | 日 K 线 |
| | `stock_quotes` | 最新行情快照 |
| `holding.py` | `holdings` | code, name, cost_price, shares, is_deleted |
| `user.py` | `user_watchlist` | 用户自选股 |
| `user_config.py` | `user_config` | key-value 配置（如 total_assets） |

## AI / 缓存表

| 文件 | 主要表 | 说明 |
|------|--------|------|
| `ai.py` | `ai_prompts` | 提示词模板 |
| | `prediction_cache` | 预测结果缓存 |
| | `deep_analysis_cache` | 深度分析缓存 |
| `chat_cache.py` | `ai_chat_cache` | query, response, search_date |
| `industry_cache.py` | `industry_analysis_cache` | 行业分析缓存 |
| `news.py` | `news` | 新闻资讯（按 title+url 去重） |

## 预测 / 跟踪表

| 文件 | 主要表 | 说明 |
|------|--------|------|
| `tracking.py` | `prediction_tracking` | 预测跟踪项 |
| `prediction.py` | `prediction_records` | 预测记录 |
| | `data_snapshots` | 数据快照 |
| | `review_records` | 复盘记录 |
| | `ai_call_logs` | LLM 调用日志 |
