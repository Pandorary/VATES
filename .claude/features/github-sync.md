# GitHub Topics 定时同步任务

## 任务目标
每 2 天从 GitHub 获取热门 Topics，提取技术栈信息，使用 LLM 生成规范的提示词模板，存入 `ai_prompts` 表。重复数据不存储。

## 实现架构

### 1. GitHub API 服务
**文件**: `backend/app/services/github_topics.py`

- 调用 GitHub API 获取热门 Topics：`https://api.github.com/search/topics?q=is:featured&per_page=10`
- 解析返回的 JSON 数据，提取：name, display_name, short_description, related_languages
- 支持可选的 GitHub API Token 认证

### 2. LLM 提示词生成服务
**文件**: `backend/app/services/prompt_generator.py`

- 接收技术栈信息（Topic 数据）
- 构造 LLM prompt，生成提示词模板
- 调用 LLM 服务生成 `skill_detail` 内容
- 解析 LLM 返回的 JSON 格式数据

### 3. 数据同步服务
**文件**: `backend/app/services/github_sync.py`

- 主同步函数：`async def sync_github_topics() -> dict`
- 调用 GitHub API 获取热门 Topics
- 对每个 Topic：提取技术栈 → LLM 生成提示词 → 去重检查 → 插入数据库

### 4. 配置项
**文件**: `config/config.py`

```python
GITHUB_SYNC_ENABLED: bool = False  # 当前已暂停
GITHUB_SYNC_INTERVAL_DAYS: int = 2
GITHUB_API_TOKEN: str = ""  # Personal Access Token (可选)
```

### 5. 定时任务注册
**文件**: `backend/app/main.py`

在 `lifespan` 中通过 APScheduler 注册：`run_github_sync` 每 N 天执行一次。

### 6. 任务入口
**文件**: `backend/app/tasks/github_jobs.py`

```python
from app.services.github_sync import sync_github_topics

async def run_github_sync():
    return await sync_github_topics()
```

## 数据映射

| GitHub Topic 字段 | ai_prompts 字段 | 来源 |
|-------------------|-----------------|------|
| related_languages[0] | role | LLM 生成 |
| LLM 解析 | role_name | LLM 生成 |
| {name}_best_practices | skill | LLM 生成 |
| {display_name} 最佳实践 | skill_name | LLM 生成 |
| LLM 生成 | skill_detail | LLM 生成 |

## 去重逻辑

- 查询时使用 `skill` 字段判断是否已存在
- SQL: `SELECT skill FROM ai_prompts WHERE skill=:skill AND is_deleted=0`
- 已存在则跳过，不更新

## 手动触发

```bash
cd D:\AI\vates
PYTHONPATH="backend;." python -c "
from app.services.github_sync import sync_github_topics
import asyncio
asyncio.run(sync_github_topics(limit=3))
"
```

## 注意事项

1. 需要配置 `LLM_API_KEY` 用于 DeepSeek API
2. GitHub API 无 Token 时限流 60次/小时
3. 每个 Topic 需要 0.5 秒延迟避免 LLM 限流
4. 启用方式：修改 `config/config.py` 中 `GITHUB_SYNC_ENABLED = True`
