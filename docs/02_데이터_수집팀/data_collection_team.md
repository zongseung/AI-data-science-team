# 02. 데이터 수집팀 상세 설계

## 1. 팀 구성

### 1.1 조직도
```
수집팀장 (Collection Lead Agent)
│
├── KOSPI 수집 에이전트
│   ├── 반도체 섹터 수집기
│   │   └── 삼성전자, SK하이닉스, DB하이텍, ...
│   ├── 자동차 섹터 수집기
│   │   └── 현대차, 기아, 현대모비스, ...
│   ├── 바이오 섹터 수집기
│   │   └── 삼성바이오로직스, 셀트리온, ...
│   ├── IT/소프트웨어 섹터 수집기
│   │   └── 네이버, 카카오, ...
│   └── 에너지/화학 섹터 수집기
│       └── LG화학, SK이노베이션, ...
│
├── KOSDAQ 수집 에이전트
│   ├── IT/소프트웨어 수집기
│   ├── 바이오/제약 수집기
│   └── 반도체/장비 수집기
│
├── 공시 수집 에이전트 (DART Collector)
│   ├── 주요 공시 (사업보고서, 반기보고서, 분기보고서)
│   ├── 수시 공시 (주요사항보고서)
│   └── 공정거래 공시
│
└── 뉴스 수집 에이전트 (News Collector)
    ├── 경제 뉴스 (한경, 매경, 서울경제)
    ├── 증권 뉴스 (이데일리, 인포스탁)
    └── 해외 뉴스 (Reuters, Bloomberg 한국 관련)
```

### 1.2 에이전트 역할 정의

| 에이전트 | 역할 | 데이터 소스 | 수집 주기 |
|---------|------|-----------|----------|
| 수집팀장 | 작업 분배, 상태 모니터링, 결과 취합 | - | 상시 |
| KOSPI 수집기 | KOSPI 종목 주가 데이터 수집 | 네이버 금융, KRX | 요청 시 / 매일 장마감 후 |
| KOSDAQ 수집기 | KOSDAQ 종목 주가 데이터 수집 | 네이버 금융, KRX | 요청 시 / 매일 장마감 후 |
| 공시 수집기 | DART 전자공시 수집 | DART OpenAPI | 요청 시 / 1시간 간격 |
| 뉴스 수집기 | 관련 뉴스 수집 및 분류 | 뉴스 사이트 | 요청 시 / 30분 간격 |

## 2. 데이터 수집 소스

### 2.1 주가 데이터 소스

#### 네이버 금융 (Naver Finance)
```
URL 패턴:
- 종목 정보: https://finance.naver.com/item/main.naver?code={종목코드}
- 시세 데이터: https://finance.naver.com/item/sise_day.naver?code={종목코드}
- 투자자별 매매동향: https://finance.naver.com/item/frgn.naver?code={종목코드}

수집 항목:
- 현재가, 전일대비, 등락률
- 시가, 고가, 저가
- 거래량, 거래대금
- 시가총액
- PER, PBR, EPS, BPS
- 52주 최고/최저
- 외국인 보유비율
- 일별 시세 (과거 데이터)
```

#### KRX 한국거래소
```
URL: http://data.krx.co.kr/
API: KRX 데이터 API

수집 항목:
- 전종목 시세 (KOSPI/KOSDAQ)
- 업종별 시세
- 투자자별 매매동향
- 공매도 현황
```

### 2.2 공시 데이터 소스

#### DART 전자공시 (OpenAPI 활용)
```
API Base URL: https://opendart.fss.or.kr/api/

엔드포인트:
- /list.json - 공시 목록 조회
- /document.xml - 공시 원문
- /fnlttSinglAcntAll.json - 단일회사 전체 재무제표
- /fnlttMultiAcnt.json - 다중회사 재무제표
- /majorstock.json - 대주주 현황

수집 항목:
- 사업보고서
- 반기/분기보고서
- 주요사항보고서 (유상증자, M&A 등)
- 재무제표 데이터
```

### 2.3 뉴스 데이터 소스

```
소스:
- 네이버 뉴스 검색: https://search.naver.com/search.naver?where=news&query={종목명}
- 한국경제: https://www.hankyung.com/
- 매일경제: https://www.mk.co.kr/

수집 항목:
- 제목, 본문 요약
- 발행일시
- 출처
- 관련 종목 태깅
```

## 3. MCP + Playwright 수집 구현

### 3.1 MCP 도구 정의

