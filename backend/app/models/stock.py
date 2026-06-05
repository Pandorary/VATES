"""股票基础模型"""
from sqlalchemy import Column, String, Date, Numeric, BigInteger, PrimaryKeyConstraint, TIMESTAMP, func
from app.database import Base


class Stock(Base):
    __tablename__ = "stocks"
    code = Column(String(10), primary_key=True, comment="股票代码")
    name = Column(String(20), comment="股票简称")
    industry = Column(String(50), comment="所属行业/板块")
    list_date = Column(Date, comment="上市日期")


class DailyQuote(Base):
    __tablename__ = "daily_quotes"
    code = Column(String(10), comment="股票代码")
    trade_date = Column(Date, comment="交易日")
    open = Column(Numeric(10, 3))
    high = Column(Numeric(10, 3))
    low = Column(Numeric(10, 3))
    close = Column(Numeric(10, 3))
    volume = Column(BigInteger, comment="成交量(手)")
    amount = Column(Numeric(16, 2), comment="成交额")
    change_pct = Column(Numeric(6, 2), comment="涨跌幅%")
    turnover_rate = Column(Numeric(6, 2), comment="换手率%")
    __table_args__ = (PrimaryKeyConstraint("code", "trade_date"),)


class StockQuote(Base):
    """最新行情快照（每只股票一行，实时更新）"""
    __tablename__ = "stock_quotes"
    code = Column(String(10), primary_key=True, comment="股票代码")
    name = Column(String(50), comment="股票简称")
    price = Column(Numeric(10, 3), comment="最新价")
    open = Column(Numeric(10, 3), comment="开盘价")
    high = Column(Numeric(10, 3), comment="最高价")
    low = Column(Numeric(10, 3), comment="最低价")
    close = Column(Numeric(10, 3), comment="昨收价")
    change = Column(Numeric(10, 3), comment="涨跌额")
    change_percent = Column(Numeric(6, 2), comment="涨跌幅%")
    volume = Column(BigInteger, comment="成交量(手)")
    amount = Column(Numeric(16, 2), comment="成交额")
    source = Column(String(20), comment="数据来源")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
