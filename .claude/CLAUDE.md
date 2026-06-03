# VATES — 项目地图

> 交易状态感知与风控辅助系统 (Trade-Aware & Vigilant Equity System)
> 每次对话自动加载。修改代码前请读此文件 + 目标文件即可，无需遍历项目。

---

## 一、项目概览

| 维度 | 说明 |
|------|------|
| **定位** | A股交易辅助决策系统 — 行情采集 + AI 预测 + 持仓诊断 + 预测跟踪 |
| **架构** | FastAPI 后端 (8001) + React 前端 (5174) + SQLite 数据库 |
| **LLM** | DeepSeek API (OpenAI 兼容接口) |
| **包管理器** | npm (根目录) + pip (backend) |
| **启动脚本** | `start.bat` 一键启动前后端 |

## 二、目录结构

```
D:\AI\vates\
├── start.bat              # 一键启动前后端 (杀端口 → 后端 → 前端)
├── run_dev.py             # Python 入口 (设置 PYTHONPATH → uvicorn)
├── restart_backend.py     # 重启后端脚本
├── package.json           # 根 npm (只含 tailwindcss 构建依赖)
├── vates.db              # SQLite 开发数据库
├── config/
│   ├── __init__.py
│   └── config.py          # ⭐ 全局配置 (DB/LLM/JWT/行情 TTL)
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── vates.db           # 运行时数据库
│   └── app/
│       ├── main.py         # ⭐ FastAPI 入口 + 路由注册
│       ├── database.py     # SQLAlchemy async engine + init_db + get_db
│       ├── routers/        # API 路由层
│       ├── models/         # ORM 模型 (SQLAlchemy)
│       ├── schemas/        # Pydantic 请求/响应模型
│       ├── services/       # 业务逻辑
│       │   └── quotes/     # 行情采集子系统
│       └── tasks/          # APScheduler 定时任务
└── frontend/
    ├── vite.config.ts      # Vite 配置 + /api 代理到 localhost:8001
    └── src/
        ├── main.tsx        # React 入口
        ├── router/         # React Router v7 路由定义
        ├── pages/          # 页面组件
        ├── components/     # 通用组件 (AppLayout + UI 库)
        ├── services/api.ts # ⭐ axios 实例 + 所有 API 函数
        ├── types/          # TypeScript 类型定义
        ├── context/        # React Context (AppProvider)
        └── hooks/          # 自定义 hooks
```

## 三、后端架构

### 3.1 系统入口与启动流程

**`main.py`** — FastAPI 应用工厂：
1. `lifespan`: 启动时 → `init_db()` 建表 → `init_quote_manager()` 初始化行情管理器 → `start_scheduler()` 启动定时采集
2. 关闭时 → `stop_scheduler()` → `engine.dispose()`
3. 注册 6 个路由模块（均挂载在 `/api/v1`）
4. CORS 全开 (`allow_origins=["*"]`)
5. 健康检查: `GET /api/health`

### 3.2 API 路由完整清单

| 路由前缀 | 文件 | 端点 | 说明 |
|----------|------|------|------|
| `/api/v1/chat` | `routers/chat.py` | `POST /chat` | AI 对话（含同天同股票缓存） |
| | | `POST /deep-analysis` | 深度分析（6 大板块） |
| | | `POST /prediction` | AI 预测走势（旧版兼容，4 时段） |
| | | `GET/POST/PUT/DELETE /admin/prompt-templates` | 提示词模板 CRUD |
| | | `POST /admin/prompt-templates/{id}/copy` | 复制模板 |
| `/api/v1/holdings` | `routers/holding.py` | `GET/POST /holdings` | 持仓列表/新增 |
| | | `PUT/DELETE /holdings/{id}` | 更新/删除持仓 |
| | | `POST /holdings/{id}/diagnose` | AI 持仓诊断 |
| | | `POST /holdings/{id}/review` | AI 持仓复盘 |
| | | `POST /holdings/{id}/refresh` | 刷新持仓现价 |
| | | `GET/PUT /holdings/total-assets` | 总资产管理 |
| `/api/v1/search` | `routers/search.py` | `POST /search` | 搜索分类（股票/行业识别） |
| | | `POST /industry-analysis` | 行业分析（同天同行业缓存） |
| `/api/v1/tracking` | `routers/tracking.py` | `GET/POST /tracking` | 预测跟踪列表 |
| | | `DELETE /tracking/{id}` | 删除跟踪项 |
| | | `GET /tracking/{id}/latest-prediction` | 最新预测 |
| | | `POST /tracking/deviation-analysis` | 偏离分析 |
| `/api/v1/prediction` | `routers/prediction.py` | `POST /prediction/stock` | 生成股票预测 |
| | | `POST /prediction/industry` | 生成行业预测 |
| | | `POST /prediction/save` | 保存预测结果 |
| | | `GET /prediction/records` | 预测记录列表 |
| | | `GET /prediction/records/{id}` | 预测详情 |
| | | `DELETE /prediction/records/{id}` | 删除预测 |
| | | `POST /prediction/records/{id}/review` | 触发复盘 |
| `/api/v1/quotes` | `routers/quotes.py` | `GET /quotes/{code}` | 单只股票行情 |
| | | `GET /quotes?codes=xxx` | 批量行情（逗号分隔） |