```python
# mcp/tools/browser_tools.py

from mcp.server import Server
from playwright.async_api import async_playwright

app = Server("stock-data-collector")

@app.tool()
async def browse_stock_page(stock_code: str) -> dict:
    """
    Playwright로 네이버 금융 종목 페이지에 접근하여 데이터 수집

    Args:
        stock_code: 종목코드 (e.g., "005930")

    Returns:
        종목의 현재 시세 데이터
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
        await page.goto(url)

        # 데이터 추출
        data = {
            "current_price": await page.locator("#_nowVal").text_content(),
            "change": await page.locator("#_diff .blind").text_content(),
            "change_rate": await page.locator("#_rate .blind").text_content(),
            "volume": await page.locator("table.no_info tr:nth-child(3) td:first-child .blind").text_content(),
            "market_cap": await page.locator("#_market_sum").text_content(),
        }

        await browser.close()
        return data


@app.tool()
async def browse_stock_history(stock_code: str, pages: int = 5) -> list:
    """
    일별 시세 데이터 수집 (과거 데이터)

    Args:
        stock_code: 종목코드
        pages: 수집할 페이지 수 (1페이지 = 10거래일)
    """
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for pg in range(1, pages + 1):
            url = f"https://finance.naver.com/item/sise_day.naver?code={stock_code}&page={pg}"
            await page.goto(url)

            rows = await page.locator("table.type2 tr").all()
            for row in rows:
                cells = await row.locator("td span.tah").all()
                if len(cells) >= 6:
                    results.append({
                        "date": await cells[0].text_content(),
                        "close": await cells[1].text_content(),
                        "change": await cells[2].text_content(),
                        "open": await cells[3].text_content(),
                        "high": await cells[4].text_content(),
                        "low": await cells[5].text_content(),
                    })

        await browser.close()
    return results


@app.tool()
async def search_dart_disclosure(stock_code: str, api_key: str) -> list:
    """
    DART OpenAPI를 통한 공시 목록 조회

    Args:
        stock_code: 종목코드
        api_key: DART OpenAPI 키
    """
    import httpx

    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": stock_code,
        "bgn_de": "20250101",
        "page_count": 10,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()

    return data.get("list", [])


@app.tool()
async def search_stock_news(query: str, count: int = 10) -> list:
    """
    네이버 뉴스에서 종목 관련 뉴스 검색

    Args:
        query: 검색어 (종목명)
        count: 수집할 뉴스 수
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = f"https://search.naver.com/search.naver?where=news&query={query}"
        await page.goto(url)

        articles = []
        news_items = await page.locator(".news_area").all()

        for item in news_items[:count]:
            title = await item.locator(".news_tit").text_content()
            desc = await item.locator(".news_dsc").text_content()
            source = await item.locator(".info.press").text_content()
            link = await item.locator(".news_tit").get_attribute("href")

            articles.append({
                "title": title.strip(),
                "description": desc.strip(),
                "source": source.strip(),
                "url": link,
            })

        await browser.close()
    return articles
```

### 3.2 수집 에이전트 구현

```python
# agents/collection/stock_collector.py

class StockCollector(BaseAgent):
    """주가 데이터 수집 에이전트"""

    def __init__(self, market: str, sector: str, stocks: list[str]):
        super().__init__(
            agent_id=f"{market}_{sector}_collector",
            name=f"{market} {sector} 수집기",
            team="collection"
        )
        self.market = market
        self.sector = sector
        self.stocks = stocks  # 종목코드 리스트

    async def execute(self, task: Task) -> TaskResult:
        """종목 데이터 수집 실행"""
        await self.update_status(AgentStatus.WORKING, f"{self.sector} 섹터 데이터 수집 중")

        results = {}
        total = len(self.stocks)

        for i, stock_code in enumerate(self.stocks):
            progress = (i + 1) / total
            await self.update_status(
                AgentStatus.WORKING,
                f"{stock_code} 수집 중 ({i+1}/{total})"
            )

            # MCP 도구 호출
            price_data = await mcp_client.call_tool("browse_stock_page", {
                "stock_code": stock_code
            })
            history = await mcp_client.call_tool("browse_stock_history", {
                "stock_code": stock_code,
                "pages": 5
            })

            results[stock_code] = {
                "current": price_data,
                "history": history
            }

            # DB 저장
            await self.save_to_db(stock_code, results[stock_code])

            # 진행상황 이벤트 발행
            await event_bus.emit(EventType.COLLECTION_PROGRESS, {
                "agent_id": self.agent_id,
                "stock_code": stock_code,
                "progress": progress
            })

        await self.update_status(AgentStatus.IDLE, "수집 완료")
        return TaskResult(success=True, data=results)
```

### 3.3 수집팀 매니저

