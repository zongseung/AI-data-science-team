# 08. LLM 연동 상세 설계

## 1. LLM 활용 영역

```
┌────────────────────────────────────────────────────────────────┐
│                    LLM 활용 맵 (ML과 역할 분리)                  │
│                                                                │
│  ┌─── LLM 담당 (자연어/해석) ───────────────────────────────┐  │
│  │  📰 감성 분석 (보조)   │ TF-IDF 결과에 LLM 감성 점수 보정  │  │
│  │  📝 EDA 인사이트 생성  │ 통계 결과를 자연어로 해석          │  │
│  │  📊 ML 리포트 작성     │ ML 예측/백테스트 결과 → 자연어 리포트│  │
│  │  💬 자연어 처리        │ 텔레그램 대화 의도 파악             │  │
│  │  🤖 에이전트 조율      │ 에이전트 간 커뮤니케이션            │  │
│  │  ⚠️ 리스크 해석        │ VaR/CVaR 수치를 투자 관점으로 해석  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─── ML 담당 (수치 예측) ────────────────────────────────┐  │
│  │  📈 주가 예측          │ Prophet/LSTM/XGBoost 앙상블     │  │
│  │  🔧 피처 엔지니어링     │ 자동 피처 생성 & 선택           │  │
│  │  🧪 백테스팅           │ Walk-Forward 전략 시뮬레이션     │  │
│  │  📊 EDA 통계           │ ADF, KPSS, Granger, GARCH      │  │
│  │  🎯 하이퍼파라미터      │ Optuna 자동 최적화             │  │
│  │  ⚠️ 리스크 계량        │ VaR, CVaR, Monte Carlo          │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

## 2. LLM 프로바이더 관리

### 2.1 다중 프로바이더 클라이언트

```python
# llm/client.py

from abc import ABC, abstractmethod
from enum import Enum


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"  # Ollama 등 로컬 모델


