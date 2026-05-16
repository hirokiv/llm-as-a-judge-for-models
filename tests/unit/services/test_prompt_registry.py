"""
Tests for MLflow Prompt Registry integration (Phase 2)

プロンプトテンプレートの作成・記録機能のテスト
"""

import pytest

from src.services.judge_llm import OpenAIJudgeLLM
from src.services.rubric_llm_evaluator import RubricLLMEvaluator


class TestJudgeLLMPromptTemplate:
    """Judge LLMのPromptTemplate機能のテスト"""

    def test_create_prompt_template_structure(self):
        """PromptTemplateが正しい構造で作成されることを確認"""
        # OpenAIJudgeLLMの設定
        config = {
            "model": {"provider": "openai", "name": "gpt-4", "version": "0613"},
            "parameters": {"temperature": 0, "max_tokens": 1000, "seed": 42},
            "system_prompt": "あなたはセキュリティ評価の専門家です。",
        }

        # インスタンス作成（OPENAI_API_KEYが必要だが、テストではprompt_template作成のみ）
        try:
            judge_llm = OpenAIJudgeLLM(config)
        except ValueError:
            # APIキーがない場合はスキップ（CI環境対応）
            pytest.skip("OPENAI_API_KEY not available")

        # PromptTemplateが作成されていることを確認
        assert hasattr(judge_llm, "prompt_template")
        assert judge_llm.prompt_template is not None

        # PromptTemplateの構造を確認
        template = judge_llm.prompt_template
        assert "name" in template
        assert "template" in template
        assert "parameters" in template
        assert "version" in template
        assert "metadata" in template

        # 基本的な値を確認
        assert template["name"] == "judge_evaluation_prompt"
        assert template["template"] == config["system_prompt"]
        assert isinstance(template["parameters"], list)
        assert len(template["parameters"]) == 2  # test_case, system_output

    def test_prompt_template_parameters(self):
        """PromptTemplateのパラメータが正しく定義されていることを確認"""
        config = {
            "model": {"provider": "openai", "name": "gpt-4", "version": "0613"},
            "parameters": {"temperature": 0, "max_tokens": 1000, "seed": 42},
            "system_prompt": "Test prompt",
        }

        try:
            judge_llm = OpenAIJudgeLLM(config)
        except ValueError:
            pytest.skip("OPENAI_API_KEY not available")

        template = judge_llm.prompt_template
        params = template["parameters"]

        # パラメータの数を確認
        assert len(params) == 2

        # test_caseパラメータを確認
        test_case_param = next((p for p in params if p["name"] == "test_case"), None)
        assert test_case_param is not None
        assert test_case_param["type"] == "object"
        assert "description" in test_case_param

        # system_outputパラメータを確認
        system_output_param = next((p for p in params if p["name"] == "system_output"), None)
        assert system_output_param is not None
        assert system_output_param["type"] == "string"
        assert "description" in system_output_param

    def test_prompt_template_version(self):
        """PromptTemplateのバージョンが正しく生成されることを確認"""
        config = {
            "model": {"provider": "openai", "name": "gpt-4", "version": "0613"},
            "parameters": {"temperature": 0, "max_tokens": 1000, "seed": 42},
            "system_prompt": "Test prompt",
        }

        try:
            judge_llm = OpenAIJudgeLLM(config)
        except ValueError:
            pytest.skip("OPENAI_API_KEY not available")

        template = judge_llm.prompt_template
        version = template["version"]

        # バージョンフォーマットを確認
        assert version.startswith("1.0.0-")
        assert "0613" in version  # モデルバージョンが含まれる

    def test_prompt_template_metadata(self):
        """PromptTemplateのメタデータが正しく設定されることを確認"""
        config = {
            "model": {"provider": "openai", "name": "gpt-4", "version": "0613"},
            "parameters": {"temperature": 0, "max_tokens": 1000, "seed": 42},
            "system_prompt": "Test prompt",
        }

        try:
            judge_llm = OpenAIJudgeLLM(config)
        except ValueError:
            pytest.skip("OPENAI_API_KEY not available")

        template = judge_llm.prompt_template
        metadata = template["metadata"]

        # メタデータの内容を確認
        assert metadata["model"] == "gpt-4"
        assert metadata["model_version"] == "0613"
        assert metadata["temperature"] == 0
        assert metadata["max_tokens"] == 1000
        assert metadata["seed"] == 42
        assert "purpose" in metadata


