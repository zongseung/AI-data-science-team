# MCP Server Setup for Crypto News Collection

암호화폐 뉴스 수집을 위한 MCP(Model Context Protocol) 서버 설정 가이드입니다. MCP를 통해 Claude가 직접 뉴스 데이터를 수집하고 분석할 수 있습니다.

---

## Overview

```
Claude Desktop / Claude Code
    │
    ├── Free Crypto News MCP ──→ 660K+ articles (primary)
    ├── RSS Reader MCP ────────→ CoinDesk, CoinTelegraph (backup)
    └── CryptoPanic MCP ───────→ Social sentiment (optional)
```

세 가지 MCP 서버를 조합하여 포괄적인 뉴스 수집 파이프라인을 구성합니다.

---

## 1. Free Crypto News MCP Server

### 개요

- **Repository**: https://github.com/nirholas/free-crypto-news
- **인증**: 불필요 (완전 무료)
- **데이터**: 660,000+ 암호화폐 뉴스 아카이브
- **기능**: 코인별 필터링, 날짜 범위 검색, 키워드 검색

### 설치

```bash
# Repository clone
git clone https://github.com/nirholas/free-crypto-news.git
cd free-crypto-news

# Dependencies 설치
npm install
# 또는
pip install -r requirements.txt
```

### MCP 설정

`.claude/settings.local.json`에 다음을 추가합니다:

```json
{
  "mcpServers": {
    "free-crypto-news": {
      "command": "npx",
      "args": ["-y", "@nirholas/free-crypto-news-mcp"],
      "env": {}
    }
  }
}
```

> **Note**: 정확한 npm 패키지명은 해당 repository의 README를 확인하세요. 위 예시는 일반적인 MCP 서버 설정 패턴입니다.

### 사용 가능한 Tools

MCP 연결 후 다음 도구를 사용할 수 있습니다:

| Tool | 설명 | 파라미터 |
|------|------|----------|
| `search_news` | 키워드로 뉴스 검색 | `query`, `coin`, `from_date`, `to_date` |
| `get_latest` | 최신 뉴스 조회 | `coin`, `limit` |
| `get_article` | 특정 기사 상세 조회 | `article_id` |

### 테스트

MCP 서버 연결 확인:

```bash
# Claude Code에서 직접 테스트
claude "Free Crypto News MCP 서버에서 BTC 최신 뉴스 5개를 가져와줘"
```

정상 동작 시 BTC 관련 최신 뉴스 목록이 반환됩니다.

---

## 2. RSS Reader MCP Server

### 개요

- **Repository**: https://github.com/kwp-lab/rss-reader-mcp
- **인증**: 불필요
- **용도**: CoinDesk, CoinTelegraph RSS feed 수집 (backup source)

### 설치

```bash
# npm을 통한 설치
npm install -g @kwp-lab/rss-reader-mcp
```

### MCP 설정

`.claude/settings.local.json`에 추가:

```json
{
  "mcpServers": {
    "rss-reader": {
      "command": "npx",
      "args": ["-y", "@kwp-lab/rss-reader-mcp"],
      "env": {}
    }
  }
}
```

### 사용할 RSS Feed URLs

```
CoinDesk:       https://www.coindesk.com/arc/outboundfeeds/rss/
CoinTelegraph:  https://cointelegraph.com/rss
```

### 사용 가능한 Tools

| Tool | 설명 | 파라미터 |
|------|------|----------|
| `read_feed` | RSS feed 읽기 | `url` |
| `search_feed` | Feed 내 키워드 검색 | `url`, `query` |

### 테스트

```bash
# CoinDesk RSS feed 읽기 테스트
claude "RSS Reader MCP로 https://www.coindesk.com/arc/outboundfeeds/rss/ 피드를 읽어줘"
```

---

## 3. CryptoPanic MCP Server (Optional)

### 개요

