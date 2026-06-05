"""数据源抽象基类 + 行情数据模型"""
from abc import ABC, abstractmethod

from pydantic import BaseModel


class QuoteData(BaseModel):
    """单只股票行情数据"""
    code: str
    name: str = ""
    price: float | None = None       # 最新价
    open: float | None = None        # 开盘价
    high: float | None = None        # 最高价
    low: float | None = None         # 最低价
    close: float | None = None       # 昨收价
    change: float | None = None      # 涨跌额
    change_percent: float | None = None  # 涨跌幅%
    volume: float | None = None      # 成交量(手)
    amount: float | None = None      # 成交额
    source: str = ""                 # 数据来源


def _market_prefix(code: str) -> tuple[str, str]:
    """根据股票代码返回 (市场标识, URL前缀)

    沪市: 6xx/9xx → market="1", prefix="sh"
    深市: 0xx/3xx → market="0", prefix="sz"
    """
    if code.startswith(("6", "9")):
        return "1", "sh"
    return "0", "sz"


class QuoteProvider(ABC):
    """数据源适配器抽象基类"""
    name: str = ""

    @abstractmethod
    async def fetch_quote(self, code: str) -> QuoteData | None:
        """获取单只股票行情"""

    async def fetch_quotes_batch(self, codes: list[str]) -> dict[str, QuoteData]:
        """批量获取行情，默认逐个调用，子类可覆写以支持批量API"""
        results: dict[str, QuoteData] = {}
        for code in codes:
            quote = await self.fetch_quote(code)
            if quote:
                results[code] = quote
        return results
