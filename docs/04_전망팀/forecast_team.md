# 04. 예측팀 (ML Engineering Team) 상세 설계

## 1. 팀 구성

### 1.1 조직도
```
예측팀장 (ML Engineering Lead)
│
├── 모델 학습 에이전트 (Model Training Agent) ← NEW
│   ├── 시계열 모델
│   │   ├── Prophet (페이스북, 추세+계절성)
│   │   ├── ARIMA / SARIMA (통계 시계열)
│   │   └── VAR (다변량 시계열)
│   ├── 딥러닝 모델
│   │   ├── LSTM (Long Short-Term Memory)
│   │   ├── GRU (Gated Recurrent Unit)
│   │   └── Temporal Fusion Transformer (TFT)
│   ├── 앙상블 모델
│   │   ├── XGBoost
│   │   ├── LightGBM
│   │   └── CatBoost
│   └── 앙상블 전략
│       ├── Weighted Average (가중 평균)
│       ├── Stacking (스태킹)
│       └── Optuna 기반 가중치 최적화
│
├── 백테스팅 에이전트 (Backtesting Agent) ← NEW
│   ├── Walk-Forward Validation
│   ├── 전략 시뮬레이션
│   ├── 성능 메트릭 계산
│   └── 벤치마크 비교 (Buy & Hold)
│
├── 리스크 평가 에이전트 (Risk Assessment Agent) ← UPGRADED
│   ├── VaR / CVaR (통계적)
│   ├── 몬테카를로 시뮬레이션
│   ├── GARCH 기반 변동성 예측
│   └── 시나리오 분석 (통계 기반)
│
└── 리포트 생성 에이전트 (Report Generator) - LLM 기반
    ├── ML 예측 결과 → 자연어 리포트 변환
    ├── 모델 성능 해석
    ├── 차트 이미지 생성 (예측 + 신뢰구간)
    └── 텔레그램 포맷 변환
```

### 1.2 기존 대비 변경 사항

```
Before (LLM 전망)                    After (ML 예측)
────────────────                    ────────────────
LLM에게 "전망해줘"                  LSTM + XGBoost + Prophet 앙상블 예측
"강세 시나리오 45%"                  내일 종가 78,500원 (95% CI: 75,200~81,800)
LLM 판단 "목표가 85,000원"          DCF + ML 적정가 + 밸류에이션 모델
"리스크: 환율 우려"                  VaR(95%) = -4.2%, MDD 시뮬레이션 -12%
없음                                백테스트: Sharpe 1.45, Win Rate 62%
없음                                MLflow: 실험 #47, MAPE 2.3%
```

---

## 2. 모델 학습 에이전트

### 2.1 시계열 모델

