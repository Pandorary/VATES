"""新浪财经行业数据适配器 — 补充数据源

通过新浪 hq.sinajs.cn API 获取中证/深证行业指数实时行情。
东财 push2 API 被封锁时，此数据源提供真实行业指数数据。

数据格式：var hq_str_{code}="名称,当前价,昨收价,开盘价,最高价,最低价,..."
"""
import logging

import httpx

from app.services.data_engine.sector import SectorData, SectorProvider

logger = logging.getLogger(__name__)

# 常用板块名称 → 新浪行业指数代码映射
# 新浪指数覆盖中证/深证体系下的主要行业
_NAME_TO_SINA_CODE: dict[str, dict] = {
    # 中证行业指数 (sz399xxx)
    "军工":       {"code": "sz399967", "name": "中证军工"},
    "航天":       {"code": "sz399967", "name": "中证军工"},
    "银行":       {"code": "sz399986", "name": "中证银行"},
    "白酒":       {"code": "sz399997", "name": "中证白酒"},
    "证券":       {"code": "sz399975", "name": "证券公司"},
    "券商":       {"code": "sz399975", "name": "证券公司"},
    "煤炭":       {"code": "sz399998", "name": "中证煤炭"},
    "传媒":       {"code": "sz399971", "name": "中证传媒"},
    "医药":       {"code": "sh000991", "name": "全指医药"},
    "医疗":       {"code": "sh000991", "name": "全指医药"},
    "信息技术":   {"code": "sh000993", "name": "全指信息"},
    "信息":       {"code": "sh000993", "name": "全指信息"},
    "消费":       {"code": "sz399993", "name": "CSWD消费"},
    "食品":       {"code": "sz399993", "name": "CSWD消费"},
    "一带一路":   {"code": "sz399991", "name": "一带一路"},
    "地产":       {"code": "sz399965", "name": "800地产"},
    "房地产":     {"code": "sz399965", "name": "800地产"},
    "科技":       {"code": "sz399339", "name": "中证科技"},
    "计算机":     {"code": "sz399363", "name": "中证计算机"},
    "硬件":       {"code": "sz399360", "name": "创硬件"},
    "红利":       {"code": "sz399324", "name": "中证红利"},
    "移动互联":   {"code": "sz399970", "name": "移动互联"},
    "国企改革":   {"code": "sz399974", "name": "国企改革"},
    "信息安全":   {"code": "sz399994", "name": "信息安全"},
    "智能家居":   {"code": "sz399996", "name": "智能家居"},
    "能源金属":   {"code": "sz399366", "name": "能源金属"},
    "粮食":       {"code": "sz399365", "name": "中证粮食"},
    "新能源":     {"code": "sz399319", "name": "能源金属"},  # 近似

    # 深证行业指数 (sz3992xx)
    "金融":       {"code": "sz399240", "name": "金融指数"},
    "IT":        {"code": "sz399239", "name": "IT指数"},
    "建筑":       {"code": "sz399242", "name": "建筑指数"},
    # 深证主题指数
    "创业板":     {"code": "sz399006", "name": "创业板指"},
    "创业科技":   {"code": "sz399279", "name": "创科技50"},
    "AI":        {"code": "sz399284", "name": "AI 50"},
    "人工智能":   {"code": "sz399284", "name": "AI 50"},

    # 上证行业指数
    "有色":       {"code": "sh000819", "name": "有色金属"},
    "有色金属":   {"code": "sh000819", "name": "有色金属"},
    "医药细分":   {"code": "sh000814", "name": "细分医药"},
    "消费电子":   {"code": "sh000847", "name": "腾讯济安"},
}


class SinaSectorProvider(SectorProvider):
    """新浪财经行业数据源 — hq.sinajs.cn 实时行情"""

    name = "sina"

    async def fetch_sector(self, code: str) -> SectorData | None:
        """按新浪指数代码获取行情

        code 可以是：
        - 新浪代码（sz399967 / sh000991）
        - 板块名称（通过 _NAME_TO_SINA_CODE 映射）
        """
        # 1. 尝试名称→代码映射
        sina_info = _lookup_sina_code(code)
        if sina_info:
            sina_code = sina_info["code"]
            default_name = sina_info["name"]
        else:
            sina_code = code
            default_name = code

        # 2. 调新浪 API
        try:
            url = f"https://hq.sinajs.cn/list={sina_code}"
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(url, headers={
                    "Referer": "https://finance.sina.com.cn",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                })
                if resp.status_code != 200:
                    return None
                raw = resp.text.strip()
        except Exception as e:
            logger.debug(f"新浪板块数据获取失败 [{sina_code}]: {e}")
            return None

        # 3. 解析
        return self._parse(sina_code, default_name, raw)

    @staticmethod
    def _parse(sina_code: str, default_name: str, raw: str) -> SectorData | None:
        """解析新浪 JS 变量格式

        格式: var hq_str_sz399967="中证军工,12501.826,12444.271,..."
        字段: 名称,当前价,昨收,开盘,最高,最低,成交量,成交额,...
        """
        if not raw or '="' not in raw:
            return None

        try:
            # 提取引号内的数据
            data_str = raw.split('="')[1].rstrip('";')
            parts = data_str.split(",")
            if len(parts) < 6:
                return None

            name = parts[0] if parts[0] else default_name
            current = _safe_float(parts[1])     # 当前价
            prev_close = _safe_float(parts[2])  # 昨收
            # open = parts[3], high = parts[4], low = parts[5]
            volume = _safe_float(parts[7]) if len(parts) > 7 else None
            amount = _safe_float(parts[8]) if len(parts) > 8 else None

            if current is None:
                return None

            # 计算涨跌幅
            change_pct = None
            if current and prev_close and prev_close != 0:
                change_pct = round((current - prev_close) / prev_close * 100, 2)

            return SectorData(
                code=sina_code,
                name=name,
                sector_index=current,
                sector_change_percent=change_pct,
                leading_stocks=[],
                policy_news=[],
                fund_flow="",
                source="sina",
            )
        except Exception as e:
            logger.debug(f"新浪板块数据解析失败 [{sina_code}]: {e}")
            return None


def _lookup_sina_code(name: str) -> dict | None:
    """按名称查新浪指数代码，支持模糊匹配"""
    key = name.lower().strip()

    # 精确匹配
    if key in _NAME_TO_SINA_CODE:
        return _NAME_TO_SINA_CODE[key]

    # 包含匹配
    for mapped_key, info in _NAME_TO_SINA_CODE.items():
        if key in mapped_key or mapped_key in key:
            return info

    return None


def _safe_float(v) -> float | None:
    """安全转 float"""
    if v is None or v == "-" or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
