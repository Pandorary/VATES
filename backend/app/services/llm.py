"""LLM 调用服务 — OpenAI 兼容接口 (DeepSeek / 通义千问 / GPT 等)"""
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


async def chat(messages: list[dict], model: str | None = None, **kwargs) -> dict:
    """调用 LLM chat completion，返回 {"content": str, "model": str, "usage": dict}"""
    url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model or settings.LLM_MODEL,
        "messages": messages,
        "max_tokens": kwargs.get("max_tokens", settings.LLM_MAX_TOKENS),
        "temperature": kwargs.get("temperature", settings.LLM_TEMPERATURE),
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    choice = data["choices"][0]
    content = choice["message"]["content"]
    return {
        "content": content,
        "model": data.get("model", body["model"]),
        "usage": data.get("usage", {}),
    }