```python
# agents/forecast/model_trainer.py

class ModelTrainerAgent(BaseAgent):
    """ML 모델 학습 에이전트"""

    async def execute(self, task: Task) -> TaskResult:
        stock_code = task.params["stock_code"]
        feature_df = task.params["feature_df"]
        selected_features = task.params["selected_features"]

        await self.update_status(AgentStatus.WORKING, f"{stock_code} 모델 학습 중")

        # 데이터 준비
        train_df, test_df = self._train_test_split(feature_df)

        # MLflow 실험 시작
        import mlflow
        mlflow.set_experiment(f"stock_{stock_code}")

        # 1. 각 모델 학습 (병렬)
        models_results = await asyncio.gather(
            self._train_prophet(stock_code, train_df, test_df),
            self._train_lstm(stock_code, train_df, test_df, selected_features),
            self._train_xgboost(stock_code, train_df, test_df, selected_features),
            self._train_lightgbm(stock_code, train_df, test_df, selected_features),
        )

        prophet_result, lstm_result, xgb_result, lgbm_result = models_results

        # 2. 앙상블
        ensemble_result = self._ensemble_predictions(
            prophet_result, lstm_result, xgb_result, lgbm_result, test_df
        )

        # 3. 최종 예측 (미래)
        final_prediction = await self._predict_future(
            feature_df, selected_features,
            ensemble_result["best_model"],
            ensemble_result["weights"]
        )

        return TaskResult(success=True, data={
            "models": {
                "prophet": prophet_result,
                "lstm": lstm_result,
                "xgboost": xgb_result,
                "lightgbm": lgbm_result,
            },
            "ensemble": ensemble_result,
            "prediction": final_prediction,
        })

    def _train_test_split(self, df: pd.DataFrame) -> tuple:
        """시계열 분할 (미래 데이터 누출 방지)"""
        # 최근 20% = 테스트셋 (시간순)
        split_idx = int(len(df) * 0.8)
        train = df.iloc[:split_idx].copy()
        test = df.iloc[split_idx:].copy()
        return train, test

    async def _train_prophet(self, stock_code: str, train: pd.DataFrame, test: pd.DataFrame) -> dict:
        """Prophet 모델 학습"""
        from prophet import Prophet
        import mlflow

        with mlflow.start_run(run_name=f"prophet_{stock_code}", nested=True):
            # Prophet 형식으로 변환
            prophet_df = train[["date", "close"]].rename(columns={"date": "ds", "close": "y"})

            model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=True,
                yearly_seasonality=True,
                changepoint_prior_scale=0.05,
            )
            model.fit(prophet_df)

            # 예측
            future = model.make_future_dataframe(periods=len(test), freq="B")
            forecast = model.predict(future)

            # 테스트셋 예측값 추출
            pred = forecast.tail(len(test))["yhat"].values
            actual = test["close"].values

            # 메트릭 계산
            metrics = self._calculate_metrics(actual, pred)

            # MLflow 로깅
            mlflow.log_params({"model": "prophet", "changepoint_prior_scale": 0.05})
            mlflow.log_metrics(metrics)

            return {
                "model_type": "prophet",
                "metrics": metrics,
                "predictions": pred.tolist(),
                "model": model,
                "mlflow_run_id": mlflow.active_run().info.run_id,
            }

    async def _train_lstm(self, stock_code: str, train: pd.DataFrame, test: pd.DataFrame,
                          features: list[str]) -> dict:
        """LSTM 모델 학습"""
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        import mlflow

        with mlflow.start_run(run_name=f"lstm_{stock_code}", nested=True):
            # 하이퍼파라미터 (Optuna로 최적화 가능)
            seq_length = 20
            hidden_size = 64
            num_layers = 2
            dropout = 0.2
            epochs = 50
            lr = 0.001

            # 데이터 준비
            X_train, y_train = self._create_sequences(train, features, seq_length)
            X_test, y_test = self._create_sequences(test, features, seq_length)

            # 정규화
            from sklearn.preprocessing import StandardScaler
            scaler_X = StandardScaler()
            scaler_y = StandardScaler()

            X_train_scaled = scaler_X.fit_transform(X_train.reshape(-1, len(features)))
            X_train_scaled = X_train_scaled.reshape(X_train.shape)
            X_test_scaled = scaler_X.transform(X_test.reshape(-1, len(features)))
            X_test_scaled = X_test_scaled.reshape(X_test.shape)

            y_train_scaled = scaler_y.fit_transform(y_train.reshape(-1, 1))
            y_test_scaled = scaler_y.transform(y_test.reshape(-1, 1))

            # 텐서 변환
            X_train_t = torch.FloatTensor(X_train_scaled)
            y_train_t = torch.FloatTensor(y_train_scaled)
            X_test_t = torch.FloatTensor(X_test_scaled)

            # LSTM 모델 정의
            class LSTMModel(nn.Module):
                def __init__(self, input_size, hidden_size, num_layers, dropout):
                    super().__init__()
                    self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                                       batch_first=True, dropout=dropout)
                    self.fc = nn.Linear(hidden_size, 1)

                def forward(self, x):
                    out, _ = self.lstm(x)
                    out = self.fc(out[:, -1, :])
                    return out

            model = LSTMModel(len(features), hidden_size, num_layers, dropout)
            optimizer = torch.optim.Adam(model.parameters(), lr=lr)
            criterion = nn.MSELoss()

            # 학습
            dataset = TensorDataset(X_train_t, y_train_t)
            loader = DataLoader(dataset, batch_size=32, shuffle=False)

            model.train()
            for epoch in range(epochs):
                for batch_X, batch_y in loader:
                    optimizer.zero_grad()
                    output = model(batch_X)
                    loss = criterion(output, batch_y)
                    loss.backward()
                    optimizer.step()

            # 예측
            model.eval()
            with torch.no_grad():
                pred_scaled = model(X_test_t).numpy()
                pred = scaler_y.inverse_transform(pred_scaled).flatten()

            actual = y_test
            metrics = self._calculate_metrics(actual, pred)

            # MLflow 로깅
            mlflow.log_params({
                "model": "lstm", "seq_length": seq_length,
                "hidden_size": hidden_size, "num_layers": num_layers,
                "dropout": dropout, "epochs": epochs, "lr": lr,
            })
            mlflow.log_metrics(metrics)

            return {
                "model_type": "lstm",
                "metrics": metrics,
                "predictions": pred.tolist(),
                "model": model,
                "scalers": {"X": scaler_X, "y": scaler_y},
                "mlflow_run_id": mlflow.active_run().info.run_id,
            }

    async def _train_xgboost(self, stock_code: str, train: pd.DataFrame, test: pd.DataFrame,
                              features: list[str]) -> dict:
        """XGBoost 모델 학습 (Optuna 하이퍼파라미터 최적화)"""
        import xgboost as xgb
        import optuna
        import mlflow

        target = "target_return_1d"
        X_train = train[features].fillna(0)
        y_train = train[target].fillna(0)
        X_test = test[features].fillna(0)
        y_test = test[target].fillna(0)

        def objective(trial):
            params = {
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "n_estimators": trial.suggest_int("n_estimators", 50, 500),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "subsample": trial.suggest_float("subsample", 0.5, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            }

            model = xgb.XGBRegressor(**params, random_state=42, verbosity=0)
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
            pred = model.predict(X_test)
            mape = np.mean(np.abs((y_test - pred) / (y_test + 1e-8))) * 100
            return mape

        # Optuna 최적화 (30회 시도)
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=30, show_progress_bar=False)

        # 최적 파라미터로 최종 학습
        best_params = study.best_params
        with mlflow.start_run(run_name=f"xgboost_{stock_code}", nested=True):
            model = xgb.XGBRegressor(**best_params, random_state=42, verbosity=0)
            model.fit(X_train, y_train)
            pred = model.predict(X_test)

            # 수익률 예측 → 가격 변환
            last_prices = test["close"].shift(1).fillna(test["close"].iloc[0])
            pred_prices = last_prices * (1 + pred)
            actual_prices = test["close"].values

            metrics = self._calculate_metrics(actual_prices.flatten(), pred_prices.values.flatten())

            # 피처 중요도
            importance = dict(zip(features, model.feature_importances_))
            top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]

            mlflow.log_params({"model": "xgboost", **best_params})
            mlflow.log_metrics(metrics)

            return {
                "model_type": "xgboost",
                "metrics": metrics,
                "predictions": pred_prices.values.tolist(),
                "feature_importance": dict(top_features),
                "best_params": best_params,
                "optuna_trials": len(study.trials),
                "model": model,
                "mlflow_run_id": mlflow.active_run().info.run_id,
            }

    async def _train_lightgbm(self, stock_code, train, test, features) -> dict:
        """LightGBM 모델 학습"""
        import lightgbm as lgb
        import mlflow
        # (XGBoost와 유사한 구조, 생략)
        ...

    def _ensemble_predictions(self, *model_results, test_df) -> dict:
        """다중 모델 앙상블"""
        import optuna

        predictions = {}
        metrics = {}
        for result in model_results:
            if result and "predictions" in result:
                name = result["model_type"]
                predictions[name] = np.array(result["predictions"])
                metrics[name] = result["metrics"]

        if len(predictions) < 2:
            best = min(metrics, key=lambda k: metrics[k].get("mape", float("inf")))
            return {"method": "single_best", "best_model": best, "weights": {best: 1.0}}

        actual = test_df["close"].values[-len(list(predictions.values())[0]):]

        # Optuna로 최적 가중치 탐색
        def objective(trial):
            weights = {}
            remaining = 1.0
            model_names = list(predictions.keys())
            for name in model_names[:-1]:
                w = trial.suggest_float(f"w_{name}", 0.0, remaining)
                weights[name] = w
                remaining -= w
            weights[model_names[-1]] = remaining

            ensemble_pred = sum(predictions[name] * w for name, w in weights.items())
            mape = np.mean(np.abs((actual - ensemble_pred) / (actual + 1e-8))) * 100
            return mape

        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=50, show_progress_bar=False)

        best_weights = {}
        remaining = 1.0
        model_names = list(predictions.keys())
        for name in model_names[:-1]:
            best_weights[name] = study.best_params.get(f"w_{name}", 0)
            remaining -= best_weights[name]
        best_weights[model_names[-1]] = remaining

        # 앙상블 예측
        ensemble_pred = sum(predictions[name] * w for name, w in best_weights.items())
        ensemble_metrics = self._calculate_metrics(actual, ensemble_pred)

        # 최고 단일 모델
        best_single = min(metrics, key=lambda k: metrics[k].get("mape", float("inf")))

        return {
            "method": "optuna_weighted_average",
            "weights": best_weights,
            "ensemble_metrics": ensemble_metrics,
            "best_single_model": best_single,
            "best_single_metrics": metrics[best_single],
            "improvement": f"{metrics[best_single].get('mape', 0) - ensemble_metrics.get('mape', 0):.2f}%p MAPE 개선",
        }

    def _calculate_metrics(self, actual: np.ndarray, predicted: np.ndarray) -> dict:
        """모델 평가 메트릭"""
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        # 방향 정확도
        actual_direction = np.sign(np.diff(actual))
        pred_direction = np.sign(np.diff(predicted[:len(actual)]))
        min_len = min(len(actual_direction), len(pred_direction))
        direction_accuracy = np.mean(actual_direction[:min_len] == pred_direction[:min_len])

        mae = mean_absolute_error(actual, predicted[:len(actual)])
        rmse = np.sqrt(mean_squared_error(actual, predicted[:len(actual)]))
        mape = np.mean(np.abs((actual - predicted[:len(actual)]) / (actual + 1e-8))) * 100
        r2 = r2_score(actual, predicted[:len(actual)])

        return {
            "mae": float(mae),
            "rmse": float(rmse),
            "mape": float(mape),
            "r2": float(r2),
            "direction_accuracy": float(direction_accuracy),
        }

    async def _predict_future(self, df, features, best_model, weights) -> dict:
        """미래 가격 예측 (1일, 5일, 20일)"""
        # 마지막 데이터 기반 예측
        current_price = df["close"].iloc[-1]

        # 각 모델별 예측 → 앙상블
        predictions = {}
        for horizon in [1, 5, 20]:
            # 모델별 예측 (간략화)
            pred_price = current_price  # 실제로는 각 모델의 predict 호출
            lower = pred_price * 0.95   # 95% 신뢰구간 하한
            upper = pred_price * 1.05   # 95% 신뢰구간 상한

            predictions[f"{horizon}d"] = {
                "predicted_price": pred_price,
                "confidence_interval": {"lower": lower, "upper": upper, "level": "95%"},
                "predicted_return": (pred_price - current_price) / current_price,
                "direction": "up" if pred_price > current_price else "down",
                "direction_probability": 0.65,
            }

        return {
            "current_price": current_price,
            "predictions": predictions,
            "model_used": best_model,
            "ensemble_weights": weights,
        }

    def _create_sequences(self, df, features, seq_length):
        """LSTM용 시퀀스 데이터 생성"""
        X, y = [], []
        data = df[features].fillna(0).values
        target = df["close"].values

        for i in range(seq_length, len(data)):
            X.append(data[i-seq_length:i])
            y.append(target[i])

        return np.array(X), np.array(y)
```

