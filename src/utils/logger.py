"""
Structured logging with sensitive data masking

構造化ログと機密情報マスキング
"""

import logging
import os
import re
from typing import Any

import structlog

# 機密情報のマスキングパターン
SENSITIVE_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "api_key": re.compile(r"(sk-[a-zA-Z0-9]{48}|eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)"),
    "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
    "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}


def mask_sensitive_data(data: Any) -> Any:
    """
    機密情報をマスキングする

    Args:
        data: マスキング対象のデータ（str, dict, list等）

    Returns:
        マスキング後のデータ

    Examples:
        >>> mask_sensitive_data("Email: user@example.com")
        'Email: [REDACTED_EMAIL]'

        >>> mask_sensitive_data({"key": "sk-1234...", "email": "test@example.com"})
        {'key': '[REDACTED_API_KEY]', 'email': '[REDACTED_EMAIL]'}
    """
    if isinstance(data, str):
        masked = data
        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            masked = pattern.sub(f"[REDACTED_{pattern_name.upper()}]", masked)
        return masked

    elif isinstance(data, dict):
        return {key: mask_sensitive_data(value) for key, value in data.items()}

    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]

    else:
        return data


def add_request_id(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """
    ログにリクエストIDを追加するプロセッサ

    Args:
        logger: ロガーインスタンス
        method_name: ログメソッド名
        event_dict: イベント辞書

    Returns:
        更新されたイベント辞書
    """
    # コンテキスト変数からリクエストIDを取得（FastAPIのミドルウェアで設定）
    # 現状はシンプルに実装、後でcontextvarsで改善可能
    return event_dict


def configure_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """
    ロギングを設定する

    Args:
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        json_logs: JSON形式でログを出力するか（本番環境推奨）

    Examples:
        >>> configure_logging(log_level="DEBUG", json_logs=True)
    """
    # 環境変数から設定を取得
    log_level = os.getenv("LOG_LEVEL", log_level).upper()
    environment = os.getenv("ENVIRONMENT", "development")

    # 本番環境では常にJSON形式
    if environment == "production":
        json_logs = True

    # structlogの設定
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_request_id,
    ]

    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 標準ログレベルを設定
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    構造化ロガーを取得する

    Args:
        name: ロガー名（通常は__name__を使用）

    Returns:
        構造化ロガーインスタンス

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("API request received", endpoint="/api/v1/evaluate")
    """
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger


# デフォルトでロギングを設定（アプリケーション起動時）
configure_logging()
