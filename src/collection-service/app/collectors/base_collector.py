"""Base collector with rate limiting, logging, and common parsing helpers."""

import asyncio
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger()


class BaseCollector(ABC):
    """Abstract base class for all data collectors.

    Provides rate limiting, structured logging, and Korean financial data parsing helpers.
    """

    def __init__(self, name: str, rate_limit_per_minute: int = 30):
        self.name = name
        self.rate_limit_per_minute = rate_limit_per_minute
        self._request_timestamps: list[float] = []
        self.log = logger.bind(collector=name)

    async def _rate_limit_wait(self) -> None:
        """Wait if necessary to respect the rate limit."""
        now = time.monotonic()
        window = 60.0

        # Remove timestamps outside the 1-minute window
        self._request_timestamps = [
            ts for ts in self._request_timestamps if now - ts < window
        ]

        if len(self._request_timestamps) >= self.rate_limit_per_minute:
            oldest = self._request_timestamps[0]
            sleep_time = window - (now - oldest) + 0.1
            self.log.info("rate_limit_wait", sleep_seconds=round(sleep_time, 2))
            await asyncio.sleep(sleep_time)

        self._request_timestamps.append(time.monotonic())

    @abstractmethod
    async def collect(self, **kwargs: Any) -> dict[str, Any]:
        """Collect data from the source. Must be implemented by subclasses."""
        ...

    @staticmethod
    def clean_price_string(price_str: str) -> int | None:
        """Parse Korean price strings like '75,300' or '75300원' into integers."""
        if not price_str:
            return None
        cleaned = re.sub(r"[^\d]", "", price_str.strip())
        return int(cleaned) if cleaned else None

    @staticmethod
    def parse_korean_number(num_str: str) -> float | None:
        """Parse Korean number strings like '1,234.56' or '-5.23%'."""
        if not num_str:
            return None
        cleaned = num_str.strip().replace(",", "").replace("%", "")
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def parse_date(date_str: str) -> datetime | None:
        """Parse date strings in common Korean financial formats."""
        if not date_str:
            return None
        date_str = date_str.strip()
        formats = [
            "%Y.%m.%d",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def parse_volume(volume_str: str) -> int | None:
        """Parse volume strings like '12,345,678'."""
        if not volume_str:
            return None
        cleaned = re.sub(r"[^\d]", "", volume_str.strip())
        return int(cleaned) if cleaned else None
