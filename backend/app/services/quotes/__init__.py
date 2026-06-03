"""行情数据采集包 — 多源故障转移 + TTL 缓存"""
from app.services.quotes.base import QuoteData
from app.services.quotes.manager import get_quote, get_quotes, get_quote_manager, init_quote_manager

__all__ = ["QuoteData", "get_quote", "get_quotes", "get_quote_manager", "init_quote_manager"]
