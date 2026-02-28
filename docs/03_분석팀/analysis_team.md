# 03. 분석팀 (Data Science Team) 상세 설계

## 1. 팀 구성

### 1.1 조직도
```
분석팀장 (Data Science Lead)
│
├── EDA 에이전트 (Exploratory Data Analysis) ← NEW
│   ├── 기초통계량 & 분포 분석
│   ├── 시계열 분해 (STL Decomposition)
│   ├── 이상치 탐지 (IQR, Z-score, Isolation Forest)
│   ├── 정상성 검정 (ADF, KPSS)
│   └── 상관관계 히트맵 & 시각화
│
├── 피처 엔지니어링 에이전트 ← NEW
│   ├── 기술적 지표 피처 (RSI, MACD, BB 등 30+)
│   ├── 래깅/리드 피처 (1~20일)
│   ├── 롤링 통계 피처 (이동평균, 이동표준편차, skew, kurt)
│   ├── 펀더멘털 피처 (PER, PBR, ROE 등)
│   ├── 감성 피처 (뉴스/공시 NLP 점수)
│   ├── 시장 피처 (KOSPI 수익률, 환율, 금리)
│   └── 피처 선택 (상관분석, mutual information, feature importance)
│
├── 통계 분석 에이전트 ← NEW
│   ├── 회귀 분석 (OLS, Ridge, Lasso)
│   ├── 가설 검정 (t-test, Mann-Whitney, ANOVA)
│   ├── Granger 인과검정
│   ├── 공적분 검정 (Engle-Granger, Johansen)
│   └── 변동성 모델 (GARCH, EGARCH)
│
├── 감성 분석 에이전트 (NLP + LLM 하이브리드) ← UPGRADED
│   ├── TF-IDF + 감성 사전 기반 정량 분석
│   ├── LLM 기반 심층 감성 분석
│   ├── 감성 시계열 생성
│   └── 감성 점수 → ML 피처 변환
│
└── 섹터 분석 에이전트 ← UPGRADED
    ├── K-Means / DBSCAN 클러스터링
    ├── PCA / t-SNE 차원축소 시각화
    ├── 섹터 내 상대 강도 (통계적)
    └── 상관관계 네트워크 분석
```

### 1.2 기존 대비 변경 사항

```
Before (증권 분석)                    After (데이터 사이언스)
────────────────────                 ────────────────────────
RSI(14) = 58.3 → "중립"            RSI(14) = 58.3 → 피처 X_rsi_14에 저장
PER = 12.5 → "저평가"              PER z-score = -0.8 (업종 내 위치) → 피처
뉴스 → LLM "긍정적"                뉴스 → TF-IDF 벡터 + LLM 점수 → 감성 피처
없음                                ADF p=0.03 → "정상 시계열, 차분 불필요"
없음                                Granger p=0.01 → "환율이 주가에 인과"
없음                                피처 50개 생성 → 상관분석으로 30개 선택
```

---

## 2. EDA 에이전트 (Exploratory Data Analysis)

### 2.1 분석 항목

