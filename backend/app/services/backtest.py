"""回测引擎 — 历史模式信号统计，滑动窗口遍历全市场数据"""
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pattern_scan import PATTERN_REGISTRY

logger = logging.getLogger(__name__)

# 回测参数
ENTRY_STOP_PCT = 0.03       # 止损线：入场价 -3%
ENTRY_TARGET_PCT = 0.05     # 止盈线：入场价 +5%
MAX_HOLD_DAYS = 3           # 最长持仓天数
MIN_WINDOW = 60             # 滑动窗口：至少需要60个交易日数据


@dataclass
class BacktestStats:
    pattern_id: int
    lookback_days: int
    sample_count: int
    win_rate: float
    avg_gain: float
    avg_loss: float
    avg_pnl_ratio: float


def _check_breakout_conditions(
    close: float, high_60: float, volume: float, avg_vol_20: float,
    change_pct: float, market_status: str,
) -> bool:
    """平台突破放量 — 历史条件检查（main_inflow 用涨跌幅+量比近似）"""
    cfg = PATTERN_REGISTRY[1].conditions
    if high_60 <= 0 or (high_60 - close) / high_60 > cfg["price_near_high"]:
        return False
    if avg_vol_20 <= 0 or volume <= avg_vol_20 * cfg["volume_ratio"]:
        return False
    # 主力净流入近似: 当日上涨 + 放量 = 大概率主力流入
    if change_pct < 1.0:
        return False
    if market_status == "RETREAT" or market_status == "ICE":
        return False
    return True


def _check_divergence_conditions(
    change_pct: float, turnover_rate: float, market_status: str,
) -> bool:
    """分歧转一致 — 历史条件检查（用涨跌幅近似涨停）"""
    cfg = PATTERN_REGISTRY[2].conditions
    # 近似涨停: 涨跌幅 >= 9.5%
    if change_pct < 9.5:
        return False
    if turnover_rate < cfg["min_turnover"]:
        return False
    if market_status == "RETREAT":
        return False
    return True


async def _load_market_status_map(db: AsyncSession) -> dict[str, str]:
    """加载历史市场状态: {trade_date_str: status}"""
    rows = await db.execute(
        text("SELECT trade_date, market_status FROM market_sentiment ORDER BY trade_date")
    )
    return {str(r[0]): r[1] for r in rows.fetchall()}


