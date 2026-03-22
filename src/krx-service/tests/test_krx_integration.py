"""
KRX 데이터 수집 통합 테스트

constants.py의 종목 리스트를 사용하여 KRX 공매도 데이터 수집 테스트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from krx.async_mdcstat300 import fetch_mdcstat300_async
from krx.utils import get_stock_info_for_krx

# Import stock codes from ai_data_science_team
sys.path.insert(0, str(Path(__file__).parent.parent))
from ai_data_science_team.config.constants import STOCK_CODES, SECTORS


async def test_single_stock(stock_name: str, days: int = 30):
    """단일 종목 KRX 데이터 수집 테스트"""
    print(f"\n{'='*60}")
    print(f"테스트: {stock_name}")
    print(f"{'='*60}")

    stock_info = get_stock_info_for_krx(stock_name, STOCK_CODES)
    if not stock_info:
        print(f"❌ {stock_name}: 표준코드 매핑 없음")
        return None

    print(f"📋 정보:")
    print(f"  - 6자리: {stock_info['short_code']}")
    print(f"  - 12자리: {stock_info['standard_code']}")
    print(f"  - DART: {stock_info['corp_code']}")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    try:
        df, raw = await fetch_mdcstat300_async(
            isu_cd=stock_info["standard_code"],
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            bld="dbms/MDC_OUT/STAT/srt/MDCSTAT30001_OUT",
            extra_payload={
                "locale": "ko_KR",
                "tboxisuCd_finder_srtisu0": stock_info["tbox_param"],
            },
        )

        print(f"✅ 수집 성공: {len(df)}행 {len(df.columns)}열")
        if not df.empty:
            print(f"\n최근 데이터:")
            print(df.head(3).to_string(index=False))

        return {"stock_name": stock_name, "rows": len(df), "data": df}

    except Exception as e:
        print(f"❌ 수집 실패: {e}")
        return None


async def test_sector(sector_name: str, days: int = 30):
    """섹터별 동시 수집 테스트"""
    print(f"\n{'='*60}")
    print(f"섹터 테스트: {sector_name}")
    print(f"{'='*60}")

    if sector_name not in SECTORS:
        print(f"❌ 섹터 '{sector_name}' 없음")
        return []

    stocks = SECTORS[sector_name]
    print(f"종목: {', '.join(stocks)}")

    # 동시 요청
    tasks = [test_single_stock(stock, days) for stock in stocks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 결과 요약
    success = sum(1 for r in results if r and isinstance(r, dict))
    print(f"\n{'='*60}")
    print(f"섹터 '{sector_name}' 수집 완료: {success}/{len(stocks)} 성공")
    print(f"{'='*60}")

    return [r for r in results if r and isinstance(r, dict)]


async def test_all_stocks(days: int = 7):
    """전체 종목 수집 테스트 (짧은 기간)"""
    print(f"\n{'='*60}")
    print(f"전체 종목 테스트 ({len(STOCK_CODES)}개)")
    print(f"기간: 최근 {days}일")
    print(f"{'='*60}")

    tasks = [
        test_single_stock(stock_name, days)
        for stock_name in STOCK_CODES.keys()
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 결과 통계
    success = [r for r in results if r and isinstance(r, dict)]
    failed = [r for r in results if not r or isinstance(r, Exception)]

    print(f"\n{'='*60}")
    print(f"전체 수집 완료")
    print(f"{'='*60}")
    print(f"✅ 성공: {len(success)}개")
    print(f"❌ 실패: {len(failed)}개")

    if success:
        total_rows = sum(r["rows"] for r in success)
        print(f"📊 총 데이터: {total_rows}행")
        print(f"\n성공 종목:")
        for r in success:
            print(f"  - {r['stock_name']}: {r['rows']}행")

    if failed:
        print(f"\n실패 종목: {len(failed)}개")

    return success


async def main():
    """메인 테스트 실행"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║          KRX 데이터 수집 통합 테스트 Suite              ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # 테스트 메뉴
    print("\n테스트 선택:")
    print("1. 단일 종목 테스트 (삼성전자)")
    print("2. 섹터 테스트 (반도체)")
    print("3. 전체 종목 테스트 (7일)")
    print("4. 종목코드 매핑 확인")
    print()

    choice = input("선택 (1-4, 기본값=1): ").strip() or "1"

    if choice == "1":
        await test_single_stock("삼성전자", days=30)

    elif choice == "2":
        await test_sector("반도체", days=30)

    elif choice == "3":
        await test_all_stocks(days=7)

    elif choice == "4":
        print("\n종목코드 매핑:")
        print(f"{'종목명':<15} {'6자리':<10} {'12자리':<15} {'매핑'}")
        print("-" * 60)
        for stock_name in STOCK_CODES.keys():
            info = get_stock_info_for_krx(stock_name, STOCK_CODES)
            if info:
                print(
                    f"{stock_name:<15} {info['short_code']:<10} "
                    f"{info['standard_code']:<15} ✅"
                )
            else:
                short = STOCK_CODES[stock_name]["stock_code"]
                print(f"{stock_name:<15} {short:<10} {'없음':<15} ❌")

    else:
        print("잘못된 선택")

    print("\n테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())
