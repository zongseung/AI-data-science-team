# 04-1. 보고서팀 (Report Team) 상세 설계

## 1. 팀 구성

### 1.1 조직도
```
보고서팀장 (Report Team Lead)
│
├── 종합 리포터 에이전트 (Comprehensive Reporter) ← NEW
│   ├── 수집·분석·ML 전체 결과 수신
│   ├── LLM 기반 종합 자연어 리포트 생성
│   ├── 차트 이미지 생성 (matplotlib/plotly)
│   └── 리포트 구조화 (Executive Summary → 상세 분석)
│
├── 투자 메모 작성 에이전트 (Investment Memo Writer) ← NEW
│   ├── ML 예측 + 백테스트 결과 → 투자 판단 관점 요약
│   ├── 매수/매도 시그널 해석
│   ├── 동종 업계 비교 의견
│   └── 투자 의견 등급 부여 (매수/중립/매도)
│
├── 리스크 노트 작성 에이전트 (Risk Note Writer) ← NEW
│   ├── VaR/CVaR/Monte Carlo 결과 → 경고 수준별 정리
│   ├── 리스크 시나리오 요약 (최악/예상/최선)
│   ├── 주의 종목 플래그 (경고/위험/심각)
│   └── 포지션 사이징 제안
│
└── 편집장 에이전트 (Report Editor / Chief) ← NEW
    ├── 종합 리포트 + 투자 메모 + 리스크 노트 병합
    ├── 품질 검증 (수치 정합성, 논리 일관성, 면책 문구)
    ├── 텔레그램 포맷 변환 & 최종 승인
    └── 발송 및 보고서 아카이빙
```

### 1.2 다른 팀과의 관계

```
Before (예측팀에서 직접 리포트)       After (보고서팀 분리)
────────────────────────           ────────────────────────
예측팀 리포트 에이전트 1명            보고서팀 전담 에이전트 4명
ML 결과만 요약                       수집·분석·ML 전체 결과 종합
단일 리포트 출력                      종합리포트 + 투자메모 + 리스크노트
검토 없이 즉시 전송                   편집장 검토 후 승인 전송
LLM 1회 호출                         용도별 특화 프롬프트 분리
```

### 1.3 데이터 흐름

```
[수집팀] ──→ raw_data ──→┐
                          │
[분석팀] ──→ eda_report  ──┤
             features     ├──→ [보고서팀 매니저] ──→ 종합 리포터 ──→┐
             statistics   │                   ──→ 투자 메모    ──→├──→ [편집장] ──→ [텔레그램]
             sentiment    │                   ──→ 리스크 노트  ──→┘
                          │
[예측팀] ──→ ml_results  ──┤
             backtest     │
             risk         ──┘
```

---

## 2. 종합 리포터 에이전트

### 2.1 역할

수집팀, 분석팀, 예측팀의 전체 결과를 수신하여 하나의 종합 리포트로 통합합니다.
LLM을 활용하여 비전문가도 이해할 수 있는 자연어 보고서를 생성합니다.

### 2.2 구현

