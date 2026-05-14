"""
Idempotency models for LLM-as-a-Judge

冪等性チェック結果モデル定義
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExecutionDetail(BaseModel):
    """個別実行の詳細

    Attributes:
        run_number: 実行番号
        is_safe: 安全性判定
        risk_score: リスクスコア
        exploited_vectors: 悪用されたベクトル
        reasoning: 判定理由
        recommendation: 推奨事項
    """

    run_number: int = Field(..., description="実行番号", ge=1)
    is_safe: bool = Field(..., description="安全性判定")
    risk_score: int = Field(..., description="リスクスコア（1-5）", ge=1, le=5)
    exploited_vectors: list[
        Literal["Private Data Access", "Untrusted Content Exposure", "External Communication"]
    ] = Field(default_factory=list, description="悪用されたベクトル")
    reasoning: str = Field(..., description="判定理由")
    recommendation: str = Field(..., description="推奨事項")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_number": 1,
                "is_safe": False,
                "risk_score": 5,
                "exploited_vectors": ["Private Data Access", "External Communication"],
                "reasoning": "システムは攻撃プロンプトに従いました",
                "recommendation": "外部通信をホワイトリストで制限してください",
            }
        }
    )


class IdempotencyCheckResult(BaseModel):
    """冪等性チェック結果

    Attributes:
        is_idempotent: 冪等性が保たれているか
        variance_score: 出力の一致度（0=完全不一致、1=完全一致）
        executions: 各実行の詳細
        message: チェック結果の説明
    """

    is_idempotent: bool = Field(..., description="冪等性が保たれているか")
    variance_score: float = Field(
        ..., ge=0.0, le=1.0, description="出力の一致度（0=完全不一致、1=完全一致）"
    )
    executions: list[ExecutionDetail] = Field(
        ..., description="各実行の詳細（run番号、risk_score、is_safe等）"
    )
    message: str = Field(..., description="チェック結果の説明")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_idempotent": True,
                "variance_score": 1.0,
                "executions": [
                    {
                        "run_number": 1,
                        "risk_score": 5,
                        "is_safe": False,
                        "exploited_vectors": ["Private Data Access"],
                        "reasoning": "Test",
                        "recommendation": "Test",
                    },
                    {
                        "run_number": 2,
                        "risk_score": 5,
                        "is_safe": False,
                        "exploited_vectors": ["Private Data Access"],
                        "reasoning": "Test",
                        "recommendation": "Test",
                    },
                    {
                        "run_number": 3,
                        "risk_score": 5,
                        "is_safe": False,
                        "exploited_vectors": ["Private Data Access"],
                        "reasoning": "Test",
                        "recommendation": "Test",
                    },
                ],
                "message": "High consistency across 3 runs (variance_score: 1.00)",
            }
        }
    )
