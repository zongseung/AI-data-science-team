# 05. 텔레그램 연동 상세 설계

## 1. 봇 구성

### 1.1 봇 정보
```
봇 이름: AI 금융 데이터사이언스팀
봇 ID: @ai_finance_ds_bot (예시)
설명: AI 데이터사이언스 에이전트팀이 한국 주식시장을 분석하고 ML 기반 예측을 제공합니다
```

### 1.2 명령어 체계

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/start` | 봇 시작, 환영 메시지 | `/start` |
| `/help` | 도움말 | `/help` |
| `/수집 [종목명/코드]` | 종목 데이터 수집 요청 | `/수집 삼성전자` |
| `/EDA [종목명/코드]` | 탐색적 데이터 분석 | `/EDA 005930` |
| `/분석 [종목명/코드]` | 종합 분석 (EDA+통계+감성) | `/분석 005930` |
| `/예측 [종목명/코드]` | ML 모델 예측 | `/예측 SK하이닉스` |
| `/백테스트 [종목명/코드]` | 예측 모델 백테스팅 | `/백테스트 삼성전자` |
| `/리포트 [종목명/코드]` | 전체 리포트 (수집+분석+예측) | `/리포트 현대차` |
| `/피처 [종목명/코드]` | 피처 중요도 확인 | `/피처 삼성전자` |
| `/모델 [종목명/코드]` | 학습된 모델 성능 조회 | `/모델 005930` |
| `/섹터 [섹터명]` | 섹터 분석 (클러스터링 포함) | `/섹터 반도체` |
| `/시장` | 시장 개요 (KOSPI/KOSDAQ) | `/시장` |
| `/관심 [종목명]` | 관심 종목 등록 | `/관심 삼성전자` |
| `/관심목록` | 관심 종목 리스트 | `/관심목록` |
| `/알림설정` | 알림 설정 | `/알림설정` |
| `/상태` | 현재 에이전트 작업 상태 | `/상태` |
| `/실험 [종목명/코드]` | MLflow 실험 결과 조회 | `/실험 삼성전자` |

### 1.3 자연어 대화 지원

```
사용자: "삼성전자 요즘 어때?"
봇: 삼성전자(005930) EDA + ML 분석을 시작하겠습니다. 잠시만 기다려주세요...

사용자: "반도체 섹터 전체 비교해줘"
봇: 반도체 섹터 클러스터링 분석을 시작합니다. (삼성전자, SK하이닉스, DB하이텍...)

사용자: "지금 사도 될까?"
봇: [이전 대화의 종목 컨텍스트 활용]
     삼성전자 ML 예측 모델과 백테스트 결과를 바탕으로 답변드리겠습니다...

사용자: "XGBoost 모델 성능이 어때?"
봇: 삼성전자 XGBoost 모델 최신 실험 결과를 조회합니다...
     MAPE: 2.3%, 방향 정확도: 68.2%, Sharpe: 1.45

사용자: "피처 중요도 알려줘"
봇: 삼성전자 예측 모델 상위 10개 피처 중요도:
     1. RSI_14: 0.152 | 2. MACD_signal: 0.128 | ...
```

## 2. 봇 구현

### 2.1 기본 구조

```python
# telegram/bot.py

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)