```python
# agents/analysis/eda.py

class EDAAgent(BaseAgent):
    """탐색적 데이터 분석 에이전트"""

    async def execute(self, task: Task) -> TaskResult:
        stock_code = task.params["stock_code"]
        df = task.params["price_df"]  # pandas DataFrame (date, open, high, low, close, volume)

        await self.update_status(AgentStatus.WORKING, f"{stock_code} EDA 수행 중")

        eda_result = {
            "descriptive_stats": self._descriptive_statistics(df),
            "distribution": self._distribution_analysis(df),
            "stationarity": self._stationarity_test(df),
            "decomposition": self._time_series_decomposition(df),
            "outliers": self._outlier_detection(df),
            "correlation": self._correlation_analysis(df),
            "autocorrelation": self._autocorrelation_analysis(df),
            "charts": [],  # 생성된 차트 경로 목록
        }

        # LLM으로 EDA 결과 해석
        eda_result["insights"] = await self._generate_insights(eda_result)

        # 차트 생성
        eda_result["charts"] = await self._generate_eda_charts(df, eda_result)

        return TaskResult(success=True, data=eda_result)

    def _descriptive_statistics(self, df: pd.DataFrame) -> dict:
        """기초통계량 분석"""
        returns = df["close"].pct_change().dropna()

        return {
            "price": {
                "mean": df["close"].mean(),
                "median": df["close"].median(),
                "std": df["close"].std(),
                "min": df["close"].min(),
                "max": df["close"].max(),
                "skewness": df["close"].skew(),
                "kurtosis": df["close"].kurtosis(),
            },
            "returns": {
                "mean_daily": returns.mean(),
                "std_daily": returns.std(),
                "annualized_return": returns.mean() * 252,
                "annualized_volatility": returns.std() * np.sqrt(252),
                "skewness": returns.skew(),
                "kurtosis": returns.kurtosis(),
                "sharpe_ratio": (returns.mean() * 252) / (returns.std() * np.sqrt(252)),
            },
            "volume": {
                "mean": df["volume"].mean(),
                "median": df["volume"].median(),
                "std": df["volume"].std(),
                "trend": "증가" if df["volume"].tail(20).mean() > df["volume"].mean() else "감소",
            },
        }

    def _distribution_analysis(self, df: pd.DataFrame) -> dict:
        """수익률 분포 분석"""
        from scipy import stats

        returns = df["close"].pct_change().dropna()

        # 정규성 검정
        shapiro_stat, shapiro_p = stats.shapiro(returns[-100:])  # 최근 100일
        jb_stat, jb_p = stats.jarque_bera(returns)

        return {
            "normality_test": {
                "shapiro": {"statistic": shapiro_stat, "p_value": shapiro_p,
                            "is_normal": shapiro_p > 0.05},
                "jarque_bera": {"statistic": jb_stat, "p_value": jb_p,
                                "is_normal": jb_p > 0.05},
            },
            "percentiles": {
                "1%": returns.quantile(0.01),
                "5%": returns.quantile(0.05),
                "25%": returns.quantile(0.25),
                "75%": returns.quantile(0.75),
                "95%": returns.quantile(0.95),
                "99%": returns.quantile(0.99),
            },
            "tail_risk": {
                "negative_days_pct": (returns < 0).mean(),
                "worst_day": returns.min(),
                "best_day": returns.max(),
                "var_95": returns.quantile(0.05),  # 95% VaR
            },
        }

    def _stationarity_test(self, df: pd.DataFrame) -> dict:
        """정상성 검정 (ADF, KPSS)"""
        from statsmodels.tsa.stattools import adfuller, kpss

        close = df["close"].dropna()
        returns = close.pct_change().dropna()

        # ADF 검정 (귀무가설: 단위근 존재 = 비정상)
        adf_price = adfuller(close)
        adf_returns = adfuller(returns)

        # KPSS 검정 (귀무가설: 정상 시계열)
        kpss_price = kpss(close, regression="ct")
        kpss_returns = kpss(returns, regression="ct")

        return {
            "price_series": {
                "adf": {"statistic": adf_price[0], "p_value": adf_price[1],
                        "is_stationary": adf_price[1] < 0.05},
                "kpss": {"statistic": kpss_price[0], "p_value": kpss_price[1],
                         "is_stationary": kpss_price[1] > 0.05},
                "conclusion": "비정상 (차분 필요)" if adf_price[1] > 0.05 else "정상",
            },
            "returns_series": {
                "adf": {"statistic": adf_returns[0], "p_value": adf_returns[1],
                        "is_stationary": adf_returns[1] < 0.05},
                "conclusion": "정상" if adf_returns[1] < 0.05 else "비정상",
            },
            "recommended_transform": "수익률(pct_change)" if adf_price[1] > 0.05 else "원본 사용 가능",
        }

    def _time_series_decomposition(self, df: pd.DataFrame) -> dict:
        """시계열 분해 (STL)"""
        from statsmodels.tsa.seasonal import STL

        close = df["close"].dropna()
        close.index = pd.DatetimeIndex(df["date"])

        stl = STL(close, period=5)  # 주간 계절성 (5거래일)
        result = stl.fit()

        return {
            "trend": {
                "direction": "상승" if result.trend.iloc[-1] > result.trend.iloc[-20] else "하락",
                "strength": float(1 - result.resid.var() / (result.trend + result.resid).var()),
            },
            "seasonality": {
                "strength": float(1 - result.resid.var() / (result.seasonal + result.resid).var()),
                "has_pattern": bool(1 - result.resid.var() / (result.seasonal + result.resid).var() > 0.3),
            },
            "residual": {
                "mean": float(result.resid.mean()),
                "std": float(result.resid.std()),
            },
        }

    def _outlier_detection(self, df: pd.DataFrame) -> dict:
        """이상치 탐지"""
        from sklearn.ensemble import IsolationForest

        returns = df["close"].pct_change().dropna()

        # 1. IQR 방식
        Q1 = returns.quantile(0.25)
        Q3 = returns.quantile(0.75)
        IQR = Q3 - Q1
        iqr_outliers = returns[(returns < Q1 - 1.5 * IQR) | (returns > Q3 + 1.5 * IQR)]

        # 2. Z-score 방식
        z_scores = (returns - returns.mean()) / returns.std()
        z_outliers = returns[abs(z_scores) > 3]

        # 3. Isolation Forest
        iso_forest = IsolationForest(contamination=0.05, random_state=42)
        labels = iso_forest.fit_predict(returns.values.reshape(-1, 1))
        iso_outliers = returns[labels == -1]

        return {
            "iqr_method": {
                "count": len(iqr_outliers),
                "dates": iqr_outliers.index.tolist()[-5:],  # 최근 5개
                "values": iqr_outliers.values.tolist()[-5:],
            },
            "zscore_method": {
                "count": len(z_outliers),
                "threshold": 3.0,
            },
            "isolation_forest": {
                "count": int((labels == -1).sum()),
                "contamination": 0.05,
            },
            "recommendation": "이상치가 분석에 영향을 줄 수 있으므로 Winsorization 권장"
                              if len(iqr_outliers) > 5 else "이상치 수준 정상",
        }

    def _correlation_analysis(self, df: pd.DataFrame) -> dict:
        """상관관계 분석"""
        # 가격, 거래량, 수익률 간 상관
        analysis_df = pd.DataFrame({
            "close": df["close"],
            "volume": df["volume"],
            "returns": df["close"].pct_change(),
            "log_returns": np.log(df["close"]).diff(),
            "volatility_20d": df["close"].pct_change().rolling(20).std(),
        }).dropna()

        corr_matrix = analysis_df.corr()

        return {
            "correlation_matrix": corr_matrix.to_dict(),
            "key_correlations": {
                "returns_volume": corr_matrix.loc["returns", "volume"],
                "returns_volatility": corr_matrix.loc["returns", "volatility_20d"],
                "volume_volatility": corr_matrix.loc["volume", "volatility_20d"],
            },
        }

    def _autocorrelation_analysis(self, df: pd.DataFrame) -> dict:
        """자기상관 분석 (ACF, PACF)"""
        from statsmodels.tsa.stattools import acf, pacf

        returns = df["close"].pct_change().dropna()

        acf_values = acf(returns, nlags=20)
        pacf_values = pacf(returns, nlags=20)

        # 유의미한 래그 식별
        confidence = 1.96 / np.sqrt(len(returns))
        significant_lags = [i for i, v in enumerate(acf_values[1:], 1) if abs(v) > confidence]

        return {
            "acf": acf_values[:10].tolist(),
            "pacf": pacf_values[:10].tolist(),
            "significant_lags": significant_lags,
            "has_autocorrelation": len(significant_lags) > 0,
            "suggested_ar_order": significant_lags[0] if significant_lags else 0,
        }

    async def _generate_insights(self, eda_result: dict) -> str:
        """LLM으로 EDA 결과 해석"""
        prompt = f"""
        다음 EDA 결과를 해석하여 주요 인사이트 3~5개를 도출해주세요.
        데이터 사이언티스트 관점에서, ML 모델링에 참고할 정보를 중심으로 작성해주세요.

        기초통계:
        - 연간 수익률: {eda_result['descriptive_stats']['returns']['annualized_return']:.2%}
        - 연간 변동성: {eda_result['descriptive_stats']['returns']['annualized_volatility']:.2%}
        - Sharpe Ratio: {eda_result['descriptive_stats']['returns']['sharpe_ratio']:.2f}
        - 수익률 왜도: {eda_result['descriptive_stats']['returns']['skewness']:.2f}
        - 수익률 첨도: {eda_result['descriptive_stats']['returns']['kurtosis']:.2f}

        정상성: {eda_result['stationarity']['price_series']['conclusion']}
        추세 방향: {eda_result['decomposition']['trend']['direction']}
        계절성 존재: {eda_result['decomposition']['seasonality']['has_pattern']}
        이상치 수(IQR): {eda_result['outliers']['iqr_method']['count']}개
        자기상관 존재: {eda_result['autocorrelation']['has_autocorrelation']}

        응답 형식: 번호 매긴 인사이트 리스트 (한국어)
        """

        return await llm_client.chat(prompt)

    async def _generate_eda_charts(self, df: pd.DataFrame, eda_result: dict) -> list[str]:
        """EDA 시각화 차트 생성"""
        import matplotlib.pyplot as plt
        import seaborn as sns
        matplotlib.use("Agg")

        charts = []

        # 1. 주가 + 거래량 차트
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), height_ratios=[3, 1])
        ax1.plot(df["date"], df["close"], label="종가")
        ax1.set_title("주가 추이")
        ax2.bar(df["date"], df["volume"], alpha=0.5)
        ax2.set_title("거래량")
        plt.tight_layout()
        path = f"/tmp/eda_price_volume.png"
        fig.savefig(path, dpi=100)
        charts.append(path)
        plt.close()

        # 2. 수익률 분포 히스토그램
        fig, ax = plt.subplots(figsize=(10, 6))
        returns = df["close"].pct_change().dropna()
        ax.hist(returns, bins=50, density=True, alpha=0.7, label="실제 분포")
        # 정규분포 오버레이
        from scipy.stats import norm
        x = np.linspace(returns.min(), returns.max(), 100)
        ax.plot(x, norm.pdf(x, returns.mean(), returns.std()), 'r-', label="정규분포")
        ax.set_title("수익률 분포")
        ax.legend()
        path = f"/tmp/eda_returns_dist.png"
        fig.savefig(path, dpi=100)
        charts.append(path)
        plt.close()

        # 3. ACF/PACF 차트
        from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        plot_acf(returns, ax=ax1, lags=20, title="ACF (자기상관)")
        plot_pacf(returns, ax=ax2, lags=20, title="PACF (편자기상관)")
        plt.tight_layout()
        path = f"/tmp/eda_acf_pacf.png"
        fig.savefig(path, dpi=100)
        charts.append(path)
        plt.close()

        return charts
```

