# 用户偏好和反馈

## 用户背景
- 用户名: Pandorary
- 项目: VATES - 交易决策辅助系统
- 角色: 全栈开发者
- 环境: Windows 11, 使用 bash

## 交互偏好

### 响应风格
- **简洁直接**：喜欢短小的回答，直奔主题
- **代码优先**：更倾向于看到代码实现而非解释
- **自动执行**：不需要反复确认，理解后直接执行

### 反馈记录

### 2026-05-21 - Switch 组件问题
- **问题**：Radix Switch 组件事件不稳定
- **解决**：添加原生 click 事件作为兜底
- **经验**：第三方组件事件不稳定时，回退到原生事件

### 2026-05-20 - UI 规范遵循
- **偏好**：严格要求遵循 UI 设计规范
- **实践**：页面优化时注重字体、颜色、间距、交互的统一性

### 2026-05-20 - 文档组织
- **要求**：将复盘记录拆分到独立文件，claude.md 只记录目录

## 技术偏好

### 后端
- **框架**：FastAPI + SQLAlchemy 2.0
- **数据库**：开发模式 SQLite (aiosqlite)，生产可切换 PostgreSQL
- **异步**：httpx + asyncio
- **定时任务**：APScheduler

### 前端
- **框架**：React 19 + TypeScript
- **样式**：Tailwind CSS v4
- **组件库**：shadcn/ui + Radix
- **路由**：React Router v7
- **通知**：Sonner
- **图标**：Lucide React

## 代码风格偏好

### 命名
- 文件名：小写下划线分隔（如 `github_topics.py`）
- 函数名：小写下划线分隔（如 `fetch_featured_topics`）
- 常量：大写下划线分隔（如 `GITHUB_API_BASE`）

### 目录结构
- 后端：`backend/app/` 下按功能分包（routers/models/services/tasks）
- 前端：`frontend/src/` 下按类型分包（pages/components/context/hooks/services/lib）
- 组件：`frontend/src/components/` 和 `frontend/src/components/ui/`