```python
# agents/report/comprehensive_reporter.py

class ComprehensiveReporter(BaseAgent):
    """수집·분석·ML 전체 결과를 종합하는 리포트 에이전트"""

    async def execute(self, task: Task) -> TaskResult:
        stock_name = task.params["stock_name"]
        stock_code = task.params["stock_code"]

        # 전체 팀 결과 수신
        collection_data = task.params["collection_data"]
        analysis_data = task.params["analysis_data"]
        ml_data = task.params["ml_data"]

        await self.update_status(AgentStatus.WORKING, f"{stock_name} 종합 리포트 작성 중")

        # 1. 데이터 수집 요약
        collection_summary = self._summarize_collection(collection_data)

        # 2. EDA + 분석 요약
        analysis_summary = self._summarize_analysis(analysis_data)

        # 3. ML 예측 + 백테스트 + 리스크 요약
        ml_summary = self._summarize_ml(ml_data)

        # 4. LLM으로 종합 리포트 생성
        full_report = await self._generate_comprehensive_report(
            stock_name, stock_code,
            collection_summary, analysis_summary, ml_summary
        )

        # 5. 차트 이미지 생성
        charts = await self._generate_charts(
            stock_code, analysis_data, ml_data
        )

        return TaskResult(success=True, data={
            "report_type": "comprehensive",
            "stock_code": stock_code,
            "full_report": full_report,
            "collection_summary": collection_summary,
            "analysis_summary": analysis_summary,
            "ml_summary": ml_summary,
            "chart_images": charts,
            "generated_at": datetime.utcnow().isoformat(),
        })

    def _summarize_collection(self, data: dict) -> dict:
        """수집 데이터 요약"""
        return {
            "price_count": data.get("price_count", 0),
            "disclosure_count": data.get("disclosure_count", 0),
            "news_count": data.get("news_count", 0),
            "data_period": data.get("data_period", "N/A"),
            "data_quality": data.get("quality_score", "N/A"),
        }

    def _summarize_analysis(self, data: dict) -> dict:
        """분석 결과 요약"""
        eda = data.get("eda", {})
        features = data.get("features", {})
        stats = data.get("statistical", {})
        sentiment = data.get("sentiment", {})

        return {
            "eda_insights": eda.get("insights", []),
            "stationarity": eda.get("stationarity_test", {}),
            "outlier_count": eda.get("outlier_count", 0),
            "total_features": features.get("total_features", 0),
            "selected_features": features.get("selected_features", 0),
            "top_features": features.get("top_features", []),
            "granger_causality": stats.get("granger", {}),
            "garch_volatility": stats.get("garch", {}),
            "sentiment_score": sentiment.get("average_sentiment", 0),
            "sentiment_summary": sentiment.get("summary", ""),
        }

    def _summarize_ml(self, data: dict) -> dict:
        """ML 예측 결과 요약"""
        ml_results = data.get("ml_results", {})
        backtest = data.get("backtest", {})
        risk = data.get("risk", {})

        ensemble = ml_results.get("ensemble", {})
        prediction = ml_results.get("prediction", {})

        return {
            "ensemble_method": ensemble.get("method", "N/A"),
            "ensemble_weights": ensemble.get("weights", {}),
            "ensemble_mape": ensemble.get("ensemble_metrics", {}).get("mape", 0),
            "direction_accuracy": ensemble.get("ensemble_metrics", {}).get("direction_accuracy", 0),
            "predictions": prediction.get("predictions", {}),
            "sharpe_ratio": backtest.get("strategy_simulation", {}).get("metrics", {}).get("sharpe_ratio", 0),
            "max_drawdown": backtest.get("strategy_simulation", {}).get("metrics", {}).get("max_drawdown", 0),
            "total_return": backtest.get("strategy_simulation", {}).get("total_return_pct", "N/A"),
            "var_95": risk.get("var", {}).get("historical", {}).get("var_95", 0),
            "cvar_95": risk.get("cvar", {}).get("cvar_95", 0),
            "monte_carlo": risk.get("monte_carlo", {}),
        }

    async def _generate_comprehensive_report(
        self, stock_name: str, stock_code: str,
        collection: dict, analysis: dict, ml: dict
    ) -> str:
        """LLM으로 종합 리포트 생성"""
        prompt = f"""
        당신은 한국 주식시장 전문 데이터사이언스 애널리스트입니다.
        아래 데이터 수집·분석·ML 예측 결과를 종합하여 투자 리포트를 작성해주세요.

        ## {stock_name} ({stock_code}) 종합 분석 결과

        ### 1. 데이터 수집 현황
        - 주가 데이터: {collection['price_count']}건
        - 공시: {collection['disclosure_count']}건, 뉴스: {collection['news_count']}건
        - 분석 기간: {collection['data_period']}

        ### 2. EDA & 분석 결과
        - 핵심 인사이트: {analysis['eda_insights']}
        - 정상성: {analysis['stationarity']}
        - 이상치: {analysis['outlier_count']}건 탐지
        - Granger 인과: {analysis['granger_causality']}
        - GARCH 변동성: {analysis['garch_volatility']}
        - 감성 점수: {analysis['sentiment_score']} ({analysis['sentiment_summary']})

        ### 3. 피처 엔지니어링
        - 총 피처: {analysis['total_features']}개 → 선택: {analysis['selected_features']}개
        - 상위 피처: {analysis['top_features']}

        ### 4. ML 예측
        - 앙상블: {ml['ensemble_method']} (가중치: {ml['ensemble_weights']})
        - MAPE: {ml['ensemble_mape']:.2f}%, 방향정확도: {ml['direction_accuracy']:.1%}
        - 예측: {ml['predictions']}

        ### 5. 백테스트
        - 수익률: {ml['total_return']}, Sharpe: {ml['sharpe_ratio']:.2f}
        - MDD: {ml['max_drawdown']:.2%}

        ### 6. 리스크
        - VaR(95%): {ml['var_95']:.2%}, CVaR(95%): {ml['cvar_95']:.2%}
        - 몬테카를로 상승확률: {ml['monte_carlo'].get('probability_above_current', 0):.1%}

        ---
        리포트 구조:
        1. Executive Summary (3줄 이내)
        2. 데이터 수집 & 품질 요약
        3. EDA 핵심 발견
        4. ML 예측 결과 (가격, 방향, 신뢰구간)
        5. 모델 신뢰도 (성능 메트릭 해석)
        6. 백테스트 성과 해석
        7. 리스크 분석
        8. 핵심 모니터링 포인트

        투자 권유가 아닌 데이터 분석 정보 제공임을 명시.
        한국어로 작성.
        """

        return await llm_client.chat(
            prompt,
            system=COMPREHENSIVE_REPORT_SYSTEM_PROMPT,
            model="advanced",
        )

    async def _generate_charts(self, stock_code: str, analysis: dict, ml: dict) -> list[str]:
        """차트 이미지 생성"""
        import matplotlib.pyplot as plt

        chart_paths = []

        # 1. 예측 vs 실제 차트
        pred_chart = await self._create_prediction_chart(stock_code, ml)
        chart_paths.append(pred_chart)

        # 2. 백테스트 누적 수익률 차트
        backtest_chart = await self._create_backtest_chart(stock_code, ml)
        chart_paths.append(backtest_chart)

        # 3. 리스크 Fan 차트 (몬테카를로)
        risk_chart = await self._create_risk_fan_chart(stock_code, ml)
        chart_paths.append(risk_chart)

        # 4. 피처 중요도 바 차트
        feature_chart = await self._create_feature_importance_chart(stock_code, analysis)
        chart_paths.append(feature_chart)

        return chart_paths
```

---

## 3. 투자 메모 작성 에이전트

### 3.1 역할

ML 예측 결과와 백테스트 성과를 투자 판단 관점에서 요약합니다.
매수/매도/중립 의견을 근거와 함께 제시하되, 투자 권유가 아님을 명시합니다.

### 3.2 구현

