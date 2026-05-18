"""Celery 应用配置 — 开发模式使用内存 broker 降级"""
from celery import Celery

celery_app = Celery(
    "vates",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=["app.tasks.daily_jobs"],
)

# 开发模式：如果 Redis 不可用，降级为同步执行
# 可在启动时设置 CELERY_ALWAYS_EAGER=True 跳过 broker
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_always_eager=True,  # 开发模式：跳过 Redis，同步执行
)

# 定时任务配置 (Celery Beat)
celery_app.conf.beat_schedule = {
    "fetch-data": {
        "task": "app.tasks.daily_jobs.fetch_daily_data",
        "schedule": 0,  # 由 Beat 实际调度控制
    },
    "calc-market-temp": {
        "task": "app.tasks.daily_jobs.calculate_market_temperature",
        "schedule": 0,
    },
    "scan-patterns": {
        "task": "app.tasks.daily_jobs.scan_patterns",
        "schedule": 0,
    },
    "generate-review": {
        "task": "app.tasks.daily_jobs.generate_review_report",
        "schedule": 0,
    },
}