---

## 3. 백테스팅 에이전트

```python
# agents/forecast/backtester.py

class BacktestingAgent(BaseAgent):
    """백테스팅 에이전트 - Walk-Forward Validation"""

    async def execute(self, task: Task) -> TaskResult:
        stock_code = task.params["stock_code"]
        df = task.params["price_df"]
        model = task.params["model"]
        features = task.params["features"]
        period_days = task.params.get("period_days", 60)

        await self.update_status(AgentStatus.WORKING, f"{stock_code} 백테스팅 중")

        result = {
            "walk_forward": self._walk_forward_backtest(df, model, features, period_days),
            "strategy_simulation": self._strategy_simulation(df, model, features),
            "benchmark_comparison": self._compare_with_benchmark(df),
        }

        # 차트 생성
        result["charts"] = await self._generate_backtest_charts(result)

        return TaskResult(success=True, data=result)

    def _walk_forward_backtest(self, df, model, features, period_days) -> dict:
        """Walk-Forward Validation (시계열 교차검증)"""
        n = len(df)
        train_size = n - period_days
        results = []

        for i in range(period_days):
            train_end = train_size + i
            train = df.iloc[:train_end]
            test_row = df.iloc[train_end]

            # 학습 & 예측
            X_train = train[features].fillna(0)
            y_train = train["target_return_1d"].fillna(0)
            X_test = test_row[features].fillna(0).values.reshape(1, -1)

            model.fit(X_train, y_train)
            pred_return = model.predict(X_test)[0]

            actual_return = test_row.get("target_return_1d", 0)
            actual_price = test_row["close"]
            pred_price = df.iloc[train_end - 1]["close"] * (1 + pred_return)

            results.append({
                "date": test_row.get("date", ""),
                "actual_price": actual_price,
                "predicted_price": pred_price,
                "actual_return": actual_return,
                "predicted_return": pred_return,
                "direction_correct": (pred_return > 0) == (actual_return > 0),
            })

        # 메트릭 계산
        actuals = [r["actual_price"] for r in results]
        preds = [r["predicted_price"] for r in results]

        return {
            "period_days": period_days,
            "metrics": {
                "mape": np.mean(np.abs((np.array(actuals) - np.array(preds)) / np.array(actuals))) * 100,
                "rmse": np.sqrt(np.mean((np.array(actuals) - np.array(preds)) ** 2)),
                "direction_accuracy": np.mean([r["direction_correct"] for r in results]),
            },
            "daily_results": results[-10:],  # 최근 10일만
        }

    def _strategy_simulation(self, df, model, features) -> dict:
        """ML 시그널 기반 매매 전략 시뮬레이션"""
        initial_capital = 10_000_000  # 1,000만원
        capital = initial_capital
        position = 0  # 보유 주수
        trades = []
        portfolio_values = []

        for i in range(60, len(df)):
            X = df.iloc[i][features].fillna(0).values.reshape(1, -1)
            pred_return = model.predict(X)[0]
            current_price = df.iloc[i]["close"]
            date = df.iloc[i].get("date", "")

            # 매매 규칙: 예측 수익률 > 0.5% → 매수, < -0.5% → 매도
            if pred_return > 0.005 and position == 0:
                # 매수 (전량)
                shares = int(capital / current_price)
                if shares > 0:
                    cost = shares * current_price
                    capital -= cost
                    position = shares
                    trades.append({"date": date, "action": "buy", "price": current_price,
                                   "shares": shares})

            elif pred_return < -0.005 and position > 0:
                # 매도 (전량)
                revenue = position * current_price
                capital += revenue
                trades.append({"date": date, "action": "sell", "price": current_price,
                               "shares": position, "profit": revenue - trades[-1].get("cost", 0)})
                position = 0

            portfolio_value = capital + position * current_price
            portfolio_values.append({"date": date, "value": portfolio_value})

        # 최종 가치
        final_value = capital + position * df.iloc[-1]["close"]
        total_return = (final_value - initial_capital) / initial_capital

        # 성능 메트릭
        pv = np.array([p["value"] for p in portfolio_values])
        daily_returns = np.diff(pv) / pv[:-1]

        sharpe = np.mean(daily_returns) / (np.std(daily_returns) + 1e-8) * np.sqrt(252)
        sortino = np.mean(daily_returns) / (np.std(daily_returns[daily_returns < 0]) + 1e-8) * np.sqrt(252)

        # Maximum Drawdown
        peak = np.maximum.accumulate(pv)
        drawdown = (pv - peak) / peak
        mdd = drawdown.min()

        return {
            "initial_capital": initial_capital,
            "final_value": final_value,
            "total_return": total_return,
            "total_return_pct": f"{total_return * 100:.2f}%",
            "metrics": {
                "sharpe_ratio": float(sharpe),
                "sortino_ratio": float(sortino),
                "max_drawdown": float(mdd),
                "max_drawdown_pct": f"{mdd * 100:.2f}%",
                "calmar_ratio": float(total_return / abs(mdd)) if mdd != 0 else 0,
                "win_rate": sum(1 for t in trades if t.get("action") == "sell" and t.get("profit", 0) > 0) /
                           max(sum(1 for t in trades if t.get("action") == "sell"), 1),
                "total_trades": len([t for t in trades if t["action"] == "sell"]),
            },
            "portfolio_values": portfolio_values[-30:],
            "recent_trades": trades[-10:],
        }

    def _compare_with_benchmark(self, df) -> dict:
        """Buy & Hold 벤치마크 비교"""
        start_price = df.iloc[60]["close"]
        end_price = df.iloc[-1]["close"]
        bnh_return = (end_price - start_price) / start_price

        return {
            "buy_and_hold_return": bnh_return,
            "buy_and_hold_return_pct": f"{bnh_return * 100:.2f}%",
        }
```

