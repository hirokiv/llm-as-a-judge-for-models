"""
Unit tests for MLflow Tracker Service

MLflow Tracker Serviceの単体テスト
"""

from unittest.mock import Mock, patch

from src.models.judge_result import JudgeResult
from src.models.test_case import LethalTrifectaVectors, TestCaseScenario
from src.services.mlflow_tracker import MLflowTrackerService, get_mlflow_tracker


class TestMLflowTrackerService:
    """MLflow Tracker Serviceのテスト"""

    @patch("src.services.mlflow_tracker.mlflow")
    @patch("src.services.mlflow_tracker.MlflowClient")
    def test_initialization(self, mock_client, mock_mlflow):
        """MLflow trackerが正しく初期化されること"""
        # Mock experiment
        mock_experiment = Mock()
        mock_experiment.experiment_id = "test-exp-123"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment

        tracker = MLflowTrackerService(
            tracking_uri="http://localhost:5000",
            experiment_name="test-experiment",
        )

        assert tracker.tracking_uri == "http://localhost:5000"
        assert tracker.experiment_name == "test-experiment"
        assert tracker.experiment_id == "test-exp-123"

        mock_mlflow.set_tracking_uri.assert_called_once_with("http://localhost:5000")
        mock_mlflow.get_experiment_by_name.assert_called_once_with("test-experiment")

    @patch("src.services.mlflow_tracker.mlflow")
    @patch("src.services.mlflow_tracker.MlflowClient")
    def test_create_new_experiment(self, mock_client, mock_mlflow):
        """存在しない実験が作成されること"""
        mock_mlflow.get_experiment_by_name.return_value = None
        mock_mlflow.create_experiment.return_value = "new-exp-456"

        tracker = MLflowTrackerService(
            tracking_uri="http://localhost:5000",
            experiment_name="new-experiment",
        )

        assert tracker.experiment_id == "new-exp-456"
        mock_mlflow.create_experiment.assert_called_once_with("new-experiment")

    @patch("src.services.mlflow_tracker.mlflow")
    @patch("src.services.mlflow_tracker.MlflowClient")
    def test_start_run(self, mock_client, mock_mlflow):
        """MLflow Runが正しく開始されること"""
        # Setup
        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp-123"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment

        mock_run = Mock()
        mock_run.info.run_id = "run-abc123"
        mock_mlflow.start_run.return_value = mock_run

        tracker = MLflowTrackerService()

        # Execute
        run_id = tracker.start_run(
            run_name="test-run",
            tags={"key": "value"},
        )

        # Assert
        assert run_id == "run-abc123"
        mock_mlflow.start_run.assert_called_once_with(
            experiment_id="exp-123",
            run_name="test-run",
            tags={"key": "value"},
        )

    @patch("src.services.mlflow_tracker.mlflow")
    @patch("src.services.mlflow_tracker.MlflowClient")
    def test_end_run(self, mock_client, mock_mlflow):
        """MLflow Runが正しく終了されること"""
        # Setup
        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp-123"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment

        mock_active_run = Mock()
        mock_active_run.info.run_id = "run-abc123"
        mock_mlflow.active_run.return_value = mock_active_run

        tracker = MLflowTrackerService()

        # Execute
        tracker.end_run(status="FINISHED")

        # Assert
        mock_mlflow.end_run.assert_called_once_with(status="FINISHED")

    @patch("src.services.mlflow_tracker.mlflow")
    @patch("src.services.mlflow_tracker.MlflowClient")
    def test_log_params(self, mock_client, mock_mlflow):
        """パラメータが正しくロギングされること"""
        # Setup
        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp-123"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment

        tracker = MLflowTrackerService()

        # Execute
        tracker.log_params(
            {
                "param1": "value1",
                "param2": 123,
            }
        )

        # Assert
        assert mock_mlflow.log_param.call_count == 2
        mock_mlflow.log_param.assert_any_call("param1", "value1")
        mock_mlflow.log_param.assert_any_call("param2", 123)

    @patch("src.services.mlflow_tracker.mlflow")
    @patch("src.services.mlflow_tracker.MlflowClient")
    def test_log_metrics(self, mock_client, mock_mlflow):
        """メトリクスが正しくロギングされること"""
        # Setup
        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp-123"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment

        tracker = MLflowTrackerService()

        # Execute
        tracker.log_metrics(
            {
                "metric1": 1.5,
                "metric2": 0.8,
            }
        )

        # Assert
        assert mock_mlflow.log_metric.call_count == 2
        mock_mlflow.log_metric.assert_any_call("metric1", 1.5)
        mock_mlflow.log_metric.assert_any_call("metric2", 0.8)

    @patch("src.services.mlflow_tracker.mlflow")
    @patch("src.services.mlflow_tracker.MlflowClient")
    def test_log_tags(self, mock_client, mock_mlflow):
        """タグが正しくロギングされること"""
        # Setup
        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp-123"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment

        tracker = MLflowTrackerService()

        # Execute
        tracker.log_tags(
            {
                "tag1": "value1",
                "tag2": "value2",
            }
        )

        # Assert
        mock_mlflow.set_tags.assert_called_once_with(
            {
                "tag1": "value1",
                "tag2": "value2",
            }
        )

    @patch("src.services.mlflow_tracker.mlflow")
    @patch("src.services.mlflow_tracker.MlflowClient")
    def test_log_evaluation_result(self, mock_client, mock_mlflow):
        """評価結果が正しくロギングされること"""
        # Setup
        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp-123"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment

        tracker = MLflowTrackerService()

        test_case = TestCaseScenario(
            id="TEST-LT-001",
            name="Test Case",
            description="Description",
            input_text="Input",
            expected_safe_behavior="Safe",
            lethal_trifecta_vectors=LethalTrifectaVectors(
                private_data_access=True,
                untrusted_content_exposure=True,
                external_communication=False,
            ),
        )

        judge_result = JudgeResult(
            is_safe=False,
            risk_score=3,
            exploited_vectors=["Private Data Access"],
            reasoning="Test reasoning",
            recommendation="Test recommendation",
            judge_model="stub",
            judge_provider="stub",
        )

        system_output = "Test system output"

        # Execute
        tracker.log_evaluation_result(
            test_case=test_case,
            judge_result=judge_result,
            system_output=system_output,
        )

        # Assert - パラメータがロギングされたこと
        assert mock_mlflow.log_param.call_count == 7
        mock_mlflow.log_param.assert_any_call("test_case_id", "TEST-LT-001")
        mock_mlflow.log_param.assert_any_call("test_case_name", "Test Case")
        mock_mlflow.log_param.assert_any_call("judge_model", "stub")
        mock_mlflow.log_param.assert_any_call("judge_provider", "stub")

        # Assert - メトリクスがロギングされたこと
        assert mock_mlflow.log_metric.call_count == 3
        mock_mlflow.log_metric.assert_any_call("risk_score", 3.0)
        mock_mlflow.log_metric.assert_any_call("is_safe", 0.0)
        mock_mlflow.log_metric.assert_any_call("exploited_vectors_count", 1.0)

        # Assert - タグがロギングされたこと
        mock_mlflow.set_tags.assert_called_once()

        # Assert - アーティファクトがロギングされたこと
        assert mock_mlflow.log_artifact.call_count == 3


class TestGetMLflowTracker:
    """get_mlflow_tracker ファクトリー関数のテスト"""

    @patch("src.services.mlflow_tracker.mlflow")
    @patch("src.services.mlflow_tracker.MlflowClient")
    def test_get_mlflow_tracker(self, mock_client, mock_mlflow):
        """MLflow trackerインスタンスが取得できること"""
        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp-123"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment

        tracker = get_mlflow_tracker()

        assert isinstance(tracker, MLflowTrackerService)
        assert tracker.experiment_name == "llm-judge-evaluations"
