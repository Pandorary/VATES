"""股票基础模型"""
from sqlalchemy import Column, String, Date, Numeric, BigInteger, Integer, PrimaryKeyConstraint
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


class MoneyFlow(Base):
    __tablename__ = "money_flow"
    code = Column(String(10))
    trade_date = Column(Date)
    main_net_inflow = Column(Numeric(14, 2), comment="主力净流入(万)")
    super_large_net = Column(Numeric(14, 2), comment="超大单净流入")
    __table_args__ = (PrimaryKeyConstraint("code", "trade_date"),)


class LimitUpRecord(Base):
    __tablename__ = "limit_up_records"
    code = Column(String(10))
    trade_date = Column(Date)
    is_continuous = Column(Integer, comment="连续涨停天数")
    board_height = Column(Integer, comment="当前连板高度")
    broken_rate = Column(Numeric(6, 2), comment="炸板率")
    __table_args__ = (PrimaryKeyConstraint("code", "trade_date"),)
