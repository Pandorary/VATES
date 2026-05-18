"""模式相关 Schema"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class PatternHistoryStats(BaseModel):
    win_rate: float
    avg_pnl_ratio: float
    sample_count: int


class PatternSignalOut(BaseModel):
    pattern_id: int
    name: str
    description: str = ""
    details: Dict[str, Any] = {}
    confirm_condition: str = ""
    fail_condition: str = ""
    risk_reference: Optional[float] = None
    history_stats: Optional[PatternHistoryStats] = None


class StockPatternsOut(BaseModel):
    code: str
    patterns_matched: List[PatternSignalOut]
    no_match: bool = False
