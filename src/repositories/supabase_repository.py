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
