# エラーハンドリング戦略

## 概要
本システムでは、予測可能なエラーから予期しないエラーまで、すべてのエラーを適切に処理し、システムの安定性と保守性を確保する。

## エラー分類

### 1. クライアントエラー（4xx）
ユーザーの入力やリクエストに起因するエラー。

### 2. サーバーエラー（5xx）
システムの内部エラーや外部サービスの障害に起因するエラー。

### 3. ビジネスロジックエラー
ドメイン固有の制約違反やビジネスルールの不一致。

## エラーレスポンス標準フォーマット

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ErrorDetail(BaseModel):
    """エラー詳細"""
    code: str  # エラーコード（機械可読）
    message: str  # エラーメッセージ（人間可読）
    details: Optional[Dict[str, Any]] = None  # 追加情報
    trace_id: Optional[str] = None  # トレースID（ログ追跡用）

class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    status: str = "error"
    error: ErrorDetail
```

### レスポンス例
```json
{
    "status": "error",
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "入力値が不正です",
        "details": {
            "field": "risk_score",
            "constraint": "must be between 1 and 5",
            "value": 10
        },
        "trace_id": "a1b2c3d4-5e6f-7890-abcd-ef1234567890"
    }
}
```

## カスタム例外クラス

### 基底例外クラス（`src/core/exceptions.py`）

```python
from typing import Optional, Dict, Any

class BaseAPIException(Exception):
    """API例外の基底クラス"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(BaseAPIException):
    """バリデーションエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details
        )

class NotFoundError(BaseAPIException):
    """リソースが見つからないエラー"""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} with id '{identifier}' not found",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )

class DuplicateError(BaseAPIException):
    """重複エラー"""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="DUPLICATE_ERROR",
            message=f"{resource} with id '{identifier}' already exists",
            status_code=409,
            details={"resource": resource, "identifier": identifier}
        )

class LLMError(BaseAPIException):
    """LLM評価エラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="LLM_ERROR",
            message=message,
            status_code=422,
            details=details
        )

class DatabaseError(BaseAPIException):
    """データベースエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="DATABASE_ERROR",
            message=message,
            status_code=500,
            details=details
        )

class MLflowError(BaseAPIException):
    """MLflowエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="MLFLOW_ERROR",
            message=message,
            status_code=500,
            details=details
        )

class AuthenticationError(BaseAPIException):
    """認証エラー"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=message,
            status_code=401
        )

