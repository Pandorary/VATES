"""AkShare 数据抓取 — 真实数据获取（无 mock）"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def fetch_daily_quotes(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """抓取个股日K线 — 使用新浪源（更稳定）"""
    import akshare as ak
    market = 'sz' if symbol.startswith(('0', '3')) else 'sh'
    full_symbol = f'{market}{symbol}'
    try:
        return ak.stock_zh_a_daily(symbol=full_symbol, start_date=start_date, end_date=end_date, adjust='qfq')
    except Exception:
        # 降级腾讯源
        return ak.stock_zh_a_hist_tx(symbol=full_symbol, start_date=start_date, end_date=end_date)


def fetch_limit_up_pool(trade_date: Optional[str] = None) -> pd.DataFrame:
    """抓取涨停板数据"""
    import akshare as ak
    if trade_date is None:
        trade_date = datetime.now().strftime('%Y%m%d')
    return ak.stock_zt_pool_em(date=trade_date)


def fetch_fund_flow(symbol: str) -> pd.DataFrame:
    """抓取个股资金流"""
    import akshare as ak
    # 根据代码判断市场
    market = 'sh' if symbol.startswith(('6', '9')) else 'sz'
    return ak.stock_individual_fund_flow(stock=symbol, market=market)


def fetch_sector_fund_flow() -> pd.DataFrame:
    """抓取行业资金流排名"""
    import akshare as ak
    try:
        return ak.stock_sector_fund_flow_rank(indicator='今日', sector_type='行业资金流')
    except Exception:
        logger.warning("行业资金流抓取失败")
        return pd.DataFrame()


def is_trade_day(d: date) -> bool:
    """简易交易日判断"""
    if d.weekday() >= 5:
        return False
    return True


def last_trade_day(ref_date: Optional[date] = None) -> date:
    """获取最近交易日"""
    d = ref_date or date.today()
    while not is_trade_day(d):
        d = d - timedelta(days=1)
    return d


def latest_trade_date_str() -> str:
    """最近交易日字符串"""
    return last_trade_day().strftime('%Y%m%d')
