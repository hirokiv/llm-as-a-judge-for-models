"""
Tests for MLflow Evaluation Datasets integration (Phase 3)

テストケースのDataset変換・記録機能のテスト
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.models.test_case import TestCaseScenario
from src.utils.test_case_loader import (
    _load_test_cases_from_yaml_file,
    load_all_test_cases,
    load_test_cases_as_dataset,
)


class TestLoadAllTestCases:
    """load_all_test_cases()のテスト"""

    def test_load_all_test_cases_returns_list(self):
        """すべてのテストケースをリストとして返すことを確認"""
        test_cases = load_all_test_cases()

        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        assert all(isinstance(tc, TestCaseScenario) for tc in test_cases)

    def test_load_all_test_cases_contains_expected_ids(self):
        """期待されるテストケースIDが含まれることを確認"""
        test_cases = load_all_test_cases()
        test_case_ids = [tc.id for tc in test_cases]

        # Lethal Trifectaテストケースが含まれることを確認
        assert "TEST-LT-001" in test_case_ids
        assert "TEST-LT-002" in test_case_ids

    def test_load_all_test_cases_each_has_required_fields(self):
        """各テストケースが必須フィールドを持つことを確認"""
        test_cases = load_all_test_cases()

        for tc in test_cases:
            assert tc.id is not None
            assert tc.name is not None
            assert tc.input_text is not None
            assert tc.lethal_trifecta_vectors is not None


class TestLoadTestCasesFromYamlFile:
    """_load_test_cases_from_yaml_file()のテスト"""

    def test_load_from_existing_yaml_file(self):
        """既存のYAMLファイルからテストケースを読み込めることを確認"""
        yaml_file = "config/test_cases/lethal_trifecta.yaml"
        test_cases = _load_test_cases_from_yaml_file(yaml_file)

        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        assert all(isinstance(tc, TestCaseScenario) for tc in test_cases)

    def test_load_from_nonexistent_yaml_file(self):
        """存在しないYAMLファイルからの読み込みでエラーが発生することを確認"""
        yaml_file = "nonexistent_file.yaml"

        with pytest.raises(FileNotFoundError):
            _load_test_cases_from_yaml_file(yaml_file)

    def test_load_from_empty_yaml_file(self):
        """空のYAMLファイルからの読み込みで空リストが返ることを確認"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"test_cases": []}, f)
            temp_file = f.name

        try:
            test_cases = _load_test_cases_from_yaml_file(temp_file)
            assert test_cases == []
        finally:
            Path(temp_file).unlink()

    def test_load_from_yaml_with_multiple_test_cases(self):
        """複数のテストケースを含むYAMLファイルから正しく読み込めることを確認"""
        test_data = {
            "test_cases": [
                {
                    "test_case_id": "TEST-LT-901",
                    "name": "Test Case 1",
                    "input_text": "Test input 1",
                    "expected_safe_behavior": "Should reject",
                    "lethal_trifecta_vectors": {
                        "private_data_access": True,
                        "untrusted_content_exposure": False,
                        "external_communication": False,
                    },
                },
                {
                    "test_case_id": "TEST-LT-902",
                    "name": "Test Case 2",
                    "input_text": "Test input 2",
                    "expected_safe_behavior": "Should accept",
                    "lethal_trifecta_vectors": {
                        "private_data_access": False,
                        "untrusted_content_exposure": True,
                        "external_communication": False,
                    },
                },
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_data, f)
            temp_file = f.name

        try:
            test_cases = _load_test_cases_from_yaml_file(temp_file)
            assert len(test_cases) == 2
            assert test_cases[0].id == "TEST-LT-901"
            assert test_cases[1].id == "TEST-LT-902"
        finally:
            Path(temp_file).unlink()


class TestLoadTestCasesAsDataset:
    """load_test_cases_as_dataset()のテスト"""

    def test_load_all_test_cases_as_dataset(self):
        """すべてのテストケースをDatasetとして読み込めることを確認"""
        try:
            import mlflow  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            pytest.skip("MLflow or pandas not available")

        dataset = load_test_cases_as_dataset()

        assert dataset is not None
        assert dataset.name == "evaluation_test_suite"
        # sourceはオブジェクトなので存在することだけ確認
        assert dataset.source is not None

    def test_load_specific_yaml_as_dataset(self):
        """特定のYAMLファイルをDatasetとして読み込めることを確認"""
        try:
            import mlflow  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            pytest.skip("MLflow or pandas not available")

        yaml_file = "config/test_cases/lethal_trifecta.yaml"
        dataset = load_test_cases_as_dataset(yaml_file=yaml_file)

        assert dataset is not None
        assert dataset.name == "evaluation_test_suite"
        # sourceはオブジェクトなので存在することだけ確認
        assert dataset.source is not None

    def test_dataset_contains_expected_columns(self):
        """DatasetのDataFrameが期待されるカラムを持つことを確認"""
        try:
            import mlflow  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            pytest.skip("MLflow or pandas not available")

        dataset = load_test_cases_as_dataset()

        # DataFrameを取得
        df = dataset._df

        # 期待されるカラムが存在することを確認
        expected_columns = [
            "test_case_id",
            "name",
            "description",
            "input_text",
            "expected_safe_behavior",
            "private_data_access",
            "untrusted_content_exposure",
            "external_communication",
            "created_at",
            "updated_at",
        ]

        for col in expected_columns:
            assert col in df.columns

    def test_dataset_dataframe_has_correct_data_types(self):
        """DatasetのDataFrameが正しいデータ型を持つことを確認"""
        try:
            import mlflow  # noqa: F401
        except ImportError:
            pytest.skip("MLflow not available")

        dataset = load_test_cases_as_dataset()
        df = dataset._df

        # データ型を確認
        assert df["test_case_id"].dtype == "object"  # string
        assert df["name"].dtype == "object"  # string
        assert df["private_data_access"].dtype == "bool"
        assert df["untrusted_content_exposure"].dtype == "bool"
        assert df["external_communication"].dtype == "bool"

    def test_dataset_with_custom_name(self):
        """カスタム名でDatasetを作成できることを確認"""
        try:
            import mlflow  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            pytest.skip("MLflow or pandas not available")

        custom_name = "custom_test_suite"
        dataset = load_test_cases_as_dataset(name=custom_name)

        assert dataset.name == custom_name

    def test_dataset_with_custom_targets(self):
        """カスタムターゲットでDatasetを作成できることを確認"""
        try:
            import mlflow  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            pytest.skip("MLflow or pandas not available")

        custom_targets = "private_data_access"
        dataset = load_test_cases_as_dataset(targets=custom_targets)

        # targetsプロパティが存在するか確認
        assert hasattr(dataset, "_targets")

    def test_load_dataset_without_mlflow_raises_error(self, monkeypatch):
        """MLflowがない環境でエラーが発生することを確認"""
        # MLFLOWAVAILABLEをFalseに設定
        from src.utils import test_case_loader

        monkeypatch.setattr(test_case_loader, "MLFLOW_AVAILABLE", False)

        with pytest.raises(ImportError, match="MLflow and pandas are required"):
            load_test_cases_as_dataset()

    def test_load_dataset_from_empty_yaml_raises_error(self):
        """空のYAMLファイルからDatasetを作成しようとするとエラーが発生することを確認"""
        try:
            import mlflow  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            pytest.skip("MLflow or pandas not available")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"test_cases": []}, f)
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="No test cases found"):
                load_test_cases_as_dataset(yaml_file=temp_file)
        finally:
            Path(temp_file).unlink()


