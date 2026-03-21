"""DART OpenAPI disclosure collector using httpx."""

from datetime import datetime, timedelta
from typing import Any

import httpx

from ai_data_science_team.collectors.base_collector import BaseCollector
from ai_data_science_team.config.constants import (
    DART_ENDPOINTS,
    DEFAULT_DISCLOSURE_DAYS,
)
from ai_data_science_team.config.settings import settings


class DisclosureCollector(BaseCollector):
    """Collects disclosure and financial statement data from DART OpenAPI.

    Uses httpx async client for API calls. Rate limited to 60 req/min per DART policy.
    """

    def __init__(self):
        super().__init__(name="disclosure", rate_limit_per_minute=60)
        self._api_key = settings.dart_api_key

    async def collect(
        self,
        stock_code: str,
        corp_code: str,
        days: int = DEFAULT_DISCLOSURE_DAYS,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Collect recent disclosures and financial statements."""
        self.log.info(
            "collect_start",
            stock_code=stock_code,
            corp_code=corp_code,
            days=days,
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            disclosures = await self._fetch_disclosure_list(
                client, corp_code, days
            )
            financials = await self._fetch_financial_statements(
                client, corp_code
            )

        result = {
            "stock_code": stock_code,
            "corp_code": corp_code,
            "disclosures": disclosures,
            "financial_statements": financials,
        }
        self.log.info(
            "collect_done",
            stock_code=stock_code,
            disclosure_count=len(disclosures),
        )
        return result

    async def _fetch_disclosure_list(
        self,
        client: httpx.AsyncClient,
        corp_code: str,
        days: int,
    ) -> list[dict[str, Any]]:
        """Fetch recent disclosure list from DART."""
        if not self._api_key:
            self.log.warning("no_dart_api_key")
            return []

        await self._rate_limit_wait()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        params = {
            "crtfc_key": self._api_key,
            "corp_code": corp_code,
            "bgn_de": start_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
            "page_count": "100",
        }

        resp = await client.get(DART_ENDPOINTS["disclosure_list"], params=params)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "000":
            self.log.warning(
                "dart_api_error",
                status=data.get("status"),
                message=data.get("message"),
            )
            return []

        disclosures = []
        for item in data.get("list", []):
            disclosures.append({
                "rcept_no": item.get("rcept_no"),
                "rcept_dt": item.get("rcept_dt"),
                "report_nm": item.get("report_nm"),
                "flr_nm": item.get("flr_nm"),
                "corp_name": item.get("corp_name"),
            })

        return disclosures

    async def _fetch_financial_statements(
        self,
        client: httpx.AsyncClient,
        corp_code: str,
        year: int | None = None,
        report_code: str = "11011",
    ) -> list[dict[str, Any]]:
        """Fetch financial statements (사업보고서) from DART.

        Args:
            corp_code: DART corporation code
            year: Business year (defaults to previous year)
            report_code: 11011=annual, 11012=semi, 11013=Q1, 11014=Q3
        """
        if not self._api_key:
            return []

        await self._rate_limit_wait()

        if year is None:
            year = datetime.now().year - 1

        params = {
            "crtfc_key": self._api_key,
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": report_code,
            "fs_div": "OFS",  # 개별재무제표
        }

        resp = await client.get(
            DART_ENDPOINTS["financial_statements"], params=params
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "000":
            self.log.warning(
                "dart_financial_error",
                status=data.get("status"),
                message=data.get("message"),
            )
            return []

        statements = []
        for item in data.get("list", []):
            statements.append({
                "account_nm": item.get("account_nm"),
                "thstrm_amount": item.get("thstrm_amount"),
                "frmtrm_amount": item.get("frmtrm_amount"),
                "bfefrmtrm_amount": item.get("bfefrmtrm_amount"),
                "sj_nm": item.get("sj_nm"),
            })

        return statements
