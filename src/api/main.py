"""
FastAPI main application for LLM-as-a-Judge

エントリーポイント
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api import __version__
from src.api.routes import evaluate, idempotency, test_cases


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """アプリケーションのライフサイクル管理"""
    # Startup
    print("🚀 Starting LLM-as-a-Judge API...")
    yield
    # Shutdown
    print("👋 Shutting down LLM-as-a-Judge API...")


# FastAPIアプリケーション初期化
app = FastAPI(
    title="LLM-as-a-Judge API",
    description="LLM-as-a-Judge for Enterprise Systems - Security Evaluation API",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS設定（開発環境用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ルートエンドポイント
@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """ルートエンドポイント"""
    return {
        "message": "LLM-as-a-Judge API",
        "version": __version__,
        "docs": "/docs",
    }


# ヘルスチェックエンドポイント
@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """
    ヘルスチェック

    システムとサービスの稼働状況を確認
    """
    import os
    from datetime import datetime, timezone

    services_status = {}
    overall_healthy = True

    # Database接続確認
    try:
        db_provider = os.getenv("DB_PROVIDER", "supabase")
        if db_provider == "supabase":
            supabase_url = os.getenv("SUPABASE_URL")
            services_status["database"] = "connected" if supabase_url else "not_configured"
        else:
            services_status["database"] = "configured"
    except Exception:
        services_status["database"] = "error"
        overall_healthy = False

    # MLflow接続確認
    try:
        mlflow_uri = os.getenv("MLFLOW_TRACKING_URI")
        services_status["mlflow"] = "connected" if mlflow_uri else "not_configured"
    except Exception:
        services_status["mlflow"] = "error"
        overall_healthy = False

    # LLM Provider確認
    try:
        llm_provider = os.getenv("LLM_PROVIDER", "stub")
        if llm_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            services_status["llm_provider"] = "available" if api_key else "not_configured"
        elif llm_provider == "stub":
            services_status["llm_provider"] = "available (stub)"
        else:
            services_status["llm_provider"] = f"configured ({llm_provider})"
    except Exception:
        services_status["llm_provider"] = "error"
        overall_healthy = False

    status_code = 200 if overall_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if overall_healthy else "degraded",
            "version": __version__,
            "services": services_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# エラーハンドラー
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """汎用エラーハンドラー"""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
            },
        },
    )


# ルーター登録
app.include_router(evaluate.router, prefix="/api/v1", tags=["Evaluate"])
app.include_router(test_cases.router, prefix="/api/v1", tags=["Test Cases"])
app.include_router(idempotency.router, prefix="/api/v1", tags=["Idempotency"])
