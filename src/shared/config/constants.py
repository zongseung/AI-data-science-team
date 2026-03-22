"""Stock codes, sector classifications, and market constants."""

# 주요 종목 코드 매핑
STOCK_CODES: dict[str, dict[str, str]] = {
    "삼성전자": {"stock_code": "005930", "corp_code": "00126380"},
    "SK하이닉스": {"stock_code": "000660", "corp_code": "00164779"},
    "LG에너지솔루션": {"stock_code": "373220", "corp_code": "01634089"},
    "삼성바이오로직스": {"stock_code": "207940", "corp_code": "00901012"},
    "현대자동차": {"stock_code": "005380", "corp_code": "00164742"},
    "기아": {"stock_code": "000270", "corp_code": "00106641"},
    "셀트리온": {"stock_code": "068270", "corp_code": "00421045"},
    "KB금융": {"stock_code": "105560", "corp_code": "00688996"},
    "POSCO홀딩스": {"stock_code": "005490", "corp_code": "00117631"},
    "NAVER": {"stock_code": "035420", "corp_code": "00266961"},
    "카카오": {"stock_code": "035720", "corp_code": "00258801"},
    "LG화학": {"stock_code": "051910", "corp_code": "00356361"},
    "삼성SDI": {"stock_code": "006400", "corp_code": "00126186"},
    "현대모비스": {"stock_code": "012330", "corp_code": "00164788"},
    "신한지주": {"stock_code": "055550", "corp_code": "00382199"},
    "하나금융지주": {"stock_code": "086790", "corp_code": "00547583"},
    "삼성물산": {"stock_code": "028260", "corp_code": "00631518"},
    "한국전력": {"stock_code": "015760", "corp_code": "00159217"},
    "포스코퓨처엠": {"stock_code": "003670", "corp_code": "00117630"},
    "LG전자": {"stock_code": "066570", "corp_code": "00401731"},
}

# 섹터 분류
SECTORS: dict[str, list[str]] = {
    "반도체": ["삼성전자", "SK하이닉스"],
    "2차전지": ["LG에너지솔루션", "삼성SDI", "포스코퓨처엠", "LG화학"],
    "바이오": ["삼성바이오로직스", "셀트리온"],
    "자동차": ["현대자동차", "기아", "현대모비스"],
    "금융": ["KB금융", "신한지주", "하나금융지주"],
    "IT/플랫폼": ["NAVER", "카카오"],
    "철강/소재": ["POSCO홀딩스"],
    "유틸리티": ["한국전력"],
    "건설/지주": ["삼성물산"],
    "가전": ["LG전자"],
}

# 네이버 금융 URL 템플릿
NAVER_FINANCE_URLS = {
    "main": "https://finance.naver.com/item/main.naver?code={stock_code}",
    "sise_day": "https://finance.naver.com/item/sise_day.naver?code={stock_code}&page={page}",
    "foreign": "https://finance.naver.com/item/frgn.naver?code={stock_code}&page={page}",
    "news": "https://search.naver.com/search.naver?where=news&query={query}",
}

# DART OpenAPI URL
DART_API_BASE_URL = "https://opendart.fss.or.kr/api"
DART_ENDPOINTS = {
    "disclosure_list": f"{DART_API_BASE_URL}/list.json",
    "financial_statements": f"{DART_API_BASE_URL}/fnlttSinglAcntAll.json",
    "company_info": f"{DART_API_BASE_URL}/company.json",
}

# 시장 데이터 URL
MARKET_DATA_URLS = {
    "kospi": "https://finance.naver.com/sise/sise_index.naver?code=KOSPI",
    "exchange_rate": "https://finance.naver.com/marketindex/",
}

# 기본 수집 설정
DEFAULT_COLLECTION_DAYS = 60
DEFAULT_NEWS_COUNT = 20
DEFAULT_DISCLOSURE_DAYS = 30

# -------------------------------------------------------------------
# Crypto / Hyperliquid constants
# -------------------------------------------------------------------

# 주요 암호화폐 코인 매핑
CRYPTO_COINS: dict[str, str] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "HYPE": "Hyperliquid",
}

# 지원하는 캔들 간격
CRYPTO_INTERVALS: list[str] = ["1m", "5m", "15m", "1h", "4h", "1d"]

# 전체 데이터 소스 목록
DATA_SOURCES: list[str] = ["krx", "hyperliquid"]
