# VATES — 项目地图

> A股交易辅助决策系统 — 行情采集 + AI 预测 + 持仓诊断 + 预测跟踪
> 每次对话自动加载。详细参考见 `docs/`。

---

## 一、项目概览

| 维度 | 说明 |
|------|------|
| **定位** | A股交易辅助决策系统 |
| **架构** | FastAPI 后端 (8001) + React 前端 (5174) + SQLite |
| **LLM** | DeepSeek API (OpenAI 兼容接口) |
| **包管理器** | npm (frontend/) + pip (backend) |
| **启动** | `scripts/start.bat` 一键启动前后端 |

## 二、目录结构

```
D:\AI\vates\
├── scripts/start.bat       # 一键启动
├── scripts/run_dev.py      # Python 入口
├── config/config.py        # ⭐ 全局配置 (DB/LLM/JWT/行情 TTL)
├── db/                     # SQLite 数据库文件
├── docs/                   # 项目接口、业务、部署文档
├── backend/app/
│   ├── main.py             # ⭐ FastAPI 入口 + 路由注册
│   ├── database.py         # SQLAlchemy async engine + get_db
│   ├── routers/            # API 路由层
│   ├── models/             # ORM 模型
│   ├── schemas/            # Pydantic 请求/响应模型
│   ├── services/           # 业务逻辑 + data_engine/ 数据引擎 + news/ 资讯采集
│   └── tasks/              # APScheduler 定时任务
└── frontend/src/
    ├── main.tsx            # React 入口
    ├── router/             # React Router v7
    ├── pages/              # 页面组件 (Lazy 加载)
    ├── components/         # AppLayout + shadcn/ui 组件库
    ├── services/api.ts     # ⭐ axios 实例 + 所有 API 函数
    └── context/            # React Context (AppProvider)
```

## 三、后端架构

**启动流程** (`main.py`)：`init_db()` 建表 → `init_quote_manager()` 行情管理器 → `start_scheduler()` 定时采集

- 7 个路由模块，挂载在 `/api/v1`
- CORS 全开，健康检查 `GET /api/health`
- 详细 API 路由 → [docs/api-routes.md](docs/api-routes.md)
- 数据模型 → [docs/data-models.md](docs/data-models.md)
- 业务服务 → [docs/services.md](docs/services.md)

## 四、前端架构

- React Router v7，首页直接加载，其他页面 `React.lazy`
- shadcn/ui + Radix 组件库，Tailwind CSS v4
- Vite proxy `/api` → `localhost:8001`
- 详细页面/路由/组件 → [docs/frontend-pages.md](docs/frontend-pages.md)

## 五、全局配置 (`config/config.py`)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///...` | 开发用 SQLite，生产切 PostgreSQL |
| `LLM_API_KEY` | DeepSeek key | LLM API 密钥 |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | LLM 接口地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型名 |
| `LLM_MAX_TOKENS` | 8192 | 最大 token |
| `LLM_TEMPERATURE` | 0.3 | 生成温度 |
| `STOCK_CACHE_TTL` | 60 | 行情缓存过期秒数 |
| `STOCK_TRADING_HOURS_ONLY` | true | 仅交易时段采集 |

所有配置可通过 `.env` 文件覆盖。

## 六、编码约定

- **后端**: Python 3.14+, FastAPI async, SQLAlchemy 2.0 async, 原生 SQL 为主
- **前端**: React 19 + TypeScript 5.x, Tailwind CSS v4, 组件懒加载
- **API 响应**: 统一包装 `{ code: number, message: string, data: T }`
- **缓存策略**: 同天同股票同参数 → DB 缓存 (`ai_chat_cache` 等)
- **行情采集**: TTL 缓存 (60s) → 多源故障转移 → DB 回退
- 详细规范 → [rules/dev-standards.md](.claude/rules/dev-standards.md)
- 技术栈详情 → [docs/tech-stack.md](docs/tech-stack.md)

## 七、数据流

- 行情采集 → [docs/data-flows.md](docs/data-flows.md)
- 开发命令 → `/dev` 或 [commands/dev.md](.claude/commands/dev.md)
- 业务主逻辑 → [docs/业务主逻辑.md](docs/业务主逻辑.md)
