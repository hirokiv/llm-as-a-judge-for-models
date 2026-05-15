"""
Tests for environment-based storage optimization (Phase 4)

環境別のデータ保存最適化機能のテスト
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.judge_result import JudgeResult
from src.services.evaluator import EvaluatorService


class TestEnvironmentBasedStorage:
    """環境別データ保存のテスト"""

    @pytest.mark.asyncio
    async def test_save_results_in_production_saves_to_supabase(
        self, evaluator_service, monkeypatch
    ):
        """本番環境ではSupabaseに保存されることを確認"""
        # 環境変数を本番に設定
        monkeypatch.setenv("ENVIRONMENT", "production")

        # Repositoryのモック
        mock_save = AsyncMock(return_value="supabase-result-id-123")
        evaluator_service.repository.save_evaluation_result = mock_save

        # Judge結果のモック
        judge_result = JudgeResult(
            is_safe=True,
            risk_score=1,
            exploited_vectors=[],
            reasoning="Test reasoning",
            recommendation="Test recommendation",
            judge_model="gpt-4",
            judge_provider="openai",
        )

        # 評価結果を保存
        result_id = await evaluator_service._save_results(
            mlflow_run_id="mlflow-run-id-456",
            test_case_id="TEST-LT-001",
            system_output="Test output",
            judge_result=judge_result,
        )

        # Supabaseに保存されたことを確認
        mock_save.assert_called_once()
        assert result_id == "supabase-result-id-123"

    @pytest.mark.asyncio
    async def test_save_results_in_development_skips_supabase(self, evaluator_service, monkeypatch):
        """開発環境ではSupabase保存がスキップされることを確認"""
        # 環境変数を開発環境に設定
        monkeypatch.setenv("ENVIRONMENT", "development")

        # Repositoryのモック
        mock_save = AsyncMock(return_value="supabase-result-id-123")
        evaluator_service.repository.save_evaluation_result = mock_save

        # Judge結果のモック
        judge_result = JudgeResult(
            is_safe=True,
            risk_score=1,
            exploited_vectors=[],
            reasoning="Test reasoning",
            recommendation="Test recommendation",
            judge_model="gpt-4",
            judge_provider="openai",
        )

        # 評価結果を保存
        result_id = await evaluator_service._save_results(
            mlflow_run_id="mlflow-run-id-456",
            test_case_id="TEST-LT-001",
            system_output="Test output",
            judge_result=judge_result,
        )

        # Supabaseに保存されていないことを確認
        mock_save.assert_not_called()
        # MLflow Run IDが返されることを確認
        assert result_id == "mlflow-run-id-456"

    @pytest.mark.asyncio
    async def test_save_results_defaults_to_development_when_env_not_set(
        self, evaluator_service, monkeypatch
    ):
        """環境変数が設定されていない場合はdevelopmentとして扱われることを確認"""
        # 環境変数を削除
        monkeypatch.delenv("ENVIRONMENT", raising=False)

        # Repositoryのモック
        mock_save = AsyncMock(return_value="supabase-result-id-123")
        evaluator_service.repository.save_evaluation_result = mock_save

        # Judge結果のモック
        judge_result = JudgeResult(
            is_safe=True,
            risk_score=1,
            exploited_vectors=[],
            reasoning="Test reasoning",
            recommendation="Test recommendation",
            judge_model="gpt-4",
            judge_provider="openai",
        )

        # 評価結果を保存
        result_id = await evaluator_service._save_results(
            mlflow_run_id="mlflow-run-id-456",
            test_case_id="TEST-LT-001",
            system_output="Test output",
            judge_result=judge_result,
        )

        # Supabaseに保存されていないことを確認（デフォルトはdevelopment）
        mock_save.assert_not_called()
        assert result_id == "mlflow-run-id-456"

    @pytest.mark.asyncio
    async def test_save_results_in_staging_skips_supabase(self, evaluator_service, monkeypatch):
        """ステージング環境ではSupabase保存がスキップされることを確認"""
        # 環境変数をステージングに設定
        monkeypatch.setenv("ENVIRONMENT", "staging")

        # Repositoryのモック
        mock_save = AsyncMock(return_value="supabase-result-id-123")
        evaluator_service.repository.save_evaluation_result = mock_save

        # Judge結果のモック
        judge_result = JudgeResult(
            is_safe=True,
            risk_score=1,
            exploited_vectors=[],
            reasoning="Test reasoning",
            recommendation="Test recommendation",
            judge_model="gpt-4",
            judge_provider="openai",
        )

        # 評価結果を保存
        result_id = await evaluator_service._save_results(
            mlflow_run_id="mlflow-run-id-456",
            test_case_id="TEST-LT-001",
            system_output="Test output",
            judge_result=judge_result,
        )

        # Supabaseに保存されていないことを確認（productionのみ保存）
        mock_save.assert_not_called()
        assert result_id == "mlflow-run-id-456"

    @pytest.mark.asyncio
    async def test_save_results_logs_environment_correctly(
        self, evaluator_service, monkeypatch, caplog
    ):
        """環境変数が正しくログに記録されることを確認"""
        import logging

        caplog.set_level(logging.INFO)

        # 環境変数を本番に設定
        monkeypatch.setenv("ENVIRONMENT", "production")

        # Repositoryのモック
        mock_save = AsyncMock(return_value="supabase-result-id-123")
        evaluator_service.repository.save_evaluation_result = mock_save

        # Judge結果のモック
        judge_result = JudgeResult(
            is_safe=True,
            risk_score=1,
            exploited_vectors=[],
            reasoning="Test reasoning",
            recommendation="Test recommendation",
            judge_model="gpt-4",
            judge_provider="openai",
        )

        # 評価結果を保存
        await evaluator_service._save_results(
            mlflow_run_id="mlflow-run-id-456",
            test_case_id="TEST-LT-001",
            system_output="Test output",
            judge_result=judge_result,
        )

        # ログに環境が記録されていることを確認
        assert any("production" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_mlflow_always_saves_regardless_of_environment(
        self, evaluator_service, monkeypatch
    ):
        """MLflowには環境に関係なく常に記録されることを確認"""
        # この動作は_save_results()の前にlog_evaluation_result()で実現されている
        # ここではドキュメント的なテストとして、MLflowへの保存は_save_results()の
        # 責任範囲外であることを確認

        # 開発環境
        monkeypatch.setenv("ENVIRONMENT", "development")

        mock_save = AsyncMock(return_value="supabase-result-id-123")
        evaluator_service.repository.save_evaluation_result = mock_save

        judge_result = JudgeResult(
            is_safe=True,
            risk_score=1,
            exploited_vectors=[],
            reasoning="Test reasoning",
            recommendation="Test recommendation",
            judge_model="gpt-4",
            judge_provider="openai",
        )

        # _save_results()はSupabaseのみを制御
        # MLflowへの保存はlog_evaluation_result()で既に完了している
        result_id = await evaluator_service._save_results(
            mlflow_run_id="mlflow-run-id-456",
            test_case_id="TEST-LT-001",
            system_output="Test output",
            judge_result=judge_result,
        )

        # 開発環境ではSupabase保存がスキップされる
        mock_save.assert_not_called()
        # MLflow Run IDが返される（MLflowには既に保存済み）
        assert result_id == "mlflow-run-id-456"


# Fixtures


@pytest.fixture
def evaluator_service(judge_llm_stub, mlflow_tracker_mock, repository_mock):
    """EvaluatorServiceのフィクスチャ"""

    return EvaluatorService(
        judge_llm=judge_llm_stub,
        mlflow_tracker=mlflow_tracker_mock,
        repository=repository_mock,
    )


@pytest.fixture
def judge_llm_stub():
    """Judge LLMのスタブ"""
    from src.services.judge_llm import JudgeLLMStub

    return JudgeLLMStub()


@pytest.fixture
def mlflow_tracker_mock():
    """MLflow Trackerのモック"""
    mock = MagicMock()
    mock.start_run = MagicMock(return_value="mlflow-run-id-456")
    mock.log_evaluation_result = MagicMock()
    mock.log_prompt = MagicMock()
    mock.log_dataset = MagicMock()
    mock.end_run = MagicMock()
    return mock


@pytest.fixture
def repository_mock():
    """Repositoryのモック"""
    mock = MagicMock()
    mock.save_evaluation_result = AsyncMock(return_value="supabase-result-id-123")
    return mock
