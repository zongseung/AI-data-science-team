from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

LOADER_URL = "https://data.krx.co.kr/comm/srt/srtLoader/index.cmd"
JSON_URL = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"


@dataclass
class KRXClient:
    """Minimal client for KRX page warm-up + JSON POST calls."""

    timeout: float = 15.0

    def __post_init__(self) -> None:
        self._client = httpx.Client(
            timeout=self.timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                ),
                "Referer": "https://data.krx.co.kr/",
                "Origin": "https://data.krx.co.kr",
            },
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "KRXClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def warmup(self, screen_id: str, isu_cd: str | None = None) -> None:
        """Open loader page once to set expected cookies/session."""
        params = {"screenId": screen_id}
        if isu_cd:
            params["isuCd"] = isu_cd
        response = self._client.get(LOADER_URL, params=params)
        response.raise_for_status()

    def post_json(self, *, bld: str, payload: dict[str, Any]) -> dict[str, Any]:
        form = {"bld": bld, **payload}
        response = self._client.post(JSON_URL, data=form)
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected KRX response format (not a JSON object).")
        return data
