"""模式扫描引擎 — 定义与扫描交易模式"""
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class PatternDefinition:
    pattern_id: int
    name: str
    description: str
    confirm_condition: str
    fail_condition: str
    conditions: dict = field(default_factory=dict)


@dataclass
class PatternScanResult:
    pattern: PatternDefinition
    matched: bool
    details: dict = field(default_factory=dict)
    pressure_price: Optional[float] = None
    support_price: Optional[float] = None


# ============================================================
# 模式定义注册表
# ============================================================

PATTERN_REGISTRY: dict[int, PatternDefinition] = {
    1: PatternDefinition(
        pattern_id=1,
        name="平台突破放量",
        description="股价位于60日新高附近(2%以内)，当日成交量大于20日均量1.5倍，主力净流入>3000万，市场非退潮期",
        confirm_condition="次日高开高走，成交量持续放大",
        fail_condition="冲高回落，放量滞涨，或次日低开低走",
        conditions={
            "volume_ratio": 1.5,
            "price_near_high": 0.02,
            "min_main_inflow": 3000,
        },
    ),
    2: PatternDefinition(
        pattern_id=2,
        name="分歧转一致",
        description="早盘分歧后放量封板，换手充分，封单稳定",
        confirm_condition="涨停封单稳定不撤单",
        fail_condition="开板后无法回封，或尾盘炸板",
        conditions={
            "min_turnover": 5.0,
            "must_limit_up": True,
        },
    ),
}


# ============================================================
# 模式扫描函数
# ============================================================

def check_breakout_volume(
    close: float,
    high_60: float,
    volume: float,
    avg_vol_20: float,
    main_inflow: float,
    market_status: str,
) -> Optional[PatternScanResult]:
    """平台突破放量模式"""
    pattern = PATTERN_REGISTRY[1]
    cfg = pattern.conditions

    # 条件1: 股价距60日新高 < 2%
    if high_60 <= 0 or (high_60 - close) / high_60 > cfg["price_near_high"]:
        return None

    # 条件2: 成交量 > 20日均量 * 1.5
    if avg_vol_20 <= 0 or volume <= avg_vol_20 * cfg["volume_ratio"]:
        return None

    # 条件3: 主力净流入 > 3000万
    if main_inflow < cfg["min_main_inflow"]:
        return None

    # 条件4: 市场状态不能是退潮期
    if market_status == "RETREAT":
        return None

    return PatternScanResult(
        pattern=pattern,
        matched=True,
        details={
            "close": close,
            "high_60": high_60,
            "volume_ratio": round(volume / avg_vol_20, 2) if avg_vol_20 > 0 else 0,
            "main_inflow": main_inflow,
        },
        pressure_price=high_60,
        support_price=round(close * 0.95, 2),
    )


def check_divergence_to_agreement(
    close: float,
    turnover_rate: float,
    is_limit_up: bool,
    market_status: str,
) -> Optional[PatternScanResult]:
    """分歧转一致模式"""
    pattern = PATTERN_REGISTRY[2]
    cfg = pattern.conditions

    # 条件1: 当日涨停
    if not is_limit_up:
        return None

    # 条件2: 换手率充分
    if turnover_rate < cfg["min_turnover"]:
        return None

    # 条件3: 非退潮期
    if market_status == "RETREAT":
        return None

    return PatternScanResult(
        pattern=pattern,
        matched=True,
        details={
            "turnover_rate": turnover_rate,
            "is_limit_up": is_limit_up,
        },
        pressure_price=None,
        support_price=round(close * 0.93, 2),
    )


# 注册所有扫描函数
SCAN_FUNCTIONS: list[Callable] = [
    check_breakout_volume,
    check_divergence_to_agreement,
]


def scan_stock(
    close: float,
    high_60: float,
    volume: float,
    avg_vol_20: float,
    main_inflow: float,
    turnover_rate: float,
    is_limit_up: bool,
    market_status: str,
) -> list[PatternScanResult]:
    """对单只股票执行所有模式扫描"""
    results = []
    kwargs = {
        "close": close,
        "high_60": high_60,
        "volume": volume,
        "avg_vol_20": avg_vol_20,
        "main_inflow": main_inflow,
        "turnover_rate": turnover_rate,
        "is_limit_up": is_limit_up,
        "market_status": market_status,
    }

    for func in SCAN_FUNCTIONS:
        try:
            result = func(**{k: v for k, v in kwargs.items() if k in func.__code__.co_varnames})
            if result:
                results.append(result)
        except Exception as e:
            logger.warning(f"模式 {func.__name__} 扫描异常: {e}")

    return results
