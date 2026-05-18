"""每日定时数据同步任务 — APScheduler 驱动"""
import logging
import asyncio
from datetime import date, timedelta
from sqlalchemy import text

from app.database import engine
from app.services.market_temp import compute_from_eastmoney

logger = logging.getLogger(__name__)

CORE_STOCKS = [
    ("000001", "平安银行", "银行"), ("000002", "万科A", "房地产"),
    ("000858", "五粮液", "白酒"), ("002230", "科大讯飞", "AI"),
    ("300750", "宁德时代", "新能源"), ("600519", "贵州茅台", "白酒"),
    ("688981", "中芯国际", "半导体"), ("002594", "比亚迪", "新能源"),
    ("601318", "中国平安", "金融"), ("300059", "东方财富", "券商"),
]


async def sync_daily_quotes():
    """同步核心股票池的日K线数据 (Sina 源)"""
    import akshare as ak

    today = date.today()
    end_date = (today - timedelta(days=1)).strftime("%Y%m%d")
    start_date = (today - timedelta(days=90)).strftime("%Y%m%d")

    async with engine.connect() as conn:
        for code, name, industry in CORE_STOCKS:
            await conn.execute(
                text("INSERT OR REPLACE INTO stocks (code, name, industry) VALUES (:c, :n, :i)"),
                {"c": code, "n": name, "i": industry},
            )

    total = 0
    async with engine.connect() as conn:
        for code, name, _ in CORE_STOCKS:
            try:
                market = "sz" if code.startswith(("0", "3")) else "sh"
                df = await asyncio.to_thread(
                    ak.stock_zh_a_daily, symbol=f"{market}{code}",
                    start_date=start_date, end_date=end_date, adjust="qfq",
                )
                for _, r in df.iterrows():
                    o = float(r["open"]); c = float(r["close"])
                    await conn.execute(text("""INSERT OR REPLACE INTO daily_quotes
                        (code, trade_date, open, high, low, close, volume, amount, change_pct, turnover_rate)
                        VALUES (:c,:d,:o,:h,:l,:cl,:v,:a,:cp,:t)"""), {
                        "c": code, "d": str(r["date"]),
                        "o": o, "h": float(r["high"]), "l": float(r["low"]),
                        "cl": c, "v": int(r["volume"]), "a": float(r["amount"]),
                        "cp": round((c - o) / o * 100, 2) if o > 0 else 0,
                        "t": float(r.get("turnover", 0)) if "turnover" in r else 0,
                    })
                total += len(df)
            except Exception as e:
                logger.warning(f"同步 {code} {name} K线失败: {e}")
        await conn.commit()
    return total


async def sync_market_temperature():
    """同步市场温度数据 (东方财富直连)"""
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    prev = (date.today() - timedelta(days=2)).strftime("%Y%m%d")
    date_display = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    result = await compute_from_eastmoney(yesterday, prev)

    async with engine.connect() as conn:
        await conn.execute(
            text("INSERT OR REPLACE INTO market_sentiment (trade_date, max_board_height, promotion_rate, bomb_rate, yesterday_limit_up_avg_return, market_status) VALUES (:d, :mh, :pr, :br, :yar, :ms)"),
            {
                "d": date_display,
                "mh": result.max_board_height,
                "pr": result.promotion_rate,
                "br": result.bomb_rate,
                "yar": result.yesterday_avg_return,
                "ms": result.status,
            },
        )
        await conn.commit()
    return result.status


async def run_daily_sync():
    """盘后全量同步入口 — APScheduler 定时调用"""
    logger.info("[SYNC] 开始每日盘后数据同步...")
    results = {}

    try:
        n = await sync_daily_quotes()
        results["quotes"] = n
        logger.info(f"[SYNC] K线同步完成: {n} 条")
    except Exception as e:
        results["quotes"] = str(e)
        logger.error(f"[SYNC] K线同步失败: {e}")

    try:
        status = await sync_market_temperature()
        results["market_temp"] = status
        logger.info(f"[SYNC] 市场温度计算完成: {status}")
    except Exception as e:
        results["market_temp"] = str(e)
        logger.error(f"[SYNC] 市场温度失败: {e}")

    try:
        from app.services.backtest import cache_all_patterns
        from app.database import async_session_factory
        async with async_session_factory() as db:
            bt_results = await cache_all_patterns(db)
            results["backtest"] = {str(k): v.sample_count for k, v in bt_results.items()}
        logger.info(f"[SYNC] 回测计算完成: {results['backtest']}")
    except Exception as e:
        results["backtest"] = str(e)
        logger.error(f"[SYNC] 回测失败: {e}")

    logger.info(f"[SYNC] 每日同步完成: {results}")
    return results
