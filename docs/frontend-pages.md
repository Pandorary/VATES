# 前端页面与路由

> 路由定义位于 `frontend/src/router/`，使用 React Router v7

## 路由表

| 路径 | 页面 | 加载方式 | 说明 |
|------|------|----------|------|
| `/` | `Home.tsx` | 直接加载 | 首页（搜索 + 分析入口） |
| `/prediction-track` | `PredictionTrack.tsx` | Lazy | 预测跟踪面板 |
| `/prediction/:stock` | `AIPrediction.tsx` | Lazy | 单股 AI 预测页 |
| `/watchlist` | `Watchlist.tsx` | Lazy | 持仓诊断 |
| `/prompts` | `PromptManager.tsx` | Lazy | 提示词管理 |

## 子页面（无独立路由）

| 页面 | 说明 |
|------|------|
| `AIPredictionEntry.tsx` | 预测参数入口（由 Home 页跳转） |
| `StockDetail.tsx` | 股票详情 |
| `DeepAnalysis.tsx` | 深度分析展示 |
| `IndustryDetail.tsx` | 行业详情 |

## 核心组件

| 文件 | 说明 |
|------|------|
| `components/AppLayout.tsx` | 顶部导航 + Outlet + Sonner Toaster |
| `components/ui/*.tsx` | shadcn/ui 组件库 |
| `context/AppContext.tsx` | 全局状态 + localStorage 持久化 |
| `hooks/useError.ts` | 错误处理 hook |
| `hooks/useLoading.ts` | 加载状态 hook |

## API 层

`services/api.ts` — axios 实例 (`baseURL="/api/v1"`, `timeout=120000`)，前端通过 Vite proxy 将 `/api` 转发到 `http://localhost:8001`。

## 类型系统

`types/index.ts` — `ApiResponse<T>`, `PaginatedData<T>`, `PredictionRecord`, `Holding`, `PromptScene` 等。