class AuthorizationError(BaseAPIException):
    """認可エラー"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            code="AUTHORIZATION_FAILED",
            message=message,
            status_code=403
        )
```

## グローバル例外ハンドラー

### FastAPI例外ハンドラー（`src/api/middleware.py`）

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uuid
import logging
from src.core.exceptions import BaseAPIException

logger = logging.getLogger(__name__)

async def base_api_exception_handler(request: Request, exc: BaseAPIException):
    """カスタムAPI例外ハンドラー"""
    trace_id = str(uuid.uuid4())

    logger.error(
        f"API Exception: {exc.code}",
        extra={
            "trace_id": trace_id,
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "trace_id": trace_id
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydanticバリデーションエラーハンドラー"""
    trace_id = str(uuid.uuid4())

    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        "Validation error",
        extra={
            "trace_id": trace_id,
            "errors": errors,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "status": "error",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": {"errors": errors},
                "trace_id": trace_id
            }
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP例外ハンドラー"""
    trace_id = str(uuid.uuid4())

    logger.error(
        f"HTTP Exception: {exc.status_code}",
        extra={
            "trace_id": trace_id,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "trace_id": trace_id
            }
        }
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    """未処理例外ハンドラー"""
    trace_id = str(uuid.uuid4())

    logger.exception(
        "Unhandled exception",
        extra={
            "trace_id": trace_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "trace_id": trace_id
            }
        }
    )

def register_exception_handlers(app):
    """例外ハンドラーを登録"""
    app.add_exception_handler(BaseAPIException, base_api_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
```

### アプリケーション初期化（`src/main.py`）

```python
from fastapi import FastAPI
from src.api.middleware import register_exception_handlers

app = FastAPI(title="LLM-as-a-Judge API")

# 例外ハンドラーを登録
register_exception_handlers(app)
```

## LLM呼び出しのリトライ機構

### デコレーターベースのリトライ（`src/core/retry.py`）

```python
import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple
from src.core.exceptions import LLMError

logger = logging.getLogger(__name__)

def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    例外発生時にリトライするデコレーター

    Args:
        max_attempts: 最大試行回数
        delay: 初回リトライまでの待機時間（秒）
        backoff: 待機時間の倍率（指数バックオフ）
        exceptions: リトライ対象の例外のタプル
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay

            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"Failed after {max_attempts} attempts: {func.__name__}",
                            extra={"error": str(e)}
                        )
                        raise LLMError(
                            message=f"Failed after {max_attempts} attempts",
                            details={
                                "function": func.__name__,
                                "last_error": str(e),
                                "attempts": max_attempts
                            }
                        )

                    logger.warning(
                        f"Attempt {attempt} failed for {func.__name__}, retrying in {current_delay}s",
                        extra={"error": str(e)}
                    )

                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1

        return wrapper
    return decorator
```

### LLM呼び出しへの適用例

```python
from langchain_core.exceptions import LangChainException
from src.core.retry import retry_on_exception

class EvaluatorService:
    @retry_on_exception(
        max_attempts=3,
        delay=2.0,
        backoff=2.0,
        exceptions=(LangChainException, TimeoutError)
    )
    def _invoke_llm(self, chain, inputs: dict) -> dict:
        """LLMを呼び出す（リトライ付き）"""
        return chain.invoke(inputs, config={"timeout": 30})

    def evaluate_test_case(self, test_case: dict, system_output: str):
        try:
            result = self._invoke_llm(self.chain, {...})
            return result
        except LLMError as e:
            # リトライ上限に達した場合の処理
            logger.error("LLM evaluation failed", extra={"error": str(e)})
            raise
```

## タイムアウト設定

### LLM呼び出しのタイムアウト

```python
# src/core/config.py
class Settings(BaseSettings):
    # タイムアウト設定（秒）
    LLM_TIMEOUT: int = 30
    DATABASE_TIMEOUT: int = 10
    HTTP_CLIENT_TIMEOUT: int = 15

    class Config:
        env_file = ".env"

# src/services/evaluator.py
from src.core.config import settings

chain.invoke(inputs, config={"timeout": settings.LLM_TIMEOUT})
```

### FastAPI リクエストタイムアウト

```python
# src/api/middleware.py
from fastapi import Request
import asyncio

@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=60.0)
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=504,
            content={
                "status": "error",
                "error": {
                    "code": "TIMEOUT",
                    "message": "Request timeout"
                }
            }
        )
```

## データベースエラーハンドリング

### トランザクションとロールバック

```python
# src/core/repository.py
from contextlib import contextmanager
from src.core.exceptions import DatabaseError

class SupabaseRepository:
    @contextmanager
    def transaction(self):
        """トランザクション管理"""
        try:
            # トランザクション開始
            yield
            # コミット
            self.client.commit()
        except Exception as e:
            # ロールバック
            self.client.rollback()
            raise DatabaseError(
                message="Database transaction failed",
                details={"error": str(e)}
            )

    def save_result(self, run_id: str, data: dict):
        try:
            with self.transaction():
                # データ保存処理
                result = self.client.table("evaluation_results").insert(data).execute()
                return result
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                message="Failed to save result",
                details={"error": str(e)}
            )
```

## ロギング戦略

### 構造化ログ（`src/core/logging_config.py`）

```python
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """構造化ログの設定"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # JSON形式のログハンドラー
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        timestamp=True
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
```

### ログ出力例

```python
logger.info(
    "Evaluation completed",
    extra={
        "test_case_id": "TEST-LT-001",
        "risk_score": 5,
        "mlflow_run_id": "abc123",
        "execution_time_ms": 1500
    }
)
```

## エラー通知（将来実装）

### Sentry統合

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

def init_sentry():
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0,
        environment=settings.ENVIRONMENT
    )
```

## エラーメトリクス

### Prometheus メトリクス

```python
from prometheus_client import Counter, Histogram

# エラーカウンター
error_counter = Counter(
    'api_errors_total',
    'Total API errors',
    ['error_code', 'endpoint']
)

# レスポンスタイムヒストグラム
response_time = Histogram(
    'api_response_time_seconds',
    'API response time',
    ['endpoint', 'status']
)
```

## ベストプラクティス

### 1. エラーメッセージの設計
- ユーザー向け: 分かりやすく、アクション可能な情報
- 開発者向け: 詳細なコンテキスト情報（trace_id、スタックトレース）
- 機密情報を含めない

### 2. エラーハンドリングの原則
- Fail Fast: エラーは早期に検出
- Fail Safe: システムの一部が故障しても全体は動作継続
- Graceful Degradation: 機能の一部を制限して動作継続

### 3. リトライ戦略
- べき等な操作のみリトライ
- 指数バックオフを使用
- 最大リトライ回数を設定
- サーキットブレーカーパターンの検討（将来実装）

### 4. ロギング
- すべてのエラーをログに記録
- 構造化ログを使用（JSON形式）
- trace_idで追跡可能に
- 個人情報や機密情報をログに含めない
