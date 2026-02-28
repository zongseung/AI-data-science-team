# 07. 보안 및 인증 상세 설계

## 1. 보안 아키텍처 개요

```
┌────────────────────────────────────────────────────────────┐
│                     보안 레이어 구조                         │
│                                                            │
│  Layer 1: 네트워크 보안                                     │
│  ├── HTTPS/TLS 강제                                        │
│  ├── CORS 정책                                             │
│  └── Rate Limiting                                         │
│                                                            │
│  Layer 2: 인증 (Authentication)                             │
│  ├── Supabase Auth (JWT)                                   │
│  ├── OAuth 2.0 (Google, GitHub)                            │
│  └── Telegram Bot Token 검증                               │
│                                                            │
│  Layer 3: 인가 (Authorization)                              │
│  ├── RBAC (Role-Based Access Control)                      │
│  ├── API 엔드포인트별 권한                                   │
│  └── 사용자별 데이터 격리                                    │
│                                                            │
│  Layer 4: 데이터 보안                                       │
│  ├── API Key 암호화 저장 (AES-256)                          │
│  ├── 환경변수 관리 (.env)                                   │
│  ├── Supabase RLS (Row Level Security)                     │
│  └── 민감 데이터 마스킹                                     │
│                                                            │
│  Layer 5: 모니터링                                          │
│  ├── 접근 로깅                                             │
│  ├── 이상 행동 탐지                                        │
│  └── 보안 이벤트 알림                                       │
└────────────────────────────────────────────────────────────┘
```

## 2. Supabase 인증

### 2.1 프로젝트 설정

```python
# db/supabase_client.py

from supabase import create_client, Client
from config.settings import settings


def get_supabase_client() -> Client:
    """Supabase 클라이언트 초기화"""
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
    )


def get_supabase_admin() -> Client:
    """Supabase Admin 클라이언트 (서버 사이드 전용)"""
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )
```

### 2.2 인증 흐름

```python
# security/auth.py

from fastapi import Depends, HTTPException, Header
from supabase import Client


async def get_current_user(
    authorization: str = Header(...),
    supabase: Client = Depends(get_supabase_client),
) -> dict:
    """JWT 토큰 검증 및 사용자 조회"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")

    try:
        user = supabase.auth.get_user(token)
        return user.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def require_role(required_role: str):
    """역할 기반 접근 제어 데코레이터"""
    async def checker(user: dict = Depends(get_current_user)):
        user_role = user.get("user_metadata", {}).get("role", "viewer")
        if user_role not in ROLE_HIERARCHY.get(required_role, [required_role]):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker
```

### 2.3 역할 정의

```python
# 사용자 역할 계층
ROLE_HIERARCHY = {
    "admin": ["admin"],
    "analyst": ["admin", "analyst"],
    "viewer": ["admin", "analyst", "viewer"],
}

# 역할별 권한
ROLE_PERMISSIONS = {
    "admin": {
        "manage_users": True,
        "manage_api_keys": True,
        "manage_stocks": True,
        "view_all_data": True,
        "trigger_analysis": True,
        "configure_alerts": True,
    },
    "analyst": {
        "manage_users": False,
        "manage_api_keys": False,
        "manage_stocks": True,
        "view_all_data": True,
        "trigger_analysis": True,
        "configure_alerts": True,
    },
    "viewer": {
        "manage_users": False,
        "manage_api_keys": False,
        "manage_stocks": False,
        "view_all_data": True,
        "trigger_analysis": False,
        "configure_alerts": True,
    },
}
```

## 3. OAuth 2.0 소셜 로그인

### 3.1 지원 프로바이더

```python
# Supabase Auth에서 지원하는 OAuth 프로바이더 설정

OAUTH_PROVIDERS = {
    "google": {
        "enabled": True,
        "scopes": ["email", "profile"],
        "description": "Google 계정으로 로그인",
    },
    "github": {
        "enabled": True,
        "scopes": ["user:email"],
        "description": "GitHub 계정으로 로그인",
    },
    "kakao": {
        "enabled": True,
        "scopes": ["profile_nickname", "account_email"],
        "description": "카카오 계정으로 로그인",
    },
}
```

### 3.2 OAuth 흐름

