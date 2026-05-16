"""
Supabase Repository implementation for LLM-as-a-Judge

Supabaseを使用したデータアクセス層の実装
"""

import json
from typing import Any

from src.models.idempotency import IdempotencyCheckResult
from src.models.judge_result import JudgeResult
from src.repositories.base import (
    BaseRepository,
    RepositoryConnectionError,
    RepositoryDuplicateError,
    RepositoryError,
)
from supabase import Client, create_client


class SupabaseRepository(BaseRepository):
    """Supabaseを使用したRepository実装"""

    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Args:
            supabase_url: Supabase URL
            supabase_key: Supabase API Key
        """
        try:
            self.client: Client = create_client(supabase_url, supabase_key)
        except Exception as e:
            raise RepositoryConnectionError(f"Failed to connect to Supabase: {e}") from e

    # Evaluation Results CRUD

    async def save_evaluation_result(
        self,
        mlflow_run_id: str,
        test_case_id: str,
        system_output: str,
        judge_result: JudgeResult,
    ) -> str:
        """評価結果を保存"""
        try:
            data = {
                "mlflow_run_id": mlflow_run_id,
                "test_case_id": test_case_id,
                "system_output": system_output,
                "is_safe": judge_result.is_safe,
                "risk_score": judge_result.risk_score,
                "exploited_vectors": judge_result.exploited_vectors,
                "reasoning": judge_result.reasoning,
                "recommendation": judge_result.recommendation,
            }

            response = self.client.table("evaluation_results").insert(data).execute()  # type: ignore[arg-type]

            if not response.data:
                raise RepositoryError("Failed to save evaluation result")

            result_data: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            return str(result_data["id"])

        except Exception as e:
            if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
                raise RepositoryDuplicateError(
                    f"Evaluation result with mlflow_run_id={mlflow_run_id} already exists"
                ) from e
            raise RepositoryError(f"Failed to save evaluation result: {e}") from e

    async def get_evaluation_result(self, result_id: str) -> dict[str, Any] | None:
        """評価結果を取得"""
        try:
            response = (
                self.client.table("evaluation_results").select("*").eq("id", result_id).execute()
            )

            if not response.data:
                return None

            result: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            return result

        except Exception as e:
            raise RepositoryError(f"Failed to get evaluation result: {e}") from e

    async def get_evaluation_result_by_mlflow_run_id(
        self, mlflow_run_id: str
    ) -> dict[str, Any] | None:
        """MLflow Run IDで評価結果を取得"""
        try:
            response = (
                self.client.table("evaluation_results")
                .select("*")
                .eq("mlflow_run_id", mlflow_run_id)
                .execute()
            )

            if not response.data:
                return None

            result: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            return result

        except Exception as e:
            raise RepositoryError(f"Failed to get evaluation result by mlflow_run_id: {e}") from e

    async def list_evaluation_results(
        self,
        test_case_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """評価結果の一覧を取得"""
        try:
            query = self.client.table("evaluation_results").select("*")

            if test_case_id:
                query = query.eq("test_case_id", test_case_id)

            response = (
                query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            )

            results: list[dict[str, Any]] = response.data or []  # type: ignore[assignment]
            return results

        except Exception as e:
            raise RepositoryError(f"Failed to list evaluation results: {e}") from e

    # Idempotency Checks CRUD

    async def save_idempotency_check(
        self,
        input_hash: str,
        model_version_key: str,
        test_case_id: str,
        check_result: IdempotencyCheckResult,
        provider: str,
        model_name: str,
        model_version: str | None,
        temperature: float,
        seed: int | None,
        prompt_version: str,
    ) -> str:
        """冪等性チェック結果を保存"""
        try:
            data = {
                "input_hash": input_hash,
                "model_version_key": model_version_key,
                "test_case_id": test_case_id,
                "provider": provider,
                "model_name": model_name,
                "model_version": model_version,
                "temperature": temperature,
                "seed": seed,
                "prompt_version": prompt_version,
                "is_idempotent": check_result.is_idempotent,
                "variance_score": check_result.variance_score,
                "executions": json.dumps(check_result.executions),
                "message": check_result.message,
            }

            response = self.client.table("idempotency_checks").insert(data).execute()

            if not response.data:
                raise RepositoryError("Failed to save idempotency check")

            result_data: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            return str(result_data["id"])

        except Exception as e:
            if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
                raise RepositoryDuplicateError(
                    f"Idempotency check with model_version_key={model_version_key}, "
                    f"input_hash={input_hash} already exists"
                ) from e
            raise RepositoryError(f"Failed to save idempotency check: {e}") from e

    async def get_idempotency_check(
        self, model_version_key: str, input_hash: str
    ) -> dict[str, Any] | None:
        """冪等性チェック結果を取得"""
        try:
            response = (
                self.client.table("idempotency_checks")
                .select("*")
                .eq("model_version_key", model_version_key)
                .eq("input_hash", input_hash)
                .execute()
            )

            if not response.data:
                return None

            result: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            # JSON文字列をパース
            executions_value = result.get("executions")
            if isinstance(executions_value, str):
                result["executions"] = json.loads(executions_value)

            return result

        except Exception as e:
            raise RepositoryError(f"Failed to get idempotency check: {e}") from e

    async def list_idempotency_checks(
        self,
        test_case_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """冪等性チェック結果の一覧を取得"""
        try:
            query = self.client.table("idempotency_checks").select("*")

            if test_case_id:
                query = query.eq("test_case_id", test_case_id)

            response = (
                query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            )

            results: list[dict[str, Any]] = response.data or []  # type: ignore[assignment]

            # JSON文字列をパース
            for result in results:
                executions_value = result.get("executions")
                if isinstance(executions_value, str):
                    result["executions"] = json.loads(executions_value)

            return results

        except Exception as e:
            raise RepositoryError(f"Failed to list idempotency checks: {e}") from e

    # System Configs CRUD

    async def get_system_config(
        self, config_key: str, environment: str | None = None
    ) -> dict[str, Any] | None:
        """システム設定を取得"""
        try:
            query = (
                self.client.table("system_configs")
                .select("*")
                .eq("config_key", config_key)
                .eq("is_active", True)
            )

            if environment:
                query = query.eq("environment", environment)
            else:
                query = query.eq("environment", "default")

            response = query.execute()

            if not response.data:
                return None

            result: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            return result

        except Exception as e:
            raise RepositoryError(f"Failed to get system config: {e}") from e

    async def list_system_configs(
        self, environment: str | None = None, is_active: bool = True
    ) -> list[dict[str, Any]]:
        """システム設定の一覧を取得"""
        try:
            query = self.client.table("system_configs").select("*")

            if environment:
                query = query.eq("environment", environment)

            if is_active:
                query = query.eq("is_active", True)

            response = query.order("config_key").execute()
            results: list[dict[str, Any]] = response.data or []  # type: ignore[assignment]
            return results

        except Exception as e:
            raise RepositoryError(f"Failed to list system configs: {e}") from e

    async def upsert_system_config(
        self,
        config_key: str,
        value: str,
        value_type: str,
        environment: str = "default",
        description: str | None = None,
        is_active: bool = True,
    ) -> str:
        """システム設定を挿入または更新"""
        try:
            data = {
                "config_key": config_key,
                "value": value,
                "value_type": value_type,
                "environment": environment,
                "description": description,
                "is_active": is_active,
            }

            response = self.client.table("system_configs").upsert(data).execute()  # type: ignore[arg-type]

            if not response.data:
                raise RepositoryError("Failed to upsert system config")

            result_data: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            return str(result_data["id"])

        except Exception as e:
            raise RepositoryError(f"Failed to upsert system config: {e}") from e

    # Target AI Systems CRUD

    async def get_target_ai_system(self, name: str) -> dict[str, Any] | None:
        """ターゲットAIシステム設定を取得"""
        try:
            response = (
                self.client.table("target_ai_systems")
                .select("*")
                .eq("name", name)
                .eq("is_active", True)
                .execute()
            )

            if not response.data:
                return None

            result: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            return result

        except Exception as e:
            raise RepositoryError(f"Failed to get target AI system: {e}") from e

    async def list_target_ai_systems(self, is_active: bool = True) -> list[dict[str, Any]]:
        """ターゲットAIシステム設定の一覧を取得"""
        try:
            query = self.client.table("target_ai_systems").select("*")

            if is_active:
                query = query.eq("is_active", True)

            response = query.order("name").execute()
            results: list[dict[str, Any]] = response.data or []  # type: ignore[assignment]
            return results

        except Exception as e:
            raise RepositoryError(f"Failed to list target AI systems: {e}") from e

    async def upsert_target_ai_system(
        self,
        name: str,
        url: str,
        headers: dict[str, Any],
        request_config: dict[str, Any],
        response_config: dict[str, Any],
        timeout_seconds: int = 30,
        stub_enabled: bool = False,
        stub_responses: dict[str, Any] | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> str:
        """ターゲットAIシステム設定を挿入または更新"""
        try:
            data = {
                "name": name,
                "url": url,
                "headers": json.dumps(headers),
                "request_config": json.dumps(request_config),
                "response_config": json.dumps(response_config),
                "timeout_seconds": timeout_seconds,
                "stub_enabled": stub_enabled,
                "stub_responses": json.dumps(stub_responses or {}),
                "description": description,
                "is_active": is_active,
            }

            response = self.client.table("target_ai_systems").upsert(data).execute()  # type: ignore[arg-type]

            if not response.data:
                raise RepositoryError("Failed to upsert target AI system")

            result_data: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            return str(result_data["id"])

        except Exception as e:
            raise RepositoryError(f"Failed to upsert target AI system: {e}") from e

    # Evaluation Criteria CRUD

    async def get_evaluation_criteria(
        self, name: str, version: str | None = None
    ) -> dict[str, Any] | None:
        """評価基準設定を取得"""
        try:
            query = (
                self.client.table("evaluation_criteria")
                .select("*")
                .eq("name", name)
                .eq("is_active", True)
            )

            if version:
                query = query.eq("version", version)
            else:
                # Get the latest version
                query = query.order("created_at", desc=True).limit(1)

            response = query.execute()

            if not response.data:
                return None

            result: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            return result

        except Exception as e:
            raise RepositoryError(f"Failed to get evaluation criteria: {e}") from e

    async def list_evaluation_criteria(self, is_active: bool = True) -> list[dict[str, Any]]:
        """評価基準設定の一覧を取得"""
        try:
            query = self.client.table("evaluation_criteria").select("*")

            if is_active:
                query = query.eq("is_active", True)

            response = query.order("name").order("version", desc=True).execute()
            results: list[dict[str, Any]] = response.data or []  # type: ignore[assignment]
            return results

        except Exception as e:
            raise RepositoryError(f"Failed to list evaluation criteria: {e}") from e

    async def upsert_evaluation_criteria(
        self,
        name: str,
        version: str,
        hard_rules: list[dict[str, Any]],
        soft_judge_criteria: list[dict[str, Any]],
        risk_score_config: dict[str, Any],
        recommendation_templates: dict[str, Any],
        hard_rules_enabled: bool = False,
        description: str | None = None,
        is_active: bool = True,
    ) -> str:
        """評価基準設定を挿入または更新"""
        try:
            data = {
                "name": name,
                "version": version,
                "hard_rules_enabled": hard_rules_enabled,
                "hard_rules": json.dumps(hard_rules),
                "soft_judge_criteria": json.dumps(soft_judge_criteria),
                "risk_score_config": json.dumps(risk_score_config),
                "recommendation_templates": json.dumps(recommendation_templates),
                "description": description,
                "is_active": is_active,
            }

            response = self.client.table("evaluation_criteria").upsert(data).execute()  # type: ignore[arg-type]

            if not response.data:
                raise RepositoryError("Failed to upsert evaluation criteria")

            result_data: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            return str(result_data["id"])

        except Exception as e:
            raise RepositoryError(f"Failed to upsert evaluation criteria: {e}") from e

    # Test Cases CRUD

    async def get_test_case(self, test_case_id: str) -> dict[str, Any] | None:
        """テストケースを取得"""
        try:
            response = self.client.table("test_cases").select("*").eq("id", test_case_id).execute()

            if not response.data:
                return None

            result: dict[str, Any] = response.data[0]  # type: ignore[assignment]
            return result

        except Exception as e:
            raise RepositoryError(f"Failed to get test case: {e}") from e

    async def list_test_cases(
        self, is_active: bool = True, limit: int = 1000
    ) -> list[dict[str, Any]]:
        """テストケースの一覧を取得"""
        try:
            query = self.client.table("test_cases").select("*")

            # Note: test_casesテーブルにis_activeカラムがない場合はスキップ
            # (初期スキーマではis_activeカラムがないため)

            response = query.order("id").limit(limit).execute()
            results: list[dict[str, Any]] = response.data or []  # type: ignore[assignment]
            return results

        except Exception as e:
            raise RepositoryError(f"Failed to list test cases: {e}") from e

    # Health Check

    async def health_check(self) -> bool:
        """データベース接続の健全性チェック"""
        try:
            # シンプルなクエリでヘルスチェック
            self.client.table("evaluation_results").select("count", count="exact").limit(  # type: ignore[arg-type]
                1
            ).execute()
            return True
        except Exception as e:
            raise RepositoryConnectionError(f"Health check failed: {e}") from e
