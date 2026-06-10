"""Playwright 爬虫行业数据源 — 备用数据源

优先抓取东方财富板块页（quote.eastmoney.com/bk/{code}.html）
备用抓取新浪财经板块页（finance.sina.com.cn）

无头 Chromium，15s 超时
"""
import logging
import re

from app.services.data_engine.sector import SectorData, SectorProvider

logger = logging.getLogger(__name__)


class PlaywrightSectorProvider(SectorProvider):
    name = "playwright"

    async def fetch_sector(self, code: str) -> SectorData | None:
        # 优先东方财富板块页
        result = await self._scrape_eastmoney(code)
        if result:
            return result

        # 备用新浪财经
        return await self._scrape_sina(code)

    async def _scrape_eastmoney(self, code: str) -> SectorData | None:
        """抓取东方财富板块详情页"""
        try:
            from playwright.async_api import async_playwright

            url = f"https://quote.eastmoney.com/bk/{code}.html"
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    # 等待关键元素
                    await page.wait_for_selector(".bk", timeout=10000)
                    html = await page.content()
                except Exception:
                    html = await page.content()
                finally:
                    await browser.close()

            return self._parse_eastmoney_html(html, code)
        except ImportError:
            logger.debug("Playwright 未安装，跳过爬虫")
            return None
        except Exception as e:
            logger.warning(f"东方财富板块页抓取失败 [{code}]: {e}")
            return None

    async def _scrape_sina(self, code: str) -> SectorData | None:
        """抓取新浪财经板块页（兜底）"""
        try:
            from playwright.async_api import async_playwright

            url = f"https://finance.sina.com.cn/stock/sector/{code}.html"
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    html = await page.content()
                except Exception:
                    html = await page.content()
                finally:
                    await browser.close()

            return self._parse_sina_html(html, code)
        except ImportError:
            logger.debug("Playwright 未安装，跳过新浪爬虫")
            return None
        except Exception as e:
            logger.warning(f"新浪板块页抓取失败 [{code}]: {e}")
            return None

    def _parse_eastmoney_html(self, html: str, code: str) -> SectorData | None:
        """解析东方财富板块页面 HTML"""
        name = ""
        index_val = None
        change_pct = None
        leaders: list[dict] = []
        fund_flow = ""

        # 板块名称
        m = re.search(r'<title>([^<]+)板块', html)
        if not m:
            m = re.search(r'var\s+_sectName\s*=\s*"([^"]+)"', html)
        if m:
            name = m.group(1).strip()

        # 指数点位和涨跌幅
        m = re.search(r'var\s+_sectIdx\s*=\s*"([^"]+)"', html)
        if m:
            try:
                index_val = float(m.group(1))
            except ValueError:
                pass
        m = re.search(r'var\s+_sectChg\s*=\s*"([^"]+)"', html)
        if m:
            try:
                change_pct = float(m.group(1))
            except ValueError:
                pass

        # 领涨个股：常见 class="stock-item" 或 "tr" 中解析
        stock_pattern = re.findall(
            r'<a[^>]*>\s*(\d{6})\s*</a>.*?<a[^>]*>([^<]+)</a>.*?([\-\+]?\d+\.\d+%)',
            html, re.DOTALL,
        )
        for sc, sn, sp in stock_pattern[:5]:
            try:
                pct = float(sp.replace("%", ""))
            except ValueError:
                pct = 0
            leaders.append({"code": sc.strip(), "name": sn.strip(), "change_pct": pct})

        # 资金流向
        flow_m = re.search(r'(?:主力|资金).*?(?:净[流入流出]+)\s*([\-\+]?\d+\.?\d*)\s*(亿|万)', html)
        if flow_m:
            fund_flow = f"主力资金净{'流入' if flow_m.group(0).count('流入') > flow_m.group(0).count('流出') else '流出'} {flow_m.group(1)}{flow_m.group(2)}"

        if not name and index_val is None:
            return None

        return SectorData(
            code=code,
            name=name,
            sector_index=index_val,
            sector_change_percent=change_pct,
            leading_stocks=leaders,
            policy_news=[],
            fund_flow=fund_flow,
            source="playwright",
        )

    def _parse_sina_html(self, html: str, code: str) -> SectorData | None:
        """解析新浪财经板块页面 HTML"""
        name = ""
        index_val = None
        change_pct = None

        # 标题
        m = re.search(r'<title>([^<]+)</title>', html)
        if m:
            title = m.group(1)
            name = re.sub(r'[_\-\s]*新浪.*$', '', title).strip()

        # 涨跌幅
        m = re.search(r'(?:涨跌幅|涨跌).*?([\-\+]?\d+\.\d+)%', html)
        if m:
            try:
                change_pct = float(m.group(1))
            except ValueError:
                pass

        # 指数点位
        m = re.search(r'(?:点位|指数|最新)[^\d]*(\d{3,6}\.?\d*)', html)
        if m:
            try:
                index_val = float(m.group(1))
            except ValueError:
                pass

        if not name:
            return None

        return SectorData(
            code=code,
            name=name,
            sector_index=index_val,
            sector_change_percent=change_pct,
            leading_stocks=[],
            policy_news=[],
            fund_flow="",
            source="playwright",
        )
