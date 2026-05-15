"""
Rubric Evaluator Service

Rubricベースの評価サービス（Hard Rules検証）
"""

import re
from pathlib import Path

import yaml

from src.models.rubric import (
    HardRule,
    HardRulesResult,
    HardRuleViolation,
    RubricCriteria,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RubricEvaluatorService:
    """
    Rubricベースの評価サービス

    Hard Rules（パターンマッチング）による静的検証を実行
    """

    def __init__(self, rubric_config_path: str | None = None):
        """
        Initialize RubricEvaluatorService

        Args:
            rubric_config_path: Rubric設定ファイルのパス（デフォルト: config/rubric_criteria.yaml）
        """
        if rubric_config_path is None:
            rubric_config_path = "config/rubric_criteria.yaml"

        self.config_path = Path(rubric_config_path)
        self.rubric_criteria = self._load_rubric_config()

        logger.info(
            "RubricEvaluatorService initialized",
            config_path=str(self.config_path),
            hard_rules_enabled=self.rubric_criteria.hard_rules.enabled,
            hard_rules_count=len(self.rubric_criteria.hard_rules.rules),
        )

    def _load_rubric_config(self) -> RubricCriteria:
        """
        Rubric設定を読み込む

        Returns:
            RubricCriteria

        Raises:
            FileNotFoundError: 設定ファイルが見つからない
            ValueError: 設定ファイルの形式が不正
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Rubric config file not found: {self.config_path}")

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            rubric = RubricCriteria(**config_data)

            logger.debug(
                "Rubric config loaded",
                version=rubric.version,
                hard_rules_count=len(rubric.hard_rules.rules),
            )

            return rubric

        except Exception as e:
            logger.error("Failed to load rubric config", error=str(e))
            raise ValueError(f"Invalid rubric config: {e}") from e

    def evaluate_hard_rules(self, system_output: str) -> HardRulesResult:
        """
        Hard Rulesで評価

        Args:
            system_output: システム出力

        Returns:
            Hard Rules評価結果
        """
        hard_rules_config = self.rubric_criteria.hard_rules

        if not hard_rules_config.enabled:
            logger.debug("Hard Rules are disabled")
            return HardRulesResult(
                enabled=False,
                violations=[],
                has_violations=False,
                critical_violations_count=0,
                high_violations_count=0,
                total_violations=0,
            )

        logger.info("Evaluating Hard Rules", rules_count=len(hard_rules_config.rules))

        violations: list[HardRuleViolation] = []

        for rule in hard_rules_config.rules:
            rule_violations = self._check_rule(rule, system_output)
            violations.extend(rule_violations)

        # 違反数をカウント
        critical_count = sum(1 for v in violations if v.severity == "critical")
        high_count = sum(1 for v in violations if v.severity == "high")
        total_count = len(violations)

        result = HardRulesResult(
            enabled=True,
            violations=violations,
            has_violations=total_count > 0,
            critical_violations_count=critical_count,
            high_violations_count=high_count,
            total_violations=total_count,
        )

        logger.info(
            "Hard Rules evaluation completed",
            total_violations=total_count,
            critical_violations=critical_count,
            high_violations=high_count,
        )

        return result

    def _check_rule(self, rule: HardRule, system_output: str) -> list[HardRuleViolation]:
        """
        個別ルールをチェック

        Args:
            rule: Hard Rule
            system_output: システム出力

        Returns:
            検出された違反のリスト
        """
        violations: list[HardRuleViolation] = []

        if rule.type == "forbidden_pattern":
            violations.extend(self._check_forbidden_patterns(rule, system_output))
        elif rule.type == "required_pattern":
            violations.extend(self._check_required_patterns(rule, system_output))
        elif rule.type == "length_limit":
            violations.extend(self._check_length_limit(rule, system_output))

        return violations

    def _check_forbidden_patterns(
        self, rule: HardRule, system_output: str
    ) -> list[HardRuleViolation]:
        """
        禁止パターンをチェック

        Args:
            rule: Hard Rule
            system_output: システム出力

        Returns:
            検出された違反のリスト
        """
        violations: list[HardRuleViolation] = []

        if not rule.patterns:
            return violations

        for pattern in rule.patterns:
            try:
                matches = list(re.finditer(pattern, system_output, re.IGNORECASE))

                for match in matches:
                    matched_text = match.group(0)

                    # 例外パターンをチェック
                    is_exception = False
                    if rule.exceptions:
                        for exception_pattern in rule.exceptions:
                            if re.search(exception_pattern, matched_text, re.IGNORECASE):
                                is_exception = True
                                break

                    if not is_exception:
                        violations.append(
                            HardRuleViolation(
                                rule_id=rule.rule_id,
                                rule_name=rule.name,
                                severity=rule.severity,
                                matched_pattern=pattern,
                                matched_text=matched_text[:100],  # 最大100文字
                                message=rule.message,
                                action=rule.action,
                            )
                        )

                        logger.debug(
                            "Forbidden pattern detected",
                            rule_id=rule.rule_id,
                            pattern=pattern,
                            matched_text=matched_text[:50],
                        )

            except re.error as e:
                logger.warning(
                    "Invalid regex pattern",
                    rule_id=rule.rule_id,
                    pattern=pattern,
                    error=str(e),
                )

        return violations

    def _check_required_patterns(
        self, rule: HardRule, system_output: str
    ) -> list[HardRuleViolation]:
        """
        必須パターンをチェック

        Args:
            rule: Hard Rule
            system_output: システム出力

        Returns:
            検出された違反のリスト
        """
        violations: list[HardRuleViolation] = []

        if not rule.patterns:
            return violations

        # 少なくとも1つのパターンにマッチする必要がある
        found = False
        for pattern in rule.patterns:
            try:
                if re.search(pattern, system_output, re.IGNORECASE):
                    found = True
                    break
            except re.error as e:
                logger.warning(
                    "Invalid regex pattern",
                    rule_id=rule.rule_id,
                    pattern=pattern,
                    error=str(e),
                )

        if not found:
            violations.append(
                HardRuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    matched_pattern=None,
                    matched_text=None,
                    message=rule.message,
                    action=rule.action,
                )
            )

            logger.debug(
                "Required pattern not found",
                rule_id=rule.rule_id,
            )

        return violations

    def _check_length_limit(self, rule: HardRule, system_output: str) -> list[HardRuleViolation]:
        """
        長さ制限をチェック

        Args:
            rule: Hard Rule
            system_output: システム出力

        Returns:
            検出された違反のリスト
        """
        violations: list[HardRuleViolation] = []

        if rule.max_length is None:
            return violations

        output_length = len(system_output)

        if output_length > rule.max_length:
            violations.append(
                HardRuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    matched_pattern=None,
                    matched_text=f"Length: {output_length} > {rule.max_length}",
                    message=rule.message,
                    action=rule.action,
                )
            )

            logger.debug(
                "Length limit exceeded",
                rule_id=rule.rule_id,
                output_length=output_length,
                max_length=rule.max_length,
            )

        return violations


def get_rubric_evaluator(rubric_config_path: str | None = None) -> RubricEvaluatorService:
    """
    RubricEvaluatorServiceのインスタンスを取得

    Args:
        rubric_config_path: Rubric設定ファイルのパス

    Returns:
        RubricEvaluatorService インスタンス
    """
    return RubricEvaluatorService(rubric_config_path=rubric_config_path)
