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
from src.api.routes import evaluate


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
    """ヘルスチェック"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "version": __version__,
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