### 3.3 数据模型 (models/)

| 文件 | 主要表 | 关键字段 |
|------|--------|----------|
| `stock.py` | `stocks` | code, name, market, industry |
| `market.py` | `daily_quotes`, `money_flow`, `limit_up_records`, `market_sentiment`, `market_config` | 行情/资金/涨停/情绪数据 |
| `holding.py` | `holdings` | code, name, cost_price, shares, is_deleted |
| `user.py` | `users`, `user_watchlist` | 用户 + 自选股 |
| `user_config.py` | `user_config` | key-value 配置（如 total_assets） |
| `ai.py` | `ai_prompts`, `prediction_cache`, `deep_analysis_cache` | 提示词模板 + 预测缓存 |
| `chat_cache.py` | `ai_chat_cache` | query, response, search_date |
| `industry_cache.py` | `industry_analysis_cache` | 行业分析缓存 |
| `tracking.py` | `prediction_tracking` | 预测跟踪项 |
| `price_cache.py` | `price_cache` | 股价缓存 |
| `prediction.py` | `prediction_records`, `data_snapshots`, `review_records` | 预测记录 + 数据快照 + 复盘 |
| | | `ai_call_logs` | LLM 调用日志 |

### 3.4 业务服务 (services/)

| 文件 | 功能 | 关键接口 |
|------|------|----------|
| `services/llm.py` | LLM 调用封装 | `chat(messages)` → `{"content", "model", "usage"}` |
| `services/data_engine.py` | 数据引擎（采集+组装） | 为预测提供结构化数据 |
| **行情子系统** | | |
| `services/quotes/base.py` | 接口定义 | `QuoteData` dataclass, `QuoteProvider` ABC |
| `services/quotes/tencent.py` | 腾讯行情源 | 实时行情 |
| `services/quotes/eastmoney.py` | 东方财富行情源 | 实时行情 |
| `services/quotes/sina.py` | 新浪行情源 | 实时行情 |
| `services/quotes/failover.py` | 故障转移管理 | 按优先级获取，支持批量 |
| `services/quotes/cross_validate.py` | 多源交叉验证 | 多源数据对比校验 |
| `services/quotes/manager.py` | ⭐ 行情管理器单例 | TTL 缓存 + 故障转移 + DB 回退 |
| `services/quotes/scheduler.py` | APScheduler 调度 | `start_scheduler()` / `stop_scheduler()` |

### 3.5 定时任务 (tasks/)

| 文件 | 功能 | 触发方式 |
|------|------|----------|
| `tasks/quote_jobs.py` | 定时行情采集 | APScheduler 定时触发 |

### 3.6 数据库连接 (`database.py`)

- **开发**: SQLite + aiosqlite，路径 `backend/vates.db`
- **生产**: PostgreSQL（通过 `DATABASE_URL` 切换）
- `get_db()`: FastAPI 依赖注入，自动 commit/rollback
- `Base`: SQLAlchemy DeclarativeBase

## 四、前端架构

### 4.1 路由 (React Router v7)

| 路径 | 页面 | 组件 | 说明 |
|------|------|------|------|
| `/` | `Home.tsx` | 直接加载 | 首页（搜索 + 分析入口） |
| `/prediction-track` | `PredictionTrack.tsx` | Lazy | 预测跟踪面板 |
| `/prediction/:stock` | `AIPrediction.tsx` | Lazy | 单股 AI 预测页 |
| `/watchlist` | `Watchlist.tsx` | Lazy | 持仓诊断 |
| `/prompts` | `PromptManager.tsx` | Lazy | 提示词管理 |

### 4.2 页面说明

| 页面 | 功能 | 路由 |
|------|------|------|
| `Home.tsx` | 搜索入口（股票/行业识别）→ 跳转分析 | `/` |
| `AIPrediction.tsx` | 展示单只股票 AI 预测结果 | `/prediction/:stock` |
| `PredictionTrack.tsx` | 预测记录列表 + 复盘跟踪 | `/prediction-track` |
| `Watchlist.tsx` | 持仓列表 + AI 诊断 + 盈亏计算 | `/watchlist` |
| `PromptManager.tsx` | 提示词模板 CRUD | `/prompts` |
| `AIPredictionEntry.tsx` | 预测参数入口（由 Home 页跳转调用） | 无独立路由 |
| `StockDetail.tsx` | 股票详情（子页面） | 无独立路由 |
| `DeepAnalysis.tsx` | 深度分析展示（子页面） | 无独立路由 |
| `IndustryDetail.tsx` | 行业详情（子页面） | 无独立路由 |

### 4.3 组件与上下文

