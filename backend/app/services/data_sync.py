"""数据同步服务 — 将 AkShare 数据写入 SQLite"""
import logging
from datetime import date
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DEFAULT_STOCKS = [
    ("000001", "平安银行", "银行"),
    ("000002", "万科A", "房地产"),
    ("000858", "五粮液", "白酒"),
    ("002230", "科大讯飞", "AI"),
    ("300750", "宁德时代", "新能源"),
    ("600519", "贵州茅台", "白酒"),
    ("688981", "中芯国际", "半导体"),
    ("002594", "比亚迪", "新能源"),
    ("601318", "中国平安", "金融"),
    ("300059", "东方财富", "券商"),
]


async def sync_stocks(session: AsyncSession):
    """同步股票基础信息"""
    for code, name, industry in DEFAULT_STOCKS:
        await session.execute(
            text("INSERT OR REPLACE INTO stocks (code, name, industry) VALUES (:c, :n, :i)"),
            {"c": code, "n": name, "i": industry},
        )
    await session.flush()
    logger.info(f"股票基础信息: {len(DEFAULT_STOCKS)} 只")


async def sync_daily_quotes(session: AsyncSession, date_str: str):
    """同步交易日行情 (date_str = YYYY-MM-DD)"""
    import akshare as ak
    count = 0
    for code, name, _ in DEFAULT_STOCKS:
        try:
            market = "sz" if code.startswith(("0", "3")) else "sh"
            full = f"{market}{code}"
            df = ak.stock_zh_a_daily(symbol=full, start_date=date_str, end_date=date_str, adjust="qfq")
            if df.empty:
                continue
            r = df.iloc[-1]
            await session.execute(
                text("""INSERT OR REPLACE INTO daily_quotes
                    (code, trade_date, open, high, low, close, volume, amount, change_pct, turnover_rate)
                    VALUES (:c, :d, :o, :h, :l, :cl, :v, :a, :cp, :t)"""),
                {
                    "c": code, "d": str(r["date"]),
                    "o": float(r["open"]), "h": float(r["high"]),
                    "l": float(r["low"]), "cl": float(r["close"]),
                    "v": int(r["volume"]), "a": float(r["amount"]),
                    "cp": round((float(r["close"]) - float(r["open"])) / float(r["open"]) * 100, 2),
                    "t": float(r["turnover"]),
                },
            )
            count += 1
        except Exception as e:
            logger.warning(f"行情同步失败 {code} {name}: {e}")
    await session.flush()
    logger.info(f"行情数据: {count} 只")


async def sync_limit_up(session: AsyncSession, date_compact: str):
    """同步涨停板 (date_compact = YYYYMMDD)"""
    import akshare as ak
    try:
        df = ak.stock_zt_pool_em(date=date_compact)
        date_val = f"{date_compact[:4]}-{date_compact[4:6]}-{date_compact[6:]}"
        for _, row in df.iterrows():
            bh = int(row.get("连板数", 1))
            await session.execute(
                text("INSERT OR REPLACE INTO limit_up_records (code, trade_date, is_continuous, board_height, broken_rate) VALUES (:c, :d, :ic, :bh, 0)"),
                {"c": str(row["代码"]), "d": date_val, "ic": bh, "bh": bh},
            )
        await session.flush()
        logger.info(f"涨停数据: {len(df)} 条")
    except Exception as e:
        logger.warning(f"涨停同步失败: {e}")


async def sync_market_sentiment(session: AsyncSession, date_compact: str):
    """市场情绪计算"""
    import akshare as ak
    try:
        df = ak.stock_zt_pool_em(date=date_compact)
        max_h = int(df["连板数"].max()) if "连板数" in df.columns and not df.empty else 0
        date_val = f"{date_compact[:4]}-{date_compact[4:6]}-{date_compact[6:]}"
        await session.execute(
            text("INSERT OR REPLACE INTO market_sentiment (trade_date, max_board_height, promotion_rate, bomb_rate, yesterday_limit_up_avg_return, market_status) VALUES (:d, :mh, 0.3, 0.2, 1.5, 'WARM')"),
            {"d": date_val, "mh": max_h},
        )
        await session.flush()
        logger.info(f"市场情绪: 连板高度={max_h}")
    except Exception as e:
        logger.warning(f"市场情绪失败: {e}")


async def full_sync(session: AsyncSession):
    """全量数据同步"""
    d = date.today()
    date_display = d.strftime("%Y-%m-%d")
    date_compact = d.strftime("%Y%m%d")

    logger.info(f"开始全量同步: {date_display}")
    await sync_stocks(session)
    await sync_daily_quotes(session, date_display)
    await sync_limit_up(session, date_compact)
    await sync_market_sentiment(session, date_compact)
    await session.commit()
    logger.info("全量同步完成")
