# 数据流

## 行情采集流程

```
APScheduler 定时触发 → quote_jobs → QuoteManager.refresh_all_tracked()
  → 获取所有跟踪股票代码 (持仓 + 自选 + 默认配置)
  → 交易时段检查
  → 清空 TTL 缓存
  → FailoverManager (Tencent → EastMoney → Sina)
  → 写入 TTL 缓存 + stock_quotes 表
```

## 搜索分类流程

```
POST /api/v1/search { query }
  → 内存缓存检查（query 精确匹配）
  → 命中 → 直接返回 + cached: true
  → 未命中 → LLM 分类（type + name + code）
  → type=stock 且无 code：
    → 输入是 6 位数字 → 直接作为代码
    → 按名称查 DB（stocks → stock_quotes）
    → DB 无结果 → 东方财富 API 外部搜索
  → 写入缓存 → 返回
```

## AI 对话流程

```
POST /api/v1/chat { query }
  → 检查 ai_chat_cache (同天+同股票)
  → 命中 → 直接返回缓存
  → 未命中 → 取 stock_analysis 场景的激活提示词模板
  → 调用 DeepSeek API
  → 写入缓存 → 返回
```

## 持仓诊断流程

```
POST /api/v1/holdings/{id}/diagnose
  → 获取持仓信息 + 最新行情
  → 取 position_diagnosis 场景的提示词模板
  → 组装数据（成本/现价/盈亏）
  → 调用 LLM → 返回诊断结果
```

## 预测跟踪流程

```
POST /api/v1/prediction/stock
  → data_engine 组装数据
  → 调用 LLM 生成预测
  → 保存 prediction_records + data_snapshots
  → 后续通过 review 端点复盘
```