```
1. 사용자가 소셜 로그인 버튼 클릭
2. Supabase Auth → 프로바이더 인증 페이지로 리다이렉트
3. 사용자 인증 완료
4. 프로바이더 → Supabase 콜백 URL로 리다이렉트 (code 포함)
5. Supabase가 code를 교환하여 JWT 발급
6. 프론트엔드에서 JWT 수신 및 저장
7. 이후 API 호출 시 JWT를 Authorization 헤더에 포함
```

## 4. API Key 관리

### 4.1 암호화 저장

```python
# security/api_key_manager.py

from cryptography.fernet import Fernet
from config.settings import settings


class APIKeyManager:
    """API 키 암호화 관리자"""

    def __init__(self):
        self.cipher = Fernet(settings.ENCRYPTION_KEY.encode())

    def encrypt_key(self, api_key: str) -> str:
        """API 키 암호화"""
        return self.cipher.encrypt(api_key.encode()).decode()

    def decrypt_key(self, encrypted_key: str) -> str:
        """API 키 복호화"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()

    async def store_key(self, user_id: str, service: str, api_key: str):
        """암호화하여 DB에 저장"""
        encrypted = self.encrypt_key(api_key)
        await supabase.table("api_keys").upsert({
            "user_id": user_id,
            "service": service,
            "encrypted_key": encrypted,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()

    async def get_key(self, user_id: str, service: str) -> str:
        """복호화하여 반환"""
        result = await supabase.table("api_keys").select("encrypted_key").eq(
            "user_id", user_id
        ).eq("service", service).single().execute()

        if result.data:
            return self.decrypt_key(result.data["encrypted_key"])
        raise KeyError(f"API key not found for service: {service}")
```

### 4.2 관리 대상 API 키

```python
# 관리 대상 외부 서비스 API 키
MANAGED_API_KEYS = {
    "dart_api": {
        "description": "DART 전자공시 OpenAPI 키",
        "url": "https://opendart.fss.or.kr/",
        "required": True,
    },
    "openai_api": {
        "description": "OpenAI API 키 (GPT 분석용)",
        "url": "https://platform.openai.com/",
        "required": False,  # Claude API 대체 가능
    },
    "anthropic_api": {
        "description": "Anthropic API 키 (Claude 분석용)",
        "url": "https://console.anthropic.com/",
        "required": False,
    },
    "telegram_bot_token": {
        "description": "텔레그램 봇 토큰",
        "url": "https://t.me/BotFather",
        "required": True,
    },
}
```

## 5. Supabase RLS (Row Level Security)

### 5.1 테이블별 RLS 정책

```sql
-- 사용자는 자신의 관심 종목만 접근 가능
CREATE POLICY "Users can view their own watchlist"
ON watchlist FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own watchlist"
ON watchlist FOR ALL
USING (auth.uid() = user_id);

-- API 키는 소유자만 접근 가능
CREATE POLICY "Users can only access their own API keys"
ON api_keys FOR ALL
USING (auth.uid() = user_id);

-- 알림 설정은 소유자만 접근 가능
CREATE POLICY "Users can manage their own alerts"
ON alert_settings FOR ALL
USING (auth.uid() = user_id);

-- 분석 결과는 모든 인증된 사용자가 조회 가능
CREATE POLICY "Authenticated users can view analyses"
ON analyses FOR SELECT
USING (auth.role() = 'authenticated');

-- 주가 데이터는 모든 인증된 사용자가 조회 가능
CREATE POLICY "Authenticated users can view stock data"
ON stock_prices FOR SELECT
USING (auth.role() = 'authenticated');

-- EDA 리포트는 모든 인증된 사용자가 조회 가능
CREATE POLICY "Authenticated users can view EDA reports"
ON eda_reports FOR SELECT
USING (auth.role() = 'authenticated');

-- 피처 데이터는 모든 인증된 사용자가 조회 가능
CREATE POLICY "Authenticated users can view features"
ON features FOR SELECT
USING (auth.role() = 'authenticated');

-- ML 실험 결과는 모든 인증된 사용자가 조회 가능
CREATE POLICY "Authenticated users can view ML experiments"
ON ml_experiments FOR SELECT
USING (auth.role() = 'authenticated');

-- ML 모델 메타데이터 조회 가능 (아티팩트 경로 제외)
CREATE POLICY "Authenticated users can view ML models"
ON ml_models FOR SELECT
USING (auth.role() = 'authenticated');

-- ML 예측 결과 조회 가능
CREATE POLICY "Authenticated users can view predictions"
ON predictions FOR SELECT
USING (auth.role() = 'authenticated');

-- 백테스트 결과 조회 가능
CREATE POLICY "Authenticated users can view backtests"
ON backtests FOR SELECT
USING (auth.role() = 'authenticated');

-- ML 실험/모델 생성은 analyst 이상만 가능
CREATE POLICY "Analysts can create ML experiments"
ON ml_experiments FOR INSERT
USING (
  auth.role() = 'authenticated' AND
  (auth.jwt() ->> 'role') IN ('admin', 'analyst')
);

CREATE POLICY "Analysts can manage ML models"
ON ml_models FOR ALL
USING (
  auth.role() = 'authenticated' AND
  (auth.jwt() ->> 'role') IN ('admin', 'analyst')
);

-- 텔레그램 세션은 소유자만 접근 가능
CREATE POLICY "Users can only access their own telegram sessions"
ON telegram_sessions FOR ALL
USING (auth.uid() = user_id);
```