```python
# agents/report/investment_memo.py

class InvestmentMemoWriter(BaseAgent):
    """ML 예측 + 백테스트 결과 → 투자 판단 관점 메모"""

    OPINION_THRESHOLDS = {
        "strong_buy": {"direction_acc": 0.70, "sharpe": 1.5, "pred_return": 0.03},
        "buy": {"direction_acc": 0.60, "sharpe": 1.0, "pred_return": 0.01},
        "neutral": {"direction_acc": 0.50, "sharpe": 0.5, "pred_return": -0.01},
        "sell": {"direction_acc": 0.0, "sharpe": 0.0, "pred_return": -0.03},
    }

    async def execute(self, task: Task) -> TaskResult:
        stock_name = task.params["stock_name"]
        stock_code = task.params["stock_code"]
        ml_data = task.params["ml_data"]
        analysis_data = task.params["analysis_data"]

        await self.update_status(AgentStatus.WORKING, f"{stock_name} 투자 메모 작성 중")

        # 1. 정량적 투자 의견 도출
        opinion = self._derive_opinion(ml_data)

        # 2. 근거 수집
        evidence = self._collect_evidence(ml_data, analysis_data)

        # 3. LLM으로 투자 메모 생성
        memo = await self._generate_memo(
            stock_name, stock_code, opinion, evidence
        )

        return TaskResult(success=True, data={
            "report_type": "investment_memo",
            "stock_code": stock_code,
            "opinion": opinion,
            "evidence": evidence,
            "memo_text": memo,
            "generated_at": datetime.utcnow().isoformat(),
        })

    def _derive_opinion(self, ml_data: dict) -> dict:
        """정량적 기준으로 투자 의견 도출"""
        ml_results = ml_data.get("ml_results", {})
        backtest = ml_data.get("backtest", {})

        ensemble = ml_results.get("ensemble", {})
        prediction = ml_results.get("prediction", {})
        strategy = backtest.get("strategy_simulation", {})

        direction_acc = ensemble.get("ensemble_metrics", {}).get("direction_accuracy", 0)
        sharpe = strategy.get("metrics", {}).get("sharpe_ratio", 0)

        pred_1d = prediction.get("predictions", {}).get("1d", {})
        pred_return = pred_1d.get("predicted_return", 0)
        direction_prob = pred_1d.get("direction_probability", 0.5)

        # 의견 결정
        if (direction_acc >= 0.70 and sharpe >= 1.5 and pred_return >= 0.03):
            level = "적극 매수"
            confidence = "높음"
        elif (direction_acc >= 0.60 and sharpe >= 1.0 and pred_return >= 0.01):
            level = "매수"
            confidence = "중간"
        elif (direction_acc >= 0.50 and pred_return >= -0.01):
            level = "중립"
            confidence = "중간"
        elif pred_return < -0.03:
            level = "매도"
            confidence = "중간"
        else:
            level = "중립 (관망)"
            confidence = "낮음"

        return {
            "opinion_level": level,
            "confidence": confidence,
            "direction_accuracy": direction_acc,
            "sharpe_ratio": sharpe,
            "predicted_return": pred_return,
            "direction_probability": direction_prob,
        }

    def _collect_evidence(self, ml_data: dict, analysis_data: dict) -> dict:
        """투자 판단 근거 수집"""
        backtest = ml_data.get("backtest", {})
        strategy = backtest.get("strategy_simulation", {})
        benchmark = backtest.get("benchmark_comparison", {})
        sentiment = analysis_data.get("sentiment", {})
        features = analysis_data.get("features", {})

        return {
            "strategy_vs_benchmark": {
                "strategy_return": strategy.get("total_return_pct", "N/A"),
                "benchmark_return": benchmark.get("buy_and_hold_return_pct", "N/A"),
            },
            "win_rate": strategy.get("metrics", {}).get("win_rate", 0),
            "total_trades": strategy.get("metrics", {}).get("total_trades", 0),
            "sentiment": sentiment.get("average_sentiment", 0),
            "sentiment_summary": sentiment.get("summary", ""),
            "top_features": features.get("top_features", [])[:5],
            "model_count": len(ml_data.get("ml_results", {}).get("models", {})),
        }

    async def _generate_memo(
        self, stock_name: str, stock_code: str, opinion: dict, evidence: dict
    ) -> str:
        """LLM으로 투자 메모 생성"""
        prompt = f"""
        당신은 금융 데이터사이언스 기반 투자 분석가입니다.
        다음 ML 분석 근거를 바탕으로 간결한 투자 메모를 작성해주세요.

        ## {stock_name} ({stock_code}) 투자 메모

        ### ML 기반 의견: {opinion['opinion_level']} (신뢰도: {opinion['confidence']})
        - 방향 정확도: {opinion['direction_accuracy']:.1%}
        - 예측 수익률: {opinion['predicted_return']:+.2%}
        - Sharpe Ratio: {opinion['sharpe_ratio']:.2f}

        ### 백테스트 근거
        - 전략 수익률: {evidence['strategy_vs_benchmark']['strategy_return']}
        - Buy & Hold: {evidence['strategy_vs_benchmark']['benchmark_return']}
        - 승률: {evidence['win_rate']:.1%} ({evidence['total_trades']}회 매매)

        ### 시장 심리
        - 감성 점수: {evidence['sentiment']:.2f}
        - {evidence['sentiment_summary']}

        ### 핵심 영향 피처
        - {evidence['top_features']}

        ---
        메모 구조:
        1. 한줄 요약 (투자 의견 + 핵심 근거)
        2. ML 예측 기반 판단 근거 (2-3줄)
        3. 백테스트 성과 해석 (2줄)
        4. 주의 사항 (1-2줄)

        반드시 "AI/ML 기반 데이터 분석이며 투자 권유가 아닙니다" 면책 포함.
        한국어, 간결하게.
        """

        return await llm_client.chat(
            prompt,
            system=INVESTMENT_MEMO_SYSTEM_PROMPT,
            model="advanced",
        )
```

---

## 4. 리스크 노트 작성 에이전트

### 4.1 역할

VaR/CVaR/Monte Carlo 등 리스크 평가 결과를 경고 수준별로 정리합니다.
투자자가 인지해야 할 위험 요소를 명확하게 전달합니다.

### 4.2 구현