---

## 3. 피처 엔지니어링 에이전트

### 3.1 피처 카테고리

```python
# agents/analysis/feature_engineer.py

class FeatureEngineerAgent(BaseAgent):
    """피처 엔지니어링 에이전트 - ML 모델 입력 피처 생성"""

    async def execute(self, task: Task) -> TaskResult:
        stock_code = task.params["stock_code"]
        df = task.params["price_df"]
        fundamental = task.params.get("fundamental", {})
        sentiment = task.params.get("sentiment_scores", [])
        market_data = task.params.get("market_data", {})

        await self.update_status(AgentStatus.WORKING, f"{stock_code} 피처 엔지니어링 중")

        # 1. 기술적 지표 피처
        df = self._add_technical_features(df)

        # 2. 래깅 피처
        df = self._add_lag_features(df)

        # 3. 롤링 통계 피처
        df = self._add_rolling_features(df)

        # 4. 펀더멘털 피처
        df = self._add_fundamental_features(df, fundamental)

        # 5. 감성 피처
        df = self._add_sentiment_features(df, sentiment)

        # 6. 시장 피처
        df = self._add_market_features(df, market_data)

        # 7. 타겟 변수 생성
        df = self._add_target_variables(df)

        # 8. 피처 선택
        selected_features, importance = self._select_features(df)

        # 9. 피처 스토어에 저장
        await self._save_to_feature_store(stock_code, df, selected_features)

        return TaskResult(success=True, data={
            "feature_df": df,
            "total_features": len([c for c in df.columns if c.startswith("f_")]),
            "selected_features": selected_features,
            "feature_importance": importance,
        })

    def _add_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 → ML 피처 변환"""
        import pandas_ta as ta

        # 이동평균
        for period in [5, 10, 20, 60, 120]:
            df[f"f_sma_{period}"] = ta.sma(df["close"], period)
            df[f"f_ema_{period}"] = ta.ema(df["close"], period)
            # 현재가 대비 이평선 괴리율 (더 유용한 피처)
            df[f"f_price_sma{period}_ratio"] = df["close"] / df[f"f_sma_{period}"]

        # 모멘텀 지표
        df["f_rsi_14"] = ta.rsi(df["close"], 14)
        df["f_rsi_7"] = ta.rsi(df["close"], 7)

        macd = ta.macd(df["close"], 12, 26, 9)
        df["f_macd"] = macd.iloc[:, 0]
        df["f_macd_signal"] = macd.iloc[:, 1]
        df["f_macd_hist"] = macd.iloc[:, 2]

        stoch = ta.stoch(df["high"], df["low"], df["close"], 14, 3)
        df["f_stoch_k"] = stoch.iloc[:, 0]
        df["f_stoch_d"] = stoch.iloc[:, 1]

        # 볼린저밴드
        bb = ta.bbands(df["close"], 20, 2)
        df["f_bb_upper"] = bb.iloc[:, 0]
        df["f_bb_mid"] = bb.iloc[:, 1]
        df["f_bb_lower"] = bb.iloc[:, 2]
        df["f_bb_width"] = (df["f_bb_upper"] - df["f_bb_lower"]) / df["f_bb_mid"]
        df["f_bb_position"] = (df["close"] - df["f_bb_lower"]) / (df["f_bb_upper"] - df["f_bb_lower"])

        # 변동성
        df["f_atr_14"] = ta.atr(df["high"], df["low"], df["close"], 14)
        df["f_atr_ratio"] = df["f_atr_14"] / df["close"]  # ATR을 가격 대비 비율로

        # 거래량
        df["f_obv"] = ta.obv(df["close"], df["volume"])
        df["f_volume_sma20_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

        # CCI, Williams %R, MFI
        df["f_cci_20"] = ta.cci(df["high"], df["low"], df["close"], 20)
        df["f_willr_14"] = ta.willr(df["high"], df["low"], df["close"], 14)
        df["f_mfi_14"] = ta.mfi(df["high"], df["low"], df["close"], df["volume"], 14)

        return df

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """래깅 피처 (과거 N일 데이터를 현재 행의 피처로)"""
        returns = df["close"].pct_change()

        for lag in [1, 2, 3, 5, 10, 20]:
            df[f"f_return_lag{lag}"] = returns.shift(lag)
            df[f"f_volume_lag{lag}"] = df["volume"].shift(lag)

        # 수익률 변화 방향 (이진 피처)
        for lag in [1, 2, 3, 5]:
            df[f"f_direction_lag{lag}"] = (returns.shift(lag) > 0).astype(int)

        return df

    def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """롤링 통계 피처"""
        returns = df["close"].pct_change()

        for window in [5, 10, 20, 60]:
            df[f"f_return_mean_{window}d"] = returns.rolling(window).mean()
            df[f"f_return_std_{window}d"] = returns.rolling(window).std()
            df[f"f_return_skew_{window}d"] = returns.rolling(window).skew()
            df[f"f_return_kurt_{window}d"] = returns.rolling(window).apply(
                lambda x: x.kurtosis(), raw=False
            )
            df[f"f_return_min_{window}d"] = returns.rolling(window).min()
            df[f"f_return_max_{window}d"] = returns.rolling(window).max()

            # 변동성 (실현 변동성)
            df[f"f_realized_vol_{window}d"] = returns.rolling(window).std() * np.sqrt(252)

        # 최고가/최저가 대비 현재가 위치
        for window in [20, 60, 120]:
            high_max = df["high"].rolling(window).max()
            low_min = df["low"].rolling(window).min()
            df[f"f_price_position_{window}d"] = (df["close"] - low_min) / (high_max - low_min)

        return df

    def _add_fundamental_features(self, df: pd.DataFrame, fundamental: dict) -> pd.DataFrame:
        """펀더멘털 피처"""
        if not fundamental:
            return df

        # 정적 피처 (변화가 느린 값) → 전체 행에 동일 값
        for key in ["per", "pbr", "roe", "roa", "debt_ratio", "operating_margin"]:
            if key in fundamental:
                df[f"f_fund_{key}"] = fundamental[key]

        # 동종업계 대비 z-score (섹터 내 상대적 위치)
        if "sector_stats" in fundamental:
            for key in ["per", "pbr", "roe"]:
                sector_mean = fundamental["sector_stats"].get(f"{key}_mean", 0)
                sector_std = fundamental["sector_stats"].get(f"{key}_std", 1)
                value = fundamental.get(key, 0)
                df[f"f_fund_{key}_zscore"] = (value - sector_mean) / sector_std if sector_std else 0

        return df

    def _add_sentiment_features(self, df: pd.DataFrame, sentiment: list) -> pd.DataFrame:
        """감성 피처 (뉴스/공시 감성 점수 → 시계열 피처)"""
        if not sentiment:
            df["f_sentiment_score"] = 0.0
            df["f_sentiment_ma5"] = 0.0
            return df

        # 감성 점수를 날짜별로 매핑
        sentiment_df = pd.DataFrame(sentiment)
        if "date" in sentiment_df.columns:
            sentiment_by_date = sentiment_df.groupby("date")["score"].mean()
            df["f_sentiment_score"] = df["date"].map(sentiment_by_date).fillna(0)
            df["f_sentiment_ma5"] = df["f_sentiment_score"].rolling(5).mean().fillna(0)
            df["f_sentiment_ma10"] = df["f_sentiment_score"].rolling(10).mean().fillna(0)
            df["f_sentiment_std5"] = df["f_sentiment_score"].rolling(5).std().fillna(0)

        return df

    def _add_market_features(self, df: pd.DataFrame, market_data: dict) -> pd.DataFrame:
        """시장 피처 (KOSPI, 환율, 금리 등)"""
        if not market_data:
            return df

        if "kospi" in market_data:
            kospi = pd.Series(market_data["kospi"])
            df["f_kospi_return"] = kospi.pct_change()
            df["f_kospi_return_ma5"] = df["f_kospi_return"].rolling(5).mean()

        if "usd_krw" in market_data:
            fx = pd.Series(market_data["usd_krw"])
            df["f_fx_return"] = fx.pct_change()

        if "us_10y_yield" in market_data:
            df["f_us_yield"] = pd.Series(market_data["us_10y_yield"])

        return df

    def _add_target_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """타겟 변수 생성"""
        returns = df["close"].pct_change()

        # 다음 날 수익률 (회귀 타겟)
        df["target_return_1d"] = returns.shift(-1)
        df["target_return_5d"] = df["close"].pct_change(5).shift(-5)

        # 다음 날 방향 (분류 타겟)
        df["target_direction_1d"] = (returns.shift(-1) > 0).astype(int)
        df["target_direction_5d"] = (df["close"].pct_change(5).shift(-5) > 0).astype(int)

        # 다음 날 종가 (가격 예측 타겟)
        df["target_price_1d"] = df["close"].shift(-1)
        df["target_price_5d"] = df["close"].shift(-5)

        return df

    def _select_features(self, df: pd.DataFrame) -> tuple[list[str], dict]:
        """피처 선택 (상관분석 + mutual information)"""
        from sklearn.feature_selection import mutual_info_regression

        feature_cols = [c for c in df.columns if c.startswith("f_")]
        target = "target_return_1d"

        # NaN 제거
        analysis_df = df[feature_cols + [target]].dropna()

        if len(analysis_df) < 30:
            return feature_cols, {}

        X = analysis_df[feature_cols]
        y = analysis_df[target]

        # 1. 상관관계 기반 (다중공선성 제거)
        corr_matrix = X.corr().abs()
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        to_drop = [col for col in upper.columns if any(upper[col] > 0.95)]

        # 2. Mutual Information
        mi_scores = mutual_info_regression(X.fillna(0), y, random_state=42)
        mi_importance = dict(zip(feature_cols, mi_scores))

        # 상위 피처 선택
        selected = [f for f in feature_cols if f not in to_drop]
        selected = sorted(selected, key=lambda f: mi_importance.get(f, 0), reverse=True)[:30]

        return selected, mi_importance
```

