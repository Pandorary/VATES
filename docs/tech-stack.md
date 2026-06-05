# 技术栈总结

## 后端

| 技术 | 用途 |
|------|------|
| **FastAPI** | Web 框架，异步 API 服务 |
| **SQLAlchemy 2.0** | ORM 框架，异步数据库操作 |
| **APScheduler** | 定时任务调度 |
| **httpx** | 异步 HTTP 客户端 |
| **DeepSeek API** | LLM 服务，通过 OpenAI 兼容接口调用 |
| **SQLite** | 开发模式数据库 (aiosqlite) |
| **Pydantic v2** | 数据校验与配置管理 (pydantic-settings) |

## 前端

| 技术 | 用途 |
|------|------|
| **React 19** | 前端框架 |
| **TypeScript 5.x** | 类型安全 |
| **Tailwind CSS v4** | 原子化 CSS 框架 |
| **shadcn/ui + Radix** | UI 组件库 (checkbox, dialog, select, separator, switch, tooltip) |
| **React Router v7** | 路由管理 |
| **axios** | HTTP 客户端 |
| **marked** | Markdown 渲染 |
| **Sonner** | Toast 通知 |
| **Lucide React** | 图标库 |
| **Vite 8** | 构建工具 |

## 数据库表

### 核心数据

| 表名 | 用途 |
|------|------|
| `stocks` | 股票基本信息 |
| `daily_quotes` | 日 K 线行情 |
| `stock_quotes` | 实时行情快照 |
| `news` | 新闻资讯 |

### 业务功能

| 表名 | 用途 |
|------|------|
| `holdings` | 用户持仓 |
| `prediction_tracking` | AI 预测跟踪列表 |
| `stock_quotes` | 实时行情快照 |
| `news` | 新闻资讯 |

### 业务功能

| 表名 | 用途 |
|------|------|
| `holdings` | 用户持仓 |
| `prediction_tracking` | AI 预测跟踪列表 |
| `prediction_records` | AI 预测记录 |
| `data_snapshots` | 预测数据快照 |
| `review_records` | 复盘记录 |
| `ai_chat_cache` | 聊天响应缓存（按日期） |
| `ai_prompts` | AI 提示词模板 |
| `deep_analysis_cache` | 深度分析缓存 |
| `industry_analysis_cache` | 行业分析缓存 |
| `ai_call_logs` | LLM 调用日志 |
| `user_config` | 用户配置（总资产等） |
| `user_watchlist` | 用户自选股 |

### 用户

| 表名 | 用途 |
|------|------|
| `user_watchlist` | 用户自选股 |
| `user_config` | 用户配置（总资产等） |

## 后端模块

### API 路由 (`app/routers/`)

| 路由 | 文件 | 功能 |
|------|------|------|
| `/api/v1/chat` | `chat.py` | AI 对话 + 提示词模板 CRUD |
| `/api/v1/holdings` | `holding.py` | 持仓管理 + AI 诊断 + 股价刷新 |
| `/api/v1/search` | `search.py` | 搜索分类（股票/行业识别） |
| `/api/v1/tracking` | `tracking.py` | 预测跟踪 + 偏离分析 |
| `/api/v1/prediction` | `prediction.py` | AI 个股/行业预测 + 保存 + 复盘 |
| `/api/v1/quotes` | `quotes.py` | 行情查询 API |
| `/api/v1/news` | `news.py` | 新闻查询 API |

### 数据模型 (`app/models/`)

| 文件 | 对应表 |
|------|--------|
| `ai.py` | ai_prompts, prediction_cache, deep_analysis_cache |
| `chat_cache.py` | ai_chat_cache |
| `holding.py` | holdings |
| `industry_cache.py` | industry_analysis_cache |
| `stock.py` | stocks, daily_quotes, stock_quotes |
| `news.py` | news |
| `holding.py` | holdings |
| `prediction.py` | prediction_records, data_snapshots, review_records, ai_call_logs |
| `tracking.py` | prediction_tracking |
| `user.py` | user_watchlist |
| `user_config.py` | user_config |

### 业务服务 (`app/services/`)

| 文件 | 功能 |
|------|------|
| `llm.py` | DeepSeek API 调用封装 |
| `data_engine/` | 数据引擎包 — 行情采集 + 预测数据组装 |

### 定时任务 (`app/tasks/`)

| 文件 | 功能 |
|------|------|
| `quote_jobs.py` | 定时行情采集（每1分钟） |
| `news_jobs.py` | 定时新闻采集（每5分钟） |

## 配置文件

| 文件 | 内容 |
|------|------|
| `config/config.py` | 全局配置 (DB, LLM, JWT, GitHub Sync) |
| `config/__init__.py` | 包初始化 |
| `.env` | 环境变量覆盖（不入库） |