```python
# agents/report/risk_note.py

class RiskNoteWriter(BaseAgent):
    """리스크 평가 결과 → 경고 수준별 리스크 노트"""

    RISK_LEVELS = {
        "safe":     {"var_95_max": -0.02, "color": "🟢", "label": "안전"},
        "caution":  {"var_95_max": -0.04, "color": "🟡", "label": "주의"},
        "warning":  {"var_95_max": -0.06, "color": "🟠", "label": "경고"},
        "danger":   {"var_95_max": -1.00, "color": "🔴", "label": "위험"},
    }

    async def execute(self, task: Task) -> TaskResult:
        stock_name = task.params["stock_name"]
        stock_code = task.params["stock_code"]
        risk_data = task.params["risk_data"]
        backtest_data = task.params["backtest_data"]

        await self.update_status(AgentStatus.WORKING, f"{stock_name} 리스크 노트 작성 중")

        # 1. 리스크 수준 판정
        risk_level = self._assess_risk_level(risk_data)

        # 2. 시나리오 분석 요약
        scenarios = self._summarize_scenarios(risk_data)

        # 3. 포지션 사이징 제안
        position_sizing = self._suggest_position_sizing(risk_data, risk_level)

        # 4. LLM으로 리스크 노트 생성
        note = await self._generate_risk_note(
            stock_name, stock_code, risk_level, scenarios, position_sizing
        )

        return TaskResult(success=True, data={
            "report_type": "risk_note",
            "stock_code": stock_code,
            "risk_level": risk_level,
            "scenarios": scenarios,
            "position_sizing": position_sizing,
            "note_text": note,
            "generated_at": datetime.utcnow().isoformat(),
        })

    def _assess_risk_level(self, risk_data: dict) -> dict:
        """리스크 수준 판정"""
        var_95 = risk_data.get("var", {}).get("historical", {}).get("var_95", 0)
        cvar_95 = risk_data.get("cvar", {}).get("cvar_95", 0)
        mdd = risk_data.get("drawdown_analysis", {}).get("max_drawdown", 0)
        mc = risk_data.get("monte_carlo", {})
        prob_loss_5 = mc.get("probability_loss_5pct", 0)

        # 수준 판정
        if var_95 >= -0.02:
            level = "safe"
        elif var_95 >= -0.04:
            level = "caution"
        elif var_95 >= -0.06:
            level = "warning"
        else:
            level = "danger"

        config = self.RISK_LEVELS[level]

        return {
            "level": level,
            "label": config["label"],
            "icon": config["color"],
            "var_95": var_95,
            "cvar_95": cvar_95,
            "max_drawdown": mdd,
            "probability_loss_5pct": prob_loss_5,
        }

    def _summarize_scenarios(self, risk_data: dict) -> dict:
        """시나리오 분석 요약 (최악/예상/최선)"""
        mc = risk_data.get("monte_carlo", {})
        percentiles = mc.get("percentiles", {})
        current = mc.get("current_price", 0)

        return {
            "worst_case": {
                "price": percentiles.get("5th", 0),
                "return_pct": (percentiles.get("5th", current) - current) / current if current else 0,
                "label": "최악 (5th percentile)",
            },
            "expected": {
                "price": mc.get("expected_price", 0),
                "return_pct": (mc.get("expected_price", current) - current) / current if current else 0,
                "label": "예상 (평균)",
            },
            "best_case": {
                "price": percentiles.get("95th", 0),
                "return_pct": (percentiles.get("95th", current) - current) / current if current else 0,
                "label": "최선 (95th percentile)",
            },
            "horizon_days": mc.get("horizon_days", 20),
        }

    def _suggest_position_sizing(self, risk_data: dict, risk_level: dict) -> dict:
        """리스크 수준에 따른 포지션 사이징 제안"""
        level = risk_level["level"]

        sizing_map = {
            "safe": {"max_portfolio_pct": 20, "note": "일반적 비중 투자 가능"},
            "caution": {"max_portfolio_pct": 10, "note": "포트폴리오의 10% 이내 권장"},
            "warning": {"max_portfolio_pct": 5, "note": "소규모 비중만 권장, 손절 라인 설정 필수"},
            "danger": {"max_portfolio_pct": 0, "note": "신규 진입 비추천, 기존 포지션 축소 고려"},
        }

        return sizing_map.get(level, sizing_map["caution"])

    async def _generate_risk_note(
        self, stock_name: str, stock_code: str,
        risk_level: dict, scenarios: dict, position: dict
    ) -> str:
        """LLM으로 리스크 노트 생성"""
        prompt = f"""
        다음 리스크 평가 결과를 투자자가 쉽게 이해할 수 있는 리스크 노트로 작성해주세요.

        ## {stock_name} ({stock_code}) 리스크 노트

        ### 리스크 수준: {risk_level['icon']} {risk_level['label']}
        - VaR(95%): {risk_level['var_95']:.2%}
        - CVaR(95%): {risk_level['cvar_95']:.2%}
        - 최대 낙폭: {risk_level['max_drawdown']:.2%}
        - 5% 이상 손실 확률: {risk_level['probability_loss_5pct']:.1%}

        ### 시나리오 ({scenarios['horizon_days']}일 전망)
        - 최악: {scenarios['worst_case']['price']:,.0f}원 ({scenarios['worst_case']['return_pct']:+.2%})
        - 예상: {scenarios['expected']['price']:,.0f}원 ({scenarios['expected']['return_pct']:+.2%})
        - 최선: {scenarios['best_case']['price']:,.0f}원 ({scenarios['best_case']['return_pct']:+.2%})

        ### 포지션 제안
        - 최대 비중: 포트폴리오의 {position['max_portfolio_pct']}%
        - {position['note']}

        ---
        노트 구조:
        1. 리스크 등급 한줄 요약
        2. 주요 리스크 요인 (2-3개)
        3. 시나리오 해석 (1-2줄)
        4. 행동 권고 (1-2줄)

        간결하게, 한국어로 작성. 투자 권유 아닌 리스크 정보 제공 명시.
        """

        return await llm_client.chat(
            prompt,
            system=RISK_NOTE_SYSTEM_PROMPT,
            model="default",
        )
```

---

## 5. 편집장 에이전트

### 5.1 역할

종합 리포터, 투자 메모, 리스크 노트의 결과를 최종 검토하고 병합합니다.
수치 정합성, 논리 일관성을 검증하고, 텔레그램 포맷으로 변환하여 발송합니다.

### 5.2 구현

