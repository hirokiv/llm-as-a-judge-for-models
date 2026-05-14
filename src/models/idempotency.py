"""
Idempotency models for LLM-as-a-Judge

冪等性チェック結果モデル定義
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IdempotencyCheckResult(BaseModel):
    """冪等性チェック結果

    Attributes:
        is_idempotent: 冪等性が保たれているか
        input_hash: 入力のハッシュ値
        executions: 各実行の詳細
        variance_score: 出力の一致度（0=完全不一致、1=完全一致）
        message: チェック結果の説明
    """

    is_idempotent: bool = Field(..., description="冪等性が保たれているか")
    input_hash: str = Field(..., description="入力のハッシュ値（SHA-256）")
    executions: list[dict[str, Any]] = Field(
        ..., description="各実行の詳細（run番号、risk_score、is_safe等）"
    )
    variance_score: float = Field(
        ..., ge=0.0, le=1.0, description="出力の一致度（0=完全不一致、1=完全一致）"
    )
    message: str = Field(..., description="チェック結果の説明")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_idempotent": True,
                "input_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
                "executions": [
                    {"run": 1, "risk_score": 5, "is_safe": False},
                    {"run": 2, "risk_score": 5, "is_safe": False},
                    {"run": 3, "risk_score": 5, "is_safe": False},
                ],
                "variance_score": 1.0,
                "message": "3回の実行で完全に同一の結果が得られました（variance_score=1.0）",
            }
        }
    )
