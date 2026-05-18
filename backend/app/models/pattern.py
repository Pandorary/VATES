"""交易模式相关模型"""
from sqlalchemy import Column, Integer, String, Date, Text, Numeric, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

# SQLite 兼容：用 Text 存储 JSON 字符串，PostgreSQL 切回 JSONB
try:
    from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
    JsonType = SQLiteJSON
except ImportError:
    JsonType = JSONB


class TradePattern(Base):
    __tablename__ = "trade_patterns"
    pattern_id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_name = Column(String(50))
    conditions_json = Column(Text, comment="条件集合 JSON")  # Text 兼容 SQLite
    risk_tips = Column(Text)


class PatternSignal(Base):
    __tablename__ = "pattern_signals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10))
    trade_date = Column(Date)
    pattern_id = Column(Integer)
    matched_details = Column(Text)  # Text 兼容 SQLite


class PatternBacktestCache(Base):
    __tablename__ = "pattern_backtest_cache"
    pattern_id = Column(Integer, primary_key=True)
    lookback_days = Column(Integer, primary_key=True)
    sample_count = Column(Integer)
    win_rate = Column(Numeric(5, 2))
    avg_gain = Column(Numeric(10, 2))
    avg_loss = Column(Numeric(10, 2))
    avg_pnl_ratio = Column(Numeric(5, 2))
    updated_at = Column(TIMESTAMP)