---

## 4. 통계 분석 에이전트

```python
# agents/analysis/statistical.py

class StatisticalAnalysisAgent(BaseAgent):
    """통계 분석 에이전트"""

    async def execute(self, task: Task) -> TaskResult:
        stock_code = task.params["stock_code"]
        df = task.params["price_df"]
        market_df = task.params.get("market_df")

        await self.update_status(AgentStatus.WORKING, f"{stock_code} 통계 분석 중")

        result = {
            "regression": self._regression_analysis(df),
            "granger_causality": self._granger_test(df, market_df),
            "cointegration": self._cointegration_test(df, market_df),
            "garch": self._garch_model(df),
            "hypothesis_tests": self._hypothesis_tests(df),
        }

        return TaskResult(success=True, data=result)

    def _regression_analysis(self, df: pd.DataFrame) -> dict:
        """회귀 분석"""
        import statsmodels.api as sm

        returns = df["close"].pct_change().dropna()
        volume_change = df["volume"].pct_change().dropna()

        # 거래량 변화 → 수익률 회귀
        X = sm.add_constant(volume_change.values[:len(returns)])
        y = returns.values[:len(volume_change)]

        try:
            model = sm.OLS(y, X).fit()
            return {
                "r_squared": model.rsquared,
                "adj_r_squared": model.rsquared_adj,
                "coefficients": model.params.tolist(),
                "p_values": model.pvalues.tolist(),
                "f_statistic": model.fvalue,
                "f_p_value": model.f_pvalue,
                "is_significant": model.f_pvalue < 0.05,
            }
        except Exception:
            return {"error": "회귀분석 실행 불가 (데이터 부족)"}

    def _granger_test(self, df: pd.DataFrame, market_df: pd.DataFrame = None) -> dict:
        """Granger 인과성 검정"""
        from statsmodels.tsa.stattools import grangercausalitytests

        if market_df is None:
            return {"skipped": "시장 데이터 없음"}

        returns = df["close"].pct_change().dropna()
        market_returns = market_df["close"].pct_change().dropna()

        # 길이 맞추기
        min_len = min(len(returns), len(market_returns))
        data = pd.DataFrame({
            "stock": returns.values[-min_len:],
            "market": market_returns.values[-min_len:],
        }).dropna()

        try:
            # 시장 → 종목 인과
            result_market_to_stock = grangercausalitytests(
                data[["stock", "market"]], maxlag=5, verbose=False
            )
            # 종목 → 시장 인과
            result_stock_to_market = grangercausalitytests(
                data[["market", "stock"]], maxlag=5, verbose=False
            )

            return {
                "market_causes_stock": {
                    f"lag_{lag}": {
                        "f_stat": test[0]["ssr_ftest"][0],
                        "p_value": test[0]["ssr_ftest"][1],
                        "is_causal": test[0]["ssr_ftest"][1] < 0.05,
                    }
                    for lag, test in result_market_to_stock.items()
                },
                "stock_causes_market": {
                    f"lag_{lag}": {
                        "f_stat": test[0]["ssr_ftest"][0],
                        "p_value": test[0]["ssr_ftest"][1],
                        "is_causal": test[0]["ssr_ftest"][1] < 0.05,
                    }
                    for lag, test in result_stock_to_market.items()
                },
            }
        except Exception as e:
            return {"error": str(e)}

    def _garch_model(self, df: pd.DataFrame) -> dict:
        """GARCH 변동성 모델"""
        from arch import arch_model

        returns = df["close"].pct_change().dropna() * 100  # 퍼센트 단위

        try:
            model = arch_model(returns, vol="Garch", p=1, q=1, dist="normal")
            result = model.fit(disp="off")

            # 향후 5일 변동성 예측
            forecast = result.forecast(horizon=5)
            predicted_vol = np.sqrt(forecast.variance.iloc[-1].values)

            return {
                "model": "GARCH(1,1)",
                "params": {
                    "omega": result.params.get("omega", 0),
                    "alpha": result.params.get("alpha[1]", 0),
                    "beta": result.params.get("beta[1]", 0),
                },
                "current_volatility": float(np.sqrt(result.conditional_volatility.iloc[-1])),
                "forecast_volatility_5d": predicted_vol.tolist(),
                "aic": result.aic,
                "bic": result.bic,
                "persistence": float(result.params.get("alpha[1]", 0) + result.params.get("beta[1]", 0)),
            }
        except Exception as e:
            return {"error": str(e)}

    def _hypothesis_tests(self, df: pd.DataFrame) -> dict:
        """가설 검정 모음"""
        from scipy import stats

        returns = df["close"].pct_change().dropna()
        recent_30 = returns.tail(30)
        previous_30 = returns.iloc[-60:-30]

        # 1. 최근 30일 평균 수익률이 0과 다른가? (one-sample t-test)
        t_stat, t_p = stats.ttest_1samp(recent_30, 0)

        # 2. 최근 30일 vs 이전 30일 평균 수익률 차이? (two-sample t-test)
        t2_stat, t2_p = stats.ttest_ind(recent_30, previous_30)

        # 3. 최근 변동성이 증가했는가? (F-test / Levene)
        lev_stat, lev_p = stats.levene(recent_30, previous_30)

        return {
            "mean_return_test": {
                "hypothesis": "최근 30일 평균 수익률 ≠ 0",
                "t_statistic": t_stat,
                "p_value": t_p,
                "significant": t_p < 0.05,
                "conclusion": f"평균 수익률이 {'0과 유의하게 다름' if t_p < 0.05 else '0과 유의한 차이 없음'}",
            },
            "period_comparison": {
                "hypothesis": "최근 30일 vs 이전 30일 수익률 차이",
                "t_statistic": t2_stat,
                "p_value": t2_p,
                "significant": t2_p < 0.05,
                "conclusion": f"두 기간 수익률이 {'유의하게 다름' if t2_p < 0.05 else '유의한 차이 없음'}",
            },
            "volatility_change": {
                "hypothesis": "최근 30일 변동성 변화",
                "levene_statistic": lev_stat,
                "p_value": lev_p,
                "significant": lev_p < 0.05,
                "recent_vol": recent_30.std(),
                "previous_vol": previous_30.std(),
                "conclusion": f"변동성이 {'유의하게 변화함' if lev_p < 0.05 else '유의한 변화 없음'}",
            },
        }
```

