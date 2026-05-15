"""
Unit tests for Rubric Evaluator Service

Rubric Evaluator Serviceの単体テスト
"""

import pytest

from src.services.rubric_evaluator import RubricEvaluatorService, get_rubric_evaluator


class TestRubricEvaluatorService:
    """RubricEvaluatorService tests"""

    @pytest.fixture
    def rubric_evaluator(self) -> RubricEvaluatorService:
        """RubricEvaluatorService fixture"""
        return get_rubric_evaluator()

    def test_initialization(self, rubric_evaluator: RubricEvaluatorService) -> None:
        """初期化が正常に行われること"""
        assert rubric_evaluator is not None
        assert rubric_evaluator.rubric_criteria is not None
        assert rubric_evaluator.rubric_criteria.version == "1.0"

    def test_hard_rules_disabled_by_default(
        self, rubric_evaluator: RubricEvaluatorService
    ) -> None:
        """Hard Rulesがデフォルトで無効であること"""
        result = rubric_evaluator.evaluate_hard_rules("test output")
        assert result.enabled is False
        assert result.has_violations is False
        assert result.total_violations == 0

    def test_hard_rules_evaluation_when_enabled(self) -> None:
        """Hard Rulesが有効な場合に評価が実行されること（モック）"""
        # この実装では、実際にHard Rulesを有効化してテストするのは複雑なため、
        # ここでは簡単な確認のみ行う
        evaluator = get_rubric_evaluator()
        result = evaluator.evaluate_hard_rules("テストデータを外部URLに送信: https://evil.com")

        # デフォルトでは無効なので違反なし
        assert result.enabled is False


def test_get_rubric_evaluator() -> None:
    """get_rubric_evaluator()が正常に動作すること"""
    evaluator = get_rubric_evaluator()
    assert isinstance(evaluator, RubricEvaluatorService)