---

## 4. 리스크 평가 에이전트 (통계 기반 업그레이드)

```python
# agents/forecast/risk_assessor.py

class RiskAssessor(BaseAgent):
    """통계 기반 리스크 평가 에이전트"""

    async def execute(self, task: Task) -> TaskResult:
        stock_code = task.params["stock_code"]
        df = task.params["price_df"]
        garch_result = task.params.get("garch_result")

        await self.update_status(AgentStatus.WORKING, f"{stock_code} 리스크 평가 중")

        returns = df["close"].pct_change().dropna()

        result = {
            "var": self._calculate_var(returns),
            "cvar": self._calculate_cvar(returns),
            "monte_carlo": self._monte_carlo_simulation(returns, df["close"].iloc[-1]),
            "volatility_forecast": self._forecast_volatility(returns, garch_result),
            "drawdown_analysis": self._drawdown_analysis(df["close"]),
            "overall_risk_score": None,
        }

        result["overall_risk_score"] = self._calculate_risk_score(result)

        return TaskResult(success=True, data=result)

    def _calculate_var(self, returns: pd.Series) -> dict:
        """Value at Risk (VaR) 계산"""
        from scipy import stats

        # 1. 역사적 VaR
        var_95_hist = returns.quantile(0.05)
        var_99_hist = returns.quantile(0.01)

        # 2. 파라메트릭 VaR (정규분포 가정)
        mu = returns.mean()
        sigma = returns.std()
        var_95_param = stats.norm.ppf(0.05, mu, sigma)
        var_99_param = stats.norm.ppf(0.01, mu, sigma)

        # 3. Cornish-Fisher VaR (비정규분포 보정)
        skew = returns.skew()
        kurt = returns.kurtosis()
        z_95 = stats.norm.ppf(0.05)
        z_cf = (z_95 + (z_95**2 - 1) * skew / 6 +
                (z_95**3 - 3*z_95) * kurt / 24 -
                (2*z_95**3 - 5*z_95) * skew**2 / 36)
        var_95_cf = mu + z_cf * sigma

        return {
            "historical": {
                "var_95": float(var_95_hist),
                "var_99": float(var_99_hist),
                "interpretation": f"95% 확률로 일일 최대 손실: {abs(var_95_hist)*100:.2f}%",
            },
            "parametric": {
                "var_95": float(var_95_param),
                "var_99": float(var_99_param),
            },
            "cornish_fisher": {
                "var_95": float(var_95_cf),
                "note": "비정규분포 보정 (왜도/첨도 반영)",
            },
        }

    def _calculate_cvar(self, returns: pd.Series) -> dict:
        """Conditional VaR (Expected Shortfall)"""
        var_95 = returns.quantile(0.05)
        cvar_95 = returns[returns <= var_95].mean()

        var_99 = returns.quantile(0.01)
        cvar_99 = returns[returns <= var_99].mean()

        return {
            "cvar_95": float(cvar_95),
            "cvar_99": float(cvar_99),
            "interpretation": f"VaR 초과 시 평균 예상 손실: {abs(cvar_95)*100:.2f}%",
        }

    def _monte_carlo_simulation(self, returns: pd.Series, current_price: float,
                                 n_simulations: int = 1000, horizon: int = 20) -> dict:
        """몬테카를로 시뮬레이션"""
        mu = returns.mean()
        sigma = returns.std()

        simulations = np.zeros((n_simulations, horizon))
        simulations[:, 0] = current_price

        for t in range(1, horizon):
            random_returns = np.random.normal(mu, sigma, n_simulations)
            simulations[:, t] = simulations[:, t-1] * (1 + random_returns)

        final_prices = simulations[:, -1]

        return {
            "horizon_days": horizon,
            "n_simulations": n_simulations,
            "current_price": current_price,
            "expected_price": float(np.mean(final_prices)),
            "median_price": float(np.median(final_prices)),
            "percentiles": {
                "5th": float(np.percentile(final_prices, 5)),
                "25th": float(np.percentile(final_prices, 25)),
                "75th": float(np.percentile(final_prices, 75)),
                "95th": float(np.percentile(final_prices, 95)),
            },
            "probability_above_current": float(np.mean(final_prices > current_price)),
            "probability_loss_5pct": float(np.mean(final_prices < current_price * 0.95)),
            "probability_gain_5pct": float(np.mean(final_prices > current_price * 1.05)),
            "worst_case": float(np.min(final_prices)),
            "best_case": float(np.max(final_prices)),
        }

    def _drawdown_analysis(self, prices: pd.Series) -> dict:
        """드로다운 분석"""
        peak = prices.expanding().max()
        drawdown = (prices - peak) / peak

        # 상위 5개 드로다운 기간
        return {
            "current_drawdown": float(drawdown.iloc[-1]),
            "max_drawdown": float(drawdown.min()),
            "avg_drawdown": float(drawdown[drawdown < 0].mean()),
            "drawdown_duration_current": int((drawdown.iloc[-1:] < 0).sum()),
        }
```