---

## 5. 감성 분석 에이전트 (NLP + LLM 하이브리드)

```python
# agents/analysis/sentiment.py

class SentimentAnalysisAgent(BaseAgent):
    """NLP + LLM 하이브리드 감성 분석 에이전트"""

    async def execute(self, task: Task) -> TaskResult:
        stock_code = task.params["stock_code"]
        news_data = task.params["news"]
        disclosures = task.params["disclosures"]

        await self.update_status(AgentStatus.WORKING, f"{stock_code} 감성 분석 중")

        # 1단계: TF-IDF 기반 정량 분석 (빠르고 저렴)
        tfidf_scores = self._tfidf_sentiment(news_data)

        # 2단계: LLM 기반 심층 분석 (상위 뉴스만, 비용 절약)
        top_news = sorted(news_data, key=lambda x: abs(x.get("relevance", 0)), reverse=True)[:5]
        llm_scores = await self._llm_sentiment(top_news)

        # 3단계: 공시 영향도 분석 (LLM)
        disclosure_impact = await self._llm_disclosure_impact(disclosures)

        # 4단계: 하이브리드 점수 생성 (ML 피처용)
        combined = self._combine_scores(tfidf_scores, llm_scores)

        # 5단계: 감성 시계열 생성
        sentiment_timeseries = self._build_sentiment_timeseries(news_data, combined)

        return TaskResult(success=True, data={
            "tfidf_scores": tfidf_scores,
            "llm_scores": llm_scores,
            "disclosure_impact": disclosure_impact,
            "combined_score": combined["average"],
            "sentiment_timeseries": sentiment_timeseries,  # 날짜별 감성 점수 → 피처로 사용
        })

    def _tfidf_sentiment(self, news: list[dict]) -> dict:
        """TF-IDF + 감성 사전 기반 분석"""
        from sklearn.feature_extraction.text import TfidfVectorizer

        # 한국어 금융 감성 사전
        positive_words = ["호실적", "신고가", "매수", "상향", "성장", "수주", "확대", "호조", "개선"]
        negative_words = ["적자", "하락", "매도", "하향", "감소", "부진", "악화", "리스크", "우려"]

        scores = []
        for article in news:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            pos_count = sum(1 for w in positive_words if w in text)
            neg_count = sum(1 for w in negative_words if w in text)
            total = pos_count + neg_count
            score = (pos_count - neg_count) / total if total > 0 else 0.0
            scores.append({"title": article.get("title"), "score": score, "method": "tfidf"})

        avg_score = np.mean([s["score"] for s in scores]) if scores else 0.0
        return {"articles": scores, "average": avg_score}

    def _combine_scores(self, tfidf: dict, llm: dict) -> dict:
        """TF-IDF와 LLM 감성 점수 앙상블"""
        tfidf_avg = tfidf.get("average", 0)
        llm_avg = llm.get("average_sentiment", 0)

        # 가중 평균 (LLM에 더 높은 가중치)
        combined = tfidf_avg * 0.3 + llm_avg * 0.7

        return {
            "tfidf_score": tfidf_avg,
            "llm_score": llm_avg,
            "average": combined,
            "method": "hybrid (TF-IDF 0.3 + LLM 0.7)",
        }

    def _build_sentiment_timeseries(self, news: list[dict], combined: dict) -> list[dict]:
        """날짜별 감성 시계열 구성 → 피처로 사용"""
        from collections import defaultdict

        daily_scores = defaultdict(list)
        for article in news:
            date = article.get("date", article.get("published_at", ""))[:10]
            score = article.get("sentiment_score", combined["average"])
            daily_scores[date].append(score)

        timeseries = [
            {"date": date, "score": np.mean(scores), "count": len(scores)}
            for date, scores in sorted(daily_scores.items())
        ]

        return timeseries
```

