"""交叉验证 — 比较多源数据一致性"""
import logging

from app.services.quotes.base import QuoteData

logger = logging.getLogger(__name__)

# 可比对的数值字段
_NUMERIC_FIELDS = ["price", "open", "high", "low", "close", "change", "change_percent", "volume", "amount"]
# 容差比例
_TOLERANCE = 0.02


def cross_validate_quotes(results: list[QuoteData]) -> tuple[QuoteData, str]:
    """交叉验证多源行情数据

    返回: (验证后的 QuoteData, 置信度标签 "高"/"中"/"低")
    """
    if not results:
        raise ValueError("results 不能为空")

    if len(results) == 1:
        # 单源：中置信度
        confidence = "中"
        return results[0], confidence

    # 多源：比对数值字段
    has_conflict = False
    base = results[0].model_copy()

    for field in _NUMERIC_FIELDS:
        values = []
        for r in results:
            v = getattr(r, field, None)
            if v is not None:
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    pass

        if len(values) < 2:
            continue

        avg = sum(values) / len(values)
        for v in values:
            if abs(avg) > 0.01 and abs(v - avg) / abs(avg) > _TOLERANCE:
                has_conflict = True
                logger.debug(f"交叉验证冲突: {field} values={values}")
                break

    if has_conflict:
        confidence = "低"
    elif sum(1 for f in _NUMERIC_FIELDS if getattr(base, f, None) is not None) >= 5:
        confidence = "高"
    else:
        confidence = "中"

    return base, confidence
