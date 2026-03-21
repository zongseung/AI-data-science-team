"""News collector using Playwright for Naver News scraping."""

from typing import Any

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from ai_data_science_team.collectors.base_collector import BaseCollector
from ai_data_science_team.config.constants import (
    DEFAULT_NEWS_COUNT,
    NAVER_FINANCE_URLS,
)


class NewsCollector(BaseCollector):
    """Scrapes financial news from Naver News search.

    Collects: title, description, source, URL, publication date.
    """

    def __init__(self):
        super().__init__(name="news", rate_limit_per_minute=15)

    async def collect(
        self,
        stock_name: str,
        count: int = DEFAULT_NEWS_COUNT,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Collect recent news articles for the given stock name."""
        self.log.info("collect_start", stock_name=stock_name, count=count)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.set_default_timeout(15_000)

            try:
                articles = await self._search_news(page, stock_name, count)
                result = {
                    "stock_name": stock_name,
                    "articles": articles,
                    "count": len(articles),
                }
                self.log.info(
                    "collect_done",
                    stock_name=stock_name,
                    article_count=len(articles),
                )
                return result
            finally:
                await browser.close()

    async def _search_news(
        self, page: Any, stock_name: str, count: int
    ) -> list[dict[str, Any]]:
        """Search and parse Naver News results."""
        articles: list[dict[str, Any]] = []
        pages_needed = (count // 10) + 1

        for page_num in range(1, pages_needed + 1):
            await self._rate_limit_wait()

            start = (page_num - 1) * 10 + 1
            query = f"{stock_name} 주가"
            url = (
                NAVER_FINANCE_URLS["news"].format(query=query)
                + f"&start={start}&sort=date"
            )

            await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            news_items = soup.select("div.news_area")
            if not news_items:
                # Fallback: try alternative selectors
                news_items = soup.select("li.bx")

            for item in news_items:
                article = self._parse_news_item(item)
                if article:
                    articles.append(article)

            if len(articles) >= count:
                break

        return articles[:count]

    def _parse_news_item(self, item: Any) -> dict[str, Any] | None:
        """Parse a single news item from the search results."""
        # Title and link
        title_tag = item.select_one("a.news_tit")
        if not title_tag:
            title_tag = item.select_one("a.title_link")
        if not title_tag:
            return None

        title = title_tag.get_text(strip=True)
        link = title_tag.get("href", "")

        # Description
        desc_tag = item.select_one("div.news_dsc") or item.select_one("a.api_txt_lines.dsc_txt_wrap")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # Source (press name)
        source_tag = item.select_one("a.info.press") or item.select_one("span.info_group a.press")
        source = source_tag.get_text(strip=True) if source_tag else ""

        # Date
        date_tag = item.select_one("span.info") or item.select_one("span.sub_txt")
        pub_date = ""
        if date_tag:
            pub_date = date_tag.get_text(strip=True)

        return {
            "title": title,
            "description": description,
            "source": source,
            "url": link,
            "published_at": pub_date,
        }
