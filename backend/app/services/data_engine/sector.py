"""行业板块数据模型 + 抽象基类 + 名称→代码映射"""
import logging
import time
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------- 行业数据模型 ----------

class SectorData(BaseModel):
    """行业板块行情数据"""
    code: str = ""                          # 板块代码，如 BK0498
    name: str = ""                          # 板块名称
    sector_index: float | None = None       # 板块指数点位
    sector_change_percent: float | None = None  # 涨跌幅%
    leading_stocks: list[dict] = []         # 领涨个股 [{code,name,change_pct}]
    policy_news: list[str] = []             # 近期政策/事件
    fund_flow: str = ""                     # 资金流向概况
    source: str = ""                        # 数据来源名称


# ---------- 抽象数据源 ----------

class SectorProvider(ABC):
    """行业数据源适配器抽象基类"""
    name: str = ""

    @abstractmethod
    async def fetch_sector(self, code: str) -> SectorData | None:
        """获取单个板块行情数据"""


# ---------- 名称→代码映射（东财板块列表缓存 + 内置兜底）----------

_SECTOR_NAME_CACHE: dict[str, dict] = {}     # {name_lower: {code, name, type}}
_CACHE_TS: float = 0
_CACHE_TTL: float = 3600                     # 1 小时
_EASTMONEY_TIMEOUT: float = 5.0              # 东财 API 超时（秒）

# 内置板块名称→代码映射（当东财 API 不可用时兜底）
# 覆盖 A 股主要行业板块，定期从东财官网同步更新
_BUILTIN_SECTORS: dict[str, dict] = {
    "半导体":       {"code": "BK0498", "name": "半导体", "type": "行业"},
    "白酒":         {"code": "BK0477", "name": "白酒", "type": "行业"},
    "新能源":       {"code": "BK0493", "name": "新能源", "type": "概念"},
    "新能源汽车":   {"code": "BK0900", "name": "新能源汽车", "type": "概念"},
    "人工智能":     {"code": "BK0800", "name": "人工智能", "type": "概念"},
    "芯片":         {"code": "BK0451", "name": "芯片", "type": "概念"},
    "5g":          {"code": "BK0700", "name": "5G概念", "type": "概念"},
    "光伏":         {"code": "BK0478", "name": "光伏", "type": "概念"},
    "锂电池":       {"code": "BK0573", "name": "锂电池", "type": "概念"},
    "医药":         {"code": "BK0465", "name": "医药", "type": "行业"},
    "生物医药":     {"code": "BK0465", "name": "医药", "type": "行业"},
    "医疗":         {"code": "BK0465", "name": "医药", "type": "行业"},
    "军工":         {"code": "BK0489", "name": "军工", "type": "概念"},
    "银行":         {"code": "BK0475", "name": "银行", "type": "行业"},
    "证券":         {"code": "BK0473", "name": "证券", "type": "行业"},
    "券商":         {"code": "BK0473", "name": "证券", "type": "行业"},
    "保险":         {"code": "BK0474", "name": "保险", "type": "行业"},
    "房地产":       {"code": "BK0451", "name": "房地产", "type": "行业"},
    "汽车":         {"code": "BK0481", "name": "汽车", "type": "行业"},
    "电力":         {"code": "BK0428", "name": "电力", "type": "行业"},
    "煤炭":         {"code": "BK0437", "name": "煤炭", "type": "行业"},
    "钢铁":         {"code": "BK0477", "name": "钢铁", "type": "行业"},
    "有色":         {"code": "BK0478", "name": "有色金属", "type": "行业"},
    "化工":         {"code": "BK0483", "name": "化工", "type": "行业"},
    "农业":         {"code": "BK0484", "name": "农牧饲渔", "type": "行业"},
    "消费":         {"code": "BK0470", "name": "消费", "type": "行业"},
    "传媒":         {"code": "BK0486", "name": "文化传媒", "type": "行业"},
    "软件":         {"code": "BK0487", "name": "软件开发", "type": "行业"},
    "计算机":       {"code": "BK0487", "name": "软件开发", "type": "行业"},
    "通信":         {"code": "BK0448", "name": "通信", "type": "行业"},
    "机械":         {"code": "BK0480", "name": "机械设备", "type": "行业"},
    "家电":         {"code": "BK0482", "name": "家电", "type": "行业"},
    "数字货币":     {"code": "BK0883", "name": "数字货币", "type": "概念"},
    "元宇宙":       {"code": "BK1000", "name": "元宇宙", "type": "概念"},
    "机器人":       {"code": "BK0891", "name": "机器人", "type": "概念"},
    "储能":         {"code": "BK1010", "name": "储能", "type": "概念"},
    "氢能":         {"code": "BK0864", "name": "氢能源", "type": "概念"},
    "碳中和":       {"code": "BK0899", "name": "碳中和", "type": "概念"},
    "东数西算":     {"code": "BK1060", "name": "东数西算", "type": "概念"},
    "信创":         {"code": "BK1100", "name": "信创", "type": "概念"},
    "chatgpt":     {"code": "BK1115", "name": "ChatGPT概念", "type": "概念"},
    "数据要素":     {"code": "BK1130", "name": "数据要素", "type": "概念"},
    "低空经济":     {"code": "BK1160", "name": "低空经济", "type": "概念"},
}


