"""行业板块行情模型"""
from sqlalchemy import Column, String, Numeric, JSON, TIMESTAMP, func
from app.database import Base


class SectorQuote(Base):
    """最新板块行情快照（每个板块一行，实时更新）"""
    __tablename__ = "sector_quotes"

    code = Column(String(20), primary_key=True, comment="板块代码，如 BK0498")
    name = Column(String(50), comment="板块名称")
    sector_index = Column(Numeric(10, 3), comment="板块指数点位")
    sector_change_percent = Column(Numeric(6, 2), comment="板块涨跌幅%")
    leading_stocks = Column(JSON, comment="领涨个股列表 [{code,name,change_pct}]")
    policy_news = Column(JSON, comment="近期行业政策/事件列表")
    fund_flow = Column(String(200), comment="板块资金流向概况")
    source = Column(String(20), comment="数据来源")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