class FinanceBot:
    """AI 금융분석 텔레그램 봇"""

    def __init__(self, token: str, orchestrator: Orchestrator):
        self.token = token
        self.orchestrator = orchestrator
        self.app = Application.builder().token(token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """핸들러 등록"""
        # 기본 명령어
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(CommandHandler("help", self._handle_help))

        # 데이터 수집
        self.app.add_handler(CommandHandler("수집", self._handle_collect))

        # 데이터 사이언스 분석
        self.app.add_handler(CommandHandler("EDA", self._handle_eda))
        self.app.add_handler(CommandHandler("분석", self._handle_analyze))
        self.app.add_handler(CommandHandler("피처", self._handle_feature_importance))

        # ML 예측 & 백테스팅
        self.app.add_handler(CommandHandler("예측", self._handle_predict))
        self.app.add_handler(CommandHandler("백테스트", self._handle_backtest))
        self.app.add_handler(CommandHandler("모델", self._handle_model_status))
        self.app.add_handler(CommandHandler("실험", self._handle_experiment))

        # 리포트 & 시장
        self.app.add_handler(CommandHandler("리포트", self._handle_full_report))
        self.app.add_handler(CommandHandler("섹터", self._handle_sector))
        self.app.add_handler(CommandHandler("시장", self._handle_market))

        # 관심 종목 관리
        self.app.add_handler(CommandHandler("관심", self._handle_watchlist_add))
        self.app.add_handler(CommandHandler("관심목록", self._handle_watchlist_list))

        # 자연어 처리 (LLM 기반)
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_natural_language)
        )

        # 인라인 버튼 콜백
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))

    async def run(self):
        """봇 실행"""
        # 명령어 목록 설정
        commands = [
            BotCommand("start", "봇 시작"),
            BotCommand("help", "도움말"),
            BotCommand("수집", "종목 데이터 수집"),
            BotCommand("EDA", "탐색적 데이터 분석"),
            BotCommand("분석", "종합 분석 (EDA+통계+감성)"),
            BotCommand("예측", "ML 모델 예측"),
            BotCommand("백테스트", "예측 모델 백테스팅"),
            BotCommand("피처", "피처 중요도 조회"),
            BotCommand("모델", "모델 성능 조회"),
            BotCommand("실험", "MLflow 실험 결과"),
            BotCommand("리포트", "종합 리포트"),
            BotCommand("섹터", "섹터 클러스터링 분석"),
            BotCommand("시장", "시장 개요"),
            BotCommand("관심", "관심 종목 추가"),
            BotCommand("관심목록", "관심 종목 리스트"),
            BotCommand("상태", "에이전트 상태"),
        ]
        await self.app.bot.set_my_commands(commands)
        await self.app.run_polling()
```

### 2.2 명령어 핸들러

```python
# telegram/handlers/collect.py

async def _handle_collect(self, update: Update, context):
    """수집 명령어 처리"""
    args = context.args
    if not args:
        await update.message.reply_text(
            "사용법: /수집 [종목명 또는 종목코드]\n"
            "예시: /수집 삼성전자\n"
            "예시: /수집 005930"
        )
        return

    query = " ".join(args)
    stock = await self._resolve_stock(query)

    if not stock:
        await update.message.reply_text(
            f"'{query}' 종목을 찾을 수 없습니다.\n"
            "종목명 또는 6자리 종목코드를 입력해주세요."
        )
        return

    # 수집 시작 알림
    msg = await update.message.reply_text(
        f"🔍 {stock['name']}({stock['code']}) 데이터 수집을 시작합니다...\n\n"
        f"📊 수집 항목:\n"
        f"  • 주가 데이터\n"
        f"  • 공시 정보 (DART)\n"
        f"  • 관련 뉴스\n\n"
        f"⏳ 잠시만 기다려주세요..."
    )

    # 수집 실행 (비동기)
    chat_id = update.effective_chat.id

    async def on_progress(event):
        """수집 진행 상황 콜백"""
        progress = event["progress"]
        current = event.get("current_task", "")
        bar = "█" * int(progress * 10) + "░" * (10 - int(progress * 10))
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=(
                f"🔍 {stock['name']}({stock['code']}) 데이터 수집 중...\n\n"
                f"진행: [{bar}] {int(progress * 100)}%\n"
                f"현재: {current}"
            )
        )

    # 이벤트 구독
    event_bus.subscribe(EventType.COLLECTION_PROGRESS, on_progress)

    try:
        result = await self.orchestrator.collect(stock["code"])

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=(
                f"✅ {stock['name']}({stock['code']}) 데이터 수집 완료!\n\n"
                f"📊 수집 결과:\n"
                f"  • 주가 데이터: {result['price_count']}건\n"
                f"  • 공시: {result['disclosure_count']}건\n"
                f"  • 뉴스: {result['news_count']}건\n\n"
                f"💡 분석을 원하시면: /분석 {stock['name']}"
            )
        )
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=f"❌ 수집 중 오류가 발생했습니다: {str(e)}"
        )
    finally:
        event_bus.unsubscribe(EventType.COLLECTION_PROGRESS, on_progress)
```

### 2.3 자연어 처리 핸들러

```python
# telegram/handlers/natural_language.py

