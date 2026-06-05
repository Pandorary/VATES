# API 路由完整清单

> 所有路由挂载在 `/api/v1`，详见 `backend/app/routers/`

## chat — AI 对话与提示词

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/chat` | AI 对话（含同天同股票缓存） |
| `POST` | `/deep-analysis` | 深度分析（6 大板块） |
| `POST` | `/prediction` | AI 预测走势（旧版兼容，4 时段） |
| `GET` | `/admin/prompt-templates` | 提示词模板列表 |
| `POST` | `/admin/prompt-templates` | 创建模板 |
| `PUT` | `/admin/prompt-templates/{id}` | 更新模板 |
| `DELETE` | `/admin/prompt-templates/{id}` | 删除模板 |
| `POST` | `/admin/prompt-templates/{id}/copy` | 复制模板 |

## holdings — 持仓管理

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/holdings` | 持仓列表 |
| `POST` | `/holdings` | 新增持仓 |
| `PUT` | `/holdings/{id}` | 更新持仓 |
| `DELETE` | `/holdings/{id}` | 删除持仓 |
| `POST` | `/holdings/{id}/diagnose` | AI 持仓诊断 |
| `POST` | `/holdings/{id}/review` | AI 持仓复盘 |
| `POST` | `/holdings/{id}/refresh` | 刷新持仓现价 |
| `GET` | `/holdings/total-assets` | 总资产查询 |
| `PUT` | `/holdings/total-assets` | 总资产更新 |

## search — 搜索分类

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/search` | 搜索分类（股票/行业识别） |
| `POST` | `/industry-analysis` | 行业分析（同天同行业缓存） |

## tracking — 预测跟踪（旧版兼容）

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/tracking` | 预测跟踪列表 |
| `POST` | `/tracking` | 新增跟踪项 |
| `DELETE` | `/tracking/{id}` | 删除跟踪项 |
| `GET` | `/tracking/{id}/latest-prediction` | 最新预测 |
| `POST` | `/tracking/deviation-analysis` | 偏离分析 |

## prediction — 预测记录（新版）

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/prediction/stock` | 生成股票预测 |
| `POST` | `/prediction/industry` | 生成行业预测 |
| `POST` | `/prediction/save` | 保存预测结果 |
| `GET` | `/prediction/records` | 预测记录列表 |
| `GET` | `/prediction/records/{id}` | 预测详情 |
| `DELETE` | `/prediction/records/{id}` | 删除预测 |
| `POST` | `/prediction/records/{id}/review` | 触发复盘 |

## quotes — 行情查询

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/quotes/{code}` | 单只股票行情 |
| `GET` | `/quotes?codes=xxx` | 批量行情（逗号分隔） |

## 其他

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