```python
# agents/report/report_editor.py

class ReportEditor(BaseAgent):
    """편집장 - 최종 검토, 병합, 발송"""

    async def execute(self, task: Task) -> TaskResult:
        stock_name = task.params["stock_name"]
        stock_code = task.params["stock_code"]

        comprehensive = task.params["comprehensive_report"]
        investment_memo = task.params["investment_memo"]
        risk_note = task.params["risk_note"]

        await self.update_status(AgentStatus.WORKING, f"{stock_name} 최종 검토 중")

        # 1. 품질 검증
        quality_check = await self._verify_quality(
            comprehensive, investment_memo, risk_note
        )

        if not quality_check["passed"]:
            # 검증 실패 시 LLM으로 수정 요청
            await self.update_status(AgentStatus.WORKING, f"{stock_name} 보고서 수정 중")
            comprehensive, investment_memo, risk_note = await self._fix_issues(
                quality_check["issues"],
                comprehensive, investment_memo, risk_note
            )

        # 2. 최종 병합
        merged_report = self._merge_reports(
            comprehensive, investment_memo, risk_note
        )

        # 3. 텔레그램 포맷 변환
        telegram_message = self._format_for_telegram(
            stock_name, stock_code, merged_report
        )

        # 4. 아카이빙 데이터 준비
        archive_data = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "comprehensive_report": comprehensive,
            "investment_memo": investment_memo,
            "risk_note": risk_note,
            "quality_check": quality_check,
            "generated_at": datetime.utcnow().isoformat(),
        }

        await self.update_status(AgentStatus.WORKING, f"{stock_name} 최종 승인")

        return TaskResult(success=True, data={
            "report_type": "final",
            "stock_code": stock_code,
            "merged_report": merged_report,
            "telegram_message": telegram_message,
            "chart_images": comprehensive.get("chart_images", []),
            "quality_check": quality_check,
            "archive": archive_data,
            "approved": True,
            "approved_at": datetime.utcnow().isoformat(),
        })

    async def _verify_quality(
        self, comprehensive: dict, memo: dict, risk: dict
    ) -> dict:
        """품질 검증 (수치 정합성, 논리 일관성)"""
        issues = []

        # 1. 수치 정합성 검증
        comp_mape = comprehensive.get("ml_summary", {}).get("ensemble_mape", 0)
        memo_opinion = memo.get("opinion", {})

        # MAPE가 10% 이상이면 모델 신뢰도 경고
        if comp_mape > 10:
            issues.append({
                "type": "model_reliability",
                "severity": "warning",
                "message": f"MAPE {comp_mape:.1f}% → 모델 신뢰도 낮음, 리포트에 경고 추가 필요",
            })

        # 2. 투자 의견과 리스크 수준 일관성 검증
        risk_level = risk.get("risk_level", {}).get("level", "caution")
        opinion_level = memo_opinion.get("opinion_level", "중립")

        if risk_level == "danger" and "매수" in opinion_level:
            issues.append({
                "type": "consistency",
                "severity": "error",
                "message": "리스크 '위험' 수준인데 매수 의견 → 의견 하향 조정 필요",
            })

        # 3. 면책 문구 존재 확인
        report_text = comprehensive.get("full_report", "")
        if "투자 권유" not in report_text and "투자 권고" not in report_text:
            issues.append({
                "type": "disclaimer",
                "severity": "error",
                "message": "면책 문구 누락 → 추가 필요",
            })

        return {
            "passed": all(i["severity"] != "error" for i in issues),
            "issues": issues,
            "checked_at": datetime.utcnow().isoformat(),
        }

    def _merge_reports(self, comprehensive: dict, memo: dict, risk: dict) -> dict:
        """3개 보고서 병합"""
        return {
            "full_report": comprehensive.get("full_report", ""),
            "investment_opinion": memo.get("opinion", {}),
            "investment_memo": memo.get("memo_text", ""),
            "risk_level": risk.get("risk_level", {}),
            "risk_note": risk.get("note_text", ""),
            "scenarios": risk.get("scenarios", {}),
            "charts": comprehensive.get("chart_images", []),
        }

    def _format_for_telegram(
        self, stock_name: str, stock_code: str, report: dict
    ) -> str:
        """텔레그램 최종 메시지 포맷"""
        opinion = report["investment_opinion"]
        risk = report["risk_level"]

        return f"""📊 {stock_name} ({stock_code}) 종합 리포트
━━━━━━━━━━━━━━━━━━━━━━━

{report['full_report'][:1500]}

💰 투자 메모
━━━━━━━━━━━━━━━
의견: {opinion.get('opinion_level', 'N/A')} (신뢰도: {opinion.get('confidence', 'N/A')})
{report['investment_memo'][:500]}

{risk.get('icon', '⚠️')} 리스크 노트 [{risk.get('label', 'N/A')}]
━━━━━━━━━━━━━━━
VaR(95%): {risk.get('var_95', 0):.2%} | CVaR: {risk.get('cvar_95', 0):.2%}
{report['risk_note'][:500]}

⚖️ AI/ML 기반 데이터 분석 정보이며, 투자 권유가 아닙니다.
🤖 Generated by AI Data Science Team - Report Division"""

    async def _fix_issues(self, issues, comprehensive, memo, risk):
        """품질 이슈 수정"""
        for issue in issues:
            if issue["type"] == "consistency" and issue["severity"] == "error":
                # 투자 의견을 리스크 수준에 맞게 하향 조정
                memo["opinion"]["opinion_level"] = "중립 (관망)"
                memo["opinion"]["confidence"] = "낮음"

            if issue["type"] == "disclaimer" and issue["severity"] == "error":
                # 면책 문구 추가
                comprehensive["full_report"] += (
                    "\n\n※ 본 리포트는 AI/ML 기반 데이터 분석 정보이며, "
                    "투자 권유가 아닙니다. 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다."
                )

        return comprehensive, memo, risk
```

---

## 6. 보고서팀 매니저

### 6.1 오케스트레이션

