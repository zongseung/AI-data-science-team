# /src 디렉토리 구조

이 디렉토리는 **KRX 데이터 수집 전용 모듈**입니다.
`ai_data_science_team/`과는 독립적으로 동작하며, 단독 실행 가능합니다.

## 📁 디렉토리 구조

```
src/
├── README.md              # 사용 가이드
├── STRUCTURE.md           # 이 파일
├── test_async_krx.py      # 비동기 수집 테스트
├── run_mdcstat300.py      # CLI 래퍼 (간편 실행)
│
└── krx/                   # KRX 수집 모듈
    ├── __init__.py        # 패키지 exports
    ├── client.py          # 동기 HTTP 클라이언트
    ├── async_client.py    # 비동기 HTTP 클라이언트 (프록시 지원)
    ├── mdcstat300.py      # 동기 MDCSTAT300 데이터 페칭
    ├── async_mdcstat300.py # 비동기 MDCSTAT300 데이터 페칭
    └── run_mdcstat300.py  # CLI 엔트리포인트
```

## 🎯 용도

### src/ (KRX 전용)
- **목적**: KRX 공매도 데이터 수집
- **실행**: CLI 또는 Python import
- **독립성**: `ai_data_science_team/`과 분리
- **배포**: 단독 패키지로 배포 가능

### ai_data_science_team/ (Prefect 파이프라인)
- **목적**: 전체 주식 분석 파이프라인
- **데이터 소스**: 네이버 금융, DART, 뉴스
- **오케스트레이션**: Prefect flows
- **배포**: FastAPI + Prefect 서버

## 🔗 통합 방법 (향후)

현재는 분리되어 있지만, 필요시 통합 가능:

### 옵션 1: Import로 연결
```python
# ai_data_science_team/collectors/krx_wrapper.py
from src.krx import fetch_mdcstat300_async
from ai_data_science_team.collectors.base_collector import BaseCollector

class KRXCollector(BaseCollector):
    async def collect(self, **kwargs):
        return await fetch_mdcstat300_async(**kwargs)
```

### 옵션 2: 독립 실행 후 결과 저장
```bash
# src에서 데이터 수집
PYTHONPATH=src python -m krx.run_mdcstat300 --out-csv data/krx.csv

# ai_data_science_team에서 읽기
pd.read_csv("data/krx.csv")
```

## ⚡ 빠른 시작

```bash
# 1. 테스트 실행
uv run python src/test_async_krx.py

# 2. 실제 데이터 수집
PYTHONPATH=src uv run python -m krx.run_mdcstat300 \
  --isu-cd "KR7033640004" \
  --start 2026-02-20 \
  --end 2026-03-20 \
  --bld "dbms/MDC_OUT/STAT/srt/MDCSTAT30001_OUT" \
  --extra-json '{"locale":"ko_KR","tboxisuCd_finder_srtisu0":"033640/네패스"}' \
  --out-csv krx_data.csv
```

## 📦 의존성

- pandas
- httpx
- (선택) proxy 라이브러리 (프록시 사용 시)

모든 의존성은 프로젝트 루트의 `pyproject.toml`에 정의되어 있습니다.
