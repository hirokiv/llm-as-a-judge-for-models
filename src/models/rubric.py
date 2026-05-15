"""
Rubric models for evaluation criteria

評価基準（Rubric）のデータモデル
"""

from typing import Literal

from pydantic import BaseModel, Field


class HardRule(BaseModel):
    """Hard Rule（静的検証ルール）"""

    rule_id: str = Field(..., description="ルールID")
    name: str = Field(..., description="ルール名")
    type: Literal["forbidden_pattern", "required_pattern", "length_limit"] = Field(
        ..., description="ルールタイプ"
    )
    severity: Literal["critical", "high", "medium", "low"] = Field(..., description="深刻度")
    patterns: list[str] | None = Field(None, description="パターンリスト（正規表現）")
    exceptions: list[str] | None = Field(None, description="例外パターンリスト")
    max_length: int | None = Field(None, description="最大長（length_limit用）")
    action: Literal["flag", "check", "warn", "block"] = Field(..., description="アクション")
    message: str = Field(..., description="検出時のメッセージ")


class HardRuleViolation(BaseModel):
    """Hard Rule違反検出結果"""

    rule_id: str = Field(..., description="違反したルールID")
    rule_name: str = Field(..., description="ルール名")
    severity: Literal["critical", "high", "medium", "low"] = Field(..., description="深刻度")
    matched_pattern: str | None = Field(None, description="マッチしたパターン")
    matched_text: str | None = Field(None, description="マッチしたテキスト")
    message: str = Field(..., description="違反メッセージ")
    action: Literal["flag", "check", "warn", "block"] = Field(..., description="推奨アクション")


class HardRulesConfig(BaseModel):
    """Hard Rules設定"""

    enabled: bool = Field(False, description="Hard Rulesの有効/無効")
    description: str | None = Field(None, description="説明")
    rules: list[HardRule] = Field(default_factory=list, description="ルールリスト")


class SoftJudgeCriterion(BaseModel):
    """Soft Judge評価基準"""

    criterion_id: str = Field(..., description="基準ID")
    name: str = Field(..., description="基準名")
    category: str = Field(..., description="カテゴリ")
    weight: float = Field(..., description="重み（0.0-1.0）", ge=0.0, le=1.0)
    description: str | None = Field(None, description="説明")


class SoftJudgeConfig(BaseModel):
    """Soft Judge設定"""

    description: str | None = Field(None, description="説明")
    criteria: list[SoftJudgeCriterion] = Field(default_factory=list, description="評価基準リスト")


class RubricCriteria(BaseModel):
    """Rubric評価基準全体"""

    version: str = Field(..., description="バージョン")
    description: str | None = Field(None, description="説明")
    hard_rules: HardRulesConfig = Field(..., description="Hard Rules設定")
    soft_judge: SoftJudgeConfig = Field(..., description="Soft Judge設定")


class HardRulesResult(BaseModel):
    """Hard Rules評価結果"""

    enabled: bool = Field(..., description="Hard Rulesが有効かどうか")
    violations: list[HardRuleViolation] = Field(
        default_factory=list, description="検出された違反リスト"
    )
    has_violations: bool = Field(..., description="違反が存在するか")
    critical_violations_count: int = Field(0, description="Critical違反の数")
    high_violations_count: int = Field(0, description="High違反の数")
    total_violations: int = Field(0, description="全違反数")

    @property
    def is_safe(self) -> bool:
        """Critical違反がない場合はTrue"""
        return self.critical_violations_count == 0

    def to_summary(self) -> str:
        """サマリー文字列を生成"""
        if not self.enabled:
            return "Hard Rules: Disabled"
        if not self.has_violations:
            return "Hard Rules: No violations detected"
        return (
            f"Hard Rules: {self.total_violations} violations "
            f"(Critical: {self.critical_violations_count}, High: {self.high_violations_count})"
        )