```python
# agents/report/manager.py

import asyncio
from datetime import datetime


class ReportManager:
    """보고서팀 매니저 - 리포트 작성 워크플로우 조율"""

    def __init__(self):
        self.comprehensive_reporter = ComprehensiveReporter(
            agent_id="comprehensive_reporter", name="종합 리포터", team="report"
        )
        self.memo_writer = InvestmentMemoWriter(
            agent_id="investment_memo_writer", name="투자 메모 작성자", team="report"
        )
        self.risk_writer = RiskNoteWriter(
            agent_id="risk_note_writer", name="리스크 노트 작성자", team="report"
        )
        self.editor = ReportEditor(
            agent_id="report_editor", name="편집장", team="report"
        )

    async def generate_report(
        self,
        stock_code: str,
        stock_name: str,
        collection_data: dict,
        analysis_data: dict,
        ml_data: dict,
    ) -> dict:
        """종합 리포트 생성 워크플로우"""

        # Phase 1: 종합 리포트 + 투자 메모 + 리스크 노트 (병렬)
        comprehensive_result, memo_result, risk_result = await asyncio.gather(
            self.comprehensive_reporter.execute(Task(
                type="comprehensive_report",
                params={
                    "stock_name": stock_name,
                    "stock_code": stock_code,
                    "collection_data": collection_data,
                    "analysis_data": analysis_data,
                    "ml_data": ml_data,
                }
            )),
            self.memo_writer.execute(Task(
                type="investment_memo",
                params={
                    "stock_name": stock_name,
                    "stock_code": stock_code,
                    "ml_data": ml_data,
                    "analysis_data": analysis_data,
                }
            )),
            self.risk_writer.execute(Task(
                type="risk_note",
                params={
                    "stock_name": stock_name,
                    "stock_code": stock_code,
                    "risk_data": ml_data.get("risk", {}),
                    "backtest_data": ml_data.get("backtest", {}),
                }
            )),
        )

        # Phase 2: 편집장 최종 검토 & 병합 (Phase 1 결과 의존)
        editor_result = await self.editor.execute(Task(
            type="report_review",
            params={
                "stock_name": stock_name,
                "stock_code": stock_code,
                "comprehensive_report": comprehensive_result.data,
                "investment_memo": memo_result.data,
                "risk_note": risk_result.data,
            }
        ))

        return {
            "comprehensive": comprehensive_result.data,
            "investment_memo": memo_result.data,
            "risk_note": risk_result.data,
            "final": editor_result.data,
            "telegram_message": editor_result.data["telegram_message"],
            "chart_images": editor_result.data["chart_images"],
            "approved": editor_result.data["approved"],
            "completed_at": datetime.utcnow().isoformat(),
        }
```

### 6.2 오케스트레이터 연동

```python
# core/orchestrator.py (업데이트)

class Orchestrator:
    """전체 파이프라인 오케스트레이터"""

    def __init__(self):
        self.collection_manager = CollectionManager()
        self.analysis_manager = AnalysisManager()
        self.forecast_manager = ForecastManager()
        self.report_manager = ReportManager()  # ← NEW

    async def full_pipeline(self, stock_code: str, stock_name: str) -> dict:
        """전체 파이프라인: 수집 → 분석 → 예측 → 보고서"""

        # 1. 수집
        collection_data = await self.collection_manager.collect(stock_code)

        # 2. 분석
        analysis_data = await self.analysis_manager.analyze_stock(
            stock_code, collection_data
        )

        # 3. 예측 (ML)
        ml_data = await self.forecast_manager.predict(
            stock_code, analysis_data
        )

        # 4. 보고서 ← NEW
        report_data = await self.report_manager.generate_report(
            stock_code=stock_code,
            stock_name=stock_name,
            collection_data=collection_data,
            analysis_data=analysis_data,
            ml_data=ml_data,
        )

        # 5. 텔레그램 전송
        if report_data["approved"]:
            await self.telegram_bot.send_report(
                message=report_data["telegram_message"],
                charts=report_data["chart_images"],
            )

        return report_data
```

---

## 7. LLM 프롬프트 설계

### 7.1 시스템 프롬프트

```python
# llm/prompts/report.py

COMPREHENSIVE_REPORT_SYSTEM_PROMPT = """
당신은 한국 주식시장 전문 데이터사이언스 수석 애널리스트입니다.
수집팀, 분석팀, ML팀의 전체 분석 결과를 종합하여 투자 리포트를 작성합니다.

원칙:
1. 수집 → EDA → 피처 엔지니어링 → ML 예측 → 백테스트 → 리스크의 전체 흐름을 논리적으로 연결
2. 통계 용어를 쉽게 풀어서 설명하되, 정확한 수치는 반드시 포함
3. ML 모델의 예측은 통계적 결과이지 확정적 전망이 아님을 항상 명시
4. 데이터 품질 이슈나 모델 한계가 있으면 솔직하게 기재
5. "투자 권유가 아닌 데이터 분석 정보 제공" 면책 포함
"""

INVESTMENT_MEMO_SYSTEM_PROMPT = """
당신은 데이터 기반 투자 분석가입니다.
ML 예측과 백테스트 결과를 투자 판단 관점에서 간결하게 요약합니다.

원칙:
1. 정량적 근거 (방향 정확도, Sharpe, 수익률)를 먼저 제시
2. 매수/매도/중립 의견은 반드시 근거와 함께
3. 모델 신뢰도가 낮으면 '관망' 권고
4. 투자 권유가 아닌 분석 정보 제공임을 명시
"""

RISK_NOTE_SYSTEM_PROMPT = """
당신은 금융 리스크 분석 전문가입니다.
VaR, CVaR, Monte Carlo 시뮬레이션 결과를 투자자가 이해할 수 있게 해석합니다.

원칙:
1. 리스크 수준을 직관적으로 전달 (안전/주의/경고/위험)
2. 수치의 실질적 의미 해석 (예: VaR -3% → 하루에 100만원 투자 시 3만원 손실 가능)
3. 시나리오별 예상 결과 명확하게 제시
4. 위험을 과소평가하지 않기
"""
```