---

## 6. 섹터 분석 에이전트 (ML 강화)

```python
# agents/analysis/sector.py

class SectorAnalysisAgent(BaseAgent):
    """ML 기반 섹터 분석 에이전트"""

    async def execute(self, task: Task) -> TaskResult:
        sector = task.params["sector"]
        stocks_data = task.params["stocks_data"]

        await self.update_status(AgentStatus.WORKING, f"{sector} 섹터 분석 중")

        analysis = {
            "relative_strength": self._calculate_relative_strength(stocks_data),
            "clustering": self._cluster_stocks(stocks_data),
            "pca": self._pca_analysis(stocks_data),
            "correlation_network": self._correlation_network(stocks_data),
            "sector_momentum": self._sector_momentum(stocks_data),
        }

        return TaskResult(success=True, data=analysis)

    def _cluster_stocks(self, data: dict) -> dict:
        """K-Means 클러스터링으로 종목 그룹화"""
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler

        # 피처 매트릭스 구성
        features = []
        stock_names = []
        for code, stock in data.items():
            features.append([
                stock.get("return_1m", 0),
                stock.get("return_3m", 0),
                stock.get("volatility", 0),
                stock.get("volume_ratio", 0),
                stock.get("per", 0),
            ])
            stock_names.append(stock.get("name", code))

        X = StandardScaler().fit_transform(features)
        n_clusters = min(3, len(features))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(X)

        clusters = {}
        for name, label in zip(stock_names, labels):
            cluster_key = f"cluster_{label}"
            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append(name)

        return {
            "n_clusters": n_clusters,
            "clusters": clusters,
            "inertia": kmeans.inertia_,
            "method": "K-Means (수익률, 변동성, 거래량, PER 기반)",
        }

    def _pca_analysis(self, data: dict) -> dict:
        """PCA 차원축소 분석"""
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler

        features = []
        for code, stock in data.items():
            features.append([
                stock.get("return_1w", 0),
                stock.get("return_1m", 0),
                stock.get("return_3m", 0),
                stock.get("volatility", 0),
                stock.get("per", 0),
                stock.get("pbr", 0),
            ])

        if len(features) < 3:
            return {"skipped": "종목 수 부족"}

        X = StandardScaler().fit_transform(features)
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X)

        return {
            "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
            "total_explained": sum(pca.explained_variance_ratio_),
            "components": X_pca.tolist(),
            "feature_loadings": pca.components_.tolist(),
        }
```