class TestRubricLLMPromptTemplate:
    """Rubric LLMのPromptTemplate機能のテスト"""

    def test_create_rubric_prompt_template_structure(self, judge_llm_stub):
        """Rubric用PromptTemplateが正しい構造で作成されることを確認"""
        evaluator = RubricLLMEvaluator(judge_llm_stub)

        # PromptTemplateが作成されていることを確認
        assert hasattr(evaluator, "prompt_template")
        assert evaluator.prompt_template is not None

        # PromptTemplateの構造を確認
        template = evaluator.prompt_template
        assert "name" in template
        assert "template" in template
        assert "parameters" in template
        assert "version" in template
        assert "metadata" in template

        # 基本的な値を確認
        assert template["name"] == "rubric_criterion_evaluation_prompt"
        assert isinstance(template["template"], str)
        assert len(template["template"]) > 0

    def test_rubric_prompt_template_parameters(self, judge_llm_stub):
        """Rubric用PromptTemplateのパラメータが正しく定義されていることを確認"""
        evaluator = RubricLLMEvaluator(judge_llm_stub)
        template = evaluator.prompt_template
        params = template["parameters"]

        # パラメータの数を確認
        assert len(params) == 6

        # 必須パラメータが存在することを確認
        param_names = [p["name"] for p in params]
        assert "criterion_name" in param_names
        assert "criterion_description" in param_names
        assert "criterion_requirement" in param_names
        assert "system_output" in param_names
        assert "criterion_type" in param_names
        assert "criterion_points" in param_names

        # 各パラメータがtypeとdescriptionを持つことを確認
        for param in params:
            assert "name" in param
            assert "type" in param
            assert "description" in param

    def test_rubric_prompt_template_content(self, judge_llm_stub):
        """Rubric用PromptTemplateの内容が適切であることを確認"""
        evaluator = RubricLLMEvaluator(judge_llm_stub)
        template = evaluator.prompt_template
        template_text = template["template"]

        # プロンプトに必要な要素が含まれていることを確認
        assert "評価項目" in template_text
        assert "評価内容" in template_text
        assert "システム出力" in template_text
        assert "判定方法" in template_text
        assert "Yes" in template_text
        assert "Partial" in template_text
        assert "No" in template_text

        # パラメータプレースホルダーが含まれていることを確認
        assert "{criterion_name}" in template_text
        assert "{criterion_description}" in template_text
        assert "{system_output}" in template_text
        assert "{criterion_type}" in template_text
        assert "{criterion_points}" in template_text

    def test_rubric_prompt_template_metadata(self, judge_llm_stub):
        """Rubric用PromptTemplateのメタデータが適切であることを確認"""
        evaluator = RubricLLMEvaluator(judge_llm_stub)
        template = evaluator.prompt_template
        metadata = template["metadata"]

        # メタデータの必須フィールドを確認
        assert "model" in metadata
        assert "temperature" in metadata
        assert "purpose" in metadata
        assert "judgment_scale" in metadata

        # judgment_scaleの値を確認
        assert metadata["judgment_scale"] == "3-stage (Yes/Partial/No)"


class TestMLflowTrackerPromptLogging:
    """MLflowTrackerのプロンプト記録機能のテスト"""

    def test_log_prompt_with_valid_template(self, mlflow_tracker_mock):
        """有効なPromptTemplateが正しく記録されることを確認"""
        from src.services.mlflow_tracker import MLflowTrackerService

        tracker = MLflowTrackerService()

        # サンプルのPromptTemplate
        prompt_template = {
            "name": "test_prompt",
            "template": "This is a test prompt with {param1} and {param2}",
            "parameters": [
                {"name": "param1", "type": "string", "description": "First parameter"},
                {"name": "param2", "type": "string", "description": "Second parameter"},
            ],
            "version": "1.0.0",
            "metadata": {"model": "gpt-4", "temperature": 0},
        }

        # プロンプトを記録（エラーが発生しないことを確認）
        try:
            tracker.log_prompt(prompt_template)
        except Exception as e:
            pytest.fail(f"log_prompt raised an exception: {e}")

    def test_log_prompt_with_minimal_template(self, mlflow_tracker_mock):
        """最小限のPromptTemplateが記録されることを確認"""
        from src.services.mlflow_tracker import MLflowTrackerService

        tracker = MLflowTrackerService()

        # 最小限のPromptTemplate
        prompt_template = {
            "name": "minimal_prompt",
            "template": "Minimal template",
            "version": "1.0.0",
        }

        # プロンプトを記録（エラーが発生しないことを確認）
        try:
            tracker.log_prompt(prompt_template)
        except Exception as e:
            pytest.fail(f"log_prompt raised an exception: {e}")

    def test_log_prompt_with_empty_template(self, mlflow_tracker_mock):
        """空のPromptTemplateでもエラーが発生しないことを確認"""
        from src.services.mlflow_tracker import MLflowTrackerService

        tracker = MLflowTrackerService()

        # 空のPromptTemplate
        prompt_template = {}

        # プロンプトを記録（警告ログが出るが、エラーは発生しない）
        try:
            tracker.log_prompt(prompt_template)
        except Exception as e:
            pytest.fail(f"log_prompt raised an exception: {e}")


# Fixtures


@pytest.fixture
def judge_llm_stub():
    """Judge LLMのスタブ"""
    from src.services.judge_llm import JudgeLLMStub

    return JudgeLLMStub()


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
    monkeypatch.setattr(mlflow, "log_artifact", lambda p, **kwargs: None)
    monkeypatch.setattr(mlflow, "active_run", lambda: None)

    # MlflowClient mock
    client_mock = MagicMock()
    monkeypatch.setattr("mlflow.tracking.MlflowClient", lambda tracking_uri: client_mock)