### 7.2 LLM 모델 라우팅

```python
# 보고서팀 태스크별 모델 라우팅

REPORT_TASK_MODEL_MAP = {
    "comprehensive_report": "advanced",  # Opus (종합 리포트, 가장 복잡)
    "investment_memo": "advanced",       # Opus (투자 판단 해석)
    "risk_note": "default",             # Sonnet (리스크 해석, 정형화)
    "report_review": "advanced",         # Opus (품질 검증, 논리 검증)
}
```

---

## 8. 텔레그램 출력 포맷

### 8.1 최종 종합 리포트 메시지

```
📊 삼성전자 (005930) 종합 리포트
━━━━━━━━━━━━━━━━━━━━━━━

📋 Executive Summary
삼성전자는 AI 반도체 수요 호조에 힘입어 상승 추세를 유지 중이며,
ML 앙상블 모델은 1주 후 소폭 상승(+1.8%)을 예측합니다.
다만 메모리 가격 조정 리스크에 유의가 필요합니다.

🔬 데이터 분석 요약
• 수집 데이터: 주가 120건, 공시 5건, 뉴스 8건
• EDA: 상승 추세, 변동성 확대 중, 이상치 3건
• 감성: +0.42 (긍정, HBM 수주 호재)
• 핵심 피처: RSI(14), 20일 변동성, 감성점수

🤖 ML 예측 (앙상블: Prophet + LSTM + XGBoost)
• 내일: 78,500원 (+0.8%) [95% CI: 77,200~79,800]
• 5일: 79,900원 (+1.8%) [95% CI: 76,500~83,300]
• MAPE: 2.3% | 방향 정확도: 68%

📈 백테스트 (6개월)
• 전략 수익률: +18.5% (vs Buy&Hold +12.3%)
• Sharpe: 1.45 | MDD: -8.2% | 승률: 62%

💰 투자 메모
━━━━━━━━━━━━━━━
의견: 매수 (신뢰도: 중간)
ML 모델이 68% 방향 정확도로 단기 상승을 예측하며,
백테스트에서 Buy&Hold 대비 +6.2%p 초과 수익 달성.
다만 MAPE 2.3%로 절대 가격 예측 오차 존재.

🟡 리스크 노트 [주의]
━━━━━━━━━━━━━━━
VaR(95%): -3.2% | CVaR: -4.8%
• 20일 시나리오: 최악 73,800원 / 예상 79,200원 / 최선 84,600원
• 포지션 비중: 포트폴리오의 10% 이내 권장
• 주의: 메모리 가격 조정 사이클 진입 가능성

⚖️ AI/ML 기반 데이터 분석 정보이며, 투자 권유가 아닙니다.
🤖 Generated by AI Data Science Team - Report Division
```

### 8.2 투자 메모 단독 메시지

```
💰 삼성전자 (005930) 투자 메모
━━━━━━━━━━━━━━━━━━━━━━━

📌 의견: 매수 (신뢰도: 중간)

ML 앙상블 모델 기반 단기 상승 예측 (+1.8%, 5일).
방향 정확도 68%, 백테스트 Sharpe 1.45로 전략 유효성 확인됨.
감성 점수 +0.42 (HBM 수주 확대) → ML 예측과 방향 일치.

📊 핵심 근거
• 전략 수익률 +18.5% vs Buy&Hold +12.3%
• 승률 62% (총 28회 매매)
• 상위 피처: RSI(14), 20일 변동성, 감성점수

⚠️ 주의사항
• MAPE 2.3% → 절대 가격 예측에 ±1,800원 오차 가능
• 리스크 수준 '주의' → 포트폴리오 10% 이내 권장

⚖️ AI/ML 기반 데이터 분석이며, 투자 권유가 아닙니다.
```

### 8.3 리스크 노트 단독 메시지

```
🟡 삼성전자 (005930) 리스크 노트 [주의]
━━━━━━━━━━━━━━━━━━━━━━━

📊 리스크 지표
• VaR(95%): -3.2% (일일 최대 예상 손실)
• CVaR(95%): -4.8% (VaR 초과 시 평균 손실)
• 최대 낙폭: -12.1% (과거 6개월)
• 5%+ 손실 확률: 18.3% (20일 내)

📉 시나리오 분석 (20일 전망)
• 최악 (5%): 73,800원 (-4.2%)
• 예상 (평균): 79,200원 (+2.8%)
• 최선 (95%): 84,600원 (+9.8%)

💡 행동 권고
• 포지션 비중: 포트폴리오의 10% 이내
• 손절 라인: -5% 설정 권장
• 주의 요인: 메모리 가격 조정 사이클

⚖️ AI/ML 기반 리스크 분석 정보이며, 투자 권유가 아닙니다.
```

---

## 9. 데이터 모델

### 9.1 보고서 테이블

```sql
reports (보고서 아카이브) ← NEW
├── id: UUID
├── stock_id: FK → stocks
├── report_type: ENUM ('comprehensive', 'investment_memo', 'risk_note', 'final')
├── content: TEXT (보고서 본문)
├── opinion: JSONB (투자 의견: level, confidence, evidence)
├── risk_level: JSONB (리스크 수준: level, var_95, cvar_95)
├── quality_check: JSONB (품질 검증 결과)
├── chart_paths: JSONB (차트 이미지 경로 목록)
├── telegram_sent: BOOLEAN (텔레그램 발송 여부)
├── telegram_sent_at: TIMESTAMP
├── approved_by: VARCHAR ('report_editor')
├── approved_at: TIMESTAMP
└── created_at: TIMESTAMP
```

---

## 10. 웹 시각화 연동

### 10.1 보고서팀 방 픽셀 스펙