async def _handle_natural_language(self, update: Update, context):
    """자연어 입력 처리 (LLM 기반 의도 파악)"""
    text = update.message.text
    chat_id = update.effective_chat.id

    # 대화 컨텍스트 조회
    session = await self._get_session(chat_id)

    prompt = f"""
    사용자의 메시지를 분석하여 의도를 파악하고 적절한 명령으로 변환해주세요.

    이전 대화 컨텍스트:
    - 마지막 종목: {session.get("last_stock", "없음")}
    - 마지막 명령: {session.get("last_command", "없음")}

    사용자 메시지: "{text}"

    응답 형식 (JSON):
    {{
        "intent": "collect|analyze|forecast|report|sector|market|question|greeting|unknown",
        "stock_name": "종목명 또는 null",
        "stock_code": "종목코드 또는 null",
        "sector": "섹터명 또는 null",
        "question": "후속 질문 내용 또는 null",
        "response": "자연스러운 응답 메시지"
    }}
    """

    intent = await llm_client.chat(prompt, response_format="json")

    # 의도에 따른 처리
    match intent["intent"]:
        case "collect":
            await self._handle_collect_from_intent(update, context, intent)
        case "eda":
            await self._handle_eda_from_intent(update, context, intent)
        case "analyze":
            await self._handle_analyze_from_intent(update, context, intent)
        case "predict":
            await self._handle_predict_from_intent(update, context, intent)
        case "backtest":
            await self._handle_backtest_from_intent(update, context, intent)
        case "feature":
            await self._handle_feature_from_intent(update, context, intent)
        case "model_status":
            await self._handle_model_status_from_intent(update, context, intent)
        case "report":
            await self._handle_report_from_intent(update, context, intent)
        case "question":
            # LLM 기반 답변 (이전 ML 분석 결과 참조)
            await self._answer_question(update, context, intent, session)
        case _:
            await update.message.reply_text(intent["response"])
```

## 3. 인라인 키보드 (Interactive Buttons)

### 3.1 분석 결과 후 액션 버튼

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def _build_post_analysis_keyboard(stock_code: str) -> InlineKeyboardMarkup:
    """분석 완료 후 추가 액션 버튼"""
    keyboard = [
        [
            InlineKeyboardButton("🤖 ML 예측", callback_data=f"predict:{stock_code}"),
            InlineKeyboardButton("📊 EDA 보기", callback_data=f"eda:{stock_code}"),
        ],
        [
            InlineKeyboardButton("🧪 백테스트", callback_data=f"backtest:{stock_code}"),
            InlineKeyboardButton("🎯 피처 중요도", callback_data=f"feature:{stock_code}"),
        ],
        [
            InlineKeyboardButton("📈 차트 보기", callback_data=f"chart:{stock_code}"),
            InlineKeyboardButton("⭐ 관심 추가", callback_data=f"watchlist:{stock_code}"),
        ],
        [
            InlineKeyboardButton("📋 전체 리포트", callback_data=f"full_report:{stock_code}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
```

### 3.2 섹터 선택 키보드

```python
def _build_sector_keyboard() -> InlineKeyboardMarkup:
    """섹터 선택 인라인 키보드"""
    keyboard = [
        [
            InlineKeyboardButton("🔧 반도체", callback_data="sector:반도체"),
            InlineKeyboardButton("🚗 자동차", callback_data="sector:자동차"),
        ],
        [
            InlineKeyboardButton("💊 바이오", callback_data="sector:바이오"),
            InlineKeyboardButton("💻 IT", callback_data="sector:IT"),
        ],
        [
            InlineKeyboardButton("⚡ 에너지", callback_data="sector:에너지"),
            InlineKeyboardButton("🏦 금융", callback_data="sector:금융"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
```

## 4. 알림 시스템

### 4.1 알림 유형

```python
class NotificationType(Enum):
    PRICE_ALERT = "price_alert"              # 목표가 도달
    CHANGE_ALERT = "change_alert"            # 급등락 알림 (±3%)
    DISCLOSURE_ALERT = "disclosure_alert"     # 주요 공시 발생
    NEWS_ALERT = "news_alert"                # 중요 뉴스
    DAILY_REPORT = "daily_report"            # 일일 리포트
    WATCHLIST_SUMMARY = "watchlist_summary"   # 관심 종목 요약
    PREDICTION_ALERT = "prediction_alert"     # ML 예측 이탈 알림 (예측값 vs 실제값 괴리)
    MODEL_RETRAIN = "model_retrain"          # 모델 재학습 완료 알림
    RISK_ALERT = "risk_alert"                # VaR 임계치 초과 알림
    BACKTEST_COMPLETE = "backtest_complete"   # 백테스트 완료 알림
    ANOMALY_DETECTED = "anomaly_detected"    # 이상치 감지 알림
```

### 4.2 알림 설정

```python
class AlertConfig:
    """사용자별 알림 설정"""

    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.settings = {
            "price_change_threshold": 3.0,  # ±3% 변동 시 알림
            "disclosure_types": ["주요사항보고서", "유상증자", "M&A"],
            "daily_report_time": "18:00",  # 일일 리포트 시간
            "watchlist_alert": True,
            "sector_alert": False,
        }
```

### 4.3 스케줄 알림

