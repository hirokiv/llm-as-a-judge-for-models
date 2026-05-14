"""
Integration tests for evaluation endpoints

評価エンドポイントの統合テスト
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestRootEndpoints:
    """ルートエンドポイントのテスト"""

    def test_root_endpoint(self):
        """ルートエンドポイントが正常に動作すること"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "LLM-as-a-Judge API"

    def test_health_check(self):
        """ヘルスチェックが正常に動作すること"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestEvaluationEndpoints:
    """評価エンドポイントの統合テスト"""

    @pytest.mark.requires_db
    def test_evaluate_endpoint_success(self):
        """評価実行エンドポイントが正常に動作すること"""
        request_data = {
            "test_case_id": "TEST-LT-001",
            "system_output": "テスト用の出力です。外部URLへのアクセスは拒否します。",
        }

        response = client.post("/api/v1/evaluate", json=request_data)

        # ステータスコードチェック
        assert response.status_code == 200

        # レスポンスボディチェック
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data

        # 評価結果チェック
        evaluation_data = data["data"]
        assert "evaluation" in evaluation_data
        assert "mlflow_run_id" in evaluation_data
        assert "result_id" in evaluation_data

        # Judge Resultの構造チェック
        evaluation = evaluation_data["evaluation"]
        assert "is_safe" in evaluation
        assert "risk_score" in evaluation
        assert "exploited_vectors" in evaluation
        assert "reasoning" in evaluation
        assert "recommendation" in evaluation

        # データ型チェック
        assert isinstance(evaluation["is_safe"], bool)
        assert isinstance(evaluation["risk_score"], int)
        assert 1 <= evaluation["risk_score"] <= 5
        assert isinstance(evaluation["exploited_vectors"], list)
        assert isinstance(evaluation["reasoning"], str)
        assert isinstance(evaluation["recommendation"], str)

    @pytest.mark.requires_db
    def test_evaluate_endpoint_validation_error(self):
        """バリデーションエラーが正しく処理されること"""
        # 不正なリクエスト（必須フィールドなし）
        request_data = {"test_case_id": "TEST-LT-001"}

        response = client.post("/api/v1/evaluate", json=request_data)

        # 422 Unprocessable Entityが返されること
        assert response.status_code == 422

    @pytest.mark.requires_db
    def test_get_evaluation_by_id(self):
        """評価結果IDで取得できること"""
        # 先に評価を実行
        request_data = {
            "test_case_id": "TEST-LT-002",
            "system_output": "テスト用の出力です。",
        }
        create_response = client.post("/api/v1/evaluate", json=request_data)
        assert create_response.status_code == 200

        result_id = create_response.json()["data"]["result_id"]

        # 評価結果を取得
        response = client.get(f"/api/v1/evaluations/{result_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "data" in data

    @pytest.mark.requires_db
    def test_list_evaluations(self):
        """評価結果一覧が取得できること"""
        response = client.get("/api/v1/evaluations")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "data" in data

        results_data = data["data"]
        assert "results" in results_data
        assert "total" in results_data
        assert "limit" in results_data
        assert "offset" in results_data

        assert isinstance(results_data["results"], list)

    @pytest.mark.requires_db
    def test_list_evaluations_with_filter(self):
        """テストケースIDでフィルタできること"""
        response = client.get("/api/v1/evaluations?test_case_id=TEST-LT-001")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.requires_db
    def test_list_evaluations_with_pagination(self):
        """ページネーションが正しく動作すること"""
        response = client.get("/api/v1/evaluations?limit=10&offset=0")
        assert response.status_code == 200

        data = response.json()
        results_data = data["data"]
        assert results_data["limit"] == 10
        assert results_data["offset"] == 0
