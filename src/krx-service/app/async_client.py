"""Async KRX client with proxy support for anti-tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

LOADER_URL = "https://data.krx.co.kr/comm/srt/srtLoader/index.cmd"
JSON_URL = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"


@dataclass
class AsyncKRXClient:
    """Async minimal client for KRX with proxy support."""

    timeout: float = 15.0
    proxy: str | None = None  # e.g., "http://proxy.example.com:8080"
    proxy_auth: tuple[str, str] | None = None  # (username, password)

    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Referer": "https://data.krx.co.kr/",
            "Origin": "https://data.krx.co.kr",
        }

        # Proxy configuration
        client_kwargs = {
            "timeout": self.timeout,
            "headers": headers,
            "follow_redirects": True,
        }

        if self.proxy:
            # httpx 2.x uses 'proxy' instead of 'proxies'
            client_kwargs["proxy"] = self.proxy
            if self.proxy_auth:
                client_kwargs["auth"] = httpx.BasicAuth(*self.proxy_auth)

        self._client = httpx.AsyncClient(**client_kwargs)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncKRXClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def warmup(self, screen_id: str, isu_cd: str | None = None) -> None:
        """Open loader page once to set expected cookies/session."""
        params = {"screenId": screen_id}
        if isu_cd:
            params["isuCd"] = isu_cd
        response = await self._client.get(LOADER_URL, params=params)
        response.raise_for_status()

    async def post_json(self, *, bld: str, payload: dict[str, Any]) -> dict[str, Any]:
        form = {"bld": bld, **payload}
        response = await self._client.post(JSON_URL, data=form)
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected KRX response format (not a JSON object).")
        return data