---

## 7. 분석팀 매니저 (업데이트)

```python
class AnalysisManager:
    """분석팀 매니저 - 데이터 사이언스 워크플로우 조율"""

    def __init__(self):
        self.eda_agent = EDAAgent(agent_id="eda_analyst", name="EDA 분석가", team="analysis")
        self.feature_agent = FeatureEngineerAgent(agent_id="feature_engineer", name="피처 엔지니어", team="analysis")
        self.stats_agent = StatisticalAnalysisAgent(agent_id="statistical_analyst", name="통계 분석가", team="analysis")
        self.sentiment_agent = SentimentAnalysisAgent(agent_id="sentiment_analyst", name="감성 분석가", team="analysis")
        self.sector_agent = SectorAnalysisAgent(agent_id="sector_analyst", name="섹터 분석가", team="analysis")

    async def analyze_stock(self, stock_code: str, collected_data: dict) -> dict:
        """종목 종합 데이터 사이언스 분석"""

        # Phase 1: EDA + 감성 + 섹터 (병렬 - 서로 독립적)
        eda_result, sentiment_result, sector_result = await asyncio.gather(
            self.eda_agent.execute(Task(
                type="eda",
                params={"stock_code": stock_code, "price_df": collected_data["price_df"]}
            )),
            self.sentiment_agent.execute(Task(
                type="sentiment",
                params={"stock_code": stock_code, "news": collected_data["news"],
                        "disclosures": collected_data["disclosures"]}
            )),
            self.sector_agent.execute(Task(
                type="sector",
                params={"sector": collected_data["sector"], "stocks_data": collected_data["sector_data"]}
            )),
        )

        # Phase 2: 피처 엔지니어링 (감성 결과 필요)
        feature_result = await self.feature_agent.execute(Task(
            type="feature_engineering",
            params={
                "stock_code": stock_code,
                "price_df": collected_data["price_df"],
                "fundamental": collected_data.get("fundamental"),
                "sentiment_scores": sentiment_result.data["sentiment_timeseries"],
                "market_data": collected_data.get("market_data"),
            }
        ))

        # Phase 3: 통계 분석 (피처 결과 참조 가능)
        stats_result = await self.stats_agent.execute(Task(
            type="statistical",
            params={
                "stock_code": stock_code,
                "price_df": collected_data["price_df"],
                "market_df": collected_data.get("market_df"),
            }
        ))

        return {
            "eda": eda_result.data,
            "features": feature_result.data,
            "statistical": stats_result.data,
            "sentiment": sentiment_result.data,
            "sector": sector_result.data,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
```