class TestMLflowTrackerDatasetLogging:
    """MLflowTrackerのDataset記録機能のテスト"""

    def test_log_dataset_with_valid_dataset(self, mlflow_tracker_mock):
        """有効なDatasetが正しく記録されることを確認"""
        try:
            import mlflow  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            pytest.skip("MLflow or pandas not available")

        from src.services.mlflow_tracker import MLflowTrackerService

        tracker = MLflowTrackerService()
        dataset = load_test_cases_as_dataset()

        # Datasetを記録（エラーが発生しないことを確認）
        try:
            tracker.log_dataset(dataset, context="evaluation")
        except Exception as e:
            pytest.fail(f"log_dataset raised an exception: {e}")

    def test_log_dataset_with_custom_context(self, mlflow_tracker_mock):
        """カスタムコンテキストでDatasetが記録されることを確認"""
        try:
            import mlflow  # noqa: F401
            import pandas  # noqa: F401
        except ImportError:
            pytest.skip("MLflow or pandas not available")

        from src.services.mlflow_tracker import MLflowTrackerService

        tracker = MLflowTrackerService()
        dataset = load_test_cases_as_dataset()

        # カスタムコンテキストでDatasetを記録
        try:
            tracker.log_dataset(dataset, context="training")
        except Exception as e:
            pytest.fail(f"log_dataset raised an exception: {e}")

    def test_log_dataset_without_dataframe_attribute(self, mlflow_tracker_mock):
        """DataFrameを持たないDatasetでもエラーが発生しないことを確認"""
        from unittest.mock import MagicMock

        from src.services.mlflow_tracker import MLflowTrackerService

        tracker = MLflowTrackerService()

        # DataFrameを持たないDatasetをモック
        mock_dataset = MagicMock()
        mock_dataset.name = "mock_dataset"
        mock_dataset.source = "mock_source"
        delattr(mock_dataset, "_df")  # _df属性を削除

        # Datasetを記録（警告ログが出るが、エラーは発生しない）
        try:
            tracker.log_dataset(mock_dataset, context="evaluation")
        except Exception as e:
            pytest.fail(f"log_dataset raised an exception: {e}")


# Fixtures


@pytest.fixture
def mlflow_tracker_mock(monkeypatch):
    """MLflow関連の関数をモック化"""
    from unittest.mock import MagicMock

    import mlflow

    # Experiment mock
    experiment_mock = MagicMock()
    experiment_mock.experiment_id = "test-experiment-id"

    # MLflow関数をモック化
    monkeypatch.setattr(mlflow, "set_tracking_uri", lambda uri: None)
    monkeypatch.setattr(mlflow, "get_experiment_by_name", lambda name: experiment_mock)
    monkeypatch.setattr(mlflow, "create_experiment", lambda name: "test-experiment-id")
    monkeypatch.setattr(mlflow, "log_param", lambda k, v: None)
    monkeypatch.setattr(mlflow, "log_metric", lambda k, v: None)
    monkeypatch.setattr(mlflow, "log_input", lambda dataset, context: None)
    monkeypatch.setattr(mlflow, "active_run", lambda: None)

    # MlflowClient mock
    client_mock = MagicMock()
    monkeypatch.setattr("mlflow.tracking.MlflowClient", lambda tracking_uri: client_mock)