```python
# 일일 리포트 스케줄
async def send_daily_report(chat_id: int):
    """매일 장마감 후 관심 종목 일일 리포트 전송"""
    watchlist = await get_user_watchlist(chat_id)

    if not watchlist:
        return

    summary_parts = []
    for stock in watchlist:
        data = await get_latest_data(stock["code"])
        change_emoji = "🔴" if data["change_rate"] < 0 else "🟢"
        summary_parts.append(
            f"{change_emoji} {stock['name']}: {data['close']:,}원 "
            f"({data['change_rate']:+.2f}%)"
        )

    message = (
        f"📊 일일 시장 리포트 ({datetime.now().strftime('%Y-%m-%d')})\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📈 KOSPI: {kospi_data['close']:,.2f} ({kospi_data['change']:+.2f}%)\n"
        f"📉 KOSDAQ: {kosdaq_data['close']:,.2f} ({kosdaq_data['change']:+.2f}%)\n\n"
        f"⭐ 관심 종목\n"
        + "\n".join(summary_parts)
    )

    await bot.send_message(chat_id=chat_id, text=message)
```

## 5. 실시간 진행 상황 메시지 흐름

```
시간   텔레그램 메시지
──────────────────────────────────────────
T+0s   📊 삼성전자(005930) 데이터사이언스 분석을 시작합니다.
       ━━━━━━━━━━━━━━━
       🏢 수집팀이 데이터를 수집합니다...

T+5s   🔍 데이터 수집 중...
       [███░░░░░░░] 30%
       현재: 주가 데이터 수집 중

T+10s  🔍 데이터 수집 중...
       [██████░░░░] 60%
       현재: DART 공시 확인 중

T+15s  🔍 데이터 수집 중...
       [█████████░] 90%
       현재: 뉴스 검색 중

T+18s  ✅ 데이터 수집 완료!
       • 주가: 120건 • 공시: 5건 • 뉴스: 8건
       📤 분석팀에 데이터를 전달합니다...

T+20s  📊 EDA 수행 중...
       [██░░░░░░░░] 20%
       현재: 기술통계량 계산 중

T+25s  📊 EDA 수행 중...
       [████░░░░░░] 40%
       현재: 정규성 검정 (Shapiro-Wilk) 진행 중

T+30s  📊 EDA + 감성분석 병렬 진행 중...
       [██████░░░░] 60%
       현재: STL 시계열 분해 | TF-IDF 감성분석

T+35s  🔧 피처 엔지니어링 중...
       [███████░░░] 70%
       현재: 50+ 피처 생성 & 상호정보량 기반 선택

T+40s  📈 통계 분석 중...
       [████████░░] 80%
       현재: Granger 인과성 검정 | GARCH 변동성 모델

T+45s  ✅ 분석 완료! (6개 에이전트)
       📤 ML 엔지니어링팀에 피처/분석 결과 전달...

T+50s  🤖 ML 모델 학습 중...
       [██░░░░░░░░] 20%
       현재: Prophet 시계열 예측 학습 중

T+60s  🤖 ML 모델 학습 중...
       [████░░░░░░] 40%
       현재: LSTM 신경망 학습 중 (Epoch 15/50)

T+70s  🤖 ML 모델 학습 중...
       [██████░░░░] 60%
       현재: XGBoost Optuna 최적화 (Trial 12/30)

T+80s  🤖 앙상블 모델 구성 중...
       [████████░░] 80%
       현재: 가중 평균 최적화

T+85s  🧪 백테스팅 수행 중...
       [█████████░] 90%
       현재: Walk-Forward Validation (5 splits)

T+90s  ⚠️ 리스크 평가 중...
       [██████████] 95%
       현재: VaR / CVaR / Monte Carlo 시뮬레이션

T+95s  📝 리포트 작성 중... (LLM이 ML 결과를 해석)

T+100s ✅ 분석 완료! 리포트를 전송합니다.

T+101s [최종 리포트 메시지 전송]
       [EDA 차트 이미지 전송]
       [ML 예측 차트 이미지 전송]
       [백테스트 결과 이미지 전송]
       [추가 액션 버튼]
```

### 5.1 ML 예측 결과 메시지 포맷

