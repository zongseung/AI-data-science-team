"""Data quality validation for collected financial data."""

from typing import Any

import structlog

logger = structlog.get_logger()


class DataQualityChecker:
    """Validates and reports data quality issues in collected data.

    Checks for: missing values, outliers, data type consistency, and completeness.
    """

    def __init__(self):
        self.log = logger.bind(component="data_quality")

    def check(self, collected_data: dict[str, Any]) -> dict[str, Any]:
        """Run all quality checks and return a quality report."""
        report: dict[str, Any] = {
            "overall_status": "pass",
            "checks": [],
            "warnings": [],
            "errors": [],
        }

        # Check price data
        if "price_data" in collected_data:
            self._check_price_data(collected_data["price_data"], report)

        # Check disclosure data
        if "disclosures" in collected_data:
            self._check_disclosure_data(collected_data["disclosures"], report)

        # Check news data
        if "news" in collected_data:
            self._check_news_data(collected_data["news"], report)

        # Check market data
        if "market_data" in collected_data:
            self._check_market_data(collected_data["market_data"], report)

        # Determine overall status
        if report["errors"]:
            report["overall_status"] = "fail"
        elif report["warnings"]:
            report["overall_status"] = "warning"

        self.log.info(
            "quality_check_done",
            status=report["overall_status"],
            warnings=len(report["warnings"]),
            errors=len(report["errors"]),
        )
        return report

    def _check_price_data(
        self, price_data: dict[str, Any], report: dict[str, Any]
    ) -> None:
        """Validate stock price data."""
        # Check current price exists
        current = price_data.get("current", {})
        if not current.get("price"):
            report["errors"].append("현재가 데이터 누락")
        else:
            report["checks"].append("현재가 확인 완료")

        # Check daily prices
        daily = price_data.get("daily_prices", [])
        if not daily:
            report["errors"].append("일별 시세 데이터 없음")
        else:
            report["checks"].append(f"일별 시세 {len(daily)}일 수집 완료")

            # Check for missing values in OHLCV
            missing_count = 0
            for row in daily:
                for field in ["open", "high", "low", "close", "volume"]:
                    if row.get(field) is None:
                        missing_count += 1

            if missing_count > 0:
                report["warnings"].append(
                    f"일별 시세 결측치 {missing_count}건 발견"
                )

            # Check for price outliers (> 30% daily change)
            outliers = []
            for i in range(1, len(daily)):
                prev_close = daily[i - 1].get("close")
                curr_close = daily[i].get("close")
                if prev_close and curr_close and prev_close > 0:
                    change_pct = abs(curr_close - prev_close) / prev_close
                    if change_pct > 0.30:
                        outliers.append(daily[i].get("date"))

            if outliers:
                report["warnings"].append(
                    f"일별 시세 이상치(30%+) {len(outliers)}건: {outliers[:3]}"
                )

    def _check_disclosure_data(
        self, disclosure_data: dict[str, Any], report: dict[str, Any]
    ) -> None:
        """Validate disclosure data."""
        disclosures = disclosure_data.get("disclosures", [])
        if not disclosures:
            report["warnings"].append("최근 공시 데이터 없음 (기간 내 공시 미존재 가능)")
        else:
            report["checks"].append(f"공시 {len(disclosures)}건 수집 완료")

        financials = disclosure_data.get("financial_statements", [])
        if not financials:
            report["warnings"].append("재무제표 데이터 없음")
        else:
            report["checks"].append(f"재무제표 항목 {len(financials)}건 수집 완료")

    def _check_news_data(
        self, news_data: dict[str, Any], report: dict[str, Any]
    ) -> None:
        """Validate news data."""
        articles = news_data.get("articles", [])
        if not articles:
            report["warnings"].append("뉴스 데이터 없음")
        else:
            report["checks"].append(f"뉴스 {len(articles)}건 수집 완료")

            # Check for articles with missing titles
            empty_titles = sum(1 for a in articles if not a.get("title"))
            if empty_titles:
                report["warnings"].append(f"제목 누락 뉴스 {empty_titles}건")

    def _check_market_data(
        self, market_data: dict[str, Any], report: dict[str, Any]
    ) -> None:
        """Validate market data."""
        kospi = market_data.get("kospi", {})
        if not kospi.get("value"):
            report["warnings"].append("KOSPI 지수 데이터 누락")
        else:
            report["checks"].append(f"KOSPI 지수: {kospi['value']}")

        exchange = market_data.get("exchange_rate", {})
        if not exchange.get("usd_krw"):
            report["warnings"].append("USD/KRW 환율 데이터 누락")
        else:
            report["checks"].append(f"USD/KRW: {exchange['usd_krw']}")
