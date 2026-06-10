"""数据引擎包 — 多源故障转移 + TTL 缓存 + 预测数据组装"""
from app.services.data_engine.base import QuoteData
from app.services.data_engine.manager import get_quote, get_quotes, get_quote_manager, init_quote_manager
from app.services.data_engine.assembler import fetch_stock_data, fetch_industry_data, get_active_template
from app.services.data_engine.eastmoney import search_stock_by_name
from app.services.data_engine.sector_manager import init_sector_manager, get_sector_manager, get_sector

__all__ = [
    "QuoteData",
    "get_quote", "get_quotes", "get_quote_manager", "init_quote_manager",
    "fetch_stock_data", "fetch_industry_data", "get_active_template",
    "search_stock_by_name",
    "init_sector_manager", "get_sector_manager", "get_sector",
]
