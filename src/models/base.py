"""
Base models for LLM-as-a-Judge

共通のバリデーションと基底クラスを提供
"""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class TimestampMixin(BaseModel):
    """タイムスタンプ付与Mixin

    created_at と updated_at フィールドを提供
    """

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="作成日時（UTC）"
    )
    updated_at: datetime | None = Field(default=None, description="更新日時（UTC）")

    model_config = ConfigDict(
        # Pydantic v2ではdatetimeは自動的にISO 8601形式にシリアライズされる
        # json_encodersは非推奨のため削除
    )


class IDMixin(BaseModel):
    """ID付与Mixin

    オプショナルなIDフィールドを提供
    """

    id: str | None = Field(default=None, description="一意識別子")

    model_config = ConfigDict(
        # IDは通常データベースで自動生成されるため、オプショナル
        validate_assignment=True
    )