## 6. Rate Limiting

### 6.1 구현

```python
# security/rate_limiter.py

from collections import defaultdict
from datetime import datetime, timedelta


class RateLimiter:
    """IP/사용자 기반 Rate Limiter"""

    def __init__(self):
        self.requests: dict[str, list[datetime]] = defaultdict(list)

    # 엔드포인트별 Rate Limit 설정
    RATE_LIMITS = {
        "default": {"max_requests": 60, "window_seconds": 60},
        "analysis": {"max_requests": 10, "window_seconds": 60},
        "collection": {"max_requests": 5, "window_seconds": 60},
        "eda": {"max_requests": 10, "window_seconds": 60},
        "prediction": {"max_requests": 5, "window_seconds": 60},      # ML 예측 (연산 비용 높음)
        "backtest": {"max_requests": 3, "window_seconds": 60},         # 백테스팅 (연산 비용 매우 높음)
        "model_training": {"max_requests": 2, "window_seconds": 300},  # 모델 학습 (5분당 2회)
        "experiment": {"max_requests": 30, "window_seconds": 60},      # MLflow 실험 조회
        "telegram": {"max_requests": 20, "window_seconds": 60},
        "websocket": {"max_requests": 100, "window_seconds": 60},
    }

    def check(self, key: str, endpoint_type: str = "default") -> bool:
        """Rate limit 확인"""
        config = self.RATE_LIMITS.get(endpoint_type, self.RATE_LIMITS["default"])
        now = datetime.utcnow()
        window = timedelta(seconds=config["window_seconds"])

        # 윈도우 밖의 요청 제거
        self.requests[key] = [
            t for t in self.requests[key] if now - t < window
        ]

        if len(self.requests[key]) >= config["max_requests"]:
            return False

        self.requests[key].append(now)
        return True

    def remaining(self, key: str, endpoint_type: str = "default") -> int:
        """남은 요청 횟수"""
        config = self.RATE_LIMITS.get(endpoint_type, self.RATE_LIMITS["default"])
        now = datetime.utcnow()
        window = timedelta(seconds=config["window_seconds"])

        recent = [t for t in self.requests[key] if now - t < window]
        return max(0, config["max_requests"] - len(recent))
```

### 6.2 FastAPI 미들웨어

```python
# FastAPI Rate Limiting 미들웨어
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        endpoint_type = self._get_endpoint_type(request.url.path)

        if not self.rate_limiter.check(client_ip, endpoint_type):
            remaining = self.rate_limiter.remaining(client_ip, endpoint_type)
            raise HTTPException(
                status_code=429,
                detail="Too Many Requests",
                headers={
                    "X-RateLimit-Remaining": str(remaining),
                    "Retry-After": "60",
                },
            )

        response = await call_next(request)
        return response
```

## 7. ML 파이프라인 보안

### 7.1 모델 아티팩트 보안

