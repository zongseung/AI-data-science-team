"""KRX utility functions for stock code conversion."""

# 주요 종목의 6자리 → 12자리 표준코드 매핑
STOCK_CODE_MAPPING = {
    # 반도체
    "005930": "KR7005930003",  # 삼성전자
    "000660": "KR7000660001",  # SK하이닉스

    # 2차전지
    "373220": "KR7373220003",  # LG에너지솔루션
    "006400": "KR7006400006",  # 삼성SDI
    "003670": "KR7003670005",  # 포스코퓨처엠
    "051910": "KR7051910008",  # LG화학

    # 바이오
    "207940": "KR7207940008",  # 삼성바이오로직스
    "068270": "KR7068270008",  # 셀트리온

    # 자동차
    "005380": "KR7005380001",  # 현대자동차
    "000270": "KR7000270009",  # 기아
    "012330": "KR7012330007",  # 현대모비스

    # 금융
    "105560": "KR7105560007",  # KB금융
    "055550": "KR7055550008",  # 신한지주
    "086790": "KR7086790003",  # 하나금융지주

    # IT/플랫폼
    "035420": "KR7035420009",  # NAVER
    "035720": "KR7035720002",  # 카카오

    # 철강/소재
    "005490": "KR7005490008",  # POSCO홀딩스

    # 유틸리티
    "015760": "KR7015760002",  # 한국전력

    # 건설/지주
    "028260": "KR7028260005",  # 삼성물산

    # 가전
    "066570": "KR7066570003",  # LG전자

    # 기타 (테스트용)
    "033640": "KR7033640004",  # 네패스
}


def convert_to_standard_code(short_code: str) -> str | None:
    """
    6자리 종목코드를 12자리 표준코드로 변환

    Args:
        short_code: 6자리 종목코드 (예: "005930")

    Returns:
        12자리 표준코드 (예: "KR7005930003") 또는 None
    """
    return STOCK_CODE_MAPPING.get(short_code)


def get_stock_info_for_krx(stock_name: str, stock_codes: dict) -> dict | None:
    """
    종목명으로 KRX 수집에 필요한 정보 생성

    Args:
        stock_name: 종목명 (예: "삼성전자")
        stock_codes: constants.STOCK_CODES

    Returns:
        {
            "stock_name": "삼성전자",
            "short_code": "005930",
            "standard_code": "KR7005930003",
            "corp_code": "00126380",
            "tbox_param": "005930/삼성전자"
        }
    """
    if stock_name not in stock_codes:
        return None

    info = stock_codes[stock_name]
    short_code = info["stock_code"]
    standard_code = convert_to_standard_code(short_code)

    if not standard_code:
        return None

    return {
        "stock_name": stock_name,
        "short_code": short_code,
        "standard_code": standard_code,
        "corp_code": info["corp_code"],
        "tbox_param": f"{short_code}/{stock_name}",
    }
