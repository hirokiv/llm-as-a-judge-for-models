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
    """Soft Judge評価基準（Rubric評価項目）"""

    criterion_id: str = Field(..., description="基準ID（例: EVAL-001）")
    name: str = Field(..., description="基準名")
    description: str = Field(..., description="評価項目の説明")
    requirement: str | None = Field(None, description="判定要件の詳細")
    points: int = Field(..., description="この項目の配点", ge=0)
    type: Literal["positive", "negative"] = Field(
        "positive", description="positive=満たすと加点、negative=満たすと減点"
    )
    category: str | None = Field(None, description="カテゴリ（オプション）")
    weight: float = Field(1.0, description="重み（0.0-1.0）", ge=0.0, le=1.0)


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


class CriterionEvaluationResult(BaseModel):
    """個別評価項目の結果"""

    criterion_id: str = Field(..., description="評価項目ID")
    name: str = Field(..., description="評価項目名")
    description: str = Field(..., description="評価項目の説明")
    judgment: Literal["Yes", "No", "Partial"] = Field(..., description="判定結果")
    score: int = Field(..., description="獲得スコア", ge=0)
    max_score: int = Field(..., description="最大スコア", ge=0)
    reasoning: str = Field(..., description="判定理由")
    type: Literal["positive", "negative"] = Field("positive", description="評価タイプ")


class RubricEvaluationResult(BaseModel):
    """Rubric評価全体の結果"""

    criteria_results: list[CriterionEvaluationResult] = Field(
        default_factory=list, description="各評価項目の結果"
    )
    total_score: int = Field(..., description="合計獲得スコア", ge=0)
    max_possible_score: int = Field(..., description="最大可能スコア", ge=0)
    score_rate: float = Field(..., description="スコア率（0.0-1.0）", ge=0.0, le=1.0)
    overall_judgment: str = Field(..., description="総合判定コメント")
    pass_threshold: float = Field(0.7, description="合格基準（0.0-1.0）", ge=0.0, le=1.0)

    @property
    def is_pass(self) -> bool:
        """合格基準を満たしているか"""
        return self.score_rate >= self.pass_threshold

    def to_summary(self) -> str:
        """サマリー文字列を生成"""
        status = "✅ Pass" if self.is_pass else "❌ Fail"
        return (
            f"Rubric: {self.total_score}/{self.max_possible_score} ({self.score_rate:.1%}) {status}"
        )