```python
# security/ml_security.py

class MLArtifactSecurity:
    """ML 모델 아티팩트 접근 제어"""

    # 모델 아티팩트 저장 경로는 서버 내부에서만 접근 가능
    ARTIFACT_BASE_PATH = "/app/ml_artifacts"

    # 모델 파일 서명 검증 (변조 방지)
    async def verify_model_integrity(self, model_path: str, expected_hash: str) -> bool:
        """모델 파일 무결성 검증 (SHA-256)"""
        import hashlib
        with open(model_path, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        return actual_hash == expected_hash

    # MLflow 접근 제어
    MLFLOW_AUTH = {
        "tracking_uri": "http://localhost:5000",  # 내부 네트워크만 접근
        "artifact_location": "supabase_storage",   # Supabase Storage에 저장
        "auth_method": "basic",                    # Basic Auth 또는 Token
    }


# 피처 데이터 접근 제어
class FeatureStorePolicy:
    """피처 스토어 접근 정책"""

    # 피처 데이터는 읽기만 허용 (수정은 파이프라인을 통해서만)
    POLICIES = {
        "features": {"read": ["admin", "analyst", "viewer"], "write": ["admin"]},
        "ml_experiments": {"read": ["admin", "analyst", "viewer"], "write": ["admin", "analyst"]},
        "ml_models": {"read": ["admin", "analyst", "viewer"], "write": ["admin", "analyst"]},
        "predictions": {"read": ["admin", "analyst", "viewer"], "write": ["admin", "analyst"]},
        "backtests": {"read": ["admin", "analyst", "viewer"], "write": ["admin", "analyst"]},
    }
```

### 7.2 ML 입력 데이터 검증

```python
# security/ml_validation.py

from pydantic import BaseModel, validator

class PredictionRequest(BaseModel):
    """ML 예측 요청 입력 검증"""
    stock_code: str
    horizon_days: int = 20

    @validator("stock_code")
    def validate_stock_code(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError("종목코드는 6자리 숫자여야 합니다")
        return v

    @validator("horizon_days")
    def validate_horizon(cls, v):
        if v < 1 or v > 60:
            raise ValueError("예측 기간은 1~60일 사이여야 합니다")
        return v


class BacktestRequest(BaseModel):
    """백테스트 요청 입력 검증"""
    stock_code: str
    n_splits: int = 5
    initial_capital: float = 10_000_000

    @validator("n_splits")
    def validate_splits(cls, v):
        if v < 2 or v > 10:
            raise ValueError("Walk-Forward 분할 수는 2~10 사이여야 합니다")
        return v

    @validator("initial_capital")
    def validate_capital(cls, v):
        if v < 1_000_000 or v > 1_000_000_000:
            raise ValueError("시뮬레이션 자본금 범위를 벗어났습니다")
        return v
```

## 8. 환경변수 관리

### 8.1 .env 구조

```bash
# .env.example (커밋 대상)

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# 암호화
ENCRYPTION_KEY=your-fernet-key

# 텔레그램
TELEGRAM_BOT_TOKEN=your-bot-token

# LLM API
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# DART
DART_API_KEY=your-dart-api-key

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_ARTIFACT_ROOT=supabase://ml-artifacts
MLFLOW_AUTH_TOKEN=your-mlflow-token

# 서버
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
CORS_ORIGINS=http://localhost:5173

# 환경
ENVIRONMENT=development
DEBUG=true
```

### 8.2 Pydantic Settings

```python
# config/settings.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # 암호화
    ENCRYPTION_KEY: str

    # 텔레그램
    TELEGRAM_BOT_TOKEN: str

    # LLM
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # DART
    DART_API_KEY: str = ""

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_ARTIFACT_ROOT: str = "./ml_artifacts"
    MLFLOW_AUTH_TOKEN: str = ""

    # 서버
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # 환경
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
```

## 9. 보안 체크리스트

```
[ ] HTTPS/TLS 설정 완료
[ ] Supabase RLS 정책 모든 테이블에 적용
[ ] API Key 암호화 저장 구현
[ ] .env 파일 .gitignore에 포함
[ ] Rate Limiting 모든 엔드포인트에 적용
[ ] CORS 허용 도메인 제한
[ ] SQL Injection 방지 (파라미터 바인딩)
[ ] XSS 방지 (입력값 이스케이프)
[ ] JWT 만료 시간 설정 (1시간)
[ ] 텔레그램 봇 토큰 노출 방지
[ ] 에러 메시지에 민감 정보 미포함
[ ] 로깅에 API 키 미포함
[ ] Dependency 보안 취약점 스캔
[ ] 접근 로그 기록
[ ] MLflow 접근 제어 설정 (내부 네트워크 제한)
[ ] ML 모델 아티팩트 무결성 검증 활성화
[ ] ML 예측 요청 입력 검증 (종목코드, 예측기간)
[ ] 피처 스토어 쓰기 권한 제한 (admin/analyst만)
[ ] ML 실험 데이터 RLS 정책 적용
[ ] 백테스트 시뮬레이션 자본금 범위 제한
```