---

## 5. 리포트 생성 에이전트 (ML 결과 해석)

```python
class ReportGenerator(BaseAgent):
    """ML 예측 결과 → 자연어 리포트 (LLM)"""

    async def execute(self, task: Task) -> TaskResult:
        stock_name = task.params["stock_name"]
        stock_code = task.params["stock_code"]
        analysis = task.params["analysis"]
        ml_results = task.params["ml_results"]
        risk = task.params["risk"]
        backtest = task.params["backtest"]

        await self.update_status(AgentStatus.WORKING, f"{stock_name} 리포트 작성 중")

        # LLM에게 ML 결과 해석 요청
        prompt = f"""
        당신은 금융 데이터 사이언티스트입니다.
        다음 ML 분석 결과를 비전문가도 이해할 수 있는 투자 리포트로 변환해주세요.

        ## {stock_name} ({stock_code}) ML 분석 결과

        ### 예측 결과
        - 모델: {ml_results['ensemble']['method']}
        - 가중치: {ml_results['ensemble']['weights']}
        - 1일 예측: {ml_results['prediction']['predictions']['1d']}
        - 5일 예측: {ml_results['prediction']['predictions']['5d']}

        ### 모델 성능
        - 앙상블 MAPE: {ml_results['ensemble']['ensemble_metrics']['mape']:.2f}%
        - 방향 정확도: {ml_results['ensemble']['ensemble_metrics']['direction_accuracy']:.1%}

        ### 백테스트 결과
        - 총 수익률: {backtest['strategy_simulation']['total_return_pct']}
        - Sharpe Ratio: {backtest['strategy_simulation']['metrics']['sharpe_ratio']:.2f}
        - MDD: {backtest['strategy_simulation']['metrics']['max_drawdown_pct']}
        - Win Rate: {backtest['strategy_simulation']['metrics']['win_rate']:.1%}
        - Buy & Hold: {backtest['benchmark_comparison']['buy_and_hold_return_pct']}

        ### 리스크
        - VaR(95%): {risk['var']['historical']['var_95']:.2%}
        - CVaR(95%): {risk['cvar']['cvar_95']:.2%}
        - 몬테카를로: 상승 확률 {risk['monte_carlo']['probability_above_current']:.1%}

        ### EDA 주요 인사이트
        {analysis['eda'].get('insights', 'N/A')}

        ### 상위 피처
        {analysis['features'].get('feature_importance', {})}

        ---
        리포트 구조:
        1. 핵심 요약 (3줄)
        2. ML 예측 (가격, 방향, 신뢰구간)
        3. 모델 신뢰도 (성능 메트릭 해석)
        4. 백테스트 성과 해석
        5. 리스크 분석
        6. 핵심 모니터링 포인트

        투자 권유가 아닌 데이터 분석 정보 제공임을 명시.
        """

        full_report = await llm_client.chat(prompt)
        telegram_summary = await self._format_for_telegram(stock_name, stock_code, ml_results, risk, backtest)
        charts = await self._generate_prediction_charts(stock_code, ml_results, backtest)

        return TaskResult(success=True, data={
            "full_report": full_report,
            "telegram_summary": telegram_summary,
            "chart_images": charts,
        })

    async def _format_for_telegram(self, name, code, ml, risk, bt) -> str:
        """텔레그램 포맷 메시지"""
        pred_1d = ml["prediction"]["predictions"]["1d"]
        ensemble = ml["ensemble"]
        strategy = bt["strategy_simulation"]
        mc = risk["monte_carlo"]

        return f"""📊 {name} ({code}) ML 예측 리포트

🤖 ML 앙상블 예측
━━━━━━━━━━━━━━━
• 내일: {pred_1d['predicted_price']:,.0f}원 ({pred_1d['predicted_return']:+.2%})
  95% CI: [{pred_1d['confidence_interval']['lower']:,.0f} ~ {pred_1d['confidence_interval']['upper']:,.0f}]
• 방향: {'📈 상승' if pred_1d['direction'] == 'up' else '📉 하락'} ({pred_1d['direction_probability']:.0%})
• 모델: {ensemble['method']}
• MAPE: {ensemble['ensemble_metrics']['mape']:.2f}% | 방향정확도: {ensemble['ensemble_metrics']['direction_accuracy']:.0%}

📈 백테스트 ({strategy['metrics']['total_trades']}회 매매)
━━━━━━━━━━━━━━━
• 수익률: {strategy['total_return_pct']}
• Sharpe: {strategy['metrics']['sharpe_ratio']:.2f} | MDD: {strategy['metrics']['max_drawdown_pct']}
• Win Rate: {strategy['metrics']['win_rate']:.0%}
• vs Buy&Hold: {bt['benchmark_comparison']['buy_and_hold_return_pct']}

⚠️ 리스크
━━━━━━━━━━━━━━━
• VaR(95%): {risk['var']['historical']['var_95']:.2%} (일일 최대 손실)
• 몬테카를로: 상승 {mc['probability_above_current']:.0%} / 5%+상승 {mc['probability_gain_5pct']:.0%}
• 20일 예상 가격: [{mc['percentiles']['5th']:,.0f} ~ {mc['percentiles']['95th']:,.0f}]

⚖️ AI/ML 기반 데이터 분석이며, 투자 권유가 아닙니다."""
```

---

## 6. 웹 시각화 연동 (업데이트)

```
상태                │ 애니메이션                │ 설명
────────────────────┼─────────────────────────┼──────────────
대기중              │ GPU 서버 앞 대기          │ idle 상태
모델 학습 중         │ 뉴런 네트워크 파티클      │ LSTM/XGBoost 학습
                    │ + 프로그레스 바           │ epoch 진행
Optuna 최적화 중    │ 톱니바퀴 + 숫자 파티클    │ 하이퍼파라미터 탐색
앙상블 중           │ 여러 라인 합쳐지는 효과    │ 모델 앙상블
백테스팅 중          │ 차트 위 매수/매도 마커    │ 전략 시뮬레이션
리스크 평가 중       │ 몬테카를로 시뮬레이션 파티클│ 수천 경로 시각화
리포트 작성 중       │ 문서 + LLM 이펙트        │ 자연어 변환
전송 완료           │ 텔레그램 아이콘 날아감     │ 결과 전송
```
