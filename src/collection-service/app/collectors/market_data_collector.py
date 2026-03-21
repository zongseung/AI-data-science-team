"""Market data collector for KOSPI index, exchange rates, and US treasury yields."""

from typing import Any

import httpx
from bs4 import BeautifulSoup

from ai_data_science_team.collectors.base_collector import BaseCollector
from ai_data_science_team.config.constants import MARKET_DATA_URLS


class MarketDataCollector(BaseCollector):
    """Collects broad market data: KOSPI index, USD/KRW exchange rate, US 10Y yield.

    Uses httpx for server-rendered pages to avoid Playwright overhead.
    """

    def __init__(self):
        super().__init__(name="market_data", rate_limit_per_minute=30)

    async def collect(self, **kwargs: Any) -> dict[str, Any]:
        """Collect all market data points."""
        self.log.info("collect_start")

        async with httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        ) as client:
            kospi = await self._fetch_kospi(client)
            exchange = await self._fetch_exchange_rate(client)
            treasury = await self._fetch_us_treasury(client)

        result = {
            "kospi": kospi,
            "exchange_rate": exchange,
            "us_treasury_10y": treasury,
        }
        self.log.info("collect_done", kospi=kospi, exchange=exchange)
        return result

    async def _fetch_kospi(self, client: httpx.AsyncClient) -> dict[str, Any]:
        """Fetch KOSPI index from Naver Finance."""
        await self._rate_limit_wait()

        resp = await client.get(MARKET_DATA_URLS["kospi"])
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        result: dict[str, Any] = {}

        # KOSPI current value
        now_value = soup.select_one("#now_value")
        if now_value:
            result["value"] = self.parse_korean_number(now_value.get_text(strip=True))

        # Change
        change_value = soup.select_one("#change_value_01")
        if change_value:
            result["change"] = self.parse_korean_number(change_value.get_text(strip=True))

        change_rate = soup.select_one("#change_rate_01")
        if change_rate:
            result["change_rate"] = self.parse_korean_number(
                change_rate.get_text(strip=True)
            )

        return result

    async def _fetch_exchange_rate(
        self, client: httpx.AsyncClient
    ) -> dict[str, Any]:
        """Fetch USD/KRW exchange rate from Naver Market Index."""
        await self._rate_limit_wait()

        resp = await client.get(MARKET_DATA_URLS["exchange_rate"])
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        result: dict[str, Any] = {}

        # USD/KRW is typically the first item in market index
        market_items = soup.select("div.market_data div.data_lst li")
        for item in market_items:
            title = item.select_one("h3 a")
            if title and "달러" in title.get_text():
                value_tag = item.select_one("span.value")
                if value_tag:
                    result["usd_krw"] = self.parse_korean_number(
                        value_tag.get_text(strip=True)
                    )

                change_tag = item.select_one("span.change")
                if change_tag:
                    result["change"] = self.parse_korean_number(
                        change_tag.get_text(strip=True)
                    )
                break

        return result

    async def _fetch_us_treasury(
        self, client: httpx.AsyncClient
    ) -> dict[str, Any]:
        """Fetch US 10-year treasury yield from investing.com via Naver."""
        await self._rate_limit_wait()

        # Use Naver's world index page as a proxy
        url = "https://finance.naver.com/world/sise.naver?symbol=CMDT_CDT"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            # Try to find US bond yield from the world market page
            result: dict[str, Any] = {}
            value_tag = soup.select_one("#rate_value")
            if value_tag:
                result["yield_10y"] = self.parse_korean_number(
                    value_tag.get_text(strip=True)
                )
            return result
        except Exception as e:
            self.log.warning("us_treasury_fetch_failed", error=str(e))
            return {}