async def _fetch_sector_list_from_eastmoney() -> dict[str, dict]:
    """从东财拉取全部行业+概念板块列表，返回 {归一化名称: {code, name, type}}"""
    global _SECTOR_NAME_CACHE, _CACHE_TS

    now = time.monotonic()
    if _CACHE_TS > 0 and (now - _CACHE_TS) < _CACHE_TTL:
        return _SECTOR_NAME_CACHE

    result: dict[str, dict] = {}

    # 板块类型: t1=行业, t2=概念, t3=地域
    for sec_type, type_label in [("t1", "行业"), ("t2", "概念"), ("t3", "地域")]:
        try:
            url = (
                "https://push2.eastmoney.com/api/qt/clist/get"
                f"?fs=m:90+{sec_type}"
                "&fid=f3&po=1&pn=500"
                "&fields=f12,f14"
            )
            async with httpx.AsyncClient(timeout=_EASTMONEY_TIMEOUT) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                data = resp.json().get("data")
                if not data or not data.get("diff"):
                    continue
                for item in data["diff"]:
                    code = str(item.get("f12", ""))
                    name = str(item.get("f14", ""))
                    if not code or not name:
                        continue
                    # 归一化 key：全小写+去空格
                    key = name.lower().strip()
                    result[key] = {"code": code, "name": name, "type": type_label}
                    # 别名：去掉常见后缀
                    for suffix in ["板块", "概念", "行业", "指数"]:
                        if name.endswith(suffix):
                            key2 = name[:-len(suffix)].lower().strip()
                            if key2 and key2 not in result:
                                result[key2] = {"code": code, "name": name, "type": type_label}
        except Exception as e:
            logger.warning(f"东财板块列表获取失败 [{type_label}]: {e}")

    _SECTOR_NAME_CACHE = result
    _CACHE_TS = now
    logger.info(f"板块列表缓存更新: {len(result)} 条")
    return result


async def lookup_sector_code(name: str) -> dict | None:
    """按名称查找板块代码，支持模糊匹配

    查找顺序：东财实时列表 → 内置映射 → 模糊匹配
    返回 {"code": "BK0498", "name": "半导体", "type": "行业"} 或 None
    """
    if not name:
        return None

    key = name.lower().strip()

    # 0. 先查内置映射（本地，瞬时响应）
    if key in _BUILTIN_SECTORS:
        return _BUILTIN_SECTORS[key]
    for builtin_key, info in _BUILTIN_SECTORS.items():
        if key in builtin_key or builtin_key in key:
            return info

    # 1. 再查东财 API 列表
    cache = await _fetch_sector_list_from_eastmoney()

    # 2. 精确匹配
    if key in cache:
        return cache[key]

    # 3. 模糊匹配：包含关系
    candidates = []
    for cached_key, info in cache.items():
        if key in cached_key or cached_key in key:
            candidates.append((len(cached_key), info))
    if candidates:
        candidates.sort()
        return candidates[0][1]

    # 4. 单个词匹配
    for cached_key, info in cache.items():
        info_name = info["name"].lower()
        if any(w in info_name for w in key.split()):
            candidates.append((len(cached_key), info))
    if candidates:
        candidates.sort()
        return candidates[0][1]

    return None


def clear_sector_name_cache():
    """清除板块名称缓存（用于测试/刷新）"""
    global _SECTOR_NAME_CACHE, _CACHE_TS
    _SECTOR_NAME_CACHE = {}
    _CACHE_TS = 0