| 文件 | 说明 |
|------|------|
| `components/AppLayout.tsx` | 顶部导航 + Outlet + Sonner Toaster |
| `components/ui/*.tsx` | shadcn/ui 组件库 (button, card, dialog, input, select, switch, table, badge, checkbox, separator, textarea, tooltip) |
| `context/AppContext.tsx` | 全局状态 (disclaimerAccepted) + localStorage 持久化 |
| `hooks/useError.ts` | 错误处理 hook |
| `hooks/useLoading.ts` | 加载状态 hook |

### 4.4 API 层 (`services/api.ts`)

- `api` (axios 实例): `baseURL="/api/v1"`, `timeout=120000`
- API 函数按模块分组: 搜索分类 / 预测(个股+行业+保存+记录+复盘) / Prompt 模板 CRUD / 持仓(CRUD+诊断+复盘+刷新+总资产) / 预测跟踪(旧版兼容)
- 前端通过 Vite proxy 将 `/api` 转发到 `http://localhost:8001`

### 4.5 类型系统 (`types/index.ts`)

- `ApiResponse<T>`: 统一响应包装
- `PaginatedData<T>`: 分页数据
- `PredictionRecord/Detail`: 预测记录类型
- `Holding`: 持仓类型
- `PromptScene`: 业务场景

## 五、数据流

### 5.1 行情采集流程
```
APScheduler 定时触发 → quote_jobs → QuoteManager.refresh_all_tracked()
  → 获取所有跟踪股票代码 (持仓 + 自选 + 默认配置)
  → 交易时段检查
  → 清空 TTL 缓存
  → FailoverManager (Tencent → EastMoney → Sina)
  → 写入 TTL 缓存 + stock_quotes 表
```

### 5.2 AI 对话流程
```
POST /api/v1/chat { query }
  → 检查 ai_chat_cache (同天+同股票)
  → 命中 → 直接返回缓存
  → 未命中 → 取 stock_analysis 场景的激活提示词模板
  → 调用 DeepSeek API
  → 写入缓存 → 返回
```

### 5.3 持仓诊断流程
```
POST /api/v1/holdings/{id}/diagnose
  → 获取持仓信息 + 最新行情
  → 取 position_diagnosis 场景的提示词模板
  → 组装数据（成本/现价/盈亏）
  → 调用 LLM → 返回诊断结果
```

## 六、全局配置 (`config/config.py`)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///...` | 数据库连接 |
| `LLM_API_KEY` | DeepSeek key | LLM API 密钥 |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | LLM 接口地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型名 |
| `LLM_MAX_TOKENS` | 8192 | 最大 token |
| `LLM_TEMPERATURE` | 0.3 | 生成温度 |
| `STOCK_CACHE_TTL` | 60 | 行情缓存过期秒数 |
| `STOCK_CACHE_MAX_SIZE` | 200 | 最大缓存条目 |
| `STOCK_TRADING_HOURS_ONLY` | true | 仅交易时段采集 |
| `JWT_SECRET/ALGORITHM/EXPIRE_MINUTES` | - | JWT 配置（预留） |

所有配置可通过 `.env` 文件覆盖。

## 七、启动与开发

### 启动开发环境
```bash
# 方式 1: 一键启动
start.bat

# 方式 2: 分别启动
python run_dev.py          # 后端 :8001
cd frontend && npm run dev # 前端 :5174
```

### 常用命令
```bash
cd frontend && npx oxlint .        # 前端 lint
cd frontend && npx oxfmt --check . # 前端格式检查
```

## 八、编码约定

- **后端**: Python 3.14+, FastAPI async, SQLAlchemy 2.0 async, 原生 SQL (text) 为主
- **前端**: React 19 + TypeScript 5.x, Tailwind CSS v4, 组件懒加载 (React.lazy)
- **API 响应**: 统一包装 `{ code: number, message: string, data: T }`
- **提示词场景**: 每个场景同时只有一个激活模板 (唯一激活规则)
- **缓存策略**: 同一天同一股票同一参数 → 数据库缓存 (ai_chat_cache 等)
- **行情采集**: TTL 缓存 (60s) → 多源故障转移 → 数据库回退
- **前端样式**: Tailwind utility classes, 无 CSS 文件 (除 index.css)
- **UI 组件**: 基于 shadcn/ui + Radix (reka-ui)
- **路由**: 首页直接加载，其他页面 React.lazy 懒加载
- **API Key**: 当前硬编码在 config.py，应迁移到 .env

## 九、技术栈速查

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI + uvicorn |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | SQLite (dev) / PostgreSQL (prod) |
| 定时任务 | APScheduler 3.x |
| LLM | DeepSeek (OpenAI 兼容) |
| HTTP 客户端 | httpx (后端), axios (前端) |
| 前端框架 | React 19 + TypeScript |
| 样式 | Tailwind CSS v4 |
| UI 库 | shadcn/ui + Radix (reka-ui) |
| 路由 | React Router v7 |
| 构建 | Vite 8 |
| 通知 | Sonner (toast) |
| 图标 | Lucide React |