---

## 8. 텔레그램 출력 포맷 (업데이트)

```
📊 삼성전자 (005930) 데이터 사이언스 분석 리포트

🔬 EDA 핵심 인사이트
━━━━━━━━━━━━━━━
• 연간 변동성: 28.5% (업종 평균 대비 높음)
• 수익률 분포: 정규분포 아님 (첨도 4.2, 음의 왜도)
• 추세: 상승 (20일 이평선 위)
• 이상치: 3건 탐지 (최근 30일)
• 자기상관: lag-1 유의 → AR(1) 모델 적합

🔧 피처 엔지니어링
━━━━━━━━━━━━━━━
• 생성 피처: 52개
• 선택 피처: 30개 (MI 기반)
• 상위 피처: RSI(14), 20일 변동성, 감성점수, BB포지션

📐 통계 분석
━━━━━━━━━━━━━━━
• Granger 인과: KOSPI → 삼성전자 (p=0.02, lag-2)
• GARCH(1,1): 현재 변동성 2.1%, 지속성 0.95
• 가설검정: 최근 30일 수익률 ≠ 0 (p=0.03)

📰 감성 분석 (하이브리드)
━━━━━━━━━━━━━━━
• 종합 감성: +0.42 (TF-IDF: +0.35, LLM: +0.45)
• 긍정: HBM 수주 확대, AI 반도체 수요
• 부정: 메모리 가격 조정 우려

→ 피처 데이터가 예측팀(ML)에 전달됩니다...
```

## 9. 웹 시각화 연동 (업데이트)

```
상태              │ 애니메이션              │ 설명
──────────────────┼───────────────────────┼──────────────
대기중            │ 노트북 앞 대기          │ idle 상태
EDA 수행 중       │ 차트 그리기 + 돋보기     │ 데이터 탐색
                  │ + 히스토그램 파티클      │
피처 생성 중      │ 톱니바퀴 회전 + 데이터 흐름│ 피처 엔지니어링
통계 분석 중      │ 수식 파티클 + 그래프     │ 가설 검정
감성 분석 중      │ 뉴스 읽기 + 이모지 파티클 │ NLP + LLM
클러스터링 중     │ 점들이 모이는 애니메이션  │ 섹터 분석
분석 완료         │ 피처 테이블 + ✓         │ 결과 정리
전달              │ 예측팀에 피처 데이터 전달  │ 서류 배달 이동
```