class LLMClient:
    """다중 프로바이더 LLM 클라이언트"""

    def __init__(self, primary: LLMProvider = LLMProvider.ANTHROPIC):
        self.primary = primary
        self.providers: dict[LLMProvider, BaseLLMProvider] = {}
        self._init_providers()

    def _init_providers(self):
        """사용 가능한 프로바이더 초기화"""
        if settings.ANTHROPIC_API_KEY:
            self.providers[LLMProvider.ANTHROPIC] = AnthropicProvider(
                api_key=settings.ANTHROPIC_API_KEY
            )
        if settings.OPENAI_API_KEY:
            self.providers[LLMProvider.OPENAI] = OpenAIProvider(
                api_key=settings.OPENAI_API_KEY
            )

    async def chat(
        self,
        prompt: str,
        system: str = "",
        response_format: str = "text",
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str | dict:
        """LLM 호출 (자동 폴백 포함)"""

        # 1차: 기본 프로바이더
        provider = self.providers.get(self.primary)
        if provider:
            try:
                return await provider.chat(
                    prompt=prompt,
                    system=system,
                    response_format=response_format,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                logger.warning(f"Primary LLM failed: {e}, trying fallback...")

        # 2차: 폴백 프로바이더
        for fallback_provider_type, fallback_provider in self.providers.items():
            if fallback_provider_type != self.primary:
                try:
                    return await fallback_provider.chat(
                        prompt=prompt,
                        system=system,
                        response_format=response_format,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                except Exception as e:
                    logger.warning(f"Fallback {fallback_provider_type} failed: {e}")

        raise RuntimeError("All LLM providers failed")
```

### 2.2 Anthropic (Claude) 프로바이더

```python
# llm/providers/anthropic_provider.py

import anthropic


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude 프로바이더"""

    MODEL_MAP = {
        "default": "claude-sonnet-4-6",
        "fast": "claude-haiku-4-5-20251001",
        "advanced": "claude-opus-4-6",
    }

    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def chat(
        self,
        prompt: str,
        system: str = "",
        response_format: str = "text",
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str | dict:
        model_id = self.MODEL_MAP.get(model or "default", model or self.MODEL_MAP["default"])

        messages = [{"role": "user", "content": prompt}]

        response = await self.client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "You are a Korean financial analyst AI assistant.",
            messages=messages,
        )

        text = response.content[0].text

        if response_format == "json":
            import json
            # JSON 블록 추출
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            return json.loads(text.strip())

        return text
```

### 2.3 OpenAI 프로바이더

```python
# llm/providers/openai_provider.py

from openai import AsyncOpenAI


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT 프로바이더"""

    MODEL_MAP = {
        "default": "gpt-4o",
        "fast": "gpt-4o-mini",
        "advanced": "gpt-4o",
    }

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def chat(
        self,
        prompt: str,
        system: str = "",
        response_format: str = "text",
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str | dict:
        model_id = self.MODEL_MAP.get(model or "default", model or self.MODEL_MAP["default"])

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content

        if response_format == "json":
            import json
            return json.loads(text)

        return text
```

## 3. 프롬프트 관리

### 3.1 프롬프트 템플릿

```python
# llm/prompts/sentiment.py

SENTIMENT_SYSTEM_PROMPT = """
당신은 한국 주식시장 전문 감성 분석 AI입니다.
뉴스와 공시를 분석하여 주가에 미칠 영향을 정량적으로 평가합니다.

분석 기준:
- 감성 점수: -1.0 (매우 부정) ~ +1.0 (매우 긍정)
- 영향 기간: short (1주 이내), medium (1개월), long (3개월+)
- 영향도: low, medium, high

항상 한국어로 응답하며, 정확한 JSON 형식으로 출력합니다.
"""

NEWS_SENTIMENT_PROMPT = """
다음 {stock_name}({stock_code}) 관련 뉴스 기사들의 감성을 분석해주세요.

뉴스 목록:
{news_list}

응답 형식 (JSON):
{{
    "articles": [
        {{
            "title": "기사 제목",
            "sentiment_score": 0.0,
            "impact_level": "medium",
            "key_factors": ["요인1", "요인2"]
        }}
    ],
    "average_sentiment": 0.0,
    "market_mood": "긍정적/중립/부정적",
    "summary": "전체 요약 (2-3문장)",
    "key_positive_factors": ["..."],
    "key_negative_factors": ["..."]
}}
"""

DISCLOSURE_IMPACT_PROMPT = """
다음 {stock_name}({stock_code}) 관련 공시의 주가 영향도를 분석해주세요.

공시 목록:
{disclosure_list}

응답 형식 (JSON):
{{
    "disclosures": [
        {{
            "title": "공시 제목",
            "type": "공시 유형",
            "impact_level": "high/medium/low",
            "direction": "positive/negative/neutral",
            "expected_duration": "short/medium/long",
            "summary": "핵심 내용 요약",
            "estimated_price_impact": "+2~3%"
        }}
    ],
    "overall_impact": "종합 영향 요약",
    "urgent_items": ["즉시 주의 필요한 공시 목록"],
    "recommendation": "투자자 행동 권고"
}}
"""
```

### 3.2 EDA 인사이트 프롬프트

```python
# llm/prompts/eda_insights.py

EDA_INSIGHT_SYSTEM_PROMPT = """
당신은 한국 주식시장 데이터 사이언스 전문가입니다.
통계 검정 결과와 EDA 수치를 투자자가 이해할 수 있는 자연어로 해석합니다.

원칙:
1. 통계 용어를 쉽게 풀어서 설명
2. 수치의 투자적 의미를 해석
3. 이상치나 특이 패턴의 시장 맥락을 제공
4. 데이터 품질 이슈가 있으면 명시
"""

EDA_INSIGHT_PROMPT = """
다음 {stock_name}({stock_code})의 EDA 결과를 해석해주세요.

**기술통계량:**
{descriptive_stats}

**정규성 검정:**
- Shapiro-Wilk p-value: {shapiro_p}
- Jarque-Bera p-value: {jb_p}
- 왜도: {skewness}, 첨도: {kurtosis}

**정상성 검정:**
- ADF p-value: {adf_p}
- KPSS p-value: {kpss_p}

**이상치 탐지:**
- Isolation Forest 감지: {outlier_count}개
- IQR 기반 감지: {iqr_outliers}개

**자기상관 분석:**
- 유의미한 ACF 래그: {acf_lags}
- 유의미한 PACF 래그: {pacf_lags}

**STL 분해:**
- 추세 방향: {trend_direction}
- 계절성 강도: {seasonal_strength}

3~5개의 핵심 인사이트를 한국어로 작성해주세요.
각 인사이트에는 투자적 시사점을 포함합니다.
"""
```

### 3.3 ML 결과 리포트 프롬프트

```python
# llm/prompts/ml_report.py

ML_REPORT_SYSTEM_PROMPT = """
당신은 한국 주식시장 전문 데이터사이언스 애널리스트 AI입니다.
ML 모델의 예측 결과, 백테스트 성과, 리스크 지표를 종합하여
투자자가 이해할 수 있는 자연어 리포트를 작성합니다.

원칙:
1. ML 모델의 예측은 통계적 결과이지 확정적 전망이 아님을 명시
2. 모델 성능 지표의 의미를 투자 관점에서 해석
3. 백테스트 결과의 한계 (과거 성과 ≠ 미래 성과) 명시
4. VaR/CVaR 등 리스크 지표를 실질적 투자 리스크로 해석
5. "투자 권유가 아닌 데이터 분석 정보 제공" 면책 포함
"""

ML_REPORT_PROMPT = """
## 종합 데이터사이언스 리포트 작성

종목: {stock_name} ({stock_code})
분석 일시: {analysis_date}

### 입력 데이터

**EDA 요약:**
{eda_summary}

**피처 엔지니어링 결과:**
- 총 생성 피처: {total_features}개
- 선택된 피처: {selected_features}개
- 상위 5 피처: {top_features}

**ML 모델 예측:**
{ml_predictions}

**모델 성능:**
- Prophet: MAPE={prophet_mape}%, R²={prophet_r2}
- LSTM: MAPE={lstm_mape}%, R²={lstm_r2}
- XGBoost: MAPE={xgb_mape}%, R²={xgb_r2}
- 앙상블 가중치: {ensemble_weights}
- 최종 앙상블: MAPE={ensemble_mape}%, 방향정확도={direction_acc}%

**백테스트 결과:**
{backtest_results}

**리스크 평가:**
{risk_assessment}

**감성 분석 결과:**
{sentiment_analysis}

### 작성 요청

위 데이터를 기반으로 다음 구조의 리포트를 작성해주세요:

1. **Executive Summary** (3줄 이내)
2. **데이터 분석 요약** (EDA에서 발견된 주요 패턴)
3. **ML 예측 결과** (앙상블 모델 예측값 + 신뢰구간 + 투자적 해석)
4. **모델 신뢰도 평가** (MAPE, 방향정확도의 의미)
5. **백테스트 성과** (전략 수익률 vs Buy&Hold, Sharpe, MDD + 의미 해석)
6. **리스크 평가** (VaR/CVaR의 투자적 의미, 최대 예상 손실)
7. **시장 심리** (감성 분석 결과와 ML 예측의 일치/불일치)
8. **핵심 피처 분석** (상위 피처가 의미하는 바)
9. **주의사항 & 한계** (모델 한계, 데이터 한계)

리포트 톤: 전문적이지만 이해하기 쉬운 한국어
"""
```

### 3.3 텔레그램 대화 프롬프트

```python
# llm/prompts/telegram.py

INTENT_CLASSIFICATION_PROMPT = """
사용자의 텔레그램 메시지를 분석하여 의도를 파악합니다.

이전 대화 컨텍스트:
- 마지막 종목: {last_stock}
- 마지막 명령: {last_command}
- 최근 분석 결과 여부: {has_recent_analysis}

사용자 메시지: "{user_message}"

의도 분류:
- collect: 데이터 수집 요청 (예: "삼성전자 데이터 모아줘")
- eda: EDA 요청 (예: "삼성전자 데이터 분석해줘", "분포 보여줘")
- analyze: 종합 분석 요청 (예: "삼성전자 분석해줘", "요즘 어때?")
- predict: ML 예측 요청 (예: "앞으로 어떨까?", "사도 될까?", "예측해줘")
- backtest: 백테스트 요청 (예: "백테스트 돌려줘", "전략 성과 보여줘")
- feature: 피처 중요도 요청 (예: "피처 중요도 알려줘", "어떤 지표가 중요해?")
- model_status: 모델 성능 조회 (예: "모델 성능 어때?", "XGBoost 결과")
- report: 전체 리포트 (예: "종합 리포트 줘")
- sector: 섹터 분석 (예: "반도체 전체 비교해줘")
- market: 시장 개요 (예: "오늘 시장 어때?")
- question: 후속 질문 (예: "그러면 매수 타이밍은?")
- greeting: 인사 (예: "안녕")
- unknown: 파악 불가

응답 형식 (JSON):
{{
    "intent": "predict",
    "stock_name": "삼성전자",
    "stock_code": "005930",
    "sector": null,
    "needs_context": false,
    "response": "삼성전자 ML 예측 분석을 시작하겠습니다."
}}
"""
```

## 4. 비용 최적화

### 4.1 모델 라우팅 전략

```python
# llm/router.py

class LLMRouter:
    """태스크 복잡도에 따른 모델 라우팅"""

    TASK_MODEL_MAP = {
        # 간단한 작업 → 저비용 모델
        "intent_classification": "fast",    # Haiku / GPT-4o-mini
        "news_summary": "fast",
        "greeting_response": "fast",

        # 중간 복잡도 → 기본 모델
        "sentiment_analysis": "default",    # Sonnet / GPT-4o
        "disclosure_impact": "default",
        "eda_insights": "default",          # EDA 통계 결과 해석
        "feature_interpretation": "default", # 피처 중요도 해석

        # 고복잡도 → 고급 모델
        "ml_report": "advanced",            # Opus / GPT-4o (ML 결과 종합 리포트)
        "risk_interpretation": "advanced",  # 리스크 지표 해석
        "full_report": "advanced",
    }

    def get_model(self, task_type: str) -> str:
        return self.TASK_MODEL_MAP.get(task_type, "default")
```

### 4.2 캐싱 전략

```python
# llm/cache.py

import hashlib
from datetime import timedelta


class LLMCache:
    """LLM 응답 캐싱"""

    # 캐시 TTL 설정 (태스크 유형별)
    CACHE_TTL = {
        "sentiment_analysis": timedelta(hours=1),      # 1시간
        "disclosure_impact": timedelta(hours=2),        # 2시간
        "eda_insights": timedelta(hours=12),            # 12시간 (EDA 결과는 자주 안 변함)
        "feature_interpretation": timedelta(hours=12),  # 12시간
        "ml_report": timedelta(hours=6),                # 6시간
        "risk_interpretation": timedelta(hours=4),      # 4시간
        "full_report": timedelta(hours=6),              # 6시간
        "intent_classification": timedelta(minutes=0),  # 캐시 안 함
    }

    async def get_or_call(
        self, task_type: str, prompt: str, llm_func, **kwargs
    ) -> str | dict:
        """캐시 히트 시 캐시 반환, 아니면 LLM 호출"""
        cache_key = self._make_key(task_type, prompt)
        ttl = self.CACHE_TTL.get(task_type)

        if ttl and ttl.total_seconds() > 0:
            cached = await self._get_cache(cache_key)
            if cached:
                logger.info(f"LLM cache hit: {task_type}")
                return cached

        result = await llm_func(prompt, **kwargs)

        if ttl and ttl.total_seconds() > 0:
            await self._set_cache(cache_key, result, ttl)

        return result

    def _make_key(self, task_type: str, prompt: str) -> str:
        content = f"{task_type}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()
```

### 4.3 비용 추적

```python
# llm/cost_tracker.py

# 모델별 대략적 비용 (USD per 1K tokens)
MODEL_COSTS = {
    "claude-opus-4-6": {"input": 0.015, "output": 0.075},
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.0008, "output": 0.004},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}

class CostTracker:
    """LLM API 비용 추적"""

    async def track_usage(self, model: str, input_tokens: int, output_tokens: int):
        cost = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        total_cost = (
            (input_tokens / 1000) * cost["input"] +
            (output_tokens / 1000) * cost["output"]
        )

        await supabase.table("llm_usage").insert({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": total_cost,
            "timestamp": datetime.utcnow().isoformat(),
        }).execute()

    async def get_daily_cost(self) -> float:
        """일일 비용 조회"""
        ...

    async def check_budget(self, daily_limit: float = 10.0) -> bool:
        """일일 예산 확인"""
        daily_cost = await self.get_daily_cost()
        return daily_cost < daily_limit
```

## 5. MCP 연동

### 5.1 LLM을 MCP 클라이언트로 활용

```python
# mcp/llm_mcp_client.py

class LLMMCPClient:
    """LLM이 MCP 도구를 호출하는 클라이언트"""

    def __init__(self, llm_client: LLMClient, mcp_tools: list[dict]):
        self.llm = llm_client
        self.tools = mcp_tools

    async def execute_with_tools(self, user_request: str) -> dict:
        """사용자 요청을 LLM이 분석하여 MCP 도구 호출"""

        # Anthropic Tool Use 형식으로 변환
        tools_schema = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            }
            for tool in self.tools
        ]

        # LLM에게 도구 사용 요청
        response = await self.llm.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools_schema,
            messages=[{"role": "user", "content": user_request}],
        )

        # 도구 호출 실행
        results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_result = await self._execute_tool(block.name, block.input)
                results.append({
                    "tool": block.name,
                    "input": block.input,
                    "result": tool_result,
                })

        return results
```

## 6. 에러 처리 및 폴백

```python
# LLM 에러 처리 전략
LLM_ERROR_HANDLING = {
    "rate_limit": {
        "action": "wait_and_retry",
        "max_retries": 3,
        "base_delay": 5,  # seconds
    },
    "context_too_long": {
        "action": "truncate_and_retry",
        "truncate_strategy": "keep_recent",  # 최근 데이터 우선
    },
    "api_error": {
        "action": "fallback_provider",
        "fallback_order": ["anthropic", "openai"],
    },
    "budget_exceeded": {
        "action": "downgrade_model",
        "downgrade_map": {
            "advanced": "default",
            "default": "fast",
        },
    },
}
```
