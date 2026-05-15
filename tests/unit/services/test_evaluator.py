"""
Unit tests for Evaluator Service

Evaluator Serviceの単体テスト
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.judge_result import JudgeResult
from src.models.test_case import LethalTrifectaVectors, TestCaseScenario
from src.services.evaluator import EvaluationResult, EvaluatorService


@pytest.fixture
def mock_judge_llm():
    """Mock Judge LLM"""
    judge_llm = AsyncMock()
    judge_llm.evaluate = AsyncMock(
        return_value=JudgeResult(
            is_safe=False,
            risk_score=4,
            exploited_vectors=["Private Data Access", "External Communication"],
            reasoning="Test reasoning",
            recommendation="Test recommendation",
            judge_model="test-model",
            judge_provider="test-provider",
        )
    )
    return judge_llm


@pytest.fixture
def mock_mlflow_tracker():
    """Mock MLflow Tracker"""
    tracker = MagicMock()
    tracker.start_run = MagicMock(return_value="test-run-id-123")
    tracker.end_run = MagicMock()
    tracker.log_evaluation_result = MagicMock()
    tracker.log_metrics = MagicMock()
    return tracker


@pytest.fixture
def mock_repository():
    """Mock Repository"""
    repository = AsyncMock()
    repository.save_evaluation_result = AsyncMock(return_value="test-result-id-456")
    return repository


@pytest.fixture
def mock_idempotency_checker():
    """Mock Idempotency Checker"""
    from src.models.idempotency import ExecutionDetail, IdempotencyCheckResult

    checker = AsyncMock()
    checker.check_idempotency = AsyncMock(
        return_value=IdempotencyCheckResult(
            is_idempotent=True,
            variance_score=1.0,
            executions=[
                ExecutionDetail(
                    run_number=1,
                    is_safe=False,
                    risk_score=4,
                    exploited_vectors=["Private Data Access"],
                    reasoning="Test",
                    recommendation="Test",
                )
            ],
            message="High consistency",
        )
    )
    return checker


@pytest.fixture
def mock_test_case():
    """Mock Test Case"""
    return TestCaseScenario(
        id="TEST-LT-001",
        name="Test Case",
        description="Test description for evaluator service unit test",
        lethal_trifecta_vectors=LethalTrifectaVectors(
            private_data_access=True,
            untrusted_content_exposure=False,
            external_communication=True,
        ),
        input_text="Test attack prompt for evaluation",
        expected_safe_behavior="System should reject the request and not expose any private data",
    )


@pytest.fixture
def evaluator_service(mock_judge_llm, mock_mlflow_tracker, mock_repository):
    """EvaluatorService fixture"""
    return EvaluatorService(
        judge_llm=mock_judge_llm,
        mlflow_tracker=mock_mlflow_tracker,
        repository=mock_repository,
    )


class TestEvaluatorService:
    """EvaluatorService tests"""

    @pytest.mark.asyncio
    async def test_evaluate_success(
        self,
        evaluator_service: EvaluatorService,
        mock_test_case: TestCaseScenario,
    ) -> None:
        """評価が正常に実行されること"""
        with patch("src.services.evaluator.load_test_case", return_value=mock_test_case):
            result = await evaluator_service.evaluate(
                test_case_id="TEST-LT-001",
                system_output="Test output",
            )

            assert isinstance(result, EvaluationResult)
            assert result.mlflow_run_id == "test-run-id-123"
            assert result.result_id == "test-result-id-456"
            assert result.test_case_id == "TEST-LT-001"
            assert result.judge_result.risk_score == 4
            assert result.judge_result.is_safe is False

    @pytest.mark.asyncio
    async def test_evaluate_with_idempotency_check(
        self,
        mock_judge_llm,
        mock_mlflow_tracker,
        mock_repository,
        mock_idempotency_checker,
        mock_test_case: TestCaseScenario,
    ) -> None:
        """冪等性チェック付きの評価が正常に実行されること"""
        evaluator = EvaluatorService(
            judge_llm=mock_judge_llm,
            mlflow_tracker=mock_mlflow_tracker,
            repository=mock_repository,
            idempotency_checker=mock_idempotency_checker,
        )

        with patch("src.services.evaluator.load_test_case", return_value=mock_test_case):
            result = await evaluator.evaluate(
                test_case_id="TEST-LT-001",
                system_output="Test output",
                enable_idempotency_check=True,
            )

            assert isinstance(result, EvaluationResult)
            mock_idempotency_checker.check_idempotency.assert_called_once()
            mock_mlflow_tracker.log_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_test_case_not_found(
        self,
        evaluator_service: EvaluatorService,
    ) -> None:
        """テストケースが見つからない場合にエラーが発生すること"""
        from src.utils.test_case_loader import TestCaseNotFoundError

        with patch(
            "src.services.evaluator.load_test_case",
            side_effect=TestCaseNotFoundError("Test case not found"),
        ):
            with pytest.raises(TestCaseNotFoundError):
                await evaluator_service.evaluate(
                    test_case_id="INVALID-ID",
                    system_output="Test output",
                )

    @pytest.mark.asyncio
    async def test_evaluate_judge_llm_error(
        self,
        mock_judge_llm,
        mock_mlflow_tracker,
        mock_repository,
        mock_test_case: TestCaseScenario,
    ) -> None:
        """Judge LLM評価でエラーが発生した場合にMLflow Runが終了すること"""
        mock_judge_llm.evaluate = AsyncMock(side_effect=Exception("Judge LLM error"))

        evaluator = EvaluatorService(
            judge_llm=mock_judge_llm,
            mlflow_tracker=mock_mlflow_tracker,
            repository=mock_repository,
        )

        with patch("src.services.evaluator.load_test_case", return_value=mock_test_case):
            with pytest.raises(Exception, match="Judge LLM error"):
                await evaluator.evaluate(
                    test_case_id="TEST-LT-001",
                    system_output="Test output",
                )

            # MLflow Runが FAILED で終了していることを確認
            mock_mlflow_tracker.end_run.assert_called_once_with(status="FAILED")

    @pytest.mark.asyncio
    async def test_run_judge_evaluation(
        self,
        evaluator_service: EvaluatorService,
        mock_test_case: TestCaseScenario,
    ) -> None:
        """Judge評価が正常に実行されること"""
        result = await evaluator_service._run_judge_evaluation(
            test_case=mock_test_case,
            system_output="Test output",
        )

        assert isinstance(result, JudgeResult)
        assert result.risk_score == 4
        assert result.is_safe is False

    @pytest.mark.asyncio
    async def test_save_results(
        self,
        evaluator_service: EvaluatorService,
        mock_judge_llm,
    ) -> None:
        """評価結果が正常に保存されること"""
        judge_result = JudgeResult(
            is_safe=False,
            risk_score=4,
            exploited_vectors=["Private Data Access"],
            reasoning="Test reasoning for evaluation service unit test",
            recommendation="Test recommendation for security improvements",
            judge_model="test",
            judge_provider="test",
        )

        result_id = await evaluator_service._save_results(
            mlflow_run_id="test-run-id",
            test_case_id="TEST-LT-001",
            system_output="Test output",
            judge_result=judge_result,
        )

        assert result_id == "test-result-id-456"

    def test_evaluation_result_to_dict(self) -> None:
        """EvaluationResultが正しく辞書に変換されること"""
        judge_result = JudgeResult(
            is_safe=False,
            risk_score=4,
            exploited_vectors=["Private Data Access"],
            reasoning="Test reasoning for evaluation result conversion",
            recommendation="Test recommendation for security improvements",
            judge_model="test",
            judge_provider="test",
        )

        result = EvaluationResult(
            judge_result=judge_result,
            mlflow_run_id="test-run-id",
            result_id="test-result-id",
            test_case_id="TEST-LT-001",
        )

        result_dict = result.to_dict()

        assert "evaluation" in result_dict
        assert "mlflow_run_id" in result_dict
        assert "result_id" in result_dict
        assert result_dict["mlflow_run_id"] == "test-run-id"
        assert result_dict["result_id"] == "test-result-id"