- **용도**: 소셜 미디어 감성 데이터 수집
- **인증**: 무료 API 토큰 필요 (https://cryptopanic.com/developers/api/)
- **특징**: Reddit, Twitter 등 소셜 미디어 기반 sentiment 데이터 제공

### API 토큰 발급

1. https://cryptopanic.com 가입 (무료)
2. https://cryptopanic.com/developers/api/ 에서 API token 발급
3. `.env` 파일에 토큰 저장

```bash
# .env
CRYPTOPANIC_API_TOKEN=your_token_here
```

### MCP 설정

```json
{
  "mcpServers": {
    "cryptopanic": {
      "command": "npx",
      "args": ["-y", "@cryptopanic/mcp-server"],
      "env": {
        "CRYPTOPANIC_API_TOKEN": "${CRYPTOPANIC_API_TOKEN}"
      }
    }
  }
}
```

> **Note**: CryptoPanic MCP는 optional이며, 소셜 감성 데이터를 추가로 활용하고 싶을 때만 설정합니다.

---

## 전체 Settings 예시

세 가지 MCP 서버를 모두 등록한 `.claude/settings.local.json` 예시:

```json
{
  "mcpServers": {
    "free-crypto-news": {
      "command": "npx",
      "args": ["-y", "@nirholas/free-crypto-news-mcp"],
      "env": {}
    },
    "rss-reader": {
      "command": "npx",
      "args": ["-y", "@kwp-lab/rss-reader-mcp"],
      "env": {}
    },
    "cryptopanic": {
      "command": "npx",
      "args": ["-y", "@cryptopanic/mcp-server"],
      "env": {
        "CRYPTOPANIC_API_TOKEN": "${CRYPTOPANIC_API_TOKEN}"
      }
    }
  }
}
```

---

## MCP 연결 테스트

### 전체 연결 상태 확인

```bash
# Claude Code에서 MCP 서버 목록 확인
claude "/mcp"
```

정상적으로 설정된 경우, 등록된 MCP 서버 목록과 사용 가능한 tool이 표시됩니다.

### 개별 서버 테스트

```bash
# 1. Free Crypto News 테스트
claude "free-crypto-news MCP에서 BTC 뉴스 3개 가져와"

# 2. RSS Reader 테스트
claude "RSS reader MCP로 CoinDesk 최신 기사 확인해줘"

# 3. CryptoPanic 테스트 (optional)
claude "CryptoPanic에서 ETH 소셜 감성 데이터 조회해줘"
```

### 예상 응답 형식

```json
{
  "title": "Bitcoin Surges Past $100K as Institutional Demand Grows",
  "description": "Bitcoin reached a new milestone...",
  "source": "coindesk",
  "url": "https://www.coindesk.com/...",
  "published_at": "2026-03-22T10:30:00Z"
}
```

---

## Fallback: Direct HTTP 수집

MCP 서버를 사용할 수 없는 경우 direct HTTP 요청으로 fallback합니다.

### Fallback 전략

```
MCP 서버 호출
    │
    ├── 성공 → 데이터 반환
    │
    └── 실패 (3회 재시도)
         │
         ├── HTTP fallback 시도
         │    ├── Free Crypto News API (direct HTTP)
         │    └── RSS Feed (httpx + feedparser)
         │
         └── 전부 실패
              ├── 이전 수집 데이터 유지
              └── Alert 발송 (Telegram/Slack)
```

### HTTP Fallback 코드 예시

```python
import httpx
import feedparser

async def fetch_news_http_fallback(coin: str) -> list[dict]:
    """MCP 불가 시 direct HTTP로 뉴스 수집"""
    articles = []

    # 1. Free Crypto News API (direct)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.freecryptonews.com/v1/news",  # 예시 URL
                params={"coin": coin, "limit": 50}
            )
            if resp.status_code == 200:
                articles.extend(resp.json().get("articles", []))
    except Exception as e:
        logger.warning(f"Free Crypto News HTTP failed: {e}")

    # 2. RSS Feed fallback
    rss_urls = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cointelegraph.com/rss",
    ]
    for url in rss_urls:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url)
                feed = feedparser.parse(resp.text)
                for entry in feed.entries:
                    if coin.lower() in (entry.title + entry.get("summary", "")).lower():
                        articles.append({
                            "title": entry.title,
                            "description": entry.get("summary", ""),
                            "url": entry.link,
                            "published_at": entry.get("published", ""),
                            "source": url.split("/")[2],
                        })
        except Exception as e:
            logger.warning(f"RSS feed {url} failed: {e}")

    return articles
```

---

## Troubleshooting

### MCP 서버가 시작되지 않는 경우

```bash
# Node.js 버전 확인 (18+ 필요)
node --version

# npx 캐시 클리어
npx clear-npx-cache

# 수동 설치 후 시도
npm install -g @nirholas/free-crypto-news-mcp
```

### 연결 타임아웃

- MCP 서버 기본 타임아웃: 30초
- 네트워크 상태 확인
- 방화벽/프록시 설정 확인

### API 토큰 인식 실패 (CryptoPanic)

```bash
# .env 파일 로드 확인
echo $CRYPTOPANIC_API_TOKEN

# 직접 환경변수 설정
export CRYPTOPANIC_API_TOKEN=your_token_here
```

### RSS Feed 파싱 오류

- Feed URL 접근 가능 여부 확인: `curl -I https://www.coindesk.com/arc/outboundfeeds/rss/`
- XML 형식 변경 시 `feedparser` 버전 업데이트: `pip install --upgrade feedparser`