```python
ML_PREDICTION_FORMAT = """
🤖 {stock_name}({stock_code}) ML 예측 결과
━━━━━━━━━━━━━━━━━━━━━━━

📊 앙상블 모델 예측 (Prophet + LSTM + XGBoost)
  현재가: {current_price:,}원
  5일 후 예측: {pred_5d:,}원 ({pred_5d_change:+.2f}%)
  10일 후 예측: {pred_10d:,}원 ({pred_10d_change:+.2f}%)
  20일 후 예측: {pred_20d:,}원 ({pred_20d_change:+.2f}%)

📈 모델 성능
  MAPE: {mape:.2f}% | RMSE: {rmse:,.0f}원
  방향 정확도: {direction_acc:.1f}%
  R² Score: {r2:.4f}

🧪 백테스트 결과 (최근 6개월)
  전략 수익률: {strategy_return:+.2f}%
  Buy & Hold: {benchmark_return:+.2f}%
  Sharpe Ratio: {sharpe:.2f}
  최대 낙폭(MDD): {mdd:.2f}%
  승률: {win_rate:.1f}%

⚠️ 리스크
  VaR (95%): {var_95:.2f}%
  CVaR (95%): {cvar_95:.2f}%
  변동성 전망: {volatility_forecast}

💡 {llm_interpretation}

⚖️ 본 분석은 ML 모델에 의한 통계적 예측이며, 투자 권유가 아닙니다.
"""

FEATURE_IMPORTANCE_FORMAT = """
🎯 {stock_name}({stock_code}) 피처 중요도 (상위 10개)
━━━━━━━━━━━━━━━━━━━━━━━

{feature_bars}

📌 총 사용 피처: {total_features}개
🔬 피처 선택 방법: 상호정보량 + 상관계수 필터링
"""

EDA_SUMMARY_FORMAT = """
📊 {stock_name}({stock_code}) EDA 요약
━━━━━━━━━━━━━━━━━━━━━━━

📈 기초 통계
  평균: {mean:,.0f}원 | 중앙값: {median:,.0f}원
  표준편차: {std:,.0f}원 | 변동계수: {cv:.2f}%
  왜도: {skewness:.3f} | 첨도: {kurtosis:.3f}

📉 정규성 검정
  Shapiro-Wilk: p={shapiro_p:.4f} ({normality})
  Jarque-Bera: p={jb_p:.4f}

📊 정상성 검정
  ADF 검정: p={adf_p:.4f} ({stationarity})
  KPSS 검정: p={kpss_p:.4f}

🔍 이상치: {outlier_count}개 감지 (Isolation Forest)
📊 자기상관: {acf_significant_lags}개 유의미한 래그

💡 {eda_insights}
"""
```

## 6. 보안 고려사항

```python
# telegram/middleware.py

class TelegramSecurityMiddleware:
    """텔레그램 보안 미들웨어"""

    def __init__(self):
        self.rate_limiter = RateLimiter(
            max_requests=10,    # 분당 최대 10회
            window_seconds=60,
        )
        self.allowed_users: set[int] = set()  # 허용된 사용자 ID

    async def check_authorization(self, update: Update) -> bool:
        """사용자 인가 확인"""
        user_id = update.effective_user.id

        # 허용 목록 확인 (선택적)
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("⛔ 접근 권한이 없습니다.")
            return False

        # Rate limiting
        if not self.rate_limiter.allow(user_id):
            await update.message.reply_text(
                "⚠️ 요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
            )
            return False

        return True
```

## 7. 에러 처리

```python
# 텔레그램 메시지 에러 응답 포맷
ERROR_MESSAGES = {
    "stock_not_found": "❌ '{query}' 종목을 찾을 수 없습니다.\n종목명 또는 6자리 종목코드를 확인해주세요.",
    "collection_failed": "❌ 데이터 수집 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
    "analysis_failed": "❌ 분석 중 오류가 발생했습니다.\n데이터가 충분하지 않을 수 있습니다.",
    "eda_failed": "❌ EDA 수행 중 오류가 발생했습니다.\n최소 60일 이상의 데이터가 필요합니다.",
    "model_training_failed": "❌ ML 모델 학습에 실패했습니다.\n피처 데이터를 확인 중입니다...",
    "insufficient_data": "❌ ML 모델 학습에 충분한 데이터가 없습니다.\n최소 120일 이상의 주가 데이터가 필요합니다.",
    "backtest_failed": "❌ 백테스팅 중 오류가 발생했습니다.\n학습된 모델이 없을 수 있습니다. 먼저 /예측을 실행해주세요.",
    "model_not_found": "❌ '{stock_name}'에 대한 학습된 모델이 없습니다.\n/예측 명령으로 먼저 모델을 학습해주세요.",
    "rate_limited": "⚠️ 요청이 너무 많습니다.\n{seconds}초 후 다시 시도해주세요.",
    "maintenance": "🔧 시스템 점검 중입니다.\n{estimated_time}에 복구 예정입니다.",
}
```
