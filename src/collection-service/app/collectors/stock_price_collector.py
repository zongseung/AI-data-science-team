"""Stock price collector using Playwright for Naver Finance scraping."""

from typing import Any

from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup

from ai_data_science_team.collectors.base_collector import BaseCollector
from ai_data_science_team.config.constants import (
    DEFAULT_COLLECTION_DAYS,
    NAVER_FINANCE_URLS,
)


class StockPriceCollector(BaseCollector):
    """Scrapes stock price data from Naver Finance using Playwright.

    Collects: current price, daily OHLCV, PER/PBR/EPS, foreign investor ratio.
    """

    def __init__(self):
        super().__init__(name="stock_price", rate_limit_per_minute=20)

    async def collect(
        self,
        stock_code: str,
        days: int = DEFAULT_COLLECTION_DAYS,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Collect stock price data for the given stock code."""
        self.log.info("collect_start", stock_code=stock_code, days=days)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.set_default_timeout(15_000)

            try:
                current = await self._fetch_current_price(page, stock_code)
                daily = await self._fetch_daily_prices(page, stock_code, days)
                fundamentals = await self._fetch_fundamentals(page, stock_code)
                foreign = await self._fetch_foreign_ratio(page, stock_code)

                result = {
                    "stock_code": stock_code,
                    "current": current,
                    "daily_prices": daily,
                    "fundamentals": fundamentals,
                    "foreign_ratio": foreign,
                }
                self.log.info(
                    "collect_done",
                    stock_code=stock_code,
                    daily_count=len(daily),
                )
                return result
            finally:
                await browser.close()

    async def _fetch_current_price(
        self, page: Page, stock_code: str
    ) -> dict[str, Any]:
        """Fetch current price and basic info from the main page."""
        await self._rate_limit_wait()
        url = NAVER_FINANCE_URLS["main"].format(stock_code=stock_code)
        await page.goto(url, wait_until="domcontentloaded")

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        result: dict[str, Any] = {"stock_code": stock_code}

        # Current price
        price_tag = soup.select_one("p.no_today .blind")
        if price_tag:
            result["price"] = self.clean_price_string(price_tag.get_text())

        # Change
        change_tag = soup.select_one("p.no_exday .blind")
        if change_tag:
            change_text = change_tag.get_text().strip()
            result["change"] = self.clean_price_string(change_text)

        # Determine up/down
        ico_tag = soup.select_one("p.no_exday em span.ico")
        if ico_tag:
            classes = ico_tag.get("class", [])
            if "up" in " ".join(classes):
                result["change_direction"] = "up"
            elif "dn" in " ".join(classes):
                result["change_direction"] = "down"
                if result.get("change"):
                    result["change"] = -result["change"]

        # Volume
        table = soup.select_one("table.no_info")
        if table:
            tds = table.select("td")
            for i, td in enumerate(tds):
                text = td.get_text(strip=True)
                if "거래량" in text and i + 1 < len(tds):
                    result["volume"] = self.parse_volume(tds[i + 1].get_text())

        return result

    async def _fetch_daily_prices(
        self, page: Page, stock_code: str, days: int
    ) -> list[dict[str, Any]]:
        """Fetch daily OHLCV data from sise_day page."""
        prices: list[dict[str, Any]] = []
        pages_needed = (days // 10) + 1

        for page_num in range(1, pages_needed + 1):
            await self._rate_limit_wait()
            url = NAVER_FINANCE_URLS["sise_day"].format(
                stock_code=stock_code, page=page_num
            )
            await page.goto(url, wait_until="domcontentloaded")

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            rows = soup.select("table.type2 tr")
            for row in rows:
                cols = row.select("td span.tah")
                if len(cols) < 7:
                    continue

                date_tag = cols[0]
                date = self.parse_date(date_tag.get_text(strip=True))
                if not date:
                    continue

                prices.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "close": self.clean_price_string(cols[1].get_text()),
                    "change": self.clean_price_string(cols[2].get_text()),
                    "open": self.clean_price_string(cols[3].get_text()),
                    "high": self.clean_price_string(cols[4].get_text()),
                    "low": self.clean_price_string(cols[5].get_text()),
                    "volume": self.parse_volume(cols[6].get_text()),
                })

            if len(prices) >= days:
                break

        return prices[:days]

    async def _fetch_fundamentals(
        self, page: Page, stock_code: str
    ) -> dict[str, Any]:
        """Extract PER, PBR, EPS from main page."""
        await self._rate_limit_wait()
        url = NAVER_FINANCE_URLS["main"].format(stock_code=stock_code)
        await page.goto(url, wait_until="domcontentloaded")

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        result: dict[str, Any] = {}

        # PER, EPS, PBR are in the table on the main page
        table = soup.select_one("table.per_table")
        if table:
            rows = table.select("tr")
            for row in rows:
                header = row.select_one("th")
                value = row.select_one("td")
                if header and value:
                    key = header.get_text(strip=True)
                    val = self.parse_korean_number(value.get_text(strip=True))
                    if "PER" in key:
                        result["per"] = val
                    elif "EPS" in key:
                        result["eps"] = val
                    elif "PBR" in key:
                        result["pbr"] = val

        # Fallback: try tab_con1 area
        if not result:
            tab_area = soup.select("div.tab_con1 table em")
            labels = ["per", "eps", "estimated_per", "estimated_eps", "pbr", "bps"]
            for i, em in enumerate(tab_area):
                if i < len(labels):
                    result[labels[i]] = self.parse_korean_number(em.get_text(strip=True))

        return result

    async def _fetch_foreign_ratio(
        self, page: Page, stock_code: str
    ) -> dict[str, Any]:
        """Fetch foreign investor holding ratio."""
        await self._rate_limit_wait()
        url = NAVER_FINANCE_URLS["foreign"].format(stock_code=stock_code, page=1)
        await page.goto(url, wait_until="domcontentloaded")

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        result: dict[str, Any] = {}

        rows = soup.select("table.type2 tr")
        for row in rows:
            cols = row.select("td span.tah")
            if len(cols) >= 6:
                date = self.parse_date(cols[0].get_text(strip=True))
                if date:
                    result = {
                        "date": date.strftime("%Y-%m-%d"),
                        "holding_ratio": self.parse_korean_number(
                            cols[5].get_text(strip=True)
                        ),
                        "net_buy": self.clean_price_string(cols[4].get_text()),
                    }
                    break

        return result