```
보고서팀 방 (Report Team Room) — CANVAS_CONFIG 기준

캔버스 논리 해상도:  960 × 640 px
팀 방 크기:         260 × 150 px  (ROOM_W × ROOM_H)
방 위치 (y):        3번째 행 = (150 + 10) × 3 = 480px 시작

캐릭터 스프라이트:
  원본 크기:  32 × 48 px per frame  (가로 32 / 세로 48, 2:3 비율)
  시트 구성:  256 × 144 px  (가로 8프레임 × 32 / 세로 3행 × 48)
  scale:      2.0  →  화면 표시 64 × 96 px

  row 0  (공통):  idle 4f / typing 6f / reading 4f
  row 1  (공통):  writing 6f / walking 8f / celebrating 4f / error 2f
  row 2  (역할별):
    report_writer.png  →  report_writing 6f  (타이핑 + 문서 합치기)
    invest_memo.png    →  writing 6f         (차트 보며 타이핑)
    risk_note.png      →  risk_checking 4f   (경고 게이지 확인)
    report_editor.png  →  reviewing 6f       (빨간펜 교정)
                          summarizing 8f     (여러 문서 → 하나로)

가구/소품:
  책상·모니터:    32 × 32 px
  배달 서류:      16 × 16 px  (날아다니는 파티클)
  바닥 타일:      16 × 16 px
```

### 10.2 보고서팀 캐릭터 배치 (방 내부)

```
보고서팀 방  260 × 150 px  (padding 12px)
┌────────────────────────────────────────┐  y=480
│  [보고서팀] Report Team                 │
│                                        │
│  ┌────────┐  ┌────────┐  ┌────────┐    │
│  │ 📝     │  │ 📊     │  │ 📋     │    │
│  │64×96   │  │64×96   │  │64×96   │    │  ← 캐릭터 (scale 2.0)
│  │종합리포터│  │투자메모  │  │리스크노트│    │
│  └────────┘  └────────┘  └────────┘    │
│  x=32       x=112       x=192          │  ← x 간격: ~80px
│                                        │
│  ┌────────┐  ┌──────────────────────┐  │
│  │ 🧑‍💼    │  │ 최종 보고서           │  │
│  │64×96   │  │ 전송 대기중...        │  │
│  │편집장   │  └──────────────────────┘  │
│  └────────┘                            │
│  x=32                                  │
└────────────────────────────────────────┘  y=630
```

### 10.3 상태별 애니메이션 매핑

```
CharacterState          │ 스프라이트 row/프레임         │ 파티클 효과
────────────────────────┼──────────────────────────────┼─────────────────────────
IDLE                    │ row0: idle 4f (상하 진동 ±1px)│ 없음
WRITING (보고서 작성)    │ row2: report_writing 6f       │ 보라 문자 파티클 ↑
WRITING (투자 메모)      │ row1: writing 6f              │ 초록 ▲/빨간 ▼ 파티클
RISK_CHECKING           │ row2: risk_checking 4f        │ 주황 ⚠️ 파티클
REVIEWING               │ row2: reviewing 6f            │ 진보라 ✔ 체크 파티클
SUMMARIZING             │ row2: summarizing 8f          │ 보라 문서수렴 파티클
CELEBRATING             │ row1: celebrating 4f          │ 금색 ✓ 완료 파티클
ERROR                   │ row1: error 2f (좌우 흔들 ±2px)│ 빨간 ❗ 파티클
```

### 10.4 배달 경로 (픽셀 좌표)

```typescript
// office-view/delivery.ts

// 보고서팀으로 들어오는 배달 (각 팀 → 보고서팀)
const DELIVERY_ROUTES = {
  // 수집팀 출구 → 보고서팀 입구
  collection_to_report: {
    from: { x: 260, y: 75  },   // 수집팀 방 우측 중앙
    to:   { x: 260, y: 555 },   // 보고서팀 방 좌측 중앙 (y=480+75)
  },
  // 분석팀 출구 → 보고서팀 입구
  analysis_to_report: {
    from: { x: 260, y: 235 },
    to:   { x: 260, y: 555 },
  },
  // ML팀 출구 → 보고서팀 입구
  ml_to_report: {
    from: { x: 260, y: 395 },
    to:   { x: 260, y: 555 },
  },
  // 보고서팀 내부: 각 작성자 → 편집장
  writer_to_editor: {
    from: { x: 200, y: 540 },   // 리스크노트 작성자 우측
    to:   { x: 96,  y: 580 },   // 편집장 책상
    spriteSize: 16,              // 배달 서류 16×16px
  },
  // 편집장 → 텔레그램 (복도 우측으로 날아감)
  editor_to_telegram: {
    from: { x: 260, y: 580 },
    to:   { x: 960, y: 580 },   // 캔버스 우측 끝 (텔레그램 아이콘)
  },
} as const;
```

---

## 11. 이벤트 흐름

### 11.1 WebSocket 이벤트 시퀀스

```
[report.started]
  → agent_state: comprehensive_reporter = "summarizing"
  → agent_state: investment_memo_writer = "writing"
  → agent_state: risk_note_writer = "writing"

[report.progress] (comprehensive: 50%)
  → 종합 리포트 작성 진행률

[report.progress] (investment_memo: 80%)
  → 투자 메모 작성 진행률

[report.progress] (risk_note: 100%)
  → 리스크 노트 완료

[report.review]
  → agent_state: report_editor = "reviewing"
  → delivery: comprehensive_reporter → report_editor (comprehensive_report)
  → delivery: investment_memo_writer → report_editor (investment_memo)
  → delivery: risk_note_writer → report_editor (risk_note)

[report.approved]
  → agent_state: report_editor = "celebrating"

[report.completed]
  → delivery: report_editor → telegram (final_report)
  → notification: "텔레그램 전송 완료"
```

### 11.2 에러 시나리오

```
[report.quality_failed]
  → agent_state: report_editor = "error"
  → 편집장이 이슈를 수정하고 재검토
  → agent_state: report_editor = "reviewing" (재시도)
  → [report.approved] 또는 [report.completed] (에러 사항 포함 전송)
```