```python
# agents/collection/manager.py

class CollectionManager:
    """수집팀 매니저 - 작업 분배 및 조율"""

    def __init__(self):
        self.agents: dict[str, StockCollector] = {}
        self.disclosure_agent = DisclosureCollector()
        self.news_agent = NewsCollector()

    async def initialize(self):
        """섹터별 수집 에이전트 초기화"""
        sectors = {
            "KOSPI": {
                "반도체": ["005930", "000660", "042700"],
                "자동차": ["005380", "000270", "012330"],
                "바이오": ["207940", "068270"],
                "IT": ["035420", "035720"],
                "에너지": ["051910", "096770"],
            },
            "KOSDAQ": {
                "IT": ["293490", "263750"],
                "바이오": ["328130", "196170"],
                "반도체장비": ["403870", "336370"],
            }
        }

        for market, market_sectors in sectors.items():
            for sector, stocks in market_sectors.items():
                agent = StockCollector(market, sector, stocks)
                self.agents[f"{market}_{sector}"] = agent

    async def collect_stock(self, stock_code: str) -> dict:
        """특정 종목 데이터 수집 요청 처리"""
        # 1. 주가 데이터 수집
        price_task = Task(type="collect_price", params={"stock_code": stock_code})

        # 2. 공시 데이터 수집 (병렬)
        disclosure_task = Task(type="collect_disclosure", params={"stock_code": stock_code})

        # 3. 뉴스 수집 (병렬)
        news_task = Task(type="collect_news", params={"stock_code": stock_code})

        # 병렬 실행
        results = await asyncio.gather(
            self._collect_price(stock_code),
            self.disclosure_agent.execute(disclosure_task),
            self.news_agent.execute(news_task),
        )

        return {
            "price": results[0],
            "disclosure": results[1],
            "news": results[2],
        }

    async def collect_sector(self, sector: str) -> dict:
        """섹터 전체 데이터 수집"""
        sector_agents = [
            agent for key, agent in self.agents.items()
            if sector in key
        ]

        results = await asyncio.gather(*[
            agent.execute(Task(type="collect_sector"))
            for agent in sector_agents
        ])

        return dict(zip([a.agent_id for a in sector_agents], results))
```

## 4. 종목 카테고리 세분화

### 4.1 KOSPI 섹터 분류

| 섹터 | 대표 종목 | 종목코드 |
|------|----------|---------|
| 반도체 | 삼성전자 | 005930 |
| | SK하이닉스 | 000660 |
| | DB하이텍 | 042700 |
| 자동차 | 현대차 | 005380 |
| | 기아 | 000270 |
| | 현대모비스 | 012330 |
| 바이오 | 삼성바이오로직스 | 207940 |
| | 셀트리온 | 068270 |
| IT | 네이버 | 035420 |
| | 카카오 | 035720 |
| 에너지/화학 | LG화학 | 051910 |
| | SK이노베이션 | 096770 |
| 금융 | KB금융 | 105560 |
| | 삼성생명 | 032830 |
| 유통 | 신세계 | 004170 |
| | 이마트 | 139480 |

### 4.2 KOSDAQ 섹터 분류

| 섹터 | 대표 종목 | 종목코드 |
|------|----------|---------|
| IT/소프트웨어 | 카카오게임즈 | 293490 |
| 바이오/제약 | HLB | 028300 |
| 반도체/장비 | 리노공업 | 058470 |
| 엔터/미디어 | 하이브 | 352820 |

### 4.3 동적 종목 관리

```python
# config/constants.py

STOCK_CATEGORIES = {
    "KOSPI": {
        "반도체": {
            "description": "반도체 설계, 제조, 장비 관련 기업",
            "stocks": ["005930", "000660", "042700"],
            "keywords": ["반도체", "메모리", "파운드리", "HBM"],
        },
        "자동차": {
            "description": "완성차, 부품, 전기차 관련 기업",
            "stocks": ["005380", "000270", "012330"],
            "keywords": ["자동차", "전기차", "EV", "자율주행"],
        },
        # ... 추가 섹터
    },
    "KOSDAQ": {
        # ... KOSDAQ 섹터
    }
}
```

## 5. 수집 스케줄링

```python
# 스케줄링 전략
SCHEDULE = {
    "realtime": {
        "주가 시세": "장중 5분 간격 (09:00 ~ 15:30)",
        "급등락 알림": "변동률 ±3% 초과 시 즉시",
    },
    "periodic": {
        "일봉 데이터": "매일 16:00 (장마감 후)",
        "공시 확인": "매 1시간",
        "뉴스 수집": "매 30분",
    },
    "on_demand": {
        "사용자 요청": "텔레그램 명령 즉시 실행",
        "섹터 전체": "요청 시 병렬 수집",
    }
}
```

## 6. 에러 핸들링

```python
class CollectionError(Exception):
    """수집 에러 기본 클래스"""
    pass

class ScrapingBlockedError(CollectionError):
    """스크래핑 차단 시"""
    pass

class DataSourceUnavailableError(CollectionError):
    """데이터 소스 접근 불가"""
    pass

# 재시도 전략
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 2,  # seconds
    "max_delay": 30,
    "exponential_backoff": True,
    "fallback_sources": {
        "naver_finance": ["krx", "yahoo_kr"],
        "dart": ["naver_disclosure"],
    }
}
```

## 7. 웹 시각화 연동

수집 진행 시 웹에서 보이는 캐릭터 상태:

```
상태           │ 애니메이션           │ 설명
───────────────┼────────────────────┼──────────────
대기중         │ 책상에 앉아 대기      │ idle 상태
수집 시작      │ 컴퓨터 화면 켜짐      │ 브라우저 열기
데이터 추출 중  │ 타이핑 + 데이터 파티클 │ Playwright 동작 중
데이터 저장    │ 서류 정리 모션        │ DB 저장 중
수집 완료      │ ✓ 체크 + 분석팀 전달  │ 서류 배달 캐릭터 이동
수집 실패      │ ❗ 경고 + 재시도      │ 에러 발생
```