async def run_backtest(
    db: AsyncSession,
    pattern_id: int,
    lookback_days: int = 120,
) -> BacktestStats:
    """运行历史回测，统计模式胜率与盈亏比

    遍历所有有足够数据的股票，滑动窗口检查触发条件，
    模拟入场后跟踪止盈/止损/到期退出。
    """
    # 市场状态映射
    market_map = await _load_market_status_map(db)

    # 取所有有行情数据的股票
    stock_rows = await db.execute(
        text("SELECT DISTINCT code FROM daily_quotes")
    )
    all_codes = [r[0] for r in stock_rows.fetchall()]
    if not all_codes:
        return BacktestStats(pattern_id=pattern_id, lookback_days=lookback_days,
                            sample_count=0, win_rate=0, avg_gain=0, avg_loss=0, avg_pnl_ratio=0)

    wins = 0
    losses = 0
    total_gain_pct = 0.0
    total_loss_pct = 0.0
    sample_count = 0

    for code in all_codes:
        # 取该股全部行情，按日期升序
        rows = await db.execute(
            text("SELECT trade_date, open, high, low, close, volume, change_pct, turnover_rate "
                 "FROM daily_quotes WHERE code=:c ORDER BY trade_date ASC"),
            {"c": code},
        )
        quotes = rows.fetchall()
        if len(quotes) < MIN_WINDOW + MAX_HOLD_DAYS:
            continue

        # 滑动窗口遍历
        for i in range(MIN_WINDOW, len(quotes) - MAX_HOLD_DAYS):
            window = quotes[i - MIN_WINDOW:i]
            today = quotes[i]
            trade_date_str = str(today[0])
            close = float(today[4])
            volume = float(today[5])
            change_pct = float(today[6]) if today[6] else 0
            turnover_rate = float(today[7]) if today[7] else 0
            market_status = market_map.get(trade_date_str, "WARM")

            # 窗口统计
            high_60 = max(float(q[2]) for q in window)
            avg_vol_20 = sum(float(q[5]) for q in window[-20:]) / 20

            # 条件检查
            triggered = False
            if pattern_id == 1:
                triggered = _check_breakout_conditions(
                    close, high_60, volume, avg_vol_20, change_pct, market_status)
            elif pattern_id == 2:
                triggered = _check_divergence_conditions(
                    change_pct, turnover_rate, market_status)

            if not triggered:
                continue

            # 模拟入场：以当日收盘价买入
            entry = close
            stop_loss = entry * (1 - ENTRY_STOP_PCT)
            take_profit = entry * (1 + ENTRY_TARGET_PCT)

            # 跟踪后续几天
            exit_price = None
            exit_reason = "hold"
            for j in range(1, MAX_HOLD_DAYS + 1):
                if i + j >= len(quotes):
                    break
                day_j = quotes[i + j]
                day_high = float(day_j[2])
                day_low = float(day_j[3])
                day_close = float(day_j[4])

                if day_low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "stop_loss"
                    break
                elif day_high >= take_profit:
                    exit_price = take_profit
                    exit_reason = "take_profit"
                    break
                elif j == MAX_HOLD_DAYS:
                    exit_price = day_close
                    exit_reason = "time_exit"
                    break

            if exit_price is None:
                exit_price = float(quotes[i + MAX_HOLD_DAYS][4]) if i + MAX_HOLD_DAYS < len(quotes) else close
                exit_reason = "time_exit"

            pnl_pct = (exit_price - entry) / entry * 100
            sample_count += 1
            if pnl_pct > 0:
                wins += 1
                total_gain_pct += pnl_pct
            else:
                losses += 1
                total_loss_pct += abs(pnl_pct)

    # 汇总统计
    win_rate = round(wins / sample_count, 4) if sample_count > 0 else 0
    avg_gain = round(total_gain_pct / wins, 2) if wins > 0 else 0
    avg_loss = round(total_loss_pct / losses, 2) if losses > 0 else 0
    avg_pnl_ratio = round(avg_gain / avg_loss, 2) if avg_loss > 0 else 0

    stats = BacktestStats(
        pattern_id=pattern_id,
        lookback_days=lookback_days,
        sample_count=sample_count,
        win_rate=win_rate,
        avg_gain=avg_gain,
        avg_loss=avg_loss,
        avg_pnl_ratio=avg_pnl_ratio,
    )

    # 写入缓存表
    await _cache_result(db, stats)
    return stats


async def _cache_result(db: AsyncSession, stats: BacktestStats):
    """写入/更新回测缓存"""
    from datetime import datetime
    await db.execute(
        text("INSERT OR REPLACE INTO pattern_backtest_cache "
             "(pattern_id, lookback_days, sample_count, win_rate, avg_gain, avg_loss, avg_pnl_ratio, updated_at) "
             "VALUES (:pid, :ld, :sc, :wr, :ag, :al, :apr, :ua)"),
        {
            "pid": stats.pattern_id,
            "ld": stats.lookback_days,
            "sc": stats.sample_count,
            "wr": stats.win_rate,
            "ag": stats.avg_gain,
            "al": stats.avg_loss,
            "apr": stats.avg_pnl_ratio,
            "ua": datetime.utcnow(),
        },
    )
    await db.commit()


async def get_cached_stats(db: AsyncSession, pattern_id: int) -> Optional[BacktestStats]:
    """读取缓存的回测结果"""
    row = await db.execute(
        text("SELECT pattern_id, lookback_days, sample_count, win_rate, avg_gain, avg_loss, avg_pnl_ratio "
             "FROM pattern_backtest_cache WHERE pattern_id=:pid ORDER BY updated_at DESC LIMIT 1"),
        {"pid": pattern_id},
    )
    r = row.fetchone()
    if r:
        return BacktestStats(
            pattern_id=r[0], lookback_days=r[1], sample_count=int(r[2]),
            win_rate=float(r[3]), avg_gain=float(r[4]), avg_loss=float(r[5]),
            avg_pnl_ratio=float(r[6]),
        )
    return None


async def cache_all_patterns(db: AsyncSession):
    """一次性预计算所有模式回测结果并缓存"""
    results = {}
    for pattern_id in [1, 2]:
        stats = await run_backtest(db, pattern_id)
        results[pattern_id] = stats
        logger.info(f"[BACKTEST] 模式 {pattern_id}: samples={stats.sample_count} "
                    f"win_rate={stats.win_rate} pnl_ratio={stats.avg_pnl_ratio}")
    return results
